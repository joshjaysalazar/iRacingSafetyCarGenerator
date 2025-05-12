import pytest

from core.detection.detector import Detector, DetectorEventTypes, DetectorSettings

# Define a little shorthand
STOPPED = DetectorEventTypes.STOPPED
OFF_TRACK = DetectorEventTypes.OFF_TRACK

@pytest.fixture
def detector():
    return Detector(DetectorSettings(
        time_range=1.0,
        accumulative_threshold=1000,
        accumulative_weights={OFF_TRACK: 1.0, STOPPED: 1.0},
        event_type_threshold={OFF_TRACK: 2, STOPPED: 3},
    ))

def test_off_track_threshold(detector, mocker):
    mocker.patch("time.time", return_value=1000.0)
    detector.register_event(OFF_TRACK, 1, 1000.1)
    detector.register_event(OFF_TRACK, 1, 1000.2)  # should not count
    assert not detector.threshold_met()
    detector.register_event(OFF_TRACK, 2, 1000.3)
    assert detector.threshold_met()

def test_stopped_threshold(detector, mocker):
    mocker.patch("time.time", return_value=1000.0)
    detector.register_event(STOPPED, 1, 1000.1)
    detector.register_event(STOPPED, 1, 1000.2)  # should not count
    assert not detector.threshold_met()
    detector.register_event(STOPPED, 2, 1000.3)
    detector.register_event(STOPPED, 2, 1000.4)  # should not count
    assert not detector.threshold_met()
    detector.register_event(STOPPED, 3, 1000.5)
    assert detector.threshold_met()

def test_mixed_threshold(detector, mocker):
    mocker.patch("time.time", return_value=1000.0)
    detector.register_event(STOPPED, 1, 1000.1)
    detector.register_event(STOPPED, 1, 1000.2) # should not count
    detector.register_event(OFF_TRACK, 1, 1000.1)
    assert not detector.threshold_met()
    detector.register_event(STOPPED, 2, 1000.3)
    detector.register_event(STOPPED, 2, 1000.4) # should not count
    assert not detector.threshold_met()
    detector.register_event(STOPPED, 3, 1000.5)
    assert detector.threshold_met()

@pytest.fixture
def accumulative_detector():
    return Detector(DetectorSettings(
        time_range=1.0,
        accumulative_threshold=5,
        accumulative_weights={OFF_TRACK: 1.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, STOPPED: 1000},
    ))

def test_accumulative_threshold_offtracks(accumulative_detector, mocker):
    detector = accumulative_detector
    mocker.patch("time.time", return_value=1000.0)
    detector.register_event(OFF_TRACK, 1, 1000.1)
    detector.register_event(OFF_TRACK, 1, 1000.2) # should not count
    detector.register_event(OFF_TRACK, 2, 1000.3)
    detector.register_event(OFF_TRACK, 3, 1000.4)
    detector.register_event(OFF_TRACK, 4, 1000.5)
    assert not detector.threshold_met()
    detector.register_event(OFF_TRACK, 5, 1000.6)
    assert detector.threshold_met()

def test_accumulative_threshold_stopped(accumulative_detector, mocker):
    detector = accumulative_detector
    mocker.patch("time.time", return_value=1000.0)
    detector.register_event(STOPPED, 1, 1000.1)
    detector.register_event(STOPPED, 1, 1000.2) # should not count
    detector.register_event(STOPPED, 2, 1000.3)
    assert not detector.threshold_met()
    detector.register_event(STOPPED, 3, 1000.4)
    assert detector.threshold_met()

# Each of these sequences will trigger the threshold on the last event
@pytest.mark.parametrize("events", [
    [OFF_TRACK, OFF_TRACK, OFF_TRACK, STOPPED],
    [OFF_TRACK, OFF_TRACK, OFF_TRACK, OFF_TRACK, STOPPED],
    [STOPPED, STOPPED, OFF_TRACK],
    [STOPPED, OFF_TRACK, STOPPED],
    [OFF_TRACK, STOPPED, OFF_TRACK, STOPPED],
])
def test_accumulative_threshold_mix(events, accumulative_detector, mocker):
    """ 3 off tracks and a stopped == 5 """
    detector = accumulative_detector
    mocker.patch("time.time", return_value=1000.0)
    for idx, event in enumerate(events):
        detector.register_event(event, idx, 1000.0 + (idx/10.0))
        if idx == len(events) - 1:
            assert detector.threshold_met()
        else:
            assert not detector.threshold_met()

def test_cleanup(detector, mocker):
    # The time range is one, so we are going to add events with 0.1 increments
    # and adjust the time in between cleanups to show the threshold_met flipping
    mocker.patch("time.time", return_value=1000.0)
    # just adding a couple to make sure maintaining the count works
    detector.register_event(OFF_TRACK, 1, 1000.01)
    detector.register_event(OFF_TRACK, 1, 1000.02)
    detector.register_event(OFF_TRACK, 1, 1000.03)
    assert not detector.threshold_met()
    detector.register_event(OFF_TRACK, 2, 1000.2)
    assert detector.threshold_met()
    detector.register_event(OFF_TRACK, 3, 1000.3)
    detector.clean_up_events() # does not clean up anything
    assert detector.threshold_met()

    mocker.patch("time.time", return_value=1001.0)
    detector.clean_up_events() # does not clean up anything
    assert detector.threshold_met()
    
    mocker.patch("time.time", return_value=1001.1)
    detector.clean_up_events() # should clean up events from driver 1
    assert detector.threshold_met() # still two off tracks in last second

    mocker.patch("time.time", return_value=1001.2)
    detector.clean_up_events() # should clean up second event
    assert not detector.threshold_met() # now there's only one off track in last second
    