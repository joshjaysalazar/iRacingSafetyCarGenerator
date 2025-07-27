import pytest

from core.detection.off_track_detector import OffTrackDetector
from irsdk import TrkLoc

class MockDrivers:
    def __init__(self, current_drivers):
        self.current_drivers = current_drivers

def test_detect_off_track_driver():
    drivers = MockDrivers([
        {"track_loc": TrkLoc.off_track, "laps_completed": 1},
        {"track_loc": TrkLoc.on_track, "laps_completed": 2},
        {"track_loc": TrkLoc.off_track, "laps_completed": 0},
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert len(result) == 2
    assert drivers.current_drivers[0] in result
    assert drivers.current_drivers[2] in result

def test_detect_no_off_track_driver():
    drivers = MockDrivers([
        {"track_loc": TrkLoc.on_track, "laps_completed": 1},
        {"track_loc": TrkLoc.in_pit_stall, "laps_completed": 2},
        {"track_loc": TrkLoc.not_in_world, "laps_completed": 3},
        {"track_loc": TrkLoc.aproaching_pits, "laps_completed": 4},
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result == []

def test_detect_off_track_driver_negative_laps():
    drivers = MockDrivers([
        {"track_loc": TrkLoc.off_track, "laps_completed": -1},
        {"track_loc": TrkLoc.off_track, "laps_completed": 0},
    ])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert len(result) == 1
    assert drivers.current_drivers[1] in result

def test_detect_empty_drivers():
    drivers = MockDrivers([])
    detector = OffTrackDetector(drivers)
    result = detector.detect()
    assert result == []