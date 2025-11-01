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
        assert settings.random is True
        assert settings.random_max_occ == 3
        assert settings.random_prob == 0.1
        assert settings.random_message == "Random safety car"
        assert settings.stopped is True
        assert settings.stopped_min == 2
        assert settings.stopped_message == "Cars stopped on track"
        assert settings.off is True
        assert settings.off_min == 3
        assert settings.off_message == "Cars off track"
        assert settings.start_multi_val == 2.0
        assert settings.start_multi_time == 10.0
        assert settings.max_safety_cars == 5
        assert settings.start_minute == 5.0
        assert settings.end_minute == 120.0
        assert settings.min_time_between == 15.0
        assert settings.laps_under_sc == 3
        assert settings.wave_arounds is True
        assert settings.laps_before_wave_arounds == 2
        assert settings.proximity_yellows is True
        assert settings.proximity_yellows_distance == 0.3

    def test_fallback_values_when_file_nonexistent(self):
        """Test that fallback values work when config file doesn't exist."""
        non_existent_path = "/tmp/non_existent_settings.ini"
        if os.path.exists(non_existent_path):
            os.unlink(non_existent_path)
        
        settings = Settings(non_existent_path)
        
        # Should still return fallback values
        assert settings.random is True
        assert settings.random_max_occ == 3
        assert settings.random_prob == 0.1

    def test_reading_existing_settings(self, temp_settings_file):
        """Test reading settings from an existing config file."""
        # Create a config file with specific values
        with open(temp_settings_file, 'w') as f:
            f.write("""[settings]
random = 0
random_max_occ = 5
random_prob = 0.25
random_message = Test Random Message
stopped = 1
stopped_min = 4
stopped_message = Test Stopped Message
off = 0
off_min = 6
off_message = Test Off Message
start_multi_val = 3.5
start_multi_time = 20.0
max_safety_cars = 8
start_minute = 10.0
end_minute = 90.0
min_time_between = 25.0
laps_under_sc = 5
wave_arounds = 0
laps_before_wave_arounds = 3
proximity_yellows = 1
proximity_yellows_distance = 0.5
""")
        
        settings = Settings(temp_settings_file)
        
        # Test that values are read correctly with proper types
        assert settings.random is False
        assert settings.random_max_occ == 5
        assert settings.random_prob == 0.25
        assert settings.random_message == "Test Random Message"
        assert settings.stopped is True
        assert settings.stopped_min == 4
        assert settings.stopped_message == "Test Stopped Message"
        assert settings.off is False
        assert settings.off_min == 6
        assert settings.off_message == "Test Off Message"
        assert settings.start_multi_val == 3.5
        assert settings.start_multi_time == 20.0
        assert settings.max_safety_cars == 8
        assert settings.start_minute == 10.0
        assert settings.end_minute == 90.0
        assert settings.min_time_between == 25.0
        assert settings.laps_under_sc == 5
        assert settings.wave_arounds is False
        assert settings.laps_before_wave_arounds == 3
        assert settings.proximity_yellows is True
        assert settings.proximity_yellows_distance == 0.5

    def test_writing_settings(self, temp_settings_file):
        """Test writing settings and verifying they persist."""
        settings = Settings(temp_settings_file)
        
        # Modify all settings
        settings.random = False
        settings.random_max_occ = 7
        settings.random_prob = 0.33
        settings.random_message = "Modified Random"
        settings.stopped = True
        settings.stopped_min = 8
        settings.stopped_message = "Modified Stopped"
        settings.off = False
        settings.off_min = 9
        settings.off_message = "Modified Off"
        settings.start_multi_val = 4.2
        settings.start_multi_time = 30.5
        settings.max_safety_cars = 12
        settings.start_minute = 8.5
        settings.end_minute = 150.0
        settings.min_time_between = 20.5
        settings.laps_under_sc = 7
        settings.wave_arounds = False
        settings.laps_before_wave_arounds = 4
        settings.proximity_yellows = True
        settings.proximity_yellows_distance = 0.8
        
        # Save settings
        settings.save()
        
        # Create a new Settings instance to read the saved file
        new_settings = Settings(temp_settings_file)
        
        # Verify all values were saved and loaded correctly
        assert new_settings.random is False
        assert new_settings.random_max_occ == 7
        assert new_settings.random_prob == 0.33
        assert new_settings.random_message == "Modified Random"
        assert new_settings.stopped is True
        assert new_settings.stopped_min == 8
        assert new_settings.stopped_message == "Modified Stopped"
        assert new_settings.off is False
        assert new_settings.off_min == 9
        assert new_settings.off_message == "Modified Off"
        assert new_settings.start_multi_val == 4.2
        assert new_settings.start_multi_time == 30.5
        assert new_settings.max_safety_cars == 12
        assert new_settings.start_minute == 8.5
        assert new_settings.end_minute == 150.0
        assert new_settings.min_time_between == 20.5
        assert new_settings.laps_under_sc == 7
        assert new_settings.wave_arounds is False
        assert new_settings.laps_before_wave_arounds == 4
        assert new_settings.proximity_yellows is True
        assert new_settings.proximity_yellows_distance == 0.8

    def test_boolean_type_conversions(self, temp_settings_file):
        """Test that boolean values are handled correctly."""
        settings = Settings(temp_settings_file)
        
        # Test setting with actual boolean values
        settings.random = True
        settings.stopped = False
        settings.save()
        
        # Reload and verify
        new_settings = Settings(temp_settings_file)
        assert new_settings.random is True
        assert new_settings.stopped is False
        
        # Test with integer values (like from tkinter IntVar)
        settings.random = 1
        settings.stopped = 0
        settings.save()
        
        new_settings = Settings(temp_settings_file)
        assert new_settings.random is True
        assert new_settings.stopped is False

    def test_numeric_type_conversions(self, temp_settings_file):
        """Test that numeric values are converted correctly."""
        settings = Settings(temp_settings_file)
        
        # Test with string inputs (like from tkinter widgets)
        settings.random_max_occ = "10"
        settings.random_prob = "0.75"
        settings.start_multi_val = "2.5"
        settings.save()
        
        # Reload and verify types are correct
        new_settings = Settings(temp_settings_file)
        assert new_settings.random_max_occ == 10
        assert isinstance(new_settings.random_max_occ, int)
        assert new_settings.random_prob == 0.75
        assert isinstance(new_settings.random_prob, float)
        assert new_settings.start_multi_val == 2.5
        assert isinstance(new_settings.start_multi_val, float)

    def test_mixed_partial_config(self, temp_settings_file):
        """Test behavior when config file has only some settings."""
        # Create config file with only some settings
        with open(temp_settings_file, 'w') as f:
            f.write("""[settings]
random = 0
random_prob = 0.8
max_safety_cars = 15
""")
        
        settings = Settings(temp_settings_file)
        
        # Should read existing values
        assert settings.random is False
        assert settings.random_prob == 0.8
        assert settings.max_safety_cars == 15
        
        # Should use fallbacks for missing values
        assert settings.random_max_occ == 3  # fallback
        assert settings.random_message == "Random safety car"  # fallback
        assert settings.stopped is True  # fallback

    def test_property_types(self, temp_settings_file):
        """Test that all properties return the expected types."""
        settings = Settings(temp_settings_file)
        
        # Boolean properties
        assert isinstance(settings.random, bool)
        assert isinstance(settings.stopped, bool)
        assert isinstance(settings.off, bool)
        assert isinstance(settings.wave_arounds, bool)
        assert isinstance(settings.proximity_yellows, bool)
        
        # Integer properties
        assert isinstance(settings.random_max_occ, int)
        assert isinstance(settings.stopped_min, int)
        assert isinstance(settings.off_min, int)
        assert isinstance(settings.max_safety_cars, int)
        assert isinstance(settings.laps_under_sc, int)
        assert isinstance(settings.laps_before_wave_arounds, int)
        
        # Float properties
        assert isinstance(settings.random_prob, float)
        assert isinstance(settings.start_multi_val, float)
        assert isinstance(settings.start_multi_time, float)
        assert isinstance(settings.start_minute, float)
        assert isinstance(settings.end_minute, float)
        assert isinstance(settings.min_time_between, float)
        assert isinstance(settings.proximity_yellows_distance, float)
        
        # String properties
        assert isinstance(settings.random_message, str)
        assert isinstance(settings.stopped_message, str)
        assert isinstance(settings.off_message, str)

    @pytest.mark.parametrize("boolean_value,expected", [
        (True, True),
        (False, False),
        (1, True),
        (0, False),
        ("1", True),
        ("0", False)
    ])
    def test_boolean_conversion_edge_cases(self, temp_settings_file, boolean_value, expected):
        """Test various boolean input formats."""
        settings = Settings(temp_settings_file)
        settings.random = boolean_value
        settings.save()
        
        new_settings = Settings(temp_settings_file)
        assert new_settings.random is expected

    def test_write_read_cycle_preserves_data(self, temp_settings_file):
        """Test that multiple write-read cycles preserve all data correctly."""
        settings = Settings(temp_settings_file)
        
        # Set some values
        original_values = {
            'random': False,
            'random_max_occ': 42,
            'random_prob': 0.123,
            'random_message': 'Test Message with spaces and symbols!@#',
            'proximity_yellows_distance': 0.987654321
        }
        
        for prop, value in original_values.items():
            setattr(settings, prop, value)
        
        settings.save()
        
        # Read back multiple times
        for _ in range(3):
            new_settings = Settings(temp_settings_file)
            assert new_settings.random is False
            assert new_settings.random_max_occ == 42
            assert new_settings.random_prob == 0.123
            assert new_settings.random_message == 'Test Message with spaces and symbols!@#'
            assert new_settings.proximity_yellows_distance == 0.987654321