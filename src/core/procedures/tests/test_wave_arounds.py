import importlib
import json
import pytest

from . import resources

from core.drivers import Driver
from core.procedures.wave_arounds import (
    WaveAroundType,
    wave_arounds_factory,
    wave_lapped_cars,
    wave_ahead_of_class_lead,
    wave_combined,
)
from irsdk import TrkLoc

def create_driver_from_test_data(idx: int, car_number: str, car_class_id: int,
                                   total_distance: float, on_pit_road: bool) -> Driver:
    """Helper to create Driver objects from test data."""
    laps_completed = int(total_distance)
    lap_distance = total_distance - laps_completed
    # laps_started is the lap you're currently on (0-indexed in iRacing)
    # If you've completed 1 lap and are 80% through lap 2, laps_started = 1
    laps_started = laps_completed if lap_distance == 0 else laps_completed + 1
    return {
        "driver_idx": idx,
        "car_number": car_number,
        "car_class_id": car_class_id,
        "is_pace_car": car_class_id == 11,  # pace car has unique class 11
        "laps_completed": laps_completed,
        "laps_started": laps_started,
        "lap_distance": lap_distance,
        "total_distance": total_distance,
        "track_loc": TrkLoc.on_track,
        "on_pit_road": on_pit_road,
    }

def test_wave_arounds_factory_valid():
    assert wave_arounds_factory(WaveAroundType.WAVE_LAPPED_CARS) == wave_lapped_cars
    assert wave_arounds_factory(WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD) == wave_ahead_of_class_lead
    assert wave_arounds_factory(WaveAroundType.WAVE_COMBINED) == wave_combined

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
wave_combined      -       -       -       -       -       -       -      -
"""
@pytest.fixture
def setup_data():
    car_classes = [11, 1, 1, 1, 1, 2, 2, 3, 3]
    car_numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8"]
    car_positions = [0.1, 1.9, 1.8, 1.7, 1.6, 1.5, 1.4, 1.3, 1.2]
    on_pit_road = [False] * 9

    drivers = [
        create_driver_from_test_data(i, car_numbers[i], car_classes[i],
                                       car_positions[i], on_pit_road[i])
        for i in range(9)
    ]

    return drivers, 0  # drivers list and pace car index

def test_wave_lapped_cars_no_cars_to_wave(setup_data):
    drivers, pace_car_idx = setup_data
    expected = []
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_no_cars_to_wave(setup_data):
    drivers, pace_car_idx = setup_data
    expected = []
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_no_cars_to_wave(setup_data):
    drivers, pace_car_idx = setup_data
    expected = []
    result = wave_combined(drivers, pace_car_idx)
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
wave_combined      -       -       -       -       -       -       -      -
"""
@pytest.fixture
def setup_data_mixed_classes(setup_data):
    drivers, pace_car_idx = setup_data
    drivers[2]["car_class_id"] = 2
    drivers[3]["car_class_id"] = 3
    drivers[6]["car_class_id"] = 1
    drivers[7]["car_class_id"] = 2
    drivers[8]["car_class_id"] = 3
    return (drivers, pace_car_idx)

def test_wave_lapped_cars_no_cars_to_wave_mixed(setup_data_mixed_classes):
    drivers, pace_car_idx = setup_data_mixed_classes
    expected = []
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_no_cars_to_wave_mixed(setup_data_mixed_classes):
    drivers, pace_car_idx = setup_data_mixed_classes
    expected = []
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_no_cars_to_wave_mixed(setup_data_mixed_classes):
    drivers, pace_car_idx = setup_data_mixed_classes
    expected = []
    result = wave_combined(drivers, pace_car_idx)
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
wave_combined      -       X       X       -       X       X       -      -
"""
@pytest.fixture
def setup_data_two_lap_ahead(setup_data):
    drivers, pace_car_idx = setup_data
    drivers[1]["car_class_id"] = 2
    drivers[1]["total_distance"] = 2.9
    drivers[1]["laps_completed"] = 2
    drivers[1]["laps_started"] = 3  # Currently on lap 3
    drivers[1]["lap_distance"] = 0.9
    drivers[4]["total_distance"] = 2.6
    drivers[4]["laps_completed"] = 2
    drivers[4]["laps_started"] = 3  # Currently on lap 3
    drivers[4]["lap_distance"] = 0.6
    return (drivers, pace_car_idx)

def test_wave_lapped_cars_two_lapped(setup_data_two_lap_ahead):
    drivers, pace_car_idx = setup_data_two_lap_ahead
    expected = ['!w 5', '!w 6']
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_all_of_A_but_lead(setup_data_two_lap_ahead):
    drivers, pace_car_idx = setup_data_two_lap_ahead
    expected = ['!w 2', '!w 3']
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_combines_both_methods(setup_data_two_lap_ahead):
    drivers, pace_car_idx = setup_data_two_lap_ahead
    # wave_lapped_cars returns ['!w 5', '!w 6']
    # wave_ahead_of_class_lead returns ['!w 2', '!w 3']
    expected = ['!w 5', '!w 6', '!w 2', '!w 3']
    result = wave_combined(drivers, pace_car_idx)
    assert result == expected


"""
## Two leaders lap ahead - B got lapped, A is split by lead ##

             S/F   v               v
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    PC(0.1)   |    B(2.9)  A(1.8)  A(2.7)  A(1.6)  B(1.5)  B(1.4)  C(1.3) C(1.2)
<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<

Class leaders      X               X                               X
wave_lapped_cars   -       -       -       X       X       X       -      -
wave_ahead_of_CL   -       X       -       -       -       -       -      -
wave_combined      -       X       -       X       X       X       -      -
"""
@pytest.fixture
def setup_data_class_a_split(setup_data):
    drivers, pace_car_idx = setup_data
    drivers[1]["car_class_id"] = 2
    drivers[1]["total_distance"] = 2.9
    drivers[1]["laps_completed"] = 2
    drivers[1]["laps_started"] = 3  # Currently on lap 3
    drivers[1]["lap_distance"] = 0.9
    drivers[3]["total_distance"] = 2.7
    drivers[3]["laps_completed"] = 2
    drivers[3]["laps_started"] = 3  # Currently on lap 3
    drivers[3]["lap_distance"] = 0.7
    return (drivers, pace_car_idx)

def test_wave_lapped_cars_one_lapped(setup_data_class_a_split):
    drivers, pace_car_idx = setup_data_class_a_split
    expected = ["!w 4", "!w 5", "!w 6"]
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead(setup_data_class_a_split):
    drivers, pace_car_idx = setup_data_class_a_split
    expected = ["!w 2"]
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_deduplicates(setup_data_class_a_split):
    drivers, pace_car_idx = setup_data_class_a_split
    # wave_lapped_cars returns ["!w 4", "!w 5", "!w 6"]
    # wave_ahead_of_class_lead returns ["!w 2"]
    expected = ["!w 4", "!w 5", "!w 6", "!w 2"]
    result = wave_combined(drivers, pace_car_idx)
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
wave_combined      -       -       -       -       X       -       X      -
"""
@pytest.fixture
def setup_data_slower_classes_waves(setup_data):
    drivers, pace_car_idx = setup_data
    for i, total_dist in [(1, 2.9), (2, 2.8), (3, 2.7), (4, 2.6), (6, 2.4), (8, 2.2)]:
        drivers[i]["total_distance"] = total_dist
        laps_completed = int(total_dist)
        drivers[i]["laps_completed"] = laps_completed
        drivers[i]["laps_started"] = laps_completed + 1  # Currently on next lap
        drivers[i]["lap_distance"] = total_dist - laps_completed
    return (drivers, pace_car_idx)

def test_wave_lapped_cars_slower_classes_none(setup_data_slower_classes_waves):
    drivers, pace_car_idx = setup_data_slower_classes_waves
    expected = []
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_slower_classes(setup_data_slower_classes_waves):
    drivers, pace_car_idx = setup_data_slower_classes_waves
    expected = ["!w 5", "!w 7"]
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_slower_classes(setup_data_slower_classes_waves):
    drivers, pace_car_idx = setup_data_slower_classes_waves
    # wave_lapped_cars returns []
    # wave_ahead_of_class_lead returns ["!w 5", "!w 7"]
    expected = ["!w 5", "!w 7"]
    result = wave_combined(drivers, pace_car_idx)
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
wave_combined      -       X       /       -       /       X       -      -
"""
@pytest.fixture
def setup_data_skip_pits(setup_data):
    drivers, pace_car_idx = setup_data
    drivers[1]["car_class_id"] = 2
    drivers[1]["total_distance"] = 2.9
    drivers[1]["laps_completed"] = 2
    drivers[1]["laps_started"] = 3  # Currently on lap 3
    drivers[1]["lap_distance"] = 0.9
    drivers[4]["total_distance"] = 2.6
    drivers[4]["laps_completed"] = 2
    drivers[4]["laps_started"] = 3  # Currently on lap 3
    drivers[4]["lap_distance"] = 0.6
    drivers[3]["on_pit_road"] = True  # A(1.7)
    drivers[5]["on_pit_road"] = True  # B(1.5)
    return (drivers, pace_car_idx)

def test_wave_lapped_cars_two_lapped_but_one_pitted(setup_data_skip_pits):
    drivers, pace_car_idx = setup_data_skip_pits
    expected = ['!w 6']
    result = wave_lapped_cars(drivers, pace_car_idx)
    assert result == expected

def test_wave_ahead_of_class_lead_two_ahead_but_one_pitted(setup_data_skip_pits):
    drivers, pace_car_idx = setup_data_skip_pits
    expected = ['!w 2']
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected

def test_wave_combined_skips_pitted_cars(setup_data_skip_pits):
    drivers, pace_car_idx = setup_data_skip_pits
    # wave_lapped_cars returns ['!w 6'] (5 is pitted)
    # wave_ahead_of_class_lead returns ['!w 2'] (3 is pitted)
    expected = ['!w 6', '!w 2']
    result = wave_combined(drivers, pace_car_idx)
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

    # Convert old format to Driver objects
    old_drivers = setup_data["drivers"]
    car_positions = setup_data["car_positions"]
    on_pit_road = setup_data["on_pit_road"]
    pace_car_idx = setup_data["pace_car_idx"]

    drivers = [
        create_driver_from_test_data(
            old_drivers[i]["CarIdx"],
            old_drivers[i]["CarNumber"],
            old_drivers[i]["CarClassID"],
            car_positions[i],
            on_pit_road[i]
        )
        for i in range(len(old_drivers))
    ]

    expected = setup_data["expected_wave_around_commands"]
    result = wave_ahead_of_class_lead(drivers, pace_car_idx)
    assert result == expected
