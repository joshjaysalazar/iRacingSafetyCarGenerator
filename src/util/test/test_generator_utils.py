import pytest

from pytest import approx
from util.generator_utils import positions_from_safety_car



@pytest.mark.parametrize("car_positions,expected", [
    ([0.9, 0.8, 0.7, 0.6, 0.0], [0.1, 0.2, 0.3, 0.4, 0.0]), # SC at S/F, grid right behind
    ([0.1, 0.2, 0.3, 0.4, 0.0], [0.9, 0.8, 0.7, 0.6, 0.0]), # SC at S/F, grid is right ahead
    ([0.1, 0.2, 0.3, 0.4, 0.15], [0.05, 0.95, 0.85, 0.75, 0.0]), # SC is right in between two cars
    ([1.9, 1.8, 1.7, 1.6, 0.0], [0.1, 0.2, 0.3, 0.4, 0.0]), # SC at S/F, grid right behind, but total laps is different
    ([1.9, 1.8, 1.7, 1.6, 0.0, -1, -1, -1], [0.1, 0.2, 0.3, 0.4, 0.0, -1, -1, -1]), # SC at S/F, grid right behind, now with empty entries
])
def test_positions_from_safety_car(car_positions, expected):
    positions = positions_from_safety_car(car_positions, 4) # 4 = the position of the pace car in our test data

    assert approx(positions) == expected
    
    