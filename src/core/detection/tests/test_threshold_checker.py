import pytest
import time

from core.detection.threshold_checker import ThresholdChecker, DetectorEventTypes, ThresholdCheckerSettings
from core.tests.test_utils import make_driver, dict_to_config

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
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.1)
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.2)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, driver2, 1000.3)
    assert threshold_checker.threshold_met()

def test_stopped_threshold(threshold_checker, mocker):
    mocker.patch("time.time", return_value=1000.0)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    threshold_checker._register_event(STOPPED, driver1, 1000.1)
    threshold_checker._register_event(STOPPED, driver1, 1000.2)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, driver2, 1000.3)
    threshold_checker._register_event(STOPPED, driver2, 1000.4)  # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, driver3, 1000.5)
    assert threshold_checker.threshold_met()

def test_mixed_threshold(threshold_checker, mocker):
    mocker.patch("time.time", return_value=1000.0)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    threshold_checker._register_event(STOPPED, driver1, 1000.1)
    threshold_checker._register_event(STOPPED, driver1, 1000.2) # should not count
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.1)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, driver2, 1000.3)
    threshold_checker._register_event(STOPPED, driver2, 1000.4) # should not count
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, driver3, 1000.5)
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
    drivers = [make_driver(track_loc=0, driver_idx=i, lap_distance=0.1 + i*0.01) for i in range(1, 6)]
    threshold_checker._register_event(OFF_TRACK, drivers[0], 1000.1)
    threshold_checker._register_event(OFF_TRACK, drivers[0], 1000.2) # should not count
    threshold_checker._register_event(OFF_TRACK, drivers[1], 1000.3)
    threshold_checker._register_event(OFF_TRACK, drivers[2], 1000.4)
    threshold_checker._register_event(OFF_TRACK, drivers[3], 1000.5)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, drivers[4], 1000.6)
    assert threshold_checker.threshold_met()

def test_accumulative_threshold_stopped(accumulative_threshold_checker, mocker):
    threshold_checker = accumulative_threshold_checker
    mocker.patch("time.time", return_value=1000.0)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    threshold_checker._register_event(STOPPED, driver1, 1000.1)
    threshold_checker._register_event(STOPPED, driver1, 1000.2) # should not count
    threshold_checker._register_event(STOPPED, driver2, 1000.3)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(STOPPED, driver3, 1000.4)
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
        driver = make_driver(track_loc=0, driver_idx=idx, lap_distance=0.1 + idx*0.01)
        threshold_checker._register_event(event, driver, 1000.0 + (idx/10.0))
        if idx == len(events) - 1:
            assert threshold_checker.threshold_met()
        else:
            assert not threshold_checker.threshold_met()

def test_cleanup(threshold_checker, mocker):
    # The time range is one, so we are going to add events with 0.1 increments
    # and adjust the time in between cleanups to show the threshold_met flipping
    mocker.patch("time.time", return_value=1000.0)
    # just adding a couple to make sure maintaining the count works
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.01)
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.02)
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.03)
    assert not threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, driver2, 1000.2)
    assert threshold_checker.threshold_met()
    threshold_checker._register_event(OFF_TRACK, driver3, 1000.3)
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
    settings = dict_to_config({
        "settings": {
            "off_min": "5",
            "stopped_min": "3",
            "proximity_yellows": "0",
            "proximity_yellows_distance": "0.05",
            "start_multi_val": "1.0",
            "start_multi_time": "300.0",
        }
    })
    threshold_checker_settings = ThresholdCheckerSettings.from_settings(settings)
    assert threshold_checker_settings.time_range == 10.0
    assert threshold_checker_settings.event_type_threshold[OFF_TRACK] == 5
    assert threshold_checker_settings.event_type_threshold[STOPPED] == 3
    assert threshold_checker_settings.accumulative_threshold == 10
    assert threshold_checker_settings.accumulative_weights[OFF_TRACK] == 1.0
    assert threshold_checker_settings.accumulative_weights[STOPPED] == 2.0

# Proximity clustering tests based on test_generator.py proximity tests
@pytest.fixture
def proximity_threshold_checker():
    """Threshold checker with proximity enabled"""
    return ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=1000,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 1.0, STOPPED: 1.0},
        event_type_threshold={OFF_TRACK: 2, RANDOM: 1, STOPPED: 3},
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.05,
    ))

def test_get_proximity_clusters_disabled(threshold_checker, mocker):
    """Test _get_proximity_clusters when proximity is disabled - should return single cluster with all events"""
    mocker.patch("time.time", return_value=1000.0)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.5)  # far apart
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.8)  # even further
    
    threshold_checker._register_event(OFF_TRACK, driver1, 1000.0)
    threshold_checker._register_event(STOPPED, driver2, 1000.0)
    threshold_checker._register_event(OFF_TRACK, driver3, 1000.0)
    
    clusters = threshold_checker._get_proximity_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 3  # All events in single cluster

def test_get_proximity_clusters_empty(proximity_threshold_checker):
    """Test _get_proximity_clusters with no events"""
    clusters = proximity_threshold_checker._get_proximity_clusters()
    assert clusters == []

def test_get_proximity_clusters_single_cluster(proximity_threshold_checker, mocker):
    """Test _get_proximity_clusters when all cars are within proximity"""
    mocker.patch("time.time", return_value=1000.0)
    # Cars within 0.05 distance of each other
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.11)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.12)
    
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.0)
    proximity_threshold_checker._register_event(STOPPED, driver2, 1000.0)
    proximity_threshold_checker._register_event(OFF_TRACK, driver3, 1000.0)
    
    clusters = proximity_threshold_checker._get_proximity_clusters()
    assert len(clusters) == 1
    assert len(clusters[0]) == 3

def test_get_proximity_clusters_multiple_clusters(proximity_threshold_checker, mocker):
    """Test _get_proximity_clusters with cars forming multiple clusters"""
    mocker.patch("time.time", return_value=1000.0)
    # Two clusters: (0.1, 0.11, 0.12) and (0.2, 0.22)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.11)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.12)
    driver4 = make_driver(track_loc=0, driver_idx=4, lap_distance=0.2)
    driver5 = make_driver(track_loc=0, driver_idx=5, lap_distance=0.22)
    
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.0)
    proximity_threshold_checker._register_event(STOPPED, driver2, 1000.0)
    proximity_threshold_checker._register_event(OFF_TRACK, driver3, 1000.0)
    proximity_threshold_checker._register_event(STOPPED, driver4, 1000.0)
    proximity_threshold_checker._register_event(OFF_TRACK, driver5, 1000.0)
    
    clusters = proximity_threshold_checker._get_proximity_clusters()
    assert len(clusters) == 2
    cluster_sizes = sorted([len(cluster) for cluster in clusters])
    assert cluster_sizes == [2, 3]  # One cluster with 3 cars, one with 2

def test_get_proximity_clusters_across_finish_line(mocker):
    """Test _get_proximity_clusters with cars near finish line (lap distances > 1.0)"""
    # Custom proximity checker with larger distance for this test
    proximity_checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.40,
        event_type_threshold={OFF_TRACK: 1000, STOPPED: 1000},
        accumulative_threshold=1000,
    ))
    
    mocker.patch("time.time", return_value=1000.0)
    # Cars across finish line should cluster together
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=1.9)  # normalized to 0.9
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=2.0)   # normalized to 0.0
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=2.1)   # normalized to 0.1
    
    proximity_checker._register_event(OFF_TRACK, driver1, 1000.0)
    proximity_checker._register_event(STOPPED, driver2, 1000.0)
    proximity_checker._register_event(OFF_TRACK, driver3, 1000.0)
    
    clusters = proximity_checker._get_proximity_clusters()
    assert len(clusters) == 2  # We will get two clusters due to the wrap-around
    # One cluster should have 2 cars (0.0 and 0.1), the other 3 cars (0.9, 0.0, 0.1)
    cluster_sizes = sorted([len(cluster) for cluster in clusters])
    assert cluster_sizes == [2, 3]

def test_get_latest_events_per_driver(proximity_threshold_checker, mocker):
    """Test _get_latest_events_per_driver method"""
    mocker.patch("time.time", return_value=1000.0)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    
    # Register multiple events for same driver - should only keep latest
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.1)
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.2)  # This should be latest
    proximity_threshold_checker._register_event(STOPPED, driver1, 1000.3)    # Different event type
    proximity_threshold_checker._register_event(OFF_TRACK, driver2, 1000.4)
    
    latest_events = proximity_threshold_checker._get_latest_events_per_driver()
    
    # Should have 3 entries: driver1 OFF_TRACK (latest), driver1 STOPPED, driver2 OFF_TRACK
    assert len(latest_events) == 3
    assert (1, OFF_TRACK) in latest_events
    assert (1, STOPPED) in latest_events
    assert (2, OFF_TRACK) in latest_events
    
    # Check that we got the latest OFF_TRACK event for driver1
    assert latest_events[(1, OFF_TRACK)][0] == 1000.2

def test_cluster_meets_threshold_individual(proximity_threshold_checker):
    """Test _cluster_meets_threshold for individual event type thresholds"""
    # Create cluster with 2 OFF_TRACK events (threshold is 2)
    cluster = [
        (1, OFF_TRACK, make_driver(track_loc=0, driver_idx=1)),
        (2, OFF_TRACK, make_driver(track_loc=0, driver_idx=2)),
    ]
    
    result = proximity_threshold_checker._cluster_meets_threshold(cluster, 1.0)
    assert result == True

def test_cluster_meets_threshold_accumulative():
    """Test _cluster_meets_threshold for accumulative threshold"""
    # Custom checker with low accumulative threshold
    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=3.0,  # Low threshold
        accumulative_weights={OFF_TRACK: 1.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, STOPPED: 1000},  # High individual thresholds
        proximity_yellows_enabled=True,
    ))
    
    # Cluster: 1 OFF_TRACK (weight 1.0) + 1 STOPPED (weight 2.0) = 3.0 total
    cluster = [
        (1, OFF_TRACK, make_driver(track_loc=0, driver_idx=1)),
        (2, STOPPED, make_driver(track_loc=0, driver_idx=2)),
    ]
    
    result = checker._cluster_meets_threshold(cluster, 1.0)
    assert result == True

def test_threshold_met_with_proximity_clusters(proximity_threshold_checker, mocker):
    """Test threshold_met using proximity clustering approach"""
    mocker.patch("time.time", return_value=1000.0)
    
    # Cars close together that should form one cluster
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.11)
    
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.0)
    proximity_threshold_checker._register_event(OFF_TRACK, driver2, 1000.0)
    
    # Should meet OFF_TRACK threshold (2 cars in proximity)
    assert proximity_threshold_checker.threshold_met() == True

def test_threshold_met_proximity_prevents_false_positive(proximity_threshold_checker, mocker):
    """Test that proximity clustering prevents false positives from spread out cars"""
    mocker.patch("time.time", return_value=1000.0)
    
    # Cars spread out - shouldn't trigger even with 2 OFF_TRACK events
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.5)  # Too far apart
    
    proximity_threshold_checker._register_event(OFF_TRACK, driver1, 1000.0)
    proximity_threshold_checker._register_event(OFF_TRACK, driver2, 1000.0)
    
    # Should NOT meet threshold because cars are not in proximity
    assert proximity_threshold_checker.threshold_met() == False

def test_threshold_met_dynamic_threshold_with_proximity(mocker):
    """Test threshold_met with both dynamic thresholds and proximity clustering"""
    # Checker with dynamic thresholds enabled
    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        event_type_threshold={OFF_TRACK: 4, STOPPED: 4},  # High base threshold
        accumulative_threshold=1000,
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.05,
        dynamic_threshold_enabled=True,
        dynamic_threshold_multiplier=0.5,  # Halve the thresholds
        dynamic_threshold_time=300.0,
        session_start_time=999.0,  # 1 second ago
    ))
    
    mocker.patch("time.time", return_value=1000.0)
    
    # 2 cars close together - should meet reduced threshold of 2 (4 * 0.5)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.11)
    
    checker._register_event(OFF_TRACK, driver1, 1000.0)
    checker._register_event(OFF_TRACK, driver2, 1000.0)
    
    assert checker.threshold_met() == True