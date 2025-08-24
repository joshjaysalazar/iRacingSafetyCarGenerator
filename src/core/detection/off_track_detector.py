import logging
from irsdk import TrkLoc
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.drivers import Drivers

logger = logging.getLogger(__name__)

class OffTrackDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the OffTrackDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.
        """
        self.drivers = drivers

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        # OffTrackDetector can always run - no time or occurrence constraints
        return True

    def detect(self) -> DetectionResult:
        """Detect if any driver is off track.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.

        Returns:
            list: A list of drivers that are off track.
        """
        off_track_drivers = []
        total_drivers = len(self.drivers.current_drivers)
        
        for driver in self.drivers.current_drivers:
            if driver["track_loc"] == TrkLoc.off_track and \
               driver["laps_completed"] >= 0:
               
               # driver is off track and is active in the session
               off_track_drivers.append(driver)
               logger.debug(f"Driver {driver['driver_idx']} is off track at position {driver['lap_distance']:.3f}")
        
        if off_track_drivers:
            logger.info(f"Found {len(off_track_drivers)} off-track drivers out of {total_drivers} total drivers")
        else:
            logger.debug(f"No off-track drivers found ({total_drivers} drivers checked)")
        
        return DetectionResult(DetectorEventTypes.OFF_TRACK, drivers=off_track_drivers)
    