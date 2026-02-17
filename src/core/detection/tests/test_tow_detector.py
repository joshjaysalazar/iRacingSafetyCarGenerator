import time
from unittest.mock import patch

from irsdk import TrkLoc

from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.detection.threshold_checker import ThresholdChecker, ThresholdCheckerSettings
from core.detection.tow_detector import TowDetector
from core.tests.test_utils import MockDrivers, make_driver


# ---------------------------------------------------------------------------
# Unit tests: TowDetector.detect()
# ---------------------------------------------------------------------------

def test_detect_tow_on_track_to_pit_stall():
    """Car on_track in previous frame, in_pit_stall in current → tow detected."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2, lap_distance=0.15)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.on_track, laps_completed=2, lap_distance=0.5)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.event_type == DetectorEventTypes.TOWING
    assert result.has_drivers()
    assert len(result.drivers) == 1
    assert result.drivers[0]["driver_idx"] == 1


def test_detect_tow_off_track_to_pit_stall():
    """Car off_track in previous frame, in_pit_stall in current → tow detected."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2, lap_distance=0.15)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.off_track, laps_completed=2, lap_distance=0.5)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert len(result.drivers) == 1
    assert result.drivers[0]["driver_idx"] == 1


def test_normal_pitstop_not_detected():
    """Car aproaching_pits in previous, in_pit_stall in current → normal pitstop, NOT a tow."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.aproaching_pits, laps_completed=2)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_already_in_pit_stall_not_detected():
    """Car in_pit_stall in both frames → NOT a tow (already parked)."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_previous_on_pit_road_not_detected():
    """Car on pit road in previous frame (driving into pits), in_pit_stall in current → NOT a tow."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=2)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.on_track, on_pit_road=True, laps_completed=2)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_ignores_pace_car():
    """Pace car towing → NOT detected."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=0, is_pace_car=True, track_loc=TrkLoc.in_pit_stall, laps_completed=2)],
        previous=[make_driver(driver_idx=0, is_pace_car=True, track_loc=TrkLoc.on_track, laps_completed=2)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_ignores_negative_laps_completed():
    """Car with laps_completed < 0 → NOT detected (not yet in world)."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall, laps_completed=-1)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.on_track, laps_completed=-1)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_ignores_not_in_world():
    """Car with current track_loc=not_in_world → NOT detected."""
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.not_in_world, laps_completed=2)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.on_track, laps_completed=2)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert result.drivers == []


def test_uses_previous_position_for_clustering():
    """The returned driver object should have the previous lap_distance (incident site),
    not the current pit stall position."""
    incident_distance = 0.5
    pit_stall_distance = 0.15
    drivers = MockDrivers(
        current=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.in_pit_stall,
                             laps_completed=2, lap_distance=pit_stall_distance)],
        previous=[make_driver(driver_idx=1, car_number="42", track_loc=TrkLoc.on_track,
                              laps_completed=2, lap_distance=incident_distance)],
    )
    detector = TowDetector(drivers)
    result = detector.detect()

    assert len(result.drivers) == 1
    assert result.drivers[0]["lap_distance"] == incident_distance


def test_should_run_always_returns_true():
    """TowDetector.should_run() always returns True; enabled/disabled
    is handled by DetectorSettings and build_detector()."""
    drivers = MockDrivers([], [])
    detector = TowDetector(drivers)

    states = [
        DetectorState(0, {}),
        DetectorState(1000, {DetectorEventTypes.TOWING: 5}),
    ]
    for state in states:
        assert detector.should_run(state) is True


# ---------------------------------------------------------------------------
# Threshold integration tests
# ---------------------------------------------------------------------------

def test_tow_triggers_safety_car_with_threshold_1():
    """With tow_cars_threshold=1, a single tow event should trigger safety car."""
    tc = ThresholdChecker(ThresholdCheckerSettings(
        event_type_threshold={
            DetectorEventTypes.TOWING: 1,
            DetectorEventTypes.OFF_TRACK: 99999,
            DetectorEventTypes.MEATBALL: 99999,
            DetectorEventTypes.RANDOM: 99999,
            DetectorEventTypes.STOPPED: 99999,
        },
        dynamic_threshold_enabled=False,
    ))
    tc.race_started(time.time())

    driver = make_driver(driver_idx=1, lap_distance=0.5)
    result = DetectionResult(DetectorEventTypes.TOWING, drivers=[driver])
    tc.register_detection_result(result)

    assert tc.threshold_met() is True


def test_tow_contributes_to_accumulative_threshold():
    """With tow_weight=2.0 and accumulative_threshold=3.0, two tow events should trigger."""
    tc = ThresholdChecker(ThresholdCheckerSettings(
        accumulative_threshold=3.0,
        accumulative_weights={
            DetectorEventTypes.TOWING: 2.0,
            DetectorEventTypes.OFF_TRACK: 0.0,
            DetectorEventTypes.MEATBALL: 0.0,
            DetectorEventTypes.RANDOM: 0.0,
            DetectorEventTypes.STOPPED: 0.0,
        },
        event_type_threshold={
            DetectorEventTypes.TOWING: 99999,
            DetectorEventTypes.OFF_TRACK: 99999,
            DetectorEventTypes.MEATBALL: 99999,
            DetectorEventTypes.RANDOM: 99999,
            DetectorEventTypes.STOPPED: 99999,
        },
        dynamic_threshold_enabled=False,
    ))
    tc.race_started(time.time())

    # Two different drivers towed: 2 * 2.0 = 4.0 >= 3.0
    for idx in range(2):
        driver = make_driver(driver_idx=idx, lap_distance=0.5)
        result = DetectionResult(DetectorEventTypes.TOWING, drivers=[driver])
        tc.register_detection_result(result)

    assert tc.threshold_met() is True


def test_tow_uses_previous_position_in_proximity_cluster():
    """With proximity clustering, a tow at position 0.5 and a stopped car at 0.5
    should cluster together (not at pit stall ~0.15)."""
    tc = ThresholdChecker(ThresholdCheckerSettings(
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.05,
        accumulative_threshold=4.0,
        accumulative_weights={
            DetectorEventTypes.TOWING: 2.0,
            DetectorEventTypes.OFF_TRACK: 0.0,
            DetectorEventTypes.MEATBALL: 0.0,
            DetectorEventTypes.RANDOM: 0.0,
            DetectorEventTypes.STOPPED: 3.0,
        },
        event_type_threshold={
            DetectorEventTypes.TOWING: 99999,
            DetectorEventTypes.OFF_TRACK: 99999,
            DetectorEventTypes.MEATBALL: 99999,
            DetectorEventTypes.RANDOM: 99999,
            DetectorEventTypes.STOPPED: 99999,
        },
        dynamic_threshold_enabled=False,
    ))
    tc.race_started(time.time())

    # Tow event at position 0.5 (previous position, incident site)
    tow_driver = make_driver(driver_idx=1, lap_distance=0.5)
    tc.register_detection_result(DetectionResult(DetectorEventTypes.TOWING, drivers=[tow_driver]))

    # Stopped car at position 0.5 (near the tow)
    stopped_driver = make_driver(driver_idx=2, lap_distance=0.5)
    tc.register_detection_result(DetectionResult(DetectorEventTypes.STOPPED, drivers=[stopped_driver]))

    # Combined: 2.0 (tow) + 3.0 (stopped) = 5.0 >= 4.0 → should trigger
    assert tc.threshold_met() is True
