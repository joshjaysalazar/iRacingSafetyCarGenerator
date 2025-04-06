import pytest

from core.procedures.class_split import get_split_class_commands

drivers = [
    {
        "CarIdx": 0,
        "CarNumber": "1",
        "CarNumberRaw": 1,
        "CarClassID": 4016,
        "CarClassEstLapTime": 40.9251,
        "CarIsPaceCar": 0,
    },
    {
        "CarIdx": 1,
        "CarNumber": "2",
        "CarNumberRaw": 2,
        "CarClassID": 4016,
        "CarClassEstLapTime": 40.9251,
        "CarIsPaceCar": 0,
    },
    {
        "CarIdx": 2,
        "CarNumber": "3",
        "CarNumberRaw": 3,
        "CarClassID": 3002,        
        "CarClassEstLapTime": 46.6068,
        "CarIsPaceCar": 0,
    },
    {
        "CarIdx": 3,
        "CarNumber": "4",
        "CarNumberRaw": 4,
        "CarClassID": 3002,        
        "CarClassEstLapTime": 46.6068,
        "CarIsPaceCar": 0,
    },
    {
        "CarIdx": 4,
        "CarNumber": "0",
        "CarNumberRaw": 0,
        "CarClassID": 11,
        "CarClassEstLapTime": 39.8243,
        "CarIsPaceCar": 1,
    },
]


split_class_test_data = [
    {
        # Test case: Cars are already in the right order
        "drivers": drivers,
        "car_positions": [2.0, 1.9, 1.8, 1.7, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, False, False, False, False, False, False, False, False],
        "expected": [],
    },
    {
        # Two are swapped
        "drivers": drivers,
        "car_positions": [2.0, 1.8, 1.9, 1.7, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, False, False, False, False, False, False, False, False],
        "expected": ["!eol 3 Splitting classes", "!eol 4 Splitting classes"],
    },
    {
        # Slower class is ahead
        "drivers": drivers,
        "car_positions": [1.8, 1.7, 2.0, 1.9, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, False, False, False, False, False, False, False, False],
        "expected": ["!eol 3 Splitting classes", "!eol 4 Splitting classes"],
    },
    {
        # Faster class is pitting
        "drivers": drivers,
        "car_positions": [2.0, 1.8, 1.9, 1.7, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, True, False, False, False, False, False, False, False],
        "expected": [],
    },
    {
        # Slower class is pitting
        "drivers": drivers,
        "car_positions": [2.0, 1.8, 1.9, 1.7, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, False, True, False, False, False, False, False, False],
        "expected": [],
    },
    {
        # Car in the back is pitting
        "drivers": drivers,
        "car_positions": [2.0, 1.8, 1.9, 1.7, 2.1, -1, -1, -1, -1],
        "on_pit_road": [False, False, False, True, False, False, False, False, False],
        "expected": ["!eol 3 Splitting classes", "!eol 4 Splitting classes"],
    },
]

@pytest.mark.parametrize("test_data", split_class_test_data)
def test_get_split_class_commands(test_data):
    commands = get_split_class_commands(test_data["drivers"], test_data["car_positions"], test_data["on_pit_road"], 4) # 4 = the position of the pace car in our test data

    assert commands == test_data["expected"]