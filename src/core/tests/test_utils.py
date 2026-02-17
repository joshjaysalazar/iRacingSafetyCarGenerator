"""Test utilities for mocking common objects across test files."""

import json
from pathlib import Path
from unittest.mock import Mock
from irsdk import TrkLoc
from configparser import ConfigParser


def drivers_from_dump_frame(dump_path: Path, frame_index: int) -> tuple[list[dict], int]:
    """Load driver data from a specific frame of an NDJSON dump file.

    Args:
        dump_path: Path to the NDJSON dump file.
        frame_index: The 0-based line/frame index to read.

    Returns:
        A tuple of (drivers_list, pace_car_idx) where:
        - drivers_list is a list of driver dicts with keys matching the format
          expected by get_split_class_commands
        - pace_car_idx is the index of the pace car in drivers_list
    """
    with open(dump_path, "r") as f:
        for i, line in enumerate(f):
            if i == frame_index:
                data = json.loads(line)
                break
        else:
            raise IndexError(f"Frame {frame_index} not found in {dump_path}")

    drivers_info = data["session_info"]["DriverInfo"]["Drivers"]
    telemetry = data["telemetry"]

    drivers = []
    pace_car_idx = None

    for d in drivers_info:
        idx = d["CarIdx"]
        driver = {
            "driver_idx": idx,
            "car_number": d["CarNumber"],
            "car_class_id": d["CarClassID"],
            "car_class_est_lap_time": d["CarClassEstLapTime"],
            "is_pace_car": d["CarIsPaceCar"] == 1,
            "lap_distance": telemetry["CarIdxLapDistPct"][idx],
            "on_pit_road": telemetry["CarIdxOnPitRoad"][idx],
            "track_loc": telemetry["CarIdxTrackSurface"][idx],
            "session_flags": telemetry["CarIdxSessionFlags"][idx],
        }
        drivers.append(driver)
        if driver["is_pace_car"]:
            pace_car_idx = len(drivers) - 1

    return drivers, pace_car_idx


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


def make_driver(track_loc=TrkLoc.on_track, laps_completed=0, lap_distance=0.0, driver_idx=0, is_pace_car=False,
                car_number="0", car_class_id=0, car_class_est_lap_time=0.0, on_pit_road=False,
                laps_started=0, total_distance=0.0, session_flags=0):
    return {
        "driver_idx": driver_idx,
        "car_number": car_number,
        "car_class_id": car_class_id,
        "car_class_est_lap_time": car_class_est_lap_time,
        "is_pace_car": is_pace_car,
        "laps_completed": laps_completed,
        "laps_started": laps_started,
        "lap_distance": lap_distance,
        "total_distance": total_distance,
        "track_loc": track_loc,
        "on_pit_road": on_pit_road,
        "session_flags": session_flags,
    }


def _convert_value(value):
    """Convert a string setting value to its appropriate Python type."""
    if value in ("0", "1"):
        return value == "1"
    elif "." in str(value):
        return float(value)
    else:
        try:
            return int(value)
        except ValueError:
            return value


# Default values for all settings properties that from_settings() methods read.
# When adding a new detector or setting, add its defaults here so existing tests
# don't need updating. Tests only need to override settings they care about.
_SETTINGS_DEFAULTS = {
    # Detector enables
    "random_detector_enabled": "1",
    "stopped_detector_enabled": "1",
    "off_track_detector_enabled": "1",
    "meatball_detector_enabled": "1",
    # Random detector
    "random_probability": "0.1",
    "detection_start_minute": "0",
    "detection_end_minute": "30",
    "random_max_safety_cars": "5",
    # Threshold checker
    "event_time_window_seconds": "10.0",
    "off_track_cars_threshold": "4",
    "stopped_cars_threshold": "2",
    "meatball_cars_threshold": "99999",
    "accumulative_threshold": "10",
    "off_track_weight": "1.0",
    "stopped_weight": "2.0",
    "meatball_weight": "0.0",
    "tow_detector_enabled": "1",
    "tow_cars_threshold": "99999",
    "tow_weight": "0.0",
    "tow_message": "Major incident detected",
    "proximity_filter_enabled": "0",
    "proximity_filter_distance_percentage": "0.05",
    "race_start_threshold_multiplier": "1.0",
    "race_start_threshold_multiplier_time_seconds": "300.0",
}


def dict_to_config(settings_dict):
    """Convert a dictionary to a Mock Settings object for testing.

    This function creates a mock Settings object that mimics the behavior of the
    actual Settings class, with property access for all settings values.

    All settings start with sensible defaults (see _SETTINGS_DEFAULTS) so that
    tests only need to specify the settings they care about. This prevents
    breakage when new detectors or settings are added.
    """
    mock_settings = Mock()

    # Start with defaults, then overlay user-provided values
    merged = dict(_SETTINGS_DEFAULTS)
    merged.update(settings_dict.get("settings", {}))

    # Set properties on the mock based on the merged dict
    for key, value in merged.items():
        setattr(mock_settings, key, _convert_value(value))

    return mock_settings