
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Protocol

from core.drivers import Driver


class DetectorEventTypes(Enum):
    """The different events we are tracking."""
    OFF_TRACK = "off_track"
    RANDOM = "random"
    STOPPED = "stopped"
    TOWING = "towing"

class DetectionResult:
    """We are using a wrapper class for our Detector classes because we need to support multiple return types:
    - A list of drivers for events like OFF_TRACK and STOPPED.
    - A boolean for events like RANDOM, which indicates whether the event was detected or not.
    Instead of managing these types across the functions using them, we limit checking against these scenarios 
    to the places where we consume a DetectionResult.
    """
    def __init__(self, event_type: DetectorEventTypes, drivers: list[Driver] = None, detected_flag: bool = None):
        self.event_type: DetectorEventTypes = event_type
        self.drivers: list[Driver] = drivers
        self.detected_flag: bool = detected_flag

    def has_drivers(self) -> bool:
        return self.drivers is not None
    
    def has_detected_flag(self) -> bool:
        return self.detected_flag is not None

@dataclass
class DetectorState:
    """Encapsulates runtime state needed by detectors for decision making."""
    current_time_since_start: float
    safety_car_event_counts: Dict[DetectorEventTypes, int]
    
    def increment_safety_car_event(self, event_type: DetectorEventTypes):
        """Increment the safety car event count for a given event type."""
        self.safety_car_event_counts[event_type] = self.safety_car_event_counts.get(event_type, 0) + 1


class SupportsDetect(Protocol):
    """Protocol for detectors that can detect events."""
    def detect(self) -> DetectionResult:
        ...
    
    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        ...