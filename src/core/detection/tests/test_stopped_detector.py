import pytest

from irsdk import TrkLoc
from core.detection.stopped_detector import StoppedDetector

class MockDrivers:
    def __init__(self, current, previous):
        self.current_drivers = current
        self.previous_drivers = previous

        # This is a fix to account for the SC entry in the drivers list
        # Ideally, we filter this out in the Drivers class so we don't have to account for this in all of our logic.
        self.current_drivers.append(make_driver(TrkLoc.not_in_world, 0, 0.0))
        self.previous_drivers.append(make_driver(TrkLoc.not_in_world, 0,  0.0))

def make_driver(track_loc, laps_completed, lap_distance):
    return {
        "track_loc": track_loc,
        "laps_completed": laps_completed,
        "lap_distance": lap_distance
    }

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
    stopped = detector.detect()
    assert stopped == [current[0]]

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
    stopped = detector.detect()
    assert stopped == []

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
    stopped = detector.detect()
    assert stopped == [current[1]]

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
    stopped = detector.detect()
    assert stopped == []

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
    stopped = detector.detect()
    assert stopped == [current[0], current[1]]