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
            chance=0.2, start_minute=5, end_minute=15
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
    

def test_detected_events_from_detector_results():
    events = {
        DetectorEventTypes.RANDOM: [1],
        DetectorEventTypes.STOPPED: False,
    }
    detected = BundledDetectedEvents.from_detector_results(events)
    assert isinstance(detected, BundledDetectedEvents)
    assert detected.events == events
