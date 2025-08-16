import pytest

from core.detection.threshold_checker import ThresholdChecker, DetectorEventTypes, ThresholdCheckerSettings

# Define a little shorthand
STOPPED = DetectorEventTypes.STOPPED
RANDOM = DetectorEventTypes.RANDOM
OFF_TRACK = DetectorEventTypes.OFF_TRACK

@pytest.fixture
def threshold_checker():
    return ThresholdChecker(ThresholdCheckerSettings(
        time_range=1.0,
        accumulative_threshold=1000,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 1.0, STOPPED: 1.0},
        event_type_threshold={OFF_TRACK: 2, RANDOM: 1, STOPPED: 3},
    ))

def test_off_track_threshold(threshold_checker, mocker):
    mocker.patch("time.time", return_value=1000.0)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.1)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.2)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, 2, 1000.3)
    assert threshold_checker.threshold_met()

def test_stopped_threshold(threshold_checker, mocker):
    mocker.patch("time.time", return_value=1000.0)
    threshold_checker._register_event(STOPPED, 1, 1000.1)
    threshold_checker._register_event(STOPPED, 1, 1000.2)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, 2, 1000.3)
    threshold_checker._register_event(STOPPED, 2, 1000.4)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, 3, 1000.5)
    assert threshold_checker.threshold_met()

def test_mixed_threshold(threshold_checker, mocker):
    mocker.patch("time.time", return_value=1000.0)
    threshold_checker._register_event(STOPPED, 1, 1000.1)
    threshold_checker._register_event(STOPPED, 1, 1000.2) # should not count
    threshold_checker._register_event(OFF_TRACK, 1, 1000.1)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, 2, 1000.3)
    threshold_checker._register_event(STOPPED, 2, 1000.4) # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, 3, 1000.5)
    assert threshold_checker.threshold_met()

@pytest.fixture
def accumulative_threshold_checker():
    return ThresholdChecker(ThresholdCheckerSettings(
        time_range=1.0,
        accumulative_threshold=5,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 1.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, RANDOM: 1, STOPPED: 1000},
    ))

def test_accumulative_threshold_offtracks(accumulative_threshold_checker, mocker):
    threshold_checker = accumulative_threshold_checker
    mocker.patch("time.time", return_value=1000.0)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.1)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.2) # should not count
    threshold_checker._register_event(OFF_TRACK, 2, 1000.3)
    threshold_checker._register_event(OFF_TRACK, 3, 1000.4)
    threshold_checker._register_event(OFF_TRACK, 4, 1000.5)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, 5, 1000.6)
    assert threshold_checker.threshold_met()

def test_accumulative_threshold_stopped(accumulative_threshold_checker, mocker):
    threshold_checker = accumulative_threshold_checker
    mocker.patch("time.time", return_value=1000.0)
    threshold_checker._register_event(STOPPED, 1, 1000.1)
    threshold_checker._register_event(STOPPED, 1, 1000.2) # should not count
    threshold_checker._register_event(STOPPED, 2, 1000.3)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, 3, 1000.4)
    assert threshold_checker.threshold_met()

# Each of these sequences will trigger the threshold on the last event
@pytest.mark.parametrize("events", [
    [OFF_TRACK, OFF_TRACK, OFF_TRACK, STOPPED],
    [OFF_TRACK, OFF_TRACK, OFF_TRACK, OFF_TRACK, STOPPED],
    [STOPPED, STOPPED, OFF_TRACK],
    [STOPPED, OFF_TRACK, STOPPED],
    [OFF_TRACK, STOPPED, OFF_TRACK, STOPPED],
])
def test_accumulative_threshold_mix(events, accumulative_threshold_checker, mocker):
    """ 3 off tracks and a stopped == 5 """
    threshold_checker = accumulative_threshold_checker
    mocker.patch("time.time", return_value=1000.0)
    for idx, event in enumerate(events):
        threshold_checker._register_event(event, idx, 1000.0 + (idx/10.0))
        if idx == len(events) - 1:
            assert threshold_checker.threshold_met()
        else:
            assert not threshold_checker.threshold_met()

def test_cleanup(threshold_checker, mocker):
    # The time range is one, so we are going to add events with 0.1 increments
    # and adjust the time in between cleanups to show the threshold_met flipping
    mocker.patch("time.time", return_value=1000.0)
    # just adding a couple to make sure maintaining the count works
    threshold_checker._register_event(OFF_TRACK, 1, 1000.01)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.02)
    threshold_checker._register_event(OFF_TRACK, 1, 1000.03)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, 2, 1000.2)
    assert threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, 3, 1000.3)
    threshold_checker.clean_up_events() # does not clean up anything
    assert threshold_checker.threshold_met()

    mocker.patch("time.time", return_value=1001.0)
    threshold_checker.clean_up_events() # does not clean up anything
    assert threshold_checker.threshold_met()
    
    mocker.patch("time.time", return_value=1001.1)
    threshold_checker.clean_up_events() # should clean up events from driver 1
    assert threshold_checker.threshold_met() # still two off tracks in last second

    mocker.patch("time.time", return_value=1001.2)
    threshold_checker.clean_up_events() # should clean up second event
    assert not threshold_checker.threshold_met() # now there's only one off track in last second
    
def test_threshold_checker_settings_from_settings():
    settings = {
        "settings": {
            "off_min": "5",
            "stopped_min": "3",
        }
    }
    threshold_checker_settings = ThresholdCheckerSettings.from_settings(settings)
    assert threshold_checker_settings.time_range == 10.0
    assert threshold_checker_settings.event_type_threshold[OFF_TRACK] == 5
    assert threshold_checker_settings.event_type_threshold[STOPPED] == 3
    assert threshold_checker_settings.accumulative_threshold == 10
    assert threshold_checker_settings.accumulative_weights[OFF_TRACK] == 1.0
    assert threshold_checker_settings.accumulative_weights[STOPPED] == 2.0