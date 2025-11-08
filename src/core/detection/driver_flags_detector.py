import logging
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.drivers import Drivers

logger = logging.getLogger(__name__)

# iRacing session flags (from irsdk Flags class)
# These are the flags that indicate a driver needs attention
FLAG_BLACK = 0x010000      # Disqualification signal
FLAG_DISQUALIFY = 0x020000 # Driver removed from race
FLAG_SERVICIBLE = 0x040000 # Vehicle permitted pit service (not sure if this is useful)
FLAG_FURLED = 0x080000     # Meatball flag indicating mechanical issues
FLAG_REPAIR = 0x100000     # Structural damage requiring attention

# We're interested in furled (meatball) and repair flags as they indicate damage
DAMAGE_FLAGS = FLAG_FURLED | FLAG_REPAIR


class DriverFlagsDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the DriverFlagsDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.
        """
        self.drivers = drivers

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        # DriverFlagsDetector can always run - no time or occurrence constraints
        return True

    def detect(self) -> DetectionResult:
        """Detect if any driver has damage flags set (meatball or repair flags).

        Returns:
            DetectionResult: A detection result containing drivers with damage flags.
        """
        flagged_drivers = []
        total_drivers = len(self.drivers.current_drivers)

        for driver in self.drivers.current_drivers:
            # Skip pace car
            if driver["is_pace_car"]:
                continue

            # Skip drivers not active in session
            if driver["laps_completed"] < 0:
                continue

            session_flags = driver["session_flags"]

            # Check if driver has any damage flags
            if session_flags & DAMAGE_FLAGS:
                flagged_drivers.append(driver)

                # Log which specific flags are set for debugging
                flags_set = []
                if session_flags & FLAG_FURLED:
                    flags_set.append("FURLED/MEATBALL")
                if session_flags & FLAG_REPAIR:
                    flags_set.append("REPAIR")
                if session_flags & FLAG_BLACK:
                    flags_set.append("BLACK")
                if session_flags & FLAG_DISQUALIFY:
                    flags_set.append("DISQUALIFY")

                logger.debug(
                    f"Driver {driver['driver_idx']} (#{driver['car_number']}) has damage flags: {', '.join(flags_set)} "
                    f"(flags=0x{session_flags:08x})"
                )

        if flagged_drivers:
            logger.info(
                f"Found {len(flagged_drivers)} drivers with damage flags out of {total_drivers} total drivers"
            )
        else:
            logger.debug(f"No drivers with damage flags found ({total_drivers} drivers checked)")

        return DetectionResult(DetectorEventTypes.DRIVER_FLAGS, drivers=flagged_drivers)
