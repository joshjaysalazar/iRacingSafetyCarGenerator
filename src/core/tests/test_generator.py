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
    mock_drivers.previous_drivers = []
    for i in range(0,65):
        mock_drivers.current_drivers.append({"lap_distance": 0, "laps_completed": 0, "track_loc": 0})
        mock_drivers.previous_drivers.append({"lap_distance": 0, "laps_completed": 0, "track_loc": 0})
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.01
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.10
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.40
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
    generator.master.settings["settings"]["proximity_yellows"] = 1
    generator.master.settings["settings"]["proximity_yellows_distance"] = 0.40
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

@pytest.mark.xfail(
    reason="Before refactoring, Safety Car events were able to trigger multiple times in a single loop cycle.",
    strict=True
)
def test_loop_triggers_safety_car_three_times(generator, mocker):
    """Test that _check_random triggers _start_safety_car when conditions are met."""
    mocker.patch.object(generator, '_start_safety_car', side_effect=lambda *args, **kwargs: setattr(generator, 'total_sc_events', generator.total_sc_events + 1))
    mocker.patch.object(generator, '_wait_for_green_flag')
    mocker.patch.object(generator.drivers, 'update')
    mocker.patch('time.sleep')

    # General settings
    generator.master.settings["settings"]["max_safety_cars"] = "1" # << It is limited to 1, but calls 3 times
    generator.master.settings["settings"]["start_minute"] = "0"
    generator.master.settings["settings"]["end_minute"] = "10"
    generator.master.settings["settings"]["min_time_between"] = "0"

    # Force a random event to trigger
    generator.master.settings["settings"]["random"] = "1"
    generator.master.settings["settings"]["random_prob"] = "0.5"
    generator.master.settings["settings"]["random_max_occ"] = "3"
    generator.master.settings["settings"]["random_message"] = "Random Event"
    mocker.patch('random.random', return_value=0.001)  # Simulate a random value that triggers the random event

    # Force a stopped event to trigger
    generator.master.settings["settings"]["stopped"] = "1"
    generator.master.settings["settings"]["stopped_min"] = "0"
    generator.master.settings["settings"]["stopped_message"] = "Stopped Event"

    # Force an off track event to trigger
    generator.master.settings["settings"]["off"] = "1"
    generator.master.settings["settings"]["off_min"] = "0"
    generator.master.settings["settings"]["off_message"] = "Off Track Event"

    # Simulate a loop cycle
    generator.start_time = time.time() - 60  # Simulate start time
    generator._loop()

    assert generator._start_safety_car.call_count == 3
    generator._start_safety_car.assert_any_call("Random Event")
    generator._start_safety_car.assert_any_call("Stopped Event")
    generator._start_safety_car.assert_any_call("Off Track Event")

def test_loop_triggers_safety_car_only_once(generator, mocker):
    """Test that _check_random triggers _start_safety_car when conditions are met."""
    mocker.patch.object(generator, '_start_safety_car', side_effect=lambda *args, **kwargs: setattr(generator, 'total_sc_events', generator.total_sc_events + 1))
    mocker.patch.object(generator, '_wait_for_green_flag')
    mocker.patch.object(generator.drivers, 'update')
    mocker.patch('time.sleep')

    # General settings
    generator.master.settings["settings"]["max_safety_cars"] = "1"
    generator.master.settings["settings"]["start_minute"] = "0"
    generator.master.settings["settings"]["end_minute"] = "10"
    generator.master.settings["settings"]["min_time_between"] = "0"

    # Force a random event to trigger
    generator.master.settings["settings"]["random"] = "1"
    generator.master.settings["settings"]["random_prob"] = "0.5"
    generator.master.settings["settings"]["random_max_occ"] = "3"
    generator.master.settings["settings"]["random_message"] = "Random Event"
    mocker.patch('random.random', return_value=0.001)  # Simulate a random value that triggers the random event

    # Force a stopped event to trigger
    generator.master.settings["settings"]["stopped"] = "1"
    generator.master.settings["settings"]["stopped_min"] = "0"
    generator.master.settings["settings"]["stopped_message"] = "Stopped Event"

    # Force an off track event to trigger
    generator.master.settings["settings"]["off"] = "1"
    generator.master.settings["settings"]["off_min"] = "0"
    generator.master.settings["settings"]["off_message"] = "Off Track Event"

    # Simulate a loop cycle
    generator.start_time = time.time() - 60  # Simulate start time
    generator._loop()

    assert generator._start_safety_car.call_count == 1
    generator._start_safety_car.assert_any_call("Random Event")