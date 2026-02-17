import logging

from irsdk import TrkLoc

from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.drivers import Drivers

logger = logging.getLogger(__name__)


class TowDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the TowDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current and previous state of drivers.
        """
        self.drivers = drivers

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        return True

    def detect(self) -> DetectionResult:
        """Detect cars that have towed to pits (teleported via iRacing's tow interface).

        A tow is identified by a state transition where the car jumps directly to
        in_pit_stall without passing through aproaching_pits — indicating the car
        teleported rather than driving into the pits normally.

        Returns the *previous* driver object so that lap_distance reflects the
        incident location (where the car was before towing), not the pit stall.

        Returns:
            DetectionResult with list of drivers that have towed to pits.
        """
        towing_drivers = []

        for current, previous in zip(self.drivers.current_drivers, self.drivers.previous_drivers):
            if current["is_pace_car"]:
                continue

            if current["laps_completed"] < 0 or current["track_loc"] == TrkLoc.not_in_world:
                logger.debug(
                    f"Skipping car #{current['car_number']} (idx {current['driver_idx']}): "
                    f"laps_completed={current['laps_completed']}, track_loc={current['track_loc']}"
                )
                continue

            # Tow signature: jumped directly to in_pit_stall without going through aproaching_pits
            if (current["track_loc"] == TrkLoc.in_pit_stall
                    and previous["track_loc"] not in (TrkLoc.in_pit_stall, TrkLoc.aproaching_pits)
                    and not previous["on_pit_road"]):
                # Use PREVIOUS driver object — its lap_distance reflects where the
                # incident/tow originated, which is the relevant position for
                # proximity clustering in the threshold checker.
                towing_drivers.append(previous)
                logger.debug(
                    f"Car #{previous['car_number']} (idx {previous['driver_idx']}) "
                    f"towed to pits from track_loc={previous['track_loc']}, "
                    f"lap_distance={previous['lap_distance']:.4f}"
                )

        if towing_drivers:
            logger.info(f"Found {len(towing_drivers)} cars towed to pits")
        else:
            logger.debug("No cars towed to pits")

        return DetectionResult(DetectorEventTypes.TOWING, drivers=towing_drivers)
