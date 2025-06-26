import pytest
import time
import math
from unittest.mock import Mock
from core.generator import Generator

@pytest.fixture
def generator():
    mock_arguments = Mock()
    mock_arguments.disable_window_interactions = True
    mock_master = Mock()
    mock_master.settings = {
        "settings": {
            "start_multi_val": "1.5",
            "start_multi_time": "300",
            "proximity_yellows": 0,
            "proximity_yellows_distance": 0.05
        }
    }
    gen = Generator(arguments=mock_arguments, master=mock_master)
    gen.start_time = 0  # Simulate the start time as 0 for testing
    mock_drivers = Mock()
    mock_drivers.current_drivers = []
    for i in range(0,65):
        mock_drivers.current_drivers.append({"lap_distance": 0})
    setattr(gen, "drivers", mock_drivers)
    return gen

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
    generator.master.settings["settings"]["proximity_yellows"] = 0
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = []

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == 0

def test_adjust_for_proximity_no_cars_in_range(generator):
    """Test adjustment method when no cars are within range of each other"""
    # The test data is written assuming a distance setting of 0.05
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.05
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.2, 0.3, 0.4, 0.5]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 1, 4: 1, 6: 1, 8: 1, 10: 1}

def test_adjust_for_proximity_single_outlier(generator):
    """Test adjustment method when a single outlier exists"""
    # The test data is written assuming a distance setting of 0.05
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.05
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = [2, 4, 6, 8]
    car_distances_list = [0.1, 0.11, 0.12, 0.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 3, 4: 3, 6: 3, 8: 1}

def test_adjust_for_proximity_distance_adjustment_down(generator):
    """Test adjustment method when the proximity distance is lowered"""
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.01
    car_indexes_list = [2, 4, 6, 8]
    car_distances_list = [0.1, 0.11, 0.14, 0.2]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 2, 4: 2, 6: 1, 8: 1}

def test_adjust_for_proximity_distance_adjustment_up(generator):
    """Test adjustment method when the proximity distance is raised"""
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.10
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.14, 0.2, 0.5]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 4, 4: 4, 6: 4, 8: 4, 10: 1}

def test_adjust_for_proximity_multiple_outliers(generator):
    """Test adjustment method when multiple outliers exist"""
    # The test data is written assuming a distance setting of 0.05
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.05
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.12, 0.2, 0.8]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 3, 4: 3, 6: 3, 8: 1, 10: 1}

def test_adjust_for_proximity_multiple_clusters(generator):
    """Test adjustment method when multiple clusters exist"""
        # The test data is written assuming a distance setting of 0.05
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.05
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = [2, 4, 6, 8, 10]
    car_distances_list = [0.1, 0.11, 0.12, 0.2, 0.22]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1

    result = generator._adjust_for_proximity(car_indexes_list)
    assert result == {2: 3, 4: 3, 6: 3, 8: 2, 10: 2}

def test_adjust_for_proximity_equidistant_cars(generator):
    """Test adjustment method when cars are equidistant at the threshold"""
        # The test data is written assuming a distance setting of 0.05
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.05
    generator.master.settings["settings"]["proximity_yellows"] = 1
    car_indexes_list = [2, 4, 6, 8, 10, 12, 14]
    car_distances_list = [0.1, 0.15, 0.2, 0.25, 0.3, 0.35, 0.4]
    num = 0
    for idx in car_indexes_list:
        generator.drivers.current_drivers[idx]["lap_distance"] = car_distances_list[num]
        num += 1
        
    result = generator._adjust_for_proximity(car_indexes_list)
    # This should return 3 because each car (except the ends of the list) is within range of
    # the car before and after it in the list
    assert result == {2: 2, 4: 3, 6: 3, 8: 3, 10: 3, 12: 3, 14: 2}

def test_check_combined_when_turned_off(generator):
    generator.master.settings["settings"]["combined"] = 0
    generator.master.settings["settings"]["combined_min"] = 7
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."

    stopped_cars = {}
    off_track_cars = {}

    result = generator._check_combined(stopped_cars, off_track_cars)
    assert result == "Combined yellows disabled"

def test_check_combined_no_stopped_no_off(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 7
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {}
    off_track_cars = {}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_no_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 7
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {2: 3, 4: 3, 6: 3}
    off_track_cars = {}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_not_called()

def test_check_combined_no_stopped_yes_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 7
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {}
    off_track_cars = {2: 3, 4: 3, 6: 3}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_yes_off_under_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 7
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {1: 3, 3: 3, 5: 3}
    off_track_cars = {2: 3, 4: 3, 6: 3}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_not_called()

def test_check_combined_yes_stopped_no_off_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 4
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {1: 4, 3: 3, 5: 2}
    off_track_cars = {}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_called_once()

def test_check_combined_no_stopped_yes_off_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 4
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {}
    off_track_cars = {2: 2, 4: 3, 6: 4}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_called_once()

def test_check_combined_yes_stopped_yes_off_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1
    generator.master.settings["settings"]["off_weight"] = 1

    stopped_cars = {1: 2, 3: 3, 5: 4}
    off_track_cars = {2: 2, 4: 3, 6: 4}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_called_once()

def test_check_combined_with_modified_weights_under_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 2
    generator.master.settings["settings"]["off_weight"] = 1
    
    stopped_cars = {1: 2, 3: 2, 5: 2}
    off_track_cars = {2: 3, 4: 3, 6: 3}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_not_called()

def test_check_combined_with_modified_weights_over_threshold(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 2
    generator.master.settings["settings"]["off_weight"] = 1
    
    stopped_cars = {1: 3, 3: 3, 5: 3}
    off_track_cars = {2: 3, 4: 3, 6: 3}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_called_once()

def test_check_combined_with_modified_weights_not_whole_numbers(generator):
    generator._start_safety_car = Mock()

    generator.master.settings["settings"]["combined"] = 1
    generator.master.settings["settings"]["combined_min"] = 8
    generator.master.settings["settings"]["combined_message"] = "Cars stopped and off track."
    generator.master.settings["settings"]["stopped_weight"] = 1.5
    generator.master.settings["settings"]["off_weight"] = 1.5
    
    stopped_cars = {1: 3, 3: 3, 5: 3}
    off_track_cars = {2: 3, 4: 3, 6: 3}

    result = generator._check_combined(stopped_cars, off_track_cars)
    generator._start_safety_car.assert_called_once()
