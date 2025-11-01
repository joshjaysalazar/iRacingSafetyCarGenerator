"""Test utilities for mocking common objects across test files."""

from unittest.mock import Mock
from irsdk import TrkLoc
from configparser import ConfigParser


def create_mock_drivers(num_drivers=60, include_previous=True):
    """Create a mock Drivers object for testing.
    
    Args:
        num_drivers (int): Number of drivers to create. Defaults to 65.
        include_previous (bool): Whether to include previous_drivers list. Defaults to True.
    
    Returns:
        Mock: Mock Drivers object with current_drivers and optionally previous_drivers.
    """
    mock_drivers = Mock()
    mock_drivers.current_drivers = []
    
    for i in range(num_drivers):
        driver_data = {
            "driver_idx": i,
            "lap_distance": 0.5,
            "laps_completed": 1,
            "track_loc": TrkLoc.on_track
        }
        mock_drivers.current_drivers.append(driver_data)
    
    if include_previous:
        mock_drivers.previous_drivers = []
        for i in range(num_drivers):
            driver_data = {
                "driver_idx": i,
                "lap_distance": 0.49,
                "laps_completed": 1,
                "track_loc": TrkLoc.on_track
            }
            mock_drivers.previous_drivers.append(driver_data)
    
    return mock_drivers


class MockDrivers:
    def __init__(self, current = [], previous = []):
        self.current_drivers = current
        self.previous_drivers = previous

        # This is a fix to account for the SC entry in the drivers list
        # Ideally, we filter this out in the Drivers class so we don't have to account for this in all of our logic.
        self.current_drivers.append(make_driver(TrkLoc.not_in_world))
        self.previous_drivers.append(make_driver(TrkLoc.not_in_world))


def make_driver(track_loc, laps_completed = 0, lap_distance = 0.0, driver_idx = 0):
    return {
        "driver_idx": driver_idx,
        "track_loc": track_loc,
        "laps_completed": laps_completed,
        "lap_distance": lap_distance
    }


def dict_to_config(settings_dict):
    """Convert a dictionary to a Mock Settings object for testing.

    This function creates a mock Settings object that mimics the behavior of the
    actual Settings class, with property access for all settings values.
    """
    mock_settings = Mock()

    # Extract the settings section
    settings_section = settings_dict.get("settings", {})

    # Set properties on the mock based on the dict
    for key, value in settings_section.items():
        # Convert string values to appropriate types
        if value in ("0", "1"):
            # Boolean values
            setattr(mock_settings, key, value == "1")
        elif "." in str(value):
            # Float values
            setattr(mock_settings, key, float(value))
        else:
            # Try int, fallback to string
            try:
                setattr(mock_settings, key, int(value))
            except ValueError:
                setattr(mock_settings, key, value)

    return mock_settings