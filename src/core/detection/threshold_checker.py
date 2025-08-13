"""This module contains the ThresholdChecker class, which is responsible for detecting safety car events
based on various criteria."""

import logging
import time

from collections import deque
from dataclasses import dataclass, field
from enum import Enum

from core.detection.detector import DetectorEventTypes
from core.detection.detector_common_types import DetectionResult

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
            DetectorEventTypes.RANDOM: 1.0,
            DetectorEventTypes.STOPPED: 2.0,
        }
    ) 
    event_type_threshold: dict = field(
        default_factory=lambda: {
            DetectorEventTypes.OFF_TRACK: 4,
            DetectorEventTypes.RANDOM: 1.0,
            DetectorEventTypes.STOPPED: 2,
        }
    ) 

    @staticmethod
    def from_settings(settings):
        return ThresholdCheckerSettings(
            time_range=10.0,
            event_type_threshold={
                DetectorEventTypes.OFF_TRACK: float(settings["settings"]["off_min"]),
                DetectorEventTypes.RANDOM: 1.0,
                DetectorEventTypes.STOPPED: float(settings["settings"]["stopped_min"]),
            },
        )

class ThresholdChecker:
    """The ThresholdChecker class is responsible to provide a signal for when a safety car event needs to
        be triggered.
    In order to do so, we track per event type which drivers have triggered that event and when.

    The overall design is to:
    * clean up any events outside the time range specified
    * register any new events occurred in the current generator loop
    * check if the accumulative or specific event type thresholds are met

    Because we do not want to count the same event multiple times, we will only count the most
    recent event for each driver. We therefore keep a dict per event type with the driver ID as key
    and the number of times the event was registered as value. We use the number of unique keys per
    event type to calculate if a threshold has been met.

    A queue is used to track the events in a FIFO manner, allowing us to efficiently update the
    dicts when events drop off outside of the time range. When the count for a driver reaches 0, we
    know we need to remove them from the dict.

    Args:
        settings (ThresholdCheckerSettings): Settings for the ThresholdChecker.
    """

    def __init__(self, settings: ThresholdCheckerSettings):
        logger.info(f"Init ThresholdChecker with settings: {settings}")
        self._settings = settings if settings else ThresholdCheckerSettings()
        self._events_dict = {det: {} for det in DetectorEventTypes} # Initialize dicts for each event type
        self._events_queue = deque()
    
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
            event_time, event_type, driver_id = self._events_queue.popleft()
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

    def register_event(self, event_type: DetectorEventTypes, driver_id: int, event_time: float = time.time()):
        """Register a new event observation.

        Args:
            event_type (ThresholdCheckerEventTypes): The event type observed.
            driver_id (int): The driver involved.
            event_time (float, optional): The time at which the event was observed. Defaults to current time.
        """
        logger.info(f"Registering event {event_type} for driver {driver_id} at {event_time}")
        count = self._events_dict[event_type].get(driver_id, 0)
        self._events_dict[event_type][driver_id] = count + 1
        self._events_queue.append((event_time, event_type, driver_id))

    def register_events(self, event_type: DetectorEventTypes, driver_ids: list[int]):
        """Like register_event, but now report a list of drivers at once all on the same event_time.

        Args:
            event_type (ThresholdCheckerEventTypes): The event type observed.
            driver_ids (list[int]): The list of driver indexes to register the event for.
            event_time (float, optional): The time at which the events were observed. Defaults to current time.
        """
        event_time = time.time()
        for driver_id in driver_ids:
            self.register_event(event_type, driver_id, event_time)

    def register_detection_result(self, detection_result: DetectionResult) -> None:
        """Register events from a DetectionResult object.

        Args:
            detection_result: A DetectionResult object containing either drivers or detected_flag.
        """
        
        if detection_result.has_drivers():
            # Extract driver indices from Driver objects
            driver_ids = [driver['driver_idx'] for driver in detection_result.drivers]
            self.register_events(detection_result.event_type, driver_ids)
        elif detection_result.has_detected_flag() and detection_result.detected_flag:
            # For events like RANDOM that just have a boolean flag
            # Use a dummy driver index since we don't have specific drivers
            self.register_events(detection_result.event_type, [0])


    def threshold_met(self):
        """ Check if the event threshold is met.

        Returns:
            bool: True if either an individual event type threshold is met or if 
             the weighted sum of event types is over the accumulative threshold.
        """
        # Loop through the event types, checking the per-event thresholds
        # and calculating the weighted sum
        logger.debug(f"Checking threshold, events_dict={self._events_dict}, settings={self._settings}")

        acc = 0
        for det in DetectorEventTypes:
            event_type_count = len(self._events_dict[det])

            # If the specific event threshold is met, return immediately
            if event_type_count >= self._settings.event_type_threshold[det]:
                logger.info(f"Threshold met for event type={det} with event_type_count={event_type_count} and threshold={self._settings.event_type_threshold[det]}")
                return True
            
            acc += event_type_count * self._settings.accumulative_weights[det]

        result = acc >= self._settings.accumulative_threshold
        logger.debug(f"Accumulative result={result} with acc={acc}")
        return result
