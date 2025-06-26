import pytest
import time
import math
from unittest.mock import MagicMock, Mock
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
    # This should return 3 because each car (except the ends of the list) is within range of
    # the car before and after it in the list
    assert result == 3
    
def test_send_wave_arounds_disabled(generator):
    """Test when wave arounds are disabled."""
    generator.master.settings["settings"]["wave_arounds"] = "0"
    generator.master.settings["settings"]["laps_before_wave_arounds"] = "2"
    result = generator._send_wave_arounds()
    assert result is True

def test_send_wave_arounds_not_time_yet(generator):
    """Test when it's not time for wave arounds."""
    generator.master.settings["settings"]["wave_arounds"] = "1"
    generator.master.settings["settings"]["laps_before_wave_arounds"] = "2"
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 6  # Not yet at wave lap
    result = generator._send_wave_arounds()
    assert result is False

def test_send_wave_arounds_wave_ahead_of_class_lead(mocker, generator):
    """Test wave arounds for cars ahead of class lead."""
    generator.master.settings["settings"]["wave_arounds"] = "1"
    generator.master.settings["settings"]["laps_before_wave_arounds"] = "1"
    generator.master.settings["settings"]["wave_around_rules_index"] = "1"  # Wave ahead of class lead
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7
    generator.ir = MagicMock()

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: ["!w 1", "!w 2"])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_commands")

    result = generator._send_wave_arounds()

    # Assert waves were actually sent
    mock_wave_around_func.assert_called_once()
    mock_command_sender.assert_called_once_with(["!w 1", "!w 2"])
    assert result is True

def test_send_wave_arounds_no_eligible_cars(generator, mocker):
    """Test wave arounds when no cars are eligible."""
    generator.master.settings["settings"]["wave_arounds"] = "1"
    generator.master.settings["settings"]["laps_before_wave_arounds"] = "1"
    generator.master.settings["settings"]["wave_around_rules_index"] = "1"  # Wave ahead of class lead
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7  # At wave lap

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: [])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_command")

    generator.ir = MagicMock()

    result = generator._send_wave_arounds()
    mock_command_sender.assert_not_called()
    assert result is True