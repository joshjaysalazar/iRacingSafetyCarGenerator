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
    mock_master.settings = {
        "settings": {
            # Multiplier dependencies
            "start_multi_val": "1.5",
            "start_multi_time": "300",
            # Proximity checker dependencies
            "proximity_yellows": "0",
            "proximity_yellows_distance": "0.05",
            # threshold checker dependencies
            "start_minute": "0",
            "end_minute": "999",
            "max_safety_cars": "999",
            "min_time_between": "0",
            "off_min": "4",
            "stopped_min": "2",
            # Detector dependencies
            "random": "0",
            "random_prob": "0.5",
            "random_max_occ": "1",
            "stopped": "1",
            "off": "1",
            # Combined threshold
            "stopped_message": "Cars stopped on track.",
            "stopped_weight": "1",
            "off_message": "Multiple cars off track.",
            "off_weight": "1",
            "combined": "1",
            "combined_min": "7",
            "combined_message": "Cars stopped and off track."
        }
    }
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
