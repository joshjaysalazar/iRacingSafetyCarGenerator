import pytest

from irsdk import TrkLoc
from core.detection.stopped_detector import StoppedDetector
from core.detection.detector_common_types import DetectorState, DetectorEventTypes
from core.detection.tests.utils import MockDrivers, make_driver


def test_detect_stopped_driver():
    current = [
        make_driver(TrkLoc.on_track, 5, 0.0),  # stopped (same pos)
        make_driver(TrkLoc.on_track, 5, 0.5),  # moving
    ]
    previous = [
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.4),
    ]
    drivers = MockDrivers(current, previous)
    detector = StoppedDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == [current[0]]

def test_detect_skips_pit_and_not_in_world():
    current = [
        make_driver(TrkLoc.aproaching_pits, 5, 0.0),
        make_driver(TrkLoc.in_pit_stall, 5, 0.0),
        make_driver(TrkLoc.not_in_world, 5, 0.0),
    ]
    previous = [
        make_driver(TrkLoc.aproaching_pits, 5, 0.0),
        make_driver(TrkLoc.in_pit_stall, 5, 0.0),
        make_driver(TrkLoc.not_in_world, 5, 0.0),
    ]
    drivers = MockDrivers(current, previous)
    detector = StoppedDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == []

def test_detect_skips_negative_lap_distance():
    current = [
        make_driver(TrkLoc.on_track, 5, -1.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
    ]
    previous = [
        make_driver(TrkLoc.on_track, 5, -1.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
    ]
    drivers = MockDrivers(current, previous)
    detector = StoppedDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == [current[1]]

def test_detect_lag_fix_clears_list():
    current = [
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
    ]
    previous = [
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
    ]
    drivers = MockDrivers(current, previous)
    detector = StoppedDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == []

def test_detect_multiple_stopped():
    current = [
        make_driver(TrkLoc.on_track, 5, 0.0),  # stopped
        make_driver(TrkLoc.on_track, 5, 0.0),  # stopped
        make_driver(TrkLoc.on_track, 5, 0.5),  # moving
    ]
    previous = [
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.0),
        make_driver(TrkLoc.on_track, 5, 0.4),
    ]
    drivers = MockDrivers(current, previous)
    detector = StoppedDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == [current[0], current[1]]


def test_should_run_always_returns_true():
    """Test that StoppedDetector should_run always returns True."""
    drivers = MockDrivers([], [])
    detector = StoppedDetector(drivers)
    
    # Create various states to test
    states = [
        DetectorState(0, {}),
        DetectorState(1000, {DetectorEventTypes.STOPPED: 5}),
        DetectorState(10000, {DetectorEventTypes.STOPPED: 100}),
    ]
    
    for state in states:
        assert detector.should_run(state) is True