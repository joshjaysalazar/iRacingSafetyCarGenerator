import logging
from irsdk import TrkLoc
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.drivers import Drivers

logger = logging.getLogger(__name__)

class StoppedDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the StoppedDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current and previous state of drivers.
        """
        self.drivers = drivers

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        # StoppedDetector can always run - no time or occurrence constraints
        return True

    def detect(self):
        """Detect if any driver is stopped.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.

        Returns:
            list: A list of drivers that are stopped.
        """
        
        # Get the indices of the stopped cars
        stopped_cars = []
        skipped_count = 0
        total_drivers = len(self.drivers.current_drivers)
        
        for current, previous in zip(self.drivers.current_drivers, self.drivers.previous_drivers):
            if current["track_loc"] in [TrkLoc.aproaching_pits, 
                                        TrkLoc.in_pit_stall, 
                                        TrkLoc.not_in_world]:
                skipped_count += 1
                continue  # Skip cars that are not driving around

            if current["lap_distance"] < 0:
                skipped_count += 1
                logger.debug(f"Driver {current['driver_idx']} has negative lap distance: {current['lap_distance']}")
                continue # Skip unexpected data
            
            current_position = current["laps_completed"] + current["lap_distance"]
            previous_position = previous["laps_completed"] + previous["lap_distance"]
            if current_position <= previous_position:
                stopped_cars.append(current)
                logger.debug(f"Driver {current['driver_idx']} appears stopped: current={current_position:.3f}, previous={previous_position:.3f}")

        # If length of stopped cars is entire field, clear list (lag fix)
        if len(stopped_cars) >= len(self.drivers.current_drivers) - 1:
            logger.warning(f"Entire field appears stopped ({len(stopped_cars)} cars), clearing list (likely lag)")
            stopped_cars = []

        if stopped_cars:
            logger.info(f"Found {len(stopped_cars)} stopped drivers out of {total_drivers - skipped_count} active drivers")
        else:
            logger.debug(f"No stopped drivers found ({total_drivers - skipped_count} active drivers checked, {skipped_count} skipped)")

        return DetectionResult(DetectorEventTypes.STOPPED, drivers=stopped_cars)
    