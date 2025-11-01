import pytest

from unittest.mock import Mock
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
    mock_settings.start_multi_val = 1.5
    mock_settings.start_multi_time = 300.0
    mock_settings.proximity_yellows = False
    mock_settings.proximity_yellows_distance = 0.05
    mock_settings.start_minute = 0.0
    mock_settings.end_minute = 999.0
    mock_settings.max_safety_cars = 999
    mock_settings.min_time_between = 0.0
    mock_settings.off_min = 4
    mock_settings.stopped_min = 2
    mock_settings.time_range = 10.0
    mock_settings.combined_min = 7.0
    mock_settings.stopped_weight = 1.0
    mock_settings.off_weight = 1.0
    mock_settings.random = False
    mock_settings.random_prob = 0.5
    mock_settings.random_max_occ = 1
    mock_settings.stopped = True
    mock_settings.off = True
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
