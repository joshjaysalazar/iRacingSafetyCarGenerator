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

@pytest.fixture
def setup_data():
    return ([
        {"CarIdx": 0, "CarClassID": 1, "CarNumber": "0"},
        {"CarIdx": 1, "CarClassID": 11, "CarNumber": "1"},  # pace car with a unique class
        {"CarIdx": 2, "CarClassID": 1, "CarNumber": "2"},
        {"CarIdx": 3, "CarClassID": 1, "CarNumber": "3"},
        {"CarIdx": 4, "CarClassID": 1, "CarNumber": "4"},
        {"CarIdx": 5, "CarClassID": 2, "CarNumber": "5"},
        {"CarIdx": 6, "CarClassID": 3, "CarNumber": "6"},
        {"CarIdx": 7, "CarClassID": 2, "CarNumber": "7"},
        {"CarIdx": 8, "CarClassID": 3, "CarNumber": "8"},
    ],
    [1.9, 0.1, 1.8, 1.7, 1.5, 1.6, 1.4, 1.3, 1.2], # default order represents "No cars to wave" case
    [False, False, False, False, False, False, False, False, False], # no cars on pit road
    1 # pace car index
    )


"""
## No cars to wave ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(1.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       X               X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
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
## All but leader class A ##

             S/F                                   v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(2.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders                              X       X       X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_no_cars_to_wave2(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[4] == 1.5 # make sure we update the right one
    car_positions[4] = 2.5
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_all_of_A_but_lead(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[4] == 1.5 # make sure we update the right one
    car_positions[4] = 2.5
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

"""
## Some in class A ##

             S/F                   v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(2.7)  B(1.6)  A(1.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders                      X       X               X
wave_lapped_cars   -       -       -       -       X       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_one_lapped(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[3] == 1.7 # make sure we update the right one
    car_positions[3] = 2.7
    expected = ["!w 5"]
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[3] == 1.7 # make sure we update the right one
    car_positions[3] = 2.7
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

"""
## Some in class B/C ##

             S/F                                                   v      v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(1.5)  C(1.4)  B(2.3) C(2.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                                               X      X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -
"""
@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_slower_classes_none(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[7] == 1.3 # make sure we update the right one
    car_positions[7] = 2.3
    assert car_positions[8] == 1.2 # make sure we update the right one
    car_positions[8] = 2.2
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_slower_classes(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[7] == 1.3 # make sure we update the right one
    car_positions[7] = 2.3
    assert car_positions[8] == 1.2 # make sure we update the right one
    car_positions[8] = 2.2
    expected = []
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
@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_one_lapped_but_pitted(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[3] == 1.7 # make sure we update the right one
    car_positions[3] = 2.7
    on_pit_road[2] = True  # car 2 is on pit road
    on_pit_road[5] = True  # car 5 is on pit road
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead_but_one_pitted(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[3] == 1.7 # make sure we update the right one
    car_positions[3] = 2.7
    on_pit_road[2] = True  # car 2 is on pit road
    on_pit_road[5] = True  # car 5 is on pit road
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

"""
## Some in class B/C, but they are pitted! ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(1.5)  C(1.4)  B(2.3) C(2.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       Pit             Pit     X      X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -

"""
@pytest.mark.skip(reason="Not implemented yet")
def test_wave_lapped_cars_slower_classes_none_and_pitted(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[7] == 1.3 # make sure we update the right one
    assert drivers[7]["CarClassID"] == 2
    car_positions[7] = 2.3
    assert car_positions[8] == 1.2 # make sure we update the right one
    assert drivers[8]["CarClassID"] == 3
    car_positions[8] = 2.2
    assert drivers[5]["CarClassID"] == 2
    on_pit_road[5] = True  # car 4 is on pit road
    assert drivers[6]["CarClassID"] == 3
    on_pit_road[6] = True  # car 6 is on pit road
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_slower_classes_but_pitted(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    assert car_positions[7] == 1.3 # make sure we update the right one
    assert drivers[7]["CarClassID"] == 2
    car_positions[7] = 2.3
    assert car_positions[8] == 1.2 # make sure we update the right one
    assert drivers[8]["CarClassID"] == 3
    car_positions[8] = 2.2
    assert drivers[5]["CarClassID"] == 2
    on_pit_road[5] = True  # car 4 is on pit road
    assert drivers[6]["CarClassID"] == 3
    on_pit_road[6] = True  # car 6 is on pit road
    expected = []
    result = wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

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
