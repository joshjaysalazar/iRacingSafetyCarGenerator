import pytest

from core.detection.off_track_detector import OffTrackDetector
from core.detection.detector_common_types import DetectorState, DetectorEventTypes
from irsdk import TrkLoc

from core.tests.test_utils import MockDrivers, make_driver

def test_detect_off_track_driver():
    drivers = MockDrivers([
        make_driver(TrkLoc.off_track, 1),
        make_driver(TrkLoc.on_track, 2),
        make_driver(TrkLoc.off_track, 0),
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert len(result.drivers) == 2
    assert drivers.current_drivers[0] in result.drivers
    assert drivers.current_drivers[2] in result.drivers

def test_detect_no_off_track_driver():
    drivers = MockDrivers([
        make_driver(TrkLoc.on_track, 1),
        make_driver(TrkLoc.on_track, 1),
        make_driver(TrkLoc.in_pit_stall, 2),
        make_driver(TrkLoc.not_in_world, 3),
        make_driver(TrkLoc.aproaching_pits, 4),
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == []

def test_detect_off_track_driver_negative_laps():
    drivers = MockDrivers([
        make_driver(TrkLoc.off_track, -1),
        make_driver(TrkLoc.off_track, 0),
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert len(result.drivers) == 1
    assert drivers.current_drivers[1] in result.drivers

def test_detect_empty_drivers():
    drivers = MockDrivers([])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result.has_drivers()
    assert result.drivers == []


def test_should_run_always_returns_true():
    """Test that OffTrackDetector should_run always returns True."""
    drivers = MockDrivers([])
    detector = OffTrackDetector(drivers)
    
    # Create various states to test
    states = [
        DetectorState(0, {}),
        DetectorState(1000, {DetectorEventTypes.OFF_TRACK: 5}),
        DetectorState(10000, {DetectorEventTypes.OFF_TRACK: 100}),
    ]
    
    for state in states:
        assert detector.should_run(state) is True