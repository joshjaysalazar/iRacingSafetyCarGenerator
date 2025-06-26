import importlib
import json
import pytest

from . import resources

from core.procedures.wave_arounds import (
    WaveAroundType,
    wave_arounds_factory,
    wave_lapped_cars,
    wave_ahead_of_class_lead,
)

def test_wave_arounds_factory_valid():
    assert wave_arounds_factory(WaveAroundType.WAVE_LAPPED_CARS) == wave_lapped_cars
    assert wave_arounds_factory(WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD) == wave_ahead_of_class_lead

def test_wave_arounds_factory_invalid():
    with pytest.raises(ValueError, match="Invalid wave around type: .*"):
        wave_arounds_factory("invalid_type")


"""
## No cars to wave ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  A(1.6)  B(1.5)  B(1.4)  C(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                               X               X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
@pytest.fixture
def setup_data():
    return ([
        {"CarIdx": 0, "CarClassID": 11, "CarNumber": "0"}, # pace car with a unique class
        {"CarIdx": 1, "CarClassID": 1, "CarNumber": "1"},
        {"CarIdx": 2, "CarClassID": 1, "CarNumber": "2"},
        {"CarIdx": 3, "CarClassID": 1, "CarNumber": "3"},
        {"CarIdx": 4, "CarClassID": 1, "CarNumber": "4"},
        {"CarIdx": 5, "CarClassID": 2, "CarNumber": "5"},
        {"CarIdx": 6, "CarClassID": 2, "CarNumber": "6"},
        {"CarIdx": 7, "CarClassID": 3, "CarNumber": "7"},
        {"CarIdx": 8, "CarClassID": 3, "CarNumber": "8"},
    ],
    [0.1, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2], # default order represents "No cars to wave" case
    [False, False, False, False, False, False, False, False, False], # no cars on pit road
    0 # pace car index
    )

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_no_cars_to_wave(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_no_cars_to_wave(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected


"""
## No cars to wave - mixed classes ##

             S/F           v       v                       v       v      v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  B(1.8)  C(1.7)  A(1.6)  B(1.5)  C(1.4)  A(1.3) B(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X       X       X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
@pytest.fixture
def setup_data_mixed_classes(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    drivers[2]["CarClassID"] = 2
    drivers[3]["CarClassID"] = 3
    drivers[6]["CarClassID"] = 1
    drivers[7]["CarClassID"] = 2
    drivers[8]["CarClassID"] = 3
    return (drivers, car_positions, on_pit_road, pace_car_idx)

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_no_cars_to_wave(setup_data_mixed_classes):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_mixed_classes
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_no_cars_to_wave(setup_data_mixed_classes):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_mixed_classes
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected


"""
## Two leaders lap ahead - B got lapped, A is ahead of lead ##

             S/F   v                       v       
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    B(2.9)  A(1.8)  A(1.7)  A(2.6)  B(1.5)  B(1.4)  C(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       X                       X
wave_lapped_cars   -       -       -       -       X       X       -      -
wave_ahead_of_CL   -       X       X       -       -       -       -      -
"""
@pytest.fixture
def setup_data_two_lap_ahead(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    drivers[1]["CarClassID"] = 2
    car_positions[1] = 2.9
    car_positions[4] = 2.6
    return (drivers, car_positions, on_pit_road, pace_car_idx)

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_two_lapped(setup_data_two_lap_ahead):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_two_lap_ahead
    expected = ['!w 5', '!w 6']
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_all_of_A_but_lead(setup_data_two_lap_ahead):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_two_lap_ahead
    expected = ['!w 2', '!w 3']
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected


"""
## Two leaders lap ahead - B got lapped, A is split by lead ##

             S/F   v               v               
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    B(2.9)  A(1.8)  A(2.7)  A(1.6)  B(1.5)  B(1.4)  C(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       X                       X
wave_lapped_cars   -       -       -       X       X       X       -      -
wave_ahead_of_CL   -       X       -       -       -       -       -      -
"""
@pytest.fixture
def setup_data_class_a_split(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    drivers[1]["CarClassID"] = 2
    car_positions[1] = 2.9
    car_positions[3] = 2.7
    return (drivers, car_positions, on_pit_road, pace_car_idx)

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_one_lapped(setup_data_class_a_split):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_class_a_split
    expected = ["!w 4", "!w 5", "!w 6"]
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead(setup_data_class_a_split):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_class_a_split
    expected = ["!w 2"]
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

"""
## B and C about to be lapped ##

             S/F   v       v       v       v               v              v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(2.9)  A(2.8)  A(2.7)  A(2.6)  B(1.5)  B(2.4)  C(1.3) C(2.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                                       X              X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       X       -       X      -
"""
@pytest.fixture
def setup_data_slower_classes_waves(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    car_positions[1] = 2.9
    car_positions[2] = 2.8
    car_positions[3] = 2.7
    car_positions[4] = 2.6
    car_positions[6] = 2.4
    car_positions[8] = 2.2
    return (drivers, car_positions, on_pit_road, pace_car_idx)

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_slower_classes_none(setup_data_slower_classes_waves):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_slower_classes_waves
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_slower_classes(setup_data_slower_classes_waves):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_slower_classes_waves
    expected = ["!w 5", "!w 7"]
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

"""
## Some in class A, but one pitted ##

             S/F                   v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(2.7)  B(1.6)  A(1.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders              Pit     X       X       Pit     X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""

"""
## Two leaders lap ahead - B got lapped, A is ahead of lead ##

             S/F   v               v       v       
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    B(2.9)  A(1.8)  A(1.7)  A(2.6)  B(1.5)  B(1.4)  C(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X               PIT     X       PIT             X
wave_lapped_cars   -       -       -       -       /       X       -      -
wave_ahead_of_CL   -       X       /       -       -       -       -      -
"""
@pytest.fixture
def setup_data_skip_pits(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    drivers[1]["CarClassID"] = 2
    car_positions[1] = 2.9
    car_positions[4] = 2.6
    on_pit_road[3] = True
    return (drivers, car_positions, on_pit_road, pace_car_idx)

@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_two_lapped_but_one_pitted(setup_data_skip_pits):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_skip_pits
    expected = ['!w 6']
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead_but_one_pitted(setup_data_skip_pits):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data_skip_pits
    expected = ['!w 2']
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected


""" 
This test case represents a real world example where the commands were sent right when the 
SC came out and there were some cars stuck between the SC and the overall lead. It showed
an issue where the trapped cars were automatically let by, but we waved them too so they gained 
a lap. Based on this, the logic was updated to only wave those that are ahead of their class
lead BUT behind the overall lead.
"""
def test_wave_ahead_of_class_real_world_example():
    setup_data = None
    with importlib.resources.path(resources, "real_world_data.json") as file_name:
        with open(file_name) as f:
            setup_data = json.load(f)

    assert setup_data is not None, "Failed to load real world data"
    drivers = setup_data["drivers"]
    car_positions = setup_data["car_positions"]
    on_pit_road = setup_data["on_pit_road"]
    pace_car_idx = setup_data["pace_car_idx"]
    expected = setup_data["expected_wave_around_commands"]
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected
