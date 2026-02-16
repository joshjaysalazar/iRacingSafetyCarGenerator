import pytest
from unittest.mock import patch

from core.detection.threshold_checker import ThresholdChecker, DetectorEventTypes, ThresholdCheckerSettings
from core.tests.test_utils import make_driver, dict_to_config

# Define a little shorthand
STOPPED = DetectorEventTypes.STOPPED
RANDOM = DetectorEventTypes.RANDOM
OFF_TRACK = DetectorEventTypes.OFF_TRACK
MEATBALL = DetectorEventTypes.MEATBALL

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
    # Mock settings object with the typed wrapper interface
    settings = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "5",
            "stopped_cars_threshold": "3",
            "accumulative_threshold": "10",
            "off_track_weight": "1.0",
            "stopped_weight": "2.0",
        }
    })

    threshold_checker_settings = ThresholdCheckerSettings.from_settings(settings)
    assert threshold_checker_settings.time_range == 5.0
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

def test_dedupe_cluster():
    """Test _dedupe_cluster keeps only the latest event per (driver_idx, event_type)"""
    driver1_early = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver1_late = make_driver(track_loc=0, driver_idx=1, lap_distance=0.15)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)

    cluster_events = [
        (1000.1, 1, OFF_TRACK, driver1_early),
        (1000.2, 1, OFF_TRACK, driver1_late),   # Later timestamp, should win
        (1000.3, 1, STOPPED, driver1_early),     # Different event type
        (1000.4, 2, OFF_TRACK, driver2),
    ]

    result = ThresholdChecker._dedupe_cluster(cluster_events)

    # Should have 3 entries: driver1 OFF_TRACK (latest), driver1 STOPPED, driver2 OFF_TRACK
    assert len(result) == 3
    result_keys = {(d_idx, e_type) for d_idx, e_type, _ in result}
    assert result_keys == {(1, OFF_TRACK), (1, STOPPED), (2, OFF_TRACK)}

    # Check that we got the latest OFF_TRACK driver_obj for driver1
    for d_idx, e_type, d_obj in result:
        if d_idx == 1 and e_type == OFF_TRACK:
            assert d_obj is driver1_late


def test_driver_in_multiple_proximity_clusters(mocker):
    """Test that a driver detected at crash site AND pit appears in both clusters"""
    proximity_checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=1000,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 1.0, STOPPED: 1.0},
        event_type_threshold={OFF_TRACK: 2, RANDOM: 1, STOPPED: 3},
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.05,
    ))
    mocker.patch("time.time", return_value=1000.0)

    # Driver 1 detected at crash site (0.5), then later at pit (0.1)
    driver1_at_crash = make_driver(track_loc=0, driver_idx=1, lap_distance=0.5)
    driver1_at_pit = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    # Driver 2 at crash site
    driver2_at_crash = make_driver(track_loc=0, driver_idx=2, lap_distance=0.51)
    # Driver 3 near pit
    driver3_at_pit = make_driver(track_loc=0, driver_idx=3, lap_distance=0.11)

    proximity_checker._register_event(OFF_TRACK, driver1_at_crash, 1000.0)
    proximity_checker._register_event(OFF_TRACK, driver1_at_pit, 1000.5)  # Later, at pit
    proximity_checker._register_event(OFF_TRACK, driver2_at_crash, 1000.1)
    proximity_checker._register_event(OFF_TRACK, driver3_at_pit, 1000.2)

    clusters = proximity_checker._get_proximity_clusters()

    # Should have 2 clusters: one near pit (0.1-0.11) and one near crash (0.5-0.51)
    assert len(clusters) == 2

    # Driver 1 should appear in both clusters (at different positions)
    for cluster in clusters:
        driver_idxs = {d_idx for d_idx, _, _ in cluster}
        assert 1 in driver_idxs, "Driver 1 should be in both clusters"


def test_same_driver_deduped_within_cluster(mocker):
    """Test that multiple detections of same driver+type at similar positions collapse to one"""
    proximity_checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=1000,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 1.0, STOPPED: 1.0},
        event_type_threshold={OFF_TRACK: 2, RANDOM: 1, STOPPED: 3},
        proximity_yellows_enabled=True,
        proximity_yellows_distance=0.05,
    ))
    mocker.patch("time.time", return_value=1000.0)

    # Same driver detected multiple times at similar positions
    driver1_t1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.10)
    driver1_t2 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.11)
    driver1_t3 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.12)

    proximity_checker._register_event(OFF_TRACK, driver1_t1, 1000.0)
    proximity_checker._register_event(OFF_TRACK, driver1_t2, 1000.1)
    proximity_checker._register_event(OFF_TRACK, driver1_t3, 1000.2)

    clusters = proximity_checker._get_proximity_clusters()

    assert len(clusters) == 1, "We are only expecting one cluster"

    # All events are in same proximity range, should produce cluster(s) where
    # driver 1 OFF_TRACK appears only once per cluster after deduping
    for cluster in clusters:
        driver1_offtrack_count = sum(1 for d_idx, e_type, _ in cluster
                                     if d_idx == 1 and e_type == OFF_TRACK)
        assert driver1_offtrack_count == 1, "Same driver+type should be deduped within a cluster"

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
    ))
    checker.race_started(999.0)  # 1 second ago
    
    mocker.patch("time.time", return_value=1000.0)
    
    # 2 cars close together - should meet reduced threshold of 2 (4 * 0.5)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.11)
    
    checker._register_event(OFF_TRACK, driver1, 1000.0)
    checker._register_event(OFF_TRACK, driver2, 1000.0)
    
    assert checker.threshold_met() == True


def test_threshold_checker_race_started():
    """Test that race_started properly sets race_start_time"""
    checker = ThresholdChecker(ThresholdCheckerSettings())
    
    # Initially race_start_time should be None
    assert checker.race_start_time is None
    
    # After calling race_started, it should be set
    start_time = 1000.0
    checker.race_started(start_time)
    assert checker.race_start_time == start_time

def test_threshold_met_warning_before_race_started(caplog):
    """Test WARNING log when threshold_met() called before race_started()"""
    checker = ThresholdChecker(ThresholdCheckerSettings())
    
    with caplog.at_level('WARNING'):
        result = checker.threshold_met()
    
    assert "Threshold checking attempted before race_started() was called" in caplog.text
    assert result is False  # Should still return sensible result

def test_dynamic_threshold_without_race_started_and_after():
    """Test dynamic threshold behavior when race hasn't started yet"""
    settings = ThresholdCheckerSettings(
        dynamic_threshold_enabled=True,
        dynamic_threshold_multiplier=0.5
    )
    checker = ThresholdChecker(settings)
    
    # Should return base threshold unchanged when race hasn't started
    base_threshold = 4.0
    result = checker._calc_dynamic_threshold(base_threshold)
    assert result == base_threshold
    
    # After race starts, should apply multiplier
    checker.race_started(1000.0)
    # Mock time to be within dynamic threshold window
    with patch('time.time', return_value=1100.0):  # 100 seconds later
        result = checker._calc_dynamic_threshold(base_threshold)
        assert result == 2.0  # 4.0 * 0.5


# End-to-end integration tests for settings → ThresholdChecker behavior
def test_accumulative_threshold_no_double_count_same_driver(mocker):
    """Test that a driver with both STOPPED and OFF_TRACK only contributes the highest weight to the accumulative score."""
    mocker.patch("time.time", return_value=1000.0)

    # Accumulative threshold = 5, stopped weight = 2.0, off_track weight = 1.0
    # If double-counted, driver1 (stopped + off_track) would contribute 3.0
    # With fix, driver1 contributes max(2.0, 1.0) = 2.0
    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=5.0,
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 0.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, RANDOM: 1000, STOPPED: 1000},
    ))

    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)

    # Driver 1 is both stopped and off track
    checker._register_event(STOPPED, driver1, 1000.0)
    checker._register_event(OFF_TRACK, driver1, 1000.1)
    # Driver 2 is stopped
    checker._register_event(STOPPED, driver2, 1000.2)

    # Without fix: acc = 2*2.0 + 1*1.0 = 5.0 (would trigger)
    # With fix: driver1 contributes max(2.0, 1.0) = 2.0, driver2 contributes 2.0, total = 4.0
    assert not checker.threshold_met(), "Should not trigger: driver1=2.0 (max of stopped/off_track) + driver2=2.0 = 4.0 < 5.0"

    # Add another driver to push over threshold
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    checker._register_event(OFF_TRACK, driver3, 1000.3)
    # Now: driver1=2.0 + driver2=2.0 + driver3=1.0 = 5.0
    assert checker.threshold_met(), "Should trigger: 2.0 + 2.0 + 1.0 = 5.0 >= 5.0"


def test_accumulative_threshold_per_event_type_still_counts_both(mocker):
    """Test that per-event-type thresholds still count a driver for each event type independently."""
    mocker.patch("time.time", return_value=1000.0)

    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=1000,  # High, won't trigger
        accumulative_weights={OFF_TRACK: 1.0, RANDOM: 0.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 2, RANDOM: 1000, STOPPED: 2},
    ))

    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)

    # Both drivers are off track
    checker._register_event(OFF_TRACK, driver1, 1000.0)
    checker._register_event(OFF_TRACK, driver2, 1000.1)
    # Driver 1 is also stopped - should not affect the OFF_TRACK per-type threshold
    checker._register_event(STOPPED, driver1, 1000.2)

    # OFF_TRACK threshold of 2 is met (driver1 + driver2)
    assert checker.threshold_met(), "Per-event-type threshold should still count both drivers for OFF_TRACK"


def test_from_settings_off_weight_affects_threshold_behavior(mocker):
    """Test that changing off_weight in settings actually changes when threshold triggers."""
    mocker.patch("time.time", return_value=1000.0)

    # Test with off_weight = 1.0
    settings_low_weight = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",  # High individual threshold
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "3",  # Low accumulative threshold
            "off_track_weight": "1.0",  # Low weight
            "stopped_weight": "2.0",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_low = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_low_weight))

    # Register 2 off-track events: 2 * 1.0 = 2.0 (below threshold of 3)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    checker_low._register_event(OFF_TRACK, driver1, 1000.0)
    checker_low._register_event(OFF_TRACK, driver2, 1000.1)

    assert not checker_low.threshold_met(), "Should not trigger with 2 off-track @ weight 1.0 (total 2.0 < 3.0)"

    # Now test with off_weight = 2.0
    settings_high_weight = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "3",
            "off_track_weight": "2.0",  # Higher weight
            "stopped_weight": "2.0",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_high = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_high_weight))

    # Register same 2 off-track events: 2 * 2.0 = 4.0 (above threshold of 3)
    checker_high._register_event(OFF_TRACK, driver1, 1000.0)
    checker_high._register_event(OFF_TRACK, driver2, 1000.1)

    assert checker_high.threshold_met(), "Should trigger with 2 off-track @ weight 2.0 (total 4.0 >= 3.0)"


def test_from_settings_stopped_weight_affects_threshold_behavior(mocker):
    """Test that changing stopped_weight in settings actually changes when threshold triggers."""
    mocker.patch("time.time", return_value=1000.0)

    # Test with stopped_weight = 1.0
    settings_low_weight = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "5",  # Accumulative threshold
            "off_track_weight": "1.0",
            "stopped_weight": "1.0",  # Low weight for stopped
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_low = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_low_weight))

    # Register 2 stopped events: 2 * 1.0 = 2.0 (below threshold of 5)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    checker_low._register_event(STOPPED, driver1, 1000.0)
    checker_low._register_event(STOPPED, driver2, 1000.1)

    assert not checker_low.threshold_met(), "Should not trigger with 2 stopped @ weight 1.0 (total 2.0 < 5.0)"

    # Now test with stopped_weight = 3.0
    settings_high_weight = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "5",
            "off_track_weight": "1.0",
            "stopped_weight": "3.0",  # Higher weight for stopped
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_high = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_high_weight))

    # Register same 2 stopped events: 2 * 3.0 = 6.0 (above threshold of 5)
    checker_high._register_event(STOPPED, driver1, 1000.0)
    checker_high._register_event(STOPPED, driver2, 1000.1)

    assert checker_high.threshold_met(), "Should trigger with 2 stopped @ weight 3.0 (total 6.0 >= 5.0)"


def test_from_settings_combined_min_affects_threshold_behavior(mocker):
    """Test that changing combined_min in settings actually changes when threshold triggers."""
    mocker.patch("time.time", return_value=1000.0)

    # Test with combined_min = 10 (high threshold)
    settings_high_threshold = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "10",  # High accumulative threshold
            "off_track_weight": "2.0",
            "stopped_weight": "2.0",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_high_threshold = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_high_threshold))

    # Register 2 off-track + 1 stopped: (2*2.0) + (1*2.0) = 6.0 (below threshold of 10)
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    checker_high_threshold._register_event(OFF_TRACK, driver1, 1000.0)
    checker_high_threshold._register_event(OFF_TRACK, driver2, 1000.1)
    checker_high_threshold._register_event(STOPPED, driver3, 1000.2)

    assert not checker_high_threshold.threshold_met(), "Should not trigger with total 6.0 < combined_min 10.0"

    # Now test with combined_min = 5 (low threshold)
    settings_low_threshold = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "5",  # Low accumulative threshold
            "off_track_weight": "2.0",
            "stopped_weight": "2.0",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_low_threshold = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_low_threshold))

    # Register same events: (2*2.0) + (1*2.0) = 6.0 (above threshold of 5)
    checker_low_threshold._register_event(OFF_TRACK, driver1, 1000.0)
    checker_low_threshold._register_event(OFF_TRACK, driver2, 1000.1)
    checker_low_threshold._register_event(STOPPED, driver3, 1000.2)

    assert checker_low_threshold.threshold_met(), "Should trigger with total 6.0 >= combined_min 5.0"


def test_from_settings_complete_integration_with_realistic_scenario(mocker):
    """Complete end-to-end test showing how UI settings control threshold behavior in realistic racing scenario.

    This test simulates a race director configuring different thresholds and weights through the UI
    and verifies the ThresholdChecker respects those settings exactly.
    """
    mocker.patch("time.time", return_value=1000.0)

    # Scenario: Race director wants stopped cars weighted more heavily than off-track
    # UI Configuration: stopped_weight=3, off_weight=1, combined_min=8
    # This means: 1 stopped car = 3 points, 1 off-track = 1 point, need 8 points total
    settings_config_1 = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",  # Disable individual thresholds
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "8",
            "off_track_weight": "1.0",
            "stopped_weight": "3.0",  # Stopped cars weighted 3x more
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_1 = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_config_1))

    # Test case 1: 5 off-track cars = 5 points (not enough)
    drivers = [make_driver(track_loc=0, driver_idx=i, lap_distance=0.1 + i*0.01) for i in range(6)]
    for i in range(5):
        checker_1._register_event(OFF_TRACK, drivers[i], 1000.0 + i*0.01)
    assert not checker_1.threshold_met(), "5 off-track (5 points) should not trigger with threshold 8"

    # Test case 2: Add 1 stopped car = 5 + 3 = 8 points (exactly threshold)
    checker_1._register_event(STOPPED, drivers[5], 1000.05)
    assert checker_1.threshold_met(), "5 off-track + 1 stopped (8 points) should trigger with threshold 8"

    # Now race director changes mind - wants equal weighting
    # UI Configuration: stopped_weight=2, off_weight=2, combined_min=10
    settings_config_2 = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "10",  # Higher threshold
            "off_track_weight": "2.0",  # Equal weights
            "stopped_weight": "2.0",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_2 = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_config_2))

    # Same scenario: 3 off-track + 2 stopped
    # With equal weights: (3*2) + (2*2) = 10 points (exactly threshold)
    for i in range(3):
        checker_2._register_event(OFF_TRACK, drivers[i], 1000.0 + i*0.01)
    for i in range(3, 5):
        checker_2._register_event(STOPPED, drivers[i], 1000.0 + i*0.01)
    assert checker_2.threshold_met(), "3 off-track + 2 stopped (10 points) should trigger with threshold 10"

    # Test case 3: Just 2 stopped + 2 off-track = 8 points (not enough with threshold 10)
    checker_3 = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_config_2))
    for i in range(2):
        checker_3._register_event(OFF_TRACK, drivers[i], 1000.0 + i*0.01)
    for i in range(2, 4):
        checker_3._register_event(STOPPED, drivers[i], 1000.0 + i*0.01)
    assert not checker_3.threshold_met(), "2 off-track + 2 stopped (8 points) should not trigger with threshold 10"

    # Race director goes conservative - very low weights but high threshold
    # UI Configuration: stopped_weight=0.5, off_weight=0.5, combined_min=15
    # This requires many more cars to trigger
    settings_config_3 = dict_to_config({
        "settings": {
            "event_time_window_seconds": "5.0",
            "off_track_cars_threshold": "999",
            "stopped_cars_threshold": "999",
            "accumulative_threshold": "15",
            "off_track_weight": "0.5",
            "stopped_weight": "0.5",
            "proximity_filter_enabled": "0",
            "proximity_filter_distance_percentage": "0.05",
            "race_start_threshold_multiplier": "1.0",
            "race_start_threshold_multiplier_time_seconds": "300.0",
        }
    })

    checker_4 = ThresholdChecker(ThresholdCheckerSettings.from_settings(settings_config_3))

    # Need 30 cars at 0.5 weight each to reach 15 points - let's use 20 (10 points, not enough)
    drivers_large = [make_driver(track_loc=0, driver_idx=i, lap_distance=0.01*i) for i in range(40)]
    for i in range(20):
        event_type = STOPPED if i % 2 == 0 else OFF_TRACK
        checker_4._register_event(event_type, drivers_large[i], 1000.0 + i*0.001)
    assert not checker_4.threshold_met(), "20 cars @ 0.5 weight (10 points) should not trigger with threshold 15"

    # Add 10 more cars to reach 30 total = 15 points
    for i in range(20, 30):
        event_type = STOPPED if i % 2 == 0 else OFF_TRACK
        checker_4._register_event(event_type, drivers_large[i], 1000.0 + i*0.001)
    assert checker_4.threshold_met(), "30 cars @ 0.5 weight (15 points) should trigger with threshold 15"


def test_per_event_type_threshold_skipped_when_not_individually_enabled(mocker):
    """Per-event-type threshold should NOT trigger for event types that are not individually enabled."""
    mocker.patch("time.time", return_value=1000.0)

    # STOPPED is NOT individually enabled, but has a low per-event-type threshold
    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=1000,  # High, won't trigger via accumulative
        accumulative_weights={OFF_TRACK: 1.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, STOPPED: 2},  # Low threshold for STOPPED
        individually_enabled_event_types={OFF_TRACK, RANDOM, MEATBALL},  # STOPPED excluded
    ))

    # Register enough STOPPED events to exceed the per-event-type threshold
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    checker._register_event(STOPPED, driver1, 1000.0)
    checker._register_event(STOPPED, driver2, 1000.1)
    checker._register_event(STOPPED, driver3, 1000.2)

    # Should NOT trigger because STOPPED per-event-type check is skipped
    assert not checker.threshold_met()


def test_accumulative_still_counts_non_individually_enabled_events(mocker):
    """Accumulative scoring should still include events from non-individually-enabled detectors."""
    mocker.patch("time.time", return_value=1000.0)

    # STOPPED is NOT individually enabled, but has accumulative weight
    checker = ThresholdChecker(ThresholdCheckerSettings(
        time_range=10.0,
        accumulative_threshold=5.0,
        accumulative_weights={OFF_TRACK: 1.0, STOPPED: 2.0},
        event_type_threshold={OFF_TRACK: 1000, STOPPED: 1000},  # High, won't trigger individually
        individually_enabled_event_types={OFF_TRACK, RANDOM, MEATBALL},  # STOPPED excluded
    ))

    # Register events: 1 OFF_TRACK (1.0) + 2 STOPPED (2*2.0=4.0) = 5.0 >= threshold
    driver1 = make_driver(track_loc=0, driver_idx=1, lap_distance=0.1)
    driver2 = make_driver(track_loc=0, driver_idx=2, lap_distance=0.2)
    driver3 = make_driver(track_loc=0, driver_idx=3, lap_distance=0.3)
    checker._register_event(OFF_TRACK, driver1, 1000.0)
    checker._register_event(STOPPED, driver2, 1000.1)
    checker._register_event(STOPPED, driver3, 1000.2)

    # Should trigger via accumulative even though STOPPED is not individually enabled
    assert checker.threshold_met()


def test_from_settings_populates_individually_enabled():
    """Verify from_settings builds individually_enabled_event_types from detector enabled flags."""
    settings = dict_to_config({
        "settings": {
            "random_detector_enabled": "1",
            "stopped_detector_enabled": "0",
            "off_track_detector_enabled": "1",
            "meatball_detector_enabled": "0",
        }
    })

    tcs = ThresholdCheckerSettings.from_settings(settings)
    assert tcs.individually_enabled_event_types == {RANDOM, OFF_TRACK}