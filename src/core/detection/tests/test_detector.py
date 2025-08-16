import pytest

from core.detection.detector_common_types import DetectionResult
from src.core.detection.detector import DetectorSettings
from unittest.mock import MagicMock, patch
from src.core.detection.detector import Detector, DetectorSettings, DetectorEventTypes, BundledDetectedEvents

class DummyDetector:
    def __init__(self, result):
        self.result = result
    def detect(self):
        return self.result
    def should_run(self, state):
        return True

def test_from_settings_valid_input():
    settings = {
        "settings": {
            "random": "1",
            "random_prob": "0.1",
            "start_minute": "10",
            "end_minute": "20",
            "random_max_occ": "3",
            "stopped": "1",
            "off_track": "0",
        }
    }
    ds = DetectorSettings.from_settings(settings)
    assert ds.random_enabled is True
    assert ds.random_chance == 0.1
    assert ds.random_start_minute == 10
    assert ds.random_end_minute == 20
    assert ds.random_max_occ == 3
    assert ds.stopped_enabled is True
    assert ds.off_track_enabled is False

def test_build_detector_enables_correct_detectors():
    drivers = MagicMock()
    settings = DetectorSettings(
        random_enabled=True,
        random_chance=0.2,
        random_start_minute=5,
        random_end_minute=15,
        random_max_occ=2,
        stopped_enabled=True,
        off_track_enabled=False,
    )
    with patch("src.core.detection.detector.RandomDetector") as mock_random, \
            patch("src.core.detection.detector.StoppedDetector") as mock_stopped, \
            patch("src.core.detection.detector.OffTrackDetector") as mock_offtrack:
        detector = Detector.build_detector(settings, drivers)
        assert DetectorEventTypes.RANDOM in detector.detectors
        assert DetectorEventTypes.STOPPED in detector.detectors
        assert DetectorEventTypes.OFF_TRACK not in detector.detectors
        mock_random.assert_called_once_with(
            chance=0.2, start_minute=5, end_minute=15, max_occurrences=2
        )
        mock_stopped.assert_called_once_with(drivers)
        mock_offtrack.assert_not_called()

def test_build_detector_all_enabled():
    drivers = MagicMock()
    settings = DetectorSettings(
        random_enabled=True,
        random_chance=0.3,
        random_start_minute=2,
        random_end_minute=10,
        random_max_occ=1,
        stopped_enabled=True,
        off_track_enabled=True,
    )
    with patch("src.core.detection.detector.RandomDetector") as mock_random, \
            patch("src.core.detection.detector.StoppedDetector") as mock_stopped, \
            patch("src.core.detection.detector.OffTrackDetector") as mock_offtrack:
        detector = Detector.build_detector(settings, drivers)
        assert set(detector.detectors.keys()) == {
            DetectorEventTypes.RANDOM,
            DetectorEventTypes.STOPPED,
            DetectorEventTypes.OFF_TRACK,
        }
        mock_random.assert_called_once()
        mock_stopped.assert_called_once()
        mock_offtrack.assert_called_once()

def test_build_detector_none_enabled():
    drivers = MagicMock()
    settings = DetectorSettings(
        random_enabled=False,
        stopped_enabled=False,
        off_track_enabled=False,
    )
    with patch("src.core.detection.detector.RandomDetector") as mock_random, \
            patch("src.core.detection.detector.StoppedDetector") as mock_stopped, \
            patch("src.core.detection.detector.OffTrackDetector") as mock_offtrack:
        detector = Detector.build_detector(settings, drivers)
        assert detector.detectors == {}
        mock_random.assert_not_called()
        mock_stopped.assert_not_called()
        mock_offtrack.assert_not_called()

def test_detector_detect_calls_all_detectors():
    dummy1 = DummyDetector(result=DetectionResult(
        DetectorEventTypes.STOPPED,
        drivers=[1, 2]
        ))
    dummy2 = DummyDetector(result=DetectionResult(
        DetectorEventTypes.RANDOM,
        detected_flag=True,
        ))
    detectors = {
        DetectorEventTypes.STOPPED: dummy1,
        DetectorEventTypes.RANDOM: dummy2,
    }
    detector = Detector(detectors)
    detector.race_started(0)  # Set start time so detector will run
    result = detector.detect()
    assert isinstance(result, BundledDetectedEvents)
    assert isinstance(result.events[DetectorEventTypes.STOPPED], DetectionResult)
    assert not result.events[DetectorEventTypes.STOPPED].has_detected_flag()
    assert result.events[DetectorEventTypes.STOPPED].has_drivers()
    assert result.events[DetectorEventTypes.STOPPED].drivers== [1, 2]

    assert isinstance(result.events[DetectorEventTypes.RANDOM], DetectionResult)
    assert result.events[DetectorEventTypes.RANDOM].has_detected_flag()
    assert not result.events[DetectorEventTypes.RANDOM].has_drivers()
    assert result.events[DetectorEventTypes.RANDOM].detected_flag == True


# Tests for new functionality
def test_detector_race_started():
    """Test that race_started sets the start time correctly."""
    detectors = {}
    detector = Detector(detectors)
    
    assert detector.start_time is None
    
    start_time = 1234567890.0
    detector.race_started(start_time)
    
    assert detector.start_time == start_time


def test_detector_detect_before_race_started():
    """Test that detect returns empty results before race starts."""
    dummy_detector = DummyDetector(DetectionResult(DetectorEventTypes.RANDOM, detected_flag=True))
    detectors = {DetectorEventTypes.RANDOM: dummy_detector}
    detector = Detector(detectors)
    
    # Don't call race_started - start_time should be None
    result = detector.detect()
    
    assert isinstance(result, BundledDetectedEvents)
    assert result.events == {}  # Should be empty


def test_detector_detect_with_should_run_false():
    """Test that detectors are skipped when should_run returns False."""
    class ShouldNotRunDetector:
        def detect(self):
            return DetectionResult(DetectorEventTypes.RANDOM, detected_flag=True)
        
        def should_run(self, state):
            return False  # Always return False
    
    detector_instance = ShouldNotRunDetector()
    detectors = {DetectorEventTypes.RANDOM: detector_instance}
    detector = Detector(detectors)
    detector.race_started(0)  # Set start time
    
    result = detector.detect()
    
    assert isinstance(result, BundledDetectedEvents)
    # Detector should be skipped, so no results
    assert DetectorEventTypes.RANDOM not in result.events


def test_detector_detect_with_should_run_true():
    """Test that detectors run when should_run returns True."""
    class ShouldRunDetector:
        def detect(self):
            return DetectionResult(DetectorEventTypes.STOPPED, drivers=[{"driver_idx": 1}])
        
        def should_run(self, state):
            return True  # Always return True
    
    detector_instance = ShouldRunDetector()
    detectors = {DetectorEventTypes.STOPPED: detector_instance}
    detector = Detector(detectors)
    detector.race_started(0)  # Set start time
    
    result = detector.detect()
    
    assert isinstance(result, BundledDetectedEvents)
    assert DetectorEventTypes.STOPPED in result.events
    assert result.events[DetectorEventTypes.STOPPED].drivers == [{"driver_idx": 1}]


def test_detector_detect_without_should_run_method():
    """Test that detectors without should_run method always run."""
    class NoShouldRunDetector:
        def detect(self):
            return DetectionResult(DetectorEventTypes.OFF_TRACK, drivers=[{"driver_idx": 2}])
        # No should_run method
    
    detector_instance = NoShouldRunDetector()
    detectors = {DetectorEventTypes.OFF_TRACK: detector_instance}
    detector = Detector(detectors)
    detector.race_started(0)  # Set start time
    
    result = detector.detect()
    
    assert isinstance(result, BundledDetectedEvents)
    assert DetectorEventTypes.OFF_TRACK in result.events
    assert result.events[DetectorEventTypes.OFF_TRACK].drivers == [{"driver_idx": 2}]


def test_detector_detect_mixed_should_run_results():
    """Test detector with mixed should_run results."""
    class ShouldRunDetector:
        def detect(self):
            return DetectionResult(DetectorEventTypes.STOPPED, drivers=[{"driver_idx": 1}])
        def should_run(self, state):
            return True
    
    class ShouldNotRunDetector:
        def detect(self):
            return DetectionResult(DetectorEventTypes.RANDOM, detected_flag=True)
        def should_run(self, state):
            return False
    
    detectors = {
        DetectorEventTypes.STOPPED: ShouldRunDetector(),
        DetectorEventTypes.RANDOM: ShouldNotRunDetector()
    }
    detector = Detector(detectors)
    detector.race_started(0)  # Set start time
    
    result = detector.detect()
    
    assert isinstance(result, BundledDetectedEvents)
    # Only the detector that should run should have results
    assert DetectorEventTypes.STOPPED in result.events
    assert DetectorEventTypes.RANDOM not in result.events


def test_detector_detect_passes_correct_state():
    """Test that detect passes correct DetectorState to should_run."""
    import time
    
    class StateCheckingDetector:
        def __init__(self):
            self.received_state = None
        
        def detect(self):
            return DetectionResult(DetectorEventTypes.RANDOM, detected_flag=True)
        
        def should_run(self, state):
            self.received_state = state
            return True
    
    detector_instance = StateCheckingDetector()
    detectors = {DetectorEventTypes.RANDOM: detector_instance}
    detector = Detector(detectors)
    
    start_time = time.time() - 100  # 100 seconds ago
    detector.race_started(start_time)
    
    # Set some event counts
    detector.safety_car_event_counts = {DetectorEventTypes.RANDOM: 2}
    
    result = detector.detect()
    
    # Verify the state was passed correctly
    state = detector_instance.received_state
    assert state is not None
    assert abs(state.current_time_since_start - 100) < 1  # Should be around 100 seconds
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 2


def test_detected_events_from_detector_results():
    events = {
        DetectorEventTypes.RANDOM: False,
        DetectorEventTypes.STOPPED: [1],
    }
    detected = BundledDetectedEvents.from_detector_results(events)
    assert isinstance(detected, BundledDetectedEvents)
    assert detected.events == events
