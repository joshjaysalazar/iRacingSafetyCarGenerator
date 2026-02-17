"""This module contains the ThresholdChecker class, which is responsible for detecting safety car events
based on various criteria."""

import logging
import time

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from core.detection.detector import DetectorEventTypes
from core.detection.detector_common_types import DetectionResult
from core.drivers import Driver

logger = logging.getLogger(__name__)
@dataclass(frozen=True)
class ThresholdCheckerSettings:
    """These settings determine when the ThresholdChecker will signal a safety car event.

    Args:
        time_range (int): Time range in seconds to consider for recent events.
        accumulative_threshold (int): This threshold considers the weighted sum of all events to
            trigger a safety car.
        accumulative_weights (dict): Weights for different event types.
        event_type_threshold (dict): The thresholds used to trigger a safety car for individual
            event types.
    """
    time_range: float = 10.0
    accumulative_threshold: float = 10.0
    accumulative_weights: dict = field(
        default_factory=lambda: {
            DetectorEventTypes.OFF_TRACK: 1.0,
            DetectorEventTypes.MEATBALL: 0.0,
            DetectorEventTypes.RANDOM: 0.0, # Random events do not contribute to the accumulative threshold
            DetectorEventTypes.STOPPED: 2.0,
            DetectorEventTypes.TOWING: 0.0,
        }
    )
    event_type_threshold: dict = field(
        default_factory=lambda: {
            DetectorEventTypes.OFF_TRACK: 4.0,
            DetectorEventTypes.MEATBALL: 99999,
            DetectorEventTypes.RANDOM: 1.0,
            DetectorEventTypes.STOPPED: 2.0,
            DetectorEventTypes.TOWING: 99999,
        }
    )
    proximity_yellows_enabled: bool = False
    proximity_yellows_distance: float = 0.05
    dynamic_threshold_enabled: bool = False
    dynamic_threshold_multiplier: float = 1.0
    dynamic_threshold_time: float = 300.0
    
    def __post_init__(self):
        # Ensure RANDOM event type is always present with correct defaults
        self.accumulative_weights[DetectorEventTypes.RANDOM] = 0.0
        self.event_type_threshold[DetectorEventTypes.RANDOM] = 1.0
        # Ensure MEATBALL event type is always present with correct defaults
        self.accumulative_weights.setdefault(DetectorEventTypes.MEATBALL, 0.0)
        self.event_type_threshold.setdefault(DetectorEventTypes.MEATBALL, 99999)
        # Ensure TOWING event type is always present with correct defaults
        self.accumulative_weights.setdefault(DetectorEventTypes.TOWING, 0.0)
        self.event_type_threshold.setdefault(DetectorEventTypes.TOWING, 99999)

    @staticmethod
    def from_settings(settings):
        return ThresholdCheckerSettings(
            time_range=settings.event_time_window_seconds,
            accumulative_threshold=settings.accumulative_threshold,
            accumulative_weights={
                DetectorEventTypes.OFF_TRACK: settings.off_track_weight,
                DetectorEventTypes.MEATBALL: settings.meatball_weight,
                DetectorEventTypes.RANDOM: 0.0, # Random events do not contribute to the accumulative threshold
                DetectorEventTypes.STOPPED: settings.stopped_weight,
                DetectorEventTypes.TOWING: settings.tow_weight,
            },
            event_type_threshold={
                DetectorEventTypes.OFF_TRACK: settings.off_track_cars_threshold,
                DetectorEventTypes.MEATBALL: settings.meatball_cars_threshold,
                DetectorEventTypes.RANDOM: 1.0, # Random does not have a threshold, it is just a flag
                DetectorEventTypes.STOPPED: settings.stopped_cars_threshold,
                DetectorEventTypes.TOWING: settings.tow_cars_threshold,
            },
            proximity_yellows_enabled=settings.proximity_filter_enabled,
            proximity_yellows_distance=settings.proximity_filter_distance_percentage,
            dynamic_threshold_enabled=True,
            dynamic_threshold_multiplier=settings.race_start_threshold_multiplier,
            dynamic_threshold_time=settings.race_start_threshold_multiplier_time_seconds,
        )

class ThresholdChecker:
    """The ThresholdChecker class is responsible to provide a signal for when a safety car event needs to
        be triggered.
    In order to do so, we track per event type which drivers have triggered that event and when.

    The overall design is to:
    * clean up any events outside the time range specified
    * register any new events occurred in the current generator loop
    * check if the accumulative or specific event type thresholds are met

    For threshold checking, we use a "cluster first, dedupe after" approach:
    * All events in the queue are used for proximity clustering at their original positions
    * After clustering, each cluster is deduped to keep only the latest event per (driver, event_type)
    * This ensures events are clustered at the position where they originally occurred, even if the
      driver has since moved (e.g., towed to pit road)

    A queue is used to track the events in a FIFO manner, allowing us to efficiently update the
    dicts when events drop off outside of the time range. When the count for a driver reaches 0, we
    know we need to remove them from the dict.

    Events store full Driver objects to enable proximity checks and position-based analysis.

    Args:
        settings (ThresholdCheckerSettings): Settings for the ThresholdChecker.
    """

    def __init__(self, settings: ThresholdCheckerSettings):
        logger.info(f"Init ThresholdChecker with settings: {settings}")
        self._settings = settings if settings else ThresholdCheckerSettings()
        self._events_dict = {det: {} for det in DetectorEventTypes} # Initialize dicts for each event type
        self._events_queue = deque()  # Stores (timestamp, event_type, driver_object)
        self.race_start_time = None
    
    def race_started(self, start_time: float):
        """Called when the race starts to set the start time for dynamic threshold calculations.
        
        Args:
            start_time: The time when the race started (from time.time())
        """
        logger.info(f"Race started at {start_time}")
        self.race_start_time = start_time
    
    def clean_up_events(self):
        """Clean up events that are outside the time range.
        
        We keep popping events from our queue until we find one that is within the time range.
        For each event we pop, we update the count of events for the driver in the dict so that
        we can clear the entry once they fall completely out of the time range.
        """
        current_time = time.time()
        while (
            len(self._events_queue) > 0 and
            current_time - self._events_queue[0][0] >= self._settings.time_range
        ):
            event_time, event_type, driver_obj = self._events_queue.popleft()
            driver_id = driver_obj['driver_idx']
            logger.info(f"Cleaning up event {event_type} for driver {driver_id} registered at {event_time}")
            if driver_id in self._events_dict[event_type]:
                count = self._events_dict[event_type][driver_id]
                if count == 1:
                    del self._events_dict[event_type][driver_id]
                else:
                    self._events_dict[event_type][driver_id] = count - 1
            else:
                logger.warning(
                    "Driver %s not found in events_dict for event type %s", driver_id, event_type
                )

    def _register_event(self, event_type: DetectorEventTypes, driver_obj: Driver, event_time: float = time.time()):
        """Register a new event observation.

        Args:
            event_type (DetectorEventTypes): The event type observed.
            driver_obj (Driver): The driver object with positional information.
            event_time (float, optional): The time at which the event was observed. Defaults to current time.
        """
        driver_id = driver_obj['driver_idx']
        logger.info(f"Registering event {event_type} for driver {driver_id} at {event_time}")
        count = self._events_dict[event_type].get(driver_id, 0)
        self._events_dict[event_type][driver_id] = count + 1
        self._events_queue.append((event_time, event_type, driver_obj))

    def _register_events(self, event_type: DetectorEventTypes, driver_objects: list[Driver]):
        """Like _register_event, but now report a list of drivers at once all on the same event_time.

        Args:
            event_type (DetectorEventTypes): The event type observed.
            driver_objects (list[Driver]): The list of driver objects to register the event for.
        """
        event_time = time.time()
        for driver_obj in driver_objects:
            self._register_event(event_type, driver_obj, event_time)

    def register_detection_result(self, detection_result: DetectionResult) -> None:
        """Register events from a DetectionResult object.

        Args:
            detection_result: A DetectionResult object containing either drivers or detected_flag.
        """
        
        if detection_result.has_drivers():
            # Register events with full driver objects
            self._register_events(detection_result.event_type, detection_result.drivers)
        elif detection_result.has_detected_flag() and detection_result.detected_flag:
            # For events like RANDOM that just have a boolean flag
            # Use a dummy driver object since we don't have specific drivers
            dummy_driver = {'driver_idx': 0, 'laps_completed': 0, 'lap_distance': 0.0, 'track_loc': 0}
            self._register_events(detection_result.event_type, [dummy_driver])


    def threshold_met(self):
        """ Check if the event threshold is met.

        Returns:
            bool: True if either an individual event type threshold is met or if 
             the weighted sum of event types is over the accumulative threshold.
        """
        if self.race_start_time is None:
            logger.warning("Threshold checking attempted before race_started() was called. Dynamic thresholds will not work correctly.")
        
        logger.debug(f"Checking threshold, events_dict={self._events_dict}, settings={self._settings}")
        
        # Get proximity clusters (single cluster if proximity disabled)
        clusters = self._get_proximity_clusters()
        
        # Calculate dynamic threshold multiplier once
        dynamic_multiplier = 1.0
        if self._settings.dynamic_threshold_enabled:
            # Use a base threshold of 1.0 to get the multiplier
            dynamic_multiplier = self._calc_dynamic_threshold(1.0)
            
        # Check each cluster against thresholds
        for cluster in clusters:
            if self._cluster_meets_threshold(cluster, dynamic_multiplier):
                return True
                
        return False

    def _get_proximity_clusters(self) -> list:
        """Get proximity clusters of events.

        Uses "cluster first, dedupe after" approach: all events from the queue are clustered
        at their original positions, then each cluster is deduped to keep only the latest
        event per (driver_idx, event_type).

        Returns:
            List of clusters. If proximity is disabled, returns single cluster with all events.
            Each cluster contains (driver_idx, event_type, driver_obj) tuples.
        """
        if not self._events_queue:
            return []

        # Build all events as (timestamp, driver_idx, event_type, driver_obj) tuples
        all_events = []
        for event_time, event_type, driver_obj in self._events_queue:
            driver_idx = driver_obj['driver_idx']
            all_events.append((event_time, driver_idx, event_type, driver_obj))

        logger.debug(f"_get_proximity_clusters: {len(all_events)} total events from queue")

        if not self._settings.proximity_yellows_enabled:
            # Return single cluster with all events, deduped
            cluster = self._dedupe_cluster(all_events)
            return [cluster] if cluster else []

        # Create proximity-based clusters (handles deduping internally)
        return self._create_proximity_clusters(all_events)

    @staticmethod
    def _dedupe_cluster(cluster_events: list) -> list:
        """Deduplicate a cluster to keep only the latest event per (driver_idx, event_type).

        Args:
            cluster_events: List of (timestamp, driver_idx, event_type, driver_obj) tuples

        Returns:
            List of (driver_idx, event_type, driver_obj) tuples with only the latest per key
        """
        latest = {}
        for timestamp, driver_idx, event_type, driver_obj in cluster_events:
            key = (driver_idx, event_type)
            if key not in latest or timestamp > latest[key][0]:
                latest[key] = (timestamp, driver_obj)

        return [(driver_idx, event_type, driver_obj)
                for (driver_idx, event_type), (_, driver_obj) in latest.items()]

    def _create_proximity_clusters(self, all_events: list) -> list:
        """Create proximity clusters from all queue events, then dedupe within each cluster.

        Args:
            all_events: List of (timestamp, driver_idx, event_type, driver_obj) tuples

        Returns:
            List of clusters, where each cluster is a list of (driver_idx, event_type, driver_obj)
        """
        if not all_events:
            return []

        # Extract positions with event info
        events_with_positions = []
        for timestamp, driver_idx, event_type, driver_obj in all_events:
            lap_distance = driver_obj['lap_distance']
            # Normalize if > 1.0 (in case laps are included)
            if lap_distance > 1.0:
                lap_distance = lap_distance % 1
            events_with_positions.append((lap_distance, timestamp, driver_idx, event_type, driver_obj))

        # Sort by lap distance
        events_with_positions.sort(key=lambda x: x[0])
        logger.debug(f"Sorted events with positions: {events_with_positions}")

        # Account for cars near finish line by extending with +1 distances
        extended_events = events_with_positions + [
            (pos + 1, ts, d_idx, e_type, d_obj)
            for pos, ts, d_idx, e_type, d_obj in events_with_positions
            if pos < self._settings.proximity_yellows_distance
        ]
        logger.debug(f"Extended events for proximity clustering: {extended_events}")

        # Find all possible proximity clusters using sliding window
        raw_clusters = []
        current_window = deque()
        for position, timestamp, driver_idx, event_type, driver_obj in extended_events:
            cluster_added = False
            # Remove events outside proximity range from the left
            while (current_window and
                   position - current_window[0][0] > self._settings.proximity_yellows_distance):

                if not cluster_added:
                    # we are about to remove the leftmost event, so save current window as a cluster
                    raw_cluster = [(ts, d_idx, e_type, d_obj) for _, ts, d_idx, e_type, d_obj in current_window]
                    raw_clusters.append(raw_cluster)
                    logger.debug(f"Formed raw proximity cluster with {len(raw_cluster)} events")
                    cluster_added = True

                current_window.popleft()

            # Add current event to window
            current_window.append((position, timestamp, driver_idx, event_type, driver_obj))

        # Add the last window as a cluster if not empty
        if current_window:
            raw_cluster = [(ts, d_idx, e_type, d_obj) for _, ts, d_idx, e_type, d_obj in current_window]
            raw_clusters.append(raw_cluster)
            logger.debug(f"Formed raw proximity cluster with {len(raw_cluster)} events")

        # Dedupe within each cluster
        clusters = [self._dedupe_cluster(raw_cluster) for raw_cluster in raw_clusters]

        logger.debug(f"Created {len(clusters)} proximity clusters from {len(all_events)} events")
        return clusters
        
    def _cluster_meets_threshold(self, cluster: list, dynamic_multiplier: float) -> bool:
        """Check if a proximity cluster meets threshold requirements.
        
        Args:
            cluster: List of (driver_idx, event_type, driver_obj) tuples
            dynamic_multiplier: Pre-calculated dynamic threshold multiplier
            
        Returns:
            True if cluster meets either per-event-type or accumulative thresholds
        """
        logger.debug(f"Checking if cluster meets threshold {cluster}")
        
        # Count events per type in this cluster
        event_counts = {det: 0 for det in DetectorEventTypes}
        for driver_idx, event_type, driver_obj in cluster:
            event_counts[event_type] += 1
            
        # Check per-event-type thresholds
        for det in DetectorEventTypes:
            event_type_count = event_counts[det]
            threshold = self._settings.event_type_threshold[det] * dynamic_multiplier
                
            if event_type_count >= threshold:
                logger.info(f"Cluster threshold met for event type={det} with cluster_count={event_type_count} and threshold={threshold}")
                return True
                
        # Check accumulative threshold
        # Each driver only contributes their highest-weighted event type
        # to avoid double-counting (e.g. a driver both stopped and off-track)
        driver_max_weights: dict[int, float] = {}
        for driver_idx, event_type, driver_obj in cluster:
            weight = self._settings.accumulative_weights.get(event_type, 0.0)
            if driver_idx not in driver_max_weights or weight > driver_max_weights[driver_idx]:
                driver_max_weights[driver_idx] = weight
        acc = sum(driver_max_weights.values())
        acc_threshold = self._settings.accumulative_threshold * dynamic_multiplier
            
        if acc >= acc_threshold:
            logger.info(f"Cluster accumulative threshold met with acc={acc} and threshold={acc_threshold}")
            return True
            
        return False
        
    def _calc_dynamic_threshold(self, base_threshold: float) -> float:
        """Calculate dynamic threshold based on session time.
        
        Args:
            base_threshold: The base threshold value to scale
            
        Returns:
            The dynamically adjusted threshold
        """
        if not self._settings.dynamic_threshold_enabled or self.race_start_time is None:
            return base_threshold
            
        current_time = time.time()
        session_elapsed = current_time - self.race_start_time
        
        # Apply multiplier if within the time window
        if session_elapsed < self._settings.dynamic_threshold_time:
            adjusted = base_threshold * self._settings.dynamic_threshold_multiplier
            logger.debug(f"Dynamic threshold: {base_threshold} * {self._settings.dynamic_threshold_multiplier} = {adjusted} (session time: {session_elapsed}s)")
            return adjusted
        else:
            logger.debug(f"Dynamic threshold: {base_threshold} (no adjustment, session time: {session_elapsed}s)")
            return base_threshold
