import pytest

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

def test_wave_lapped_cars_not_implemented():
    with pytest.raises(NotImplementedError, match="wave_lapped_cars is not implemented yet."):
        wave_lapped_cars([], [], [], 0)

def test_wave_ahead_of_class_lead_not_implemented():
    with pytest.raises(NotImplementedError, match="wave_ahead_of_lead is not implemented yet."):
        wave_ahead_of_class_lead([], [], [], 0)