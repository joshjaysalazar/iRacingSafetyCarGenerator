# import pytest

# from core.procedures.wave_arounds import (
#     WaveAroundType,
#     wave_arounds_factory,
#     wave_lapped_cars,
#     wave_ahead_of_class_lead,
# )

# def test_wave_arounds_factory_valid():
#     assert wave_arounds_factory(WaveAroundType.WAVE_LAPPED_CARS) == wave_lapped_cars
#     assert wave_arounds_factory(WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD) == wave_ahead_of_class_lead

# def test_wave_arounds_factory_invalid():
#     with pytest.raises(ValueError, match="Invalid wave around type: .*"):
#         wave_arounds_factory("invalid_type")

# def test_wave_lapped_cars_not_implemented():
#     with pytest.raises(NotImplementedError, match="wave_lapped_cars is not implemented yet."):
#         wave_lapped_cars([], [], [], 0)

# def test_wave_ahead_of_class_lead_not_implemented():
#     with pytest.raises(NotImplementedError, match="wave_ahead_of_lead is not implemented yet."):
#         wave_ahead_of_class_lead([], [], [], 0)


import pytest
from src.core.procedures.wave_arounds import wave_lapped_cars

@pytest.fixture
def setup_data():
    return [
        {"CarIdx": 0, "CarClassID": 1},
        {"CarIdx": 1, "CarClassID": 99},  # pace car with a unique class
        {"CarIdx": 2, "CarClassID": 1},
        {"CarIdx": 3, "CarClassID": 2},
        {"CarIdx": 4, "CarClassID": 1},
        {"CarIdx": 5, "CarClassID": 2},
    ], [3.1, 3.5, 3.4, 2.4, 2.5, 2.6], [False, False, False, False, False, False], 1


"""
## No cars to wave ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(1.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       X               X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -

## All but leader class A ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(2.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders                              X       X       X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   X       X       X       -       -       -       -      -

## Some in class A ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(2.7)  B(1.6)  A(2.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders                      X       X               X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   X       X       -       -       -       -       -      -

## Some in class B/C ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(2.5)  C(1.4)  B(2.3) C(2.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                                               X      X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       X       -       X       -      -

## Some in class A, but one pitted ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(2.7)  B(1.6)  A(2.5)  C(1.4)  B(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders              Pit     X       X               X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   X       -       -       -       -       -       -      -

## Some in class B/C, but they are pitted! ##

             S/F
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    A(1.9)  A(1.8)  A(1.7)  B(1.6)  A(2.5)  C(1.4)  B(2.3) C(2.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X                       Pit             Pit     X      X
wave_lapped_cars   -       -       -       -       -       -       -      -
wave_ahead_of_CL   -       -       -       -       -       -       -      -

"""


def test_wave_lapped_cars_no_cars_to_wave(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    car_positions = [3.1, 3.2, 3.3, 2.4, 2.5, 2.6]  # all cars are properly ordered
    expected = []
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_lapped_cars_some_cars_to_wave(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    car_positions = [3.2, 3.3, 3.1, 2.5, 2.4]  # car 0, 4 out of place, considering laps
    expected = ["wave_car_0", "wave_car_4"]
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected
def test_wave_lapped_cars_all_on_pit_road(setup_data):
    drivers, car_positions, on_pit_road, pace_car_idx = setup_data
    car_positions = [3.2, 3.3, 3.1, 2.5, 2.4]  # car 0, 4 out of place, considering laps
    on_pit_road = [True, True, True, True, True]
    expected = []  # no cars to wave since all are on pit road
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected

def test_wave_lapped_cars_mixed_class(setup_data):
    drivers = [
        {"CarIdx": 0, "CarClassID": 1},
        {"CarIdx": 1, "CarClassID": 99},  # pace car with a unique class
        {"CarIdx": 2, "CarClassID": 1},
        {"CarIdx": 3, "CarClassID": 2},
        {"CarIdx": 4, "CarClassID": 3},
    ]
    car_positions = [3.2, 3.3, 3.1, 2.5, 2.4]  # car 0, 4 out of place, considering laps
    on_pit_road = [False, False, False, False, False]
    pace_car_idx = 1

    expected = ["wave_car_0", "wave_car_4"]
    result = wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx)
    assert result == expected