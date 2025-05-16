import pytest

from unittest.mock import MagicMock, Mock
from core.detection.threshold_checker import ThresholdChecker
from core.detection.detector import Detector, DetectorSettings
from core.generator import Generator
from core.interactions.command_sender import CommandSender
from core.interactions.mock_sender import MockSender
from core.tests.test_utils import create_mock_drivers

@pytest.fixture
def generator():
    mock_arguments = Mock()
    mock_arguments.disable_window_interactions = True
    mock_master = Mock()

    # Create a mock settings object that behaves like our Settings wrapper
    mock_settings = Mock()
    # Set default values for all properties used in tests
    mock_settings.race_start_threshold_multiplier = 1.5
    mock_settings.race_start_threshold_multiplier_time_seconds = 300.0
    mock_settings.proximity_filter_enabled = False
    mock_settings.proximity_filter_distance_percentage = 0.05
    mock_settings.detection_start_minute = 0.0
    mock_settings.detection_end_minute = 999.0
    mock_settings.max_safety_cars = 999
    mock_settings.min_time_between_safety_cars_minutes = 0.0
    mock_settings.off_track_cars_threshold = 4
    mock_settings.stopped_cars_threshold = 2
    mock_settings.event_time_window_seconds = 5.0
    mock_settings.accumulative_threshold = 7.0
    mock_settings.stopped_weight = 1.0
    mock_settings.off_track_weight = 1.0
    mock_settings.random_detector_enabled = False
    mock_settings.random_probability = 0.5
    mock_settings.random_max_safety_cars = 1
    mock_settings.stopped_detector_enabled = True
    mock_settings.off_track_detector_enabled = True
    mock_master.settings = mock_settings
    gen = Generator(arguments=mock_arguments, master=mock_master)
    gen.start_time = 0  # Simulate the start time as 0 for testing

    # Setup mock drivers
    mock_drivers = create_mock_drivers()
    gen.drivers = mock_drivers

    # Setup detector
    detector_settings = DetectorSettings.from_settings(mock_master.settings)
    gen.detector = Detector.build_detector(detector_settings, mock_drivers)

    return gen

def test_command_sender_init():
    """Test the initialization of the CommandSender."""
    mock_arguments = Mock()
    # This needs to be True to make tests work on MacOS
    mock_arguments.disable_window_interactions = True

    # We need the generator to send actual commands
    mock_arguments.dry_run = False
    generator = Generator(arguments=mock_arguments)
    assert isinstance(generator.command_sender, CommandSender)

    # In this case, we want to avoid sending commands
    mock_arguments.dry_run = True
    generator = Generator(arguments=mock_arguments)
    assert isinstance(generator.command_sender, MockSender)


def test_notify_race_started_calls_both_components(generator):
    """Test that _notify_race_started calls race_started on both detector and threshold_checker"""

    # Create mock detector and threshold_checker
    generator.detector = Mock(spec=Detector)
    generator.threshold_checker = Mock(spec=ThresholdChecker)

    start_time = 1000.0
    generator._notify_race_started(start_time)

    # Verify both components were called
    generator.detector.race_started.assert_called_once_with(start_time)
    generator.threshold_checker.race_started.assert_called_once_with(start_time)

def test_send_wave_arounds_disabled(generator):
    """Test when wave arounds are disabled."""
    generator.master.settings.wave_arounds_enabled = False
    generator.master.settings.laps_before_wave_arounds = 2
    result = generator._send_wave_arounds()
    assert result is True

def test_send_wave_arounds_not_time_yet(generator):
    """Test when it's not time for wave arounds."""
    generator.master.settings.wave_arounds_enabled = True
    generator.master.settings.laps_before_wave_arounds = 2
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 6  # Not yet at wave lap
    result = generator._send_wave_arounds()
    assert result is False

def test_send_wave_arounds_wave_ahead_of_class_lead(mocker, generator):
    """Test wave arounds for cars ahead of class lead."""
    generator.master.settings.wave_arounds_enabled = True
    generator.master.settings.laps_before_wave_arounds = 1
    generator.master.settings.wave_around_rules_index = 1  # Wave ahead of class lead
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7
    generator.ir = MagicMock()

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: ["!w 1", "!w 2"])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_commands")

    result = generator._send_wave_arounds()

    # Assert waves were actually sent
    mock_wave_around_func.assert_called_once()
    mock_command_sender.assert_called_once_with(["!w 1", "!w 2"])
    assert result is True

def test_send_wave_arounds_no_eligible_cars(generator, mocker):
    """Test wave arounds when no cars are eligible."""
    generator.master.settings.wave_arounds_enabled = True
    generator.master.settings.laps_before_wave_arounds = 1
    generator.master.settings.wave_around_rules_index = 1  # Wave ahead of class lead
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7  # At wave lap

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: [])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_command")

    generator.ir = MagicMock()

    result = generator._send_wave_arounds()
    mock_command_sender.assert_not_called()
    assert result is True
