import pytest
import tempfile
import os
from core.settings import Settings


@pytest.fixture
def temp_settings_file():
    """Create a temporary settings file for testing."""
    temp_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.ini')
    temp_file.close()
    yield temp_file.name
    # Cleanup
    if os.path.exists(temp_file.name):
        os.unlink(temp_file.name)


class TestSettings:
    """Test cases for the typed Settings wrapper class."""

    def test_fallback_values_when_file_empty(self, temp_settings_file):
        """Test that fallback values are returned when config file is empty."""
        settings = Settings(temp_settings_file)
        
        # Test all properties return their fallback values
        assert settings.random_detector_enabled is True
        assert settings.random_max_safety_cars == 1
        assert settings.random_probability == 0.1
        assert settings.random_message == "Hazard on track."
        assert settings.stopped_detector_enabled is True
        assert settings.stopped_cars_threshold == 2
        assert settings.stopped_message == "Cars stopped on track"
        assert settings.off_track_detector_enabled is True
        assert settings.off_track_cars_threshold == 4
        assert settings.off_track_message == "Multiple cars off track"
        assert settings.race_start_threshold_multiplier == 1.0
        assert settings.race_start_threshold_multiplier_time_seconds == 30.0
        assert settings.max_safety_cars == 2
        assert settings.detection_start_minute == 0.0
        assert settings.detection_end_minute == 30.0
        assert settings.min_time_between_safety_cars_minutes == 3.0
        assert settings.laps_under_safety_car == 2
        assert settings.wave_arounds_enabled is True
        assert settings.laps_before_wave_arounds == 0
        assert settings.proximity_filter_enabled is True
        assert settings.proximity_filter_distance_percentage == 0.25

    def test_fallback_values_when_file_nonexistent(self):
        """Test that fallback values work when config file doesn't exist."""
        non_existent_path = "/tmp/non_existent_settings.ini"
        if os.path.exists(non_existent_path):
            os.unlink(non_existent_path)
        
        settings = Settings(non_existent_path)
        
        # Should still return fallback values
        assert settings.random_detector_enabled is True
        assert settings.random_max_safety_cars == 1
        assert settings.random_probability == 0.1


    def test_writing_settings(self, temp_settings_file):
        """Test writing settings and verifying they persist."""
        settings = Settings(temp_settings_file)
        
        # Modify all settings
        settings.random_detector_enabled = False
        settings.random_max_safety_cars = 7
        settings.random_probability = 0.33
        settings.random_message = "Modified Random"
        settings.stopped_detector_enabled = True
        settings.stopped_cars_threshold = 8
        settings.stopped_message = "Modified Stopped"
        settings.off_track_detector_enabled = False
        settings.off_track_cars_threshold = 9
        settings.off_track_message = "Modified Off"
        settings.race_start_threshold_multiplier = 4.2
        settings.race_start_threshold_multiplier_time_seconds = 30.5
        settings.max_safety_cars = 12
        settings.detection_start_minute = 8.5
        settings.detection_end_minute = 150.0
        settings.min_time_between_safety_cars_minutes = 20.5
        settings.laps_under_safety_car = 7
        settings.wave_arounds_enabled = False
        settings.laps_before_wave_arounds = 4
        settings.proximity_filter_enabled = True
        settings.proximity_filter_distance_percentage = 0.8
        
        # Save settings
        settings.save()
        
        # Create a new Settings instance to read the saved file
        new_settings = Settings(temp_settings_file)
        
        # Verify all values were saved and loaded correctly
        assert new_settings.random_detector_enabled is False
        assert new_settings.random_max_safety_cars == 7
        assert new_settings.random_probability == 0.33
        assert new_settings.random_message == "Modified Random"
        assert new_settings.stopped_detector_enabled is True
        assert new_settings.stopped_cars_threshold == 8
        assert new_settings.stopped_message == "Modified Stopped"
        assert new_settings.off_track_detector_enabled is False
        assert new_settings.off_track_cars_threshold == 9
        assert new_settings.off_track_message == "Modified Off"
        assert new_settings.race_start_threshold_multiplier == 4.2
        assert new_settings.race_start_threshold_multiplier_time_seconds == 30.5
        assert new_settings.max_safety_cars == 12
        assert new_settings.detection_start_minute == 8.5
        assert new_settings.detection_end_minute == 150.0
        assert new_settings.min_time_between_safety_cars_minutes == 20.5
        assert new_settings.laps_under_safety_car == 7
        assert new_settings.wave_arounds_enabled is False
        assert new_settings.laps_before_wave_arounds == 4
        assert new_settings.proximity_filter_enabled is True
        assert new_settings.proximity_filter_distance_percentage == 0.8
