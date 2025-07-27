
from dataclasses import dataclass
from enum import Enum

from core.detection.off_track_detector import OffTrackDetector
from core.detection.random_detector import RandomDetector
from core.detection.stopped_detector import StoppedDetector
from core.drivers import Drivers
from typing import Dict, Protocol

class SupportsDetect(Protocol):
    """Protocol for detectors that can detect events."""
    def detect(self) -> list | bool:
        ...

class DetectorEventTypes(Enum):
    """The different events we are tracking."""
    OFF_TRACK = "off_track"
    RANDOM = "random"
    STOPPED = "stopped"
    
class DetectedEvents:
    """Wrapper for detected events from various detectors."""
    def __init__(self, events):
        self.events = events

    @staticmethod
    def from_detector_results(events):
        """Create DetectedEvents from the results of detectors."""
        return DetectedEvents(events)
    
@dataclass(frozen=True)
class DetectorSettings:
    # RandomDetector settings
    random_enabled: bool = False
    random_chance: float = 0.1
    random_start_minute: float = 3
    random_end_minute: float = 30
    random_max_occ: int = 1
    
    # StoppedDetector settings
    stopped_enabled: bool = True
    
    # OffTrackDetector settings
    off_track_enabled: bool = True
    
    @staticmethod
    def from_settings(settings):
        return DetectorSettings(
            random_enabled=settings["settings"]["random"] == "1",
            random_chance=float(settings["settings"]["random_prob"]),
            random_start_minute=float(settings["settings"]["start_minute"]),
            random_end_minute=float(settings["settings"]["end_minute"]),
            random_max_occ=int(settings["settings"]["random_max_occ"]),
            stopped_enabled=settings["settings"]["stopped"] == "1",
            off_track_enabled=settings["settings"]["off_track"] == "1",
        )

    
class Detector:
    def __init__(self, detectors: Dict[DetectorEventTypes, SupportsDetect]):
        self.detectors = detectors 

    @staticmethod
    def build_detector(settings: DetectorSettings, drivers: Drivers):
        """Build the detector with the enabled detectors based on settings.

        Args:
            settings (DetectorSettings): Settings indicating which detectors to enable and their parameters.
            drivers (Drivers): A reference to the Drivers object containing the state of drivers.

        Returns:
            Detector: An instance of Detector with the enabled detectors based on settings.
        """
        detectors = {}
        if settings.random_enabled:
            detectors[DetectorEventTypes.RANDOM] = RandomDetector(
                chance=settings.random_chance,
                start_minute=settings.random_start_minute,
                end_minute=settings.random_end_minute
            )
        if settings.stopped_enabled:
            detectors[DetectorEventTypes.STOPPED] = StoppedDetector(drivers)

        if settings.off_track_enabled:
            detectors[DetectorEventTypes.OFF_TRACK] = OffTrackDetector(drivers)
        
        return Detector(detectors)
    

    def detect(self):
        """Run all detectors and return their results."""
        events = {}
        for event_type, detector in self.detectors.items():
            results = detector.detect()
            events[event_type] = results
            
        return DetectedEvents.from_detector_results(events)