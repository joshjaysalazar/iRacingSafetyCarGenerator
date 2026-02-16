"""End-to-end test utilities for replaying NDJSON SDK dumps through the detection pipeline.

This module provides a replay harness that feeds recorded SDK frames through the same
Detector/ThresholdChecker components used by the Generator, enabling deterministic testing
of safety car triggering and wave around logic against real session data.

Usage:
    from core.tests.e2e_utils import DumpReplayer, make_settings

    replayer = DumpReplayer(
        dump_path=Path("docs/dumps/my_recording.ndjson"),
        settings=make_settings(stopped_cars_threshold=3),
    )
    result = replayer.run()
    assert result.total_safety_cars() >= 1
"""

import json
import logging
from copy import deepcopy
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import irsdk

from core.detection.detector import Detector, DetectorSettings
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes
from core.detection.threshold_checker import ThresholdChecker, ThresholdCheckerSettings
from core.drivers import Driver
from core.procedures.wave_arounds import wave_around_type_from_selection, wave_arounds_factory
from core.settings import Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result data classes
# ---------------------------------------------------------------------------

@dataclass
class DetectionLogEntry:
    """Per-frame detection snapshot for debugging."""
    frame_index: int
    timestamp: float
    stopped_drivers: list[int] = field(default_factory=list)
    off_track_drivers: list[int] = field(default_factory=list)
    random_triggered: bool = False
    threshold_met: bool = False


@dataclass
class SafetyCarEvent:
    """Records when and why a safety car was triggered."""
    frame_index: int
    timestamp: float
    reason: str = ""
    wave_commands: list[str] = field(default_factory=list)
    wave_frame_index: Optional[int] = None


@dataclass
class ReplayResult:
    """Aggregated results from a dump replay run."""
    safety_car_events: list[SafetyCarEvent] = field(default_factory=list)
    detection_log: list[DetectionLogEntry] = field(default_factory=list)
    frame_count: int = 0

    def total_safety_cars(self) -> int:
        return len(self.safety_car_events)

    def sc_triggered_at_frame(self, frame_index: int) -> bool:
        return any(sc.frame_index == frame_index for sc in self.safety_car_events)

    def wave_commands_for_sc(self, sc_index: int) -> list[str]:
        """Get wave around commands for the Nth safety car event (0-indexed)."""
        if sc_index < len(self.safety_car_events):
            return self.safety_car_events[sc_index].wave_commands
        return []

    def waved_car_numbers_for_sc(self, sc_index: int) -> list[str]:
        """Get car numbers waved for the Nth safety car event (0-indexed)."""
        commands = self.wave_commands_for_sc(sc_index)
        return [cmd.replace("!w ", "") for cmd in commands]


# ---------------------------------------------------------------------------
# Mock Drivers for replay
# ---------------------------------------------------------------------------

class ReplayDrivers:
    """Lightweight Drivers replacement that updates from dump frames instead of the SDK.

    Maintains the same interface as core.drivers.Drivers so that detectors work unchanged:
    - current_drivers / previous_drivers (double-buffer)
    - session_info with pace_car_idx
    """

    def __init__(self):
        self.current_drivers: list[Driver] = []
        self.previous_drivers: list[Driver] = []
        self.session_info: dict = {"pace_car_idx": -1}

    def update_from_frame(self, frame: dict) -> None:
        """Update driver state from a single NDJSON dump frame.

        Mirrors the logic of Drivers.update() but reads from the dump frame
        instead of the live SDK.
        """
        self.previous_drivers = deepcopy(self.current_drivers)
        self.current_drivers = []

        telemetry = frame["telemetry"]
        driver_info = frame["session_info"]["DriverInfo"]["Drivers"]

        laps_completed = telemetry["CarIdxLapCompleted"]
        laps_started = telemetry["CarIdxLap"]
        lap_distance = telemetry["CarIdxLapDistPct"]
        track_loc = telemetry["CarIdxTrackSurface"]
        on_pit_road = telemetry["CarIdxOnPitRoad"]

        self.session_info = {
            "pace_car_idx": frame["session_info"]["DriverInfo"]["PaceCarIdx"],
        }

        for driver_details in driver_info:
            car_idx = driver_details["CarIdx"]
            self.current_drivers.append({
                "driver_idx": car_idx,
                "car_number": driver_details["CarNumber"],
                "car_class_id": driver_details["CarClassID"],
                "car_class_est_lap_time": driver_details["CarClassEstLapTime"],
                "is_pace_car": driver_details["CarIsPaceCar"] == 1,
                "laps_completed": laps_completed[car_idx],
                "laps_started": laps_started[car_idx],
                "lap_distance": lap_distance[car_idx],
                "total_distance": laps_completed[car_idx] + lap_distance[car_idx],
                "track_loc": track_loc[car_idx],
                "on_pit_road": on_pit_road[car_idx],
            })


# ---------------------------------------------------------------------------
# Settings helper
# ---------------------------------------------------------------------------

def make_settings(**overrides) -> Settings:
    """Create a Settings object for testing, with sensible defaults and per-setting overrides.

    All settings start with their Settings class fallback defaults. Any keyword argument
    matching a Settings property name will override that value.

    Example:
        settings = make_settings(
            stopped_cars_threshold=3,
            off_track_cars_threshold=5,
            wave_arounds_enabled=True,
            laps_before_wave_arounds=1,
            wave_around_rules_index=0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
        )
    """
    # Create a Settings backed by an in-memory ConfigParser (no file I/O).
    # Settings.__init__ reads from a file, but a non-existent path just yields an empty config.
    settings = Settings(config_file="/dev/null")

    # Apply overrides via property setters (which write to the underlying ConfigParser)
    for key, value in overrides.items():
        if not hasattr(settings, key):
            raise ValueError(f"Unknown setting: {key}")
        setattr(settings, key, value)

    return settings


# ---------------------------------------------------------------------------
# Dump Replayer
# ---------------------------------------------------------------------------

class DumpReplayer:
    """Replays an NDJSON SDK dump through the detection pipeline frame-by-frame.

    This replays the same detection logic that Generator._loop() uses:
    1. Update drivers from the frame
    2. Run all enabled detectors
    3. Register results with the ThresholdChecker
    4. Check if threshold is met → record safety car event
    5. Optionally compute wave around commands for each SC

    Args:
        dump_path: Path to the NDJSON dump file.
        settings: A Settings object (use make_settings() to create one).
            If None, default settings are used.
        compute_waves: Whether to compute wave around commands at each SC event.
            Wave arounds are computed at the frame where the SC fires, using
            the current driver state. For more realistic wave timing, see
            compute_waves_after_laps.
        compute_waves_after_laps: If set, wave around commands are computed
            this many laps after the SC lap (matching laps_before_wave_arounds).
            Requires the dump to have enough frames after the SC.

    Usage:
        replayer = DumpReplayer(
            Path("docs/dumps/race_weird_sc_with_lots_of_waves.ndjson"),
            settings=make_settings(stopped_cars_threshold=2),
        )
        result = replayer.run()
        print(f"SCs triggered: {result.total_safety_cars()}")
        for i, sc in enumerate(result.safety_car_events):
            print(f"  SC {i}: frame {sc.frame_index}, waves: {sc.wave_commands}")
    """

    def __init__(
        self,
        dump_path: Path,
        settings: Optional[Settings] = None,
        compute_waves: bool = True,
        compute_waves_after_laps: Optional[int] = None,
    ):
        self.dump_path = Path(dump_path)
        self.settings = settings or make_settings()
        self.compute_waves = compute_waves
        self.compute_waves_after_laps = compute_waves_after_laps

    def _load_frames(self) -> list[dict]:
        """Load all frames from the NDJSON dump file."""
        frames = []
        with open(self.dump_path, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    frames.append(json.loads(line))
        return frames

    @staticmethod
    def _detect_race_active(frame: dict) -> bool:
        """Check if the race is active in this frame.

        Looks for green flag OR SessionState == racing (4), matching the
        Generator's logic which considers both conditions.
        """
        flags = frame["telemetry"].get("SessionFlags", 0)
        state = frame["telemetry"].get("SessionState", 0)
        green_flag = flags & irsdk.Flags.green
        racing = state == irsdk.SessionState.racing
        return bool(green_flag or racing)

    def _get_wave_commands(self, drivers: ReplayDrivers) -> list[str]:
        """Compute wave around commands using current driver state."""
        wave_around_type = wave_around_type_from_selection(
            self.settings.wave_around_rules_index
        )
        wave_func = wave_arounds_factory(wave_around_type)
        return wave_func(
            drivers.current_drivers,
            drivers.session_info["pace_car_idx"],
        )

    def _get_current_lap_from_frame(self, frame: dict) -> int:
        """Get the current max lap from frame telemetry (excluding pit road cars)."""
        laps = frame["telemetry"]["CarIdxLap"]
        on_pit = frame["telemetry"]["CarIdxOnPitRoad"]
        active_laps = [lap for lap, pit in zip(laps, on_pit) if not pit and lap >= 0]
        return max(active_laps) if active_laps else 0

    def run(self) -> ReplayResult:
        """Replay the dump and return results.

        Processes each frame through the detection pipeline, tracking when
        safety cars would trigger and what wave arounds would be sent.
        """
        frames = self._load_frames()
        result = ReplayResult(frame_count=len(frames))

        # Build components from settings (same as Generator.run)
        drivers = ReplayDrivers()
        detector_settings = DetectorSettings.from_settings(self.settings)
        detector = Detector.build_detector(detector_settings, drivers)
        tc_settings = ThresholdCheckerSettings.from_settings(self.settings)
        threshold_checker = ThresholdChecker(tc_settings)

        race_started = False
        start_time = None

        # Track pending wave arounds (SC events waiting for the right lap)
        pending_waves: list[tuple[SafetyCarEvent, int]] = []  # (sc_event, wave_target_lap)

        for i, frame in enumerate(frames):
            frame_time = frame["_metadata"]["epoch"]

            # Patch time.time so ThresholdChecker/Detector use frame timestamps
            with patch("time.time", return_value=frame_time):
                # Update drivers from frame
                drivers.update_from_frame(frame)

                # Detect race start
                if not race_started and self._detect_race_active(frame):
                    race_started = True
                    start_time = frame_time
                    detector.race_started(start_time)
                    threshold_checker.race_started(start_time)
                    logger.debug(f"Race detected as active at frame {i}")
                    continue

                if not race_started:
                    continue

                # Check eligibility window
                elapsed_minutes = (frame_time - start_time) / 60.0
                if elapsed_minutes < self.settings.detection_start_minute:
                    continue
                if elapsed_minutes > self.settings.detection_end_minute:
                    break

                # Run detection cycle
                detector_results = detector.detect()
                threshold_checker.clean_up_events()

                # Build detection log entry
                log_entry = DetectionLogEntry(
                    frame_index=i,
                    timestamp=frame_time,
                )

                for event_type in DetectorEventTypes:
                    detection_result = detector_results.get_events(event_type)
                    if detection_result:
                        threshold_checker.register_detection_result(detection_result)
                        # Log what was detected
                        if detection_result.has_drivers():
                            driver_idxs = [d["driver_idx"] for d in detection_result.drivers]
                            if event_type == DetectorEventTypes.STOPPED:
                                log_entry.stopped_drivers = driver_idxs
                            elif event_type == DetectorEventTypes.OFF_TRACK:
                                log_entry.off_track_drivers = driver_idxs
                        elif detection_result.has_detected_flag() and detection_result.detected_flag:
                            log_entry.random_triggered = True

                # Check threshold
                met, message = threshold_checker.threshold_met()
                if met:
                    log_entry.threshold_met = True

                    sc_event = SafetyCarEvent(
                        frame_index=i,
                        timestamp=frame_time,
                        reason=message or "Threshold met",
                    )

                    if self.compute_waves:
                        if self.compute_waves_after_laps is not None:
                            # Defer wave computation to a later frame
                            lap_at_sc = self._get_current_lap_from_frame(frame)
                            wave_target = lap_at_sc + self.compute_waves_after_laps + 1
                            pending_waves.append((sc_event, wave_target))
                        else:
                            # Compute waves immediately at the SC frame
                            sc_event.wave_commands = self._get_wave_commands(drivers)

                    result.safety_car_events.append(sc_event)

                    # Reset threshold checker for next potential SC
                    threshold_checker = ThresholdChecker(tc_settings)
                    threshold_checker.race_started(start_time)

                result.detection_log.append(log_entry)

                # Process pending wave arounds (check if we've reached the target lap)
                if pending_waves:
                    current_lap = self._get_current_lap_from_frame(frame)
                    still_pending = []
                    for sc_event, wave_target in pending_waves:
                        if current_lap >= wave_target:
                            sc_event.wave_commands = self._get_wave_commands(drivers)
                            sc_event.wave_frame_index = i
                        else:
                            still_pending.append((sc_event, wave_target))
                    pending_waves = still_pending

        return result
