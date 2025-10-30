import pytest
import time
import math

from unittest.mock import Mock, call
from core.detection.threshold_checker import ThresholdChecker, DetectorEventTypes, ThresholdCheckerSettings
from core.detection.detector import Detector, DetectorSettings
from core.generator import Generator
from core.interactions.command_sender import CommandSender
from core.interactions.mock_sender import MockSender
from core.tests.test_utils import create_mock_drivers

@pytest.fixture
def generator():
    mock_arguments = Mock()
    mock_arguments.disable_window_interactions = True
    mock_master = Mock()
    mock_master.settings = {
        "settings": {
            # Multiplier dependencies
            "start_multi_val": "1.5",
            "start_multi_time": "300",
            # Proximity checker dependencies
            "proximity_yellows": "0",
            "proximity_yellows_distance": "0.05",
            # threshold checker dependencies
            "start_minute": "0",
            "end_minute": "999",
            "max_safety_cars": "999",
            "min_time_between": "0",
            "off_min": "4",
            "stopped_min": "2",
            # Detector dependencies
            "random": "0",
            "random_prob": "0.5",
            "random_max_occ": "1",
            "stopped": "1",
            "off": "1",
            # Combined threshold
            "stopped_weight": "1",
            "off_weight": "1",
            "combined": "1",
            "combined_min": "7",
            "combined_message": "Cars stopped and off track."
        }
    }
    gen = Generator(arguments=mock_arguments, master=mock_master)
    gen.start_time = 0  # Simulate the start time as 0 for testing

    # Setup mock drivers
    mock_drivers = create_mock_drivers()
    gen.drivers = mock_drivers
    
    # Setup detector
    detector_settings = DetectorSettings.from_settings(mock_master.settings)
    gen.detector = Detector.build_detector(detector_settings, mock_drivers)
    
    return gen

def test_command_sender_init():
    """Test the initialization of the CommandSender."""
    mock_arguments = Mock()    
    # This needs to be True to make tests work on MacOS
    mock_arguments.disable_window_interactions = True
    
    # We need the generator to send actual commands
    mock_arguments.dry_run = False
    generator = Generator(arguments=mock_arguments)
    assert isinstance(generator.command_sender, CommandSender)

    # In this case, we want to avoid sending commands
    mock_arguments.dry_run = True
    generator = Generator(arguments=mock_arguments)
    assert isinstance(generator.command_sender, MockSender)


def test_threshold_no_multiplier(generator):
    """Test when multiplier is 0."""
    generator.master.settings["settings"]["start_multi_val"] = "0"
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold

def test_threshold_no_adjustment(generator):
    """Test when adjustment time has passed."""
    generator.master.settings["settings"]["start_multi_time"] = "0"
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold

def test_threshold_with_multiplier(generator):
    """Test when multiplier is applied."""
    generator.start_time = time.time() - 295  # Simulate 295 seconds since start
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    expected = math.ceil(threshold * 1.5)  # Multiplier is 1.5
    assert result == expected

def test_threshold_no_adjustment_due_to_time(generator):
    """Test when adjustment time has passed."""
    generator.start_time = time.time() - 301  # Simulate 301 seconds since start
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold

def test_adjust_for_proximity_disabled(generator):
    """Test adjustment method when proximity_yellows = 0"""
    generator.master.settings["settings"]["proximity_yellows"] = "0"
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 5

def test_adjust_for_proximity_empty_list_arg(generator):
    """Test adjustment method when the passed list is empty"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = []

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 0

def test_adjust_for_proximity_no_cars_in_range(generator):
    """Test adjustment method when no cars are within range of each other"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 1

def test_adjust_for_proximity_single_outlier(generator):
    """Test adjustment method when a single outlier exists"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = [2, 4, 6, 8]
    car_distances_list = [0.1, 0.11, 0.12, 0.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 3

def test_adjust_for_proximity_distance_adjustment_down(generator):
    """Test adjustment method when the proximity distance is lowered"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    generator.master.settings["settings"]["proximity_yellows_distance"] = "0.01"
    car_indexes_list = [2, 4, 6, 8]
    car_distances_list = [0.1, 0.11, 0.14, 0.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 2

def test_adjust_for_proximity_distance_adjustment_up(generator):
    """Test adjustment method when the proximity distance is raised"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    generator.master.settings["settings"]["proximity_yellows_distance"] = "0.10"
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.14, 0.2, 0.5]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 4

def test_adjust_for_proximity_multiple_outliers(generator):
    """Test adjustment method when multiple outliers exist"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.12, 0.2, 0.8]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 3

def test_adjust_for_proximity_multiple_clusters(generator):
    """Test adjustment method when multiple clusters exist"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.12, 0.2, 0.22]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 3

def test_adjust_for_proximity_equidistant_cars(generator):
    """Test adjustment method when cars are equidistant at the threshold"""
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    car_indexes_list = [2, 4, 6, 8, 10, 12, 14]
    car_distances_list = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1
        
    result = generator._adjust_for_proximity(car_indexes_list)

    # This should return 2 because the sliding window of length 0.05 will only ever contain two cars
    assert result == 2

def test_adjust_for_proximity_longer_distance_across_finish(generator):
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    generator.master.settings["settings"]["proximity_yellows_distance"] = "0.40"
    car_indexes_list = [2, 4, 6, 8, 10, 12]
    car_distances_list = [0.7, 0.8, 0.9, 1.0, 0.1, 0.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1
        
    result = generator._adjust_for_proximity(car_indexes_list)
    # This should return 5 because only the cars on the ends are not in range
    assert result == 5

def test_adjust_for_proximity_lapped_cars(generator):
    """ This situation should not happen but adding in case we mess up in the future """
    generator.master.settings["settings"]["proximity_yellows"] = "1"
    generator.master.settings["settings"]["proximity_yellows_distance"] = "0.40"
    car_indexes_list = [2, 4, 6, 8, 10, 12]
    car_distances_list = [1.7, 2.8, 3.9, 4.0, 5.1, 6.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1
        
    result = generator._adjust_for_proximity(car_indexes_list)
    # This should return 5 because only the cars on the ends are not in range
    # This is an extreme example with cars on different laps, but still at the same spot
    assert result == 5


def test_notify_race_started_calls_both_components(generator, mocker):
    """Test that _notify_race_started calls race_started on both detector and threshold_checker"""
    
    # Create mock detector and threshold_checker
    generator.detector = Mock(spec=Detector)
    generator.threshold_checker = Mock(spec=ThresholdChecker)
    
    start_time = 1000.0
    generator._notify_race_started(start_time)
    
    # Verify both components were called
    generator.detector.race_started.assert_called_once_with(start_time)
    generator.threshold_checker.race_started.assert_called_once_with(start_time)

def test_check_combined_when_turned_off(generator):
    generator.master.settings["settings"]["combined"] = 0

    stopped_cars_count = 1
    off_track_cars_count = 1

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    assert result == "Combined yellows disabled"

def test_check_combined_no_stopped_no_off(generator):
    generator._start_safety_car = Mock()

    stopped_cars_count = 0
    off_track_cars_count = 0

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_no_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    stopped_cars_count = 3
    off_track_cars_count = 0

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_not_called()

def test_check_combined_no_stopped_yes_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    stopped_cars_count = 0
    off_track_cars_count = 3

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_yes_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    stopped_cars_count = 3
    off_track_cars_count = 3

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_yes_off_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined_min"] = 8

    stopped_cars_count = 4
    off_track_cars_count = 4

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_called_once()

def test_check_combined_with_modified_weights_under_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["stopped_weight"] = 2

    stopped_cars_count = 2
    off_track_cars_count = 3

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_not_called()

def test_check_combined_with_modified_weights_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["off_weight"] = 2

    stopped_cars_count = 3
    off_track_cars_count = 3

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_called_once()

def test_check_combined_with_modified_weights_not_whole_numbers(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["stopped_weight"] = 1.5
    generator.master.settings["settings"]["off_weight"] = 1.5

    stopped_cars_count = 3
    off_track_cars_count = 3

    result = generator._check_combined(stopped_cars_count, off_track_cars_count)
    generator._start_safety_car.assert_called_once()
