
import logging
import time
from dataclasses import dataclass
from enum import Enum

from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState, SupportsDetect
from core.detection.off_track_detector import OffTrackDetector
from core.detection.random_detector import RandomDetector
from core.detection.stopped_detector import StoppedDetector
from core.drivers import Drivers
from typing import Dict

logger = logging.getLogger(__name__)


class BundledDetectedEvents:
    """Wrapper to bundle up all detected events across different detectors."""
    def __init__(self, events):
        self.events: Dict[DetectorEventTypes, DetectionResult] = events

    @staticmethod
    def from_detector_results(events: Dict[DetectorEventTypes, DetectionResult]) -> "BundledDetectedEvents":
        """Create DetectedEvents from the results of detectors."""
        return BundledDetectedEvents(events)
    
    def get_events(self, event_type: DetectorEventTypes) -> DetectionResult:
        """Get events of a specific type."""
        return self.events.get(event_type, None)
    
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
            off_track_enabled=settings["settings"]["off"] == "1",
        )

    
class Detector:
    def __init__(self, detectors: Dict[DetectorEventTypes, SupportsDetect]):
        self.detectors = detectors
        self.start_time = None
        self.safety_car_event_counts = {event_type: 0 for event_type in DetectorEventTypes}
    
    def race_started(self, start_time: float):
        """Called when the race starts to set the start time for time-based calculations."""
        logger.info(f"Race started at {start_time}, enabled detectors: {list(self.detectors.keys())}")
        self.start_time = start_time 

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
                end_minute=settings.random_end_minute,
                max_occurrences=settings.random_max_occ
            )
        if settings.stopped_enabled:
            detectors[DetectorEventTypes.STOPPED] = StoppedDetector(drivers)

        if settings.off_track_enabled:
            detectors[DetectorEventTypes.OFF_TRACK] = OffTrackDetector(drivers)
        
        return Detector(detectors)
    

    def detect(self) -> BundledDetectedEvents:
        """Run all detectors and return their results."""
        if self.start_time is None:
            logger.debug("Race hasn't started yet, returning empty results")
            return BundledDetectedEvents.from_detector_results({})
            
        # Create detector state
        state = DetectorState(
            current_time_since_start=time.time() - self.start_time,
            safety_car_event_counts=self.safety_car_event_counts
        )
        
        logger.debug(f"Running detection cycle, time since start: {state.current_time_since_start:.1f}s")
        
        events = {}
        for event_type, detector in self.detectors.items():
            # Check if detector should run
            if hasattr(detector, 'should_run') and not detector.should_run(state):
                logger.debug(f"{event_type} detector skipped (should_run=False)")
                continue
                
            # Run detector
            logger.debug(f"Running {event_type} detector")
            result = detector.detect()
            events[event_type] = result
            
            # Log detection results
            if result.has_drivers():
                logger.info(f"{event_type} detector found {len(result.drivers)} drivers")
            elif result.has_detected_flag():
                logger.info(f"{event_type} detector triggered (flag=True)")
            
        logger.debug(f"Detection cycle complete, ran {len(events)} detectors")
        return BundledDetectedEvents.from_detector_results(events)