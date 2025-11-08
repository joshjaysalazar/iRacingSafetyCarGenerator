import logging
import statistics
from typing import Dict, Optional
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState
from core.drivers import Drivers, Driver

logger = logging.getLogger(__name__)


class PitEntryStatistics:
    """Statistics about observed pit entry locations."""
    def __init__(self):
        self.estimated_location: Optional[float] = None
        self.confidence_interval: Optional[float] = None
        self.observation_count: int = 0

    def __repr__(self):
        if self.estimated_location is None:
            return "PitEntryStatistics(no data)"
        return f"PitEntryStatistics(location={self.estimated_location:.3f}, CI=±{self.confidence_interval:.3f}, n={self.observation_count})"


class TowingDetector:
    """Detects when drivers tow to pit road instead of driving there.

    This detector works by:
    1. Tracking transitions from not on pit road -> on pit road
    2. Recording the lap distance percentage where normal pit entries occur
    3. Detecting anomalous transitions (large delta) as potential tows
    4. Maintaining statistics on pit entry location with confidence intervals
    """

    # Maximum expected delta in lap distance when entering pits normally
    # This accounts for the physical distance between pit entry detection and the pit road flag
    # Setting to 0.05 (5% of track) as a reasonable threshold
    MAX_NORMAL_PIT_ENTRY_DELTA = 0.05

    # Minimum number of observations before we trust our pit entry estimate
    MIN_OBSERVATIONS_FOR_DETECTION = 3

    def __init__(self, drivers: Drivers, max_pit_entry_delta: float = MAX_NORMAL_PIT_ENTRY_DELTA):
        """Initialize the TowingDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.
            max_pit_entry_delta (float): Maximum lap distance delta for normal pit entry.
        """
        self.drivers = drivers
        self.max_pit_entry_delta = max_pit_entry_delta

        # Track previous state for each car
        self.previous_state: Dict[int, Dict] = {}  # car_idx -> {on_pit_road, lap_dist_pct}

        # Track observed pit entry locations (only valid ones)
        self.pit_entry_observations: list[float] = []

        # Statistics
        self.statistics = PitEntryStatistics()

        logger.info(f"TowingDetector initialized with max_pit_entry_delta={max_pit_entry_delta:.3f}")

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        # TowingDetector can always run - no time or occurrence constraints
        return True

    def _calculate_lap_distance_delta(self, prev_dist: float, curr_dist: float) -> float:
        """Calculate the delta in lap distance, accounting for track wrap-around.

        Args:
            prev_dist: Previous lap distance percentage (0.0 to 1.0)
            curr_dist: Current lap distance percentage (0.0 to 1.0)

        Returns:
            Delta in lap distance (always positive, accounts for wrap-around)
        """
        # Simple forward delta
        delta = curr_dist - prev_dist

        # If negative, car crossed start/finish line
        if delta < 0:
            delta += 1.0

        return delta

    def _update_statistics(self):
        """Update pit entry statistics based on current observations."""
        if len(self.pit_entry_observations) == 0:
            self.statistics.estimated_location = None
            self.statistics.confidence_interval = None
            self.statistics.observation_count = 0
            return

        # Use median as it's more robust to outliers
        self.statistics.estimated_location = statistics.median(self.pit_entry_observations)
        self.statistics.observation_count = len(self.pit_entry_observations)

        # Calculate confidence interval using standard deviation
        if len(self.pit_entry_observations) >= 2:
            stdev = statistics.stdev(self.pit_entry_observations)
            self.statistics.confidence_interval = stdev
        else:
            self.statistics.confidence_interval = 0.0

        logger.debug(f"Updated pit entry statistics: {self.statistics}")

    def _is_near_pit_entry(self, lap_dist_pct: float) -> bool:
        """Check if a position is near the estimated pit entry location.

        Args:
            lap_dist_pct: Lap distance percentage to check

        Returns:
            True if near pit entry, False otherwise
        """
        if self.statistics.estimated_location is None:
            return True  # No data yet, be permissive

        # Check if within max_pit_entry_delta of estimated location
        # Account for track wrap-around
        delta_forward = self._calculate_lap_distance_delta(self.statistics.estimated_location, lap_dist_pct)
        delta_backward = self._calculate_lap_distance_delta(lap_dist_pct, self.statistics.estimated_location)

        min_delta = min(delta_forward, delta_backward)

        return min_delta <= self.max_pit_entry_delta

    def detect(self) -> DetectionResult:
        """Detect drivers who likely towed to pits.

        Returns:
            DetectionResult containing list of drivers who likely towed
        """
        towing_drivers = []

        for driver in self.drivers.current_drivers:
            car_idx = driver["driver_idx"]
            current_on_pit = driver["on_pit_road"]
            current_lap_dist = driver["lap_distance"]

            # Skip pace car
            if driver["is_pace_car"]:
                continue

            # Skip if driver hasn't started racing yet
            if driver["laps_completed"] < 0:
                continue

            # Get previous state
            prev_state = self.previous_state.get(car_idx)

            if prev_state is not None:
                prev_on_pit = prev_state["on_pit_road"]
                prev_lap_dist = prev_state["lap_dist_pct"]

                # Check for transition from off pit road -> on pit road
                if not prev_on_pit and current_on_pit:
                    # Calculate delta
                    delta = self._calculate_lap_distance_delta(prev_lap_dist, current_lap_dist)

                    logger.debug(f"Car {driver['car_number']} entered pits: prev={prev_lap_dist:.3f}, curr={current_lap_dist:.3f}, delta={delta:.3f}")

                    # If delta is reasonable, this is a normal pit entry
                    if delta <= self.max_pit_entry_delta:
                        # Add to observations
                        self.pit_entry_observations.append(current_lap_dist)
                        self._update_statistics()
                        logger.info(f"Car {driver['car_number']} normal pit entry at {current_lap_dist:.3f} (delta={delta:.3f})")
                    else:
                        # Large delta suggests towing
                        # But only flag if we have enough data to be confident
                        if len(self.pit_entry_observations) >= self.MIN_OBSERVATIONS_FOR_DETECTION:
                            # Double-check: is this position actually near our estimated pit entry?
                            if not self._is_near_pit_entry(current_lap_dist):
                                towing_drivers.append(driver)
                                logger.warning(f"Car {driver['car_number']} likely TOWED: appeared on pit road at {current_lap_dist:.3f} (delta={delta:.3f}, expected near {self.statistics.estimated_location:.3f})")
                            else:
                                # Near pit entry but large delta - might be going slow, add as observation
                                self.pit_entry_observations.append(current_lap_dist)
                                self._update_statistics()
                                logger.info(f"Car {driver['car_number']} slow pit entry at {current_lap_dist:.3f} (delta={delta:.3f})")
                        else:
                            # Not enough data yet, be conservative and assume it's valid
                            # Don't add to observations though since delta is suspiciously large
                            logger.debug(f"Car {driver['car_number']} large delta pit entry at {current_lap_dist:.3f} (delta={delta:.3f}), but insufficient data to confirm tow")

            # Update previous state
            self.previous_state[car_idx] = {
                "on_pit_road": current_on_pit,
                "lap_dist_pct": current_lap_dist
            }

        if towing_drivers:
            logger.info(f"Found {len(towing_drivers)} drivers who likely towed")

        return DetectionResult(DetectorEventTypes.TOWING, drivers=towing_drivers)

    def get_statistics(self) -> PitEntryStatistics:
        """Get current pit entry statistics for UI display.

        Returns:
            PitEntryStatistics object with current statistics
        """
        return self.statistics
