
from enum import Enum
from typing import Protocol

from core.drivers import Driver


class DetectorEventTypes(Enum):
    """The different events we are tracking."""
    OFF_TRACK = "off_track"
    RANDOM = "random"
    STOPPED = "stopped"

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

class SupportsDetect(Protocol):
    """Protocol for detectors that can detect events."""
    def detect(self) -> DetectionResult:
        ...