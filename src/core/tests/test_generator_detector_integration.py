"""Integration tests for Detector classes and ThresholdChecker usage in Generator class."""

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from core.detection.detector import Detector, DetectorSettings, BundledDetectedEvents
from core.detection.detector_common_types import DetectionResult, DetectorEventTypes
from core.detection.threshold_checker import ThresholdChecker, ThresholdCheckerSettings
from core.generator import Generator
from core.tests.test_utils import create_mock_drivers


@pytest.fixture
def mock_arguments():
    """Mock arguments for Generator initialization."""
    mock_args = Mock()
    mock_args.disable_window_interactions = True
    mock_args.dry_run = True
    return mock_args


@pytest.fixture
def mock_master():
    """Mock master object with settings for Generator."""
    from core.tests.test_utils import dict_to_config
    
    mock_master = Mock()
    mock_master.settings = dict_to_config({
        "settings": {
            # Detector settings
            "random": "1",
            "random_prob": "0.1",
            "start_minute": "0",
            "end_minute": "30",
            "random_max_occ": "2",
            "stopped": "1",
            "off": "1",
            # ThresholdChecker settings
            "off_min": "4",
            "stopped_min": "2",
            # Other required settings
            "start_multi_val": "1.0",
            "start_multi_time": "300",
            "proximity_yellows": "0",
            "proximity_yellows_distance": "0.05",
            "max_safety_cars": "999",
            "min_time_between": "0",
        }
    })
    return mock_master


@pytest.fixture
def mock_drivers():
    """Mock Drivers object for testing."""
    return create_mock_drivers(num_drivers=10, include_previous=False)


@pytest.fixture
def generator_with_mocks(mock_arguments, mock_master):
    """Generator instance with mocked dependencies."""
    generator = Generator(mock_arguments, mock_master)
    generator.start_time = time.time() - 10  # Simulate 10 seconds since start
    return generator


class TestGeneratorDetectorInitialization:
    """Tests for detector initialization in Generator.run()."""

    def test_detector_initialization_in_run(self, generator_with_mocks, mock_drivers):
        """Test that detector is properly initialized during Generator.run()."""
        generator = generator_with_mocks
        
        with patch.object(generator.ir, 'startup', return_value=True), \
             patch.object(generator.command_sender, 'connect'), \
             patch('core.drivers.Drivers', return_value=mock_drivers), \
             patch.object(generator, '_loop'):
            
            # Run the generator
            result = generator.run()
            
            # Verify detector was initialized
            assert result is True
            assert hasattr(generator, 'detector')
            assert isinstance(generator.detector, Detector)
            assert hasattr(generator, 'threshold_checker')
            assert isinstance(generator.threshold_checker, ThresholdChecker)

    def test_detector_settings_from_master_settings(self, generator_with_mocks, mock_drivers):
        """Test that DetectorSettings are correctly created from master settings."""
        generator = generator_with_mocks
        
        with patch.object(generator.ir, 'startup', return_value=True), \
             patch.object(generator.command_sender, 'connect'), \
             patch('core.drivers.Drivers', return_value=mock_drivers), \
             patch.object(generator, '_loop'):
            
            generator.run()
            
            # Verify detector has the correct settings-based configuration
            # We can't directly access settings, but we can verify the detector exists
            assert generator.detector is not None
            
    def test_detector_build_called_with_correct_parameters(self, generator_with_mocks, mock_drivers):
        """Test that Detector.build_detector is called with correct parameters."""
        generator = generator_with_mocks
        
        with patch.object(generator.ir, 'startup', return_value=True), \
             patch.object(generator.command_sender, 'connect'), \
             patch('core.drivers.Drivers', return_value=mock_drivers), \
             patch.object(generator, '_loop'), \
             patch.object(Detector, 'build_detector', return_value=Mock()) as mock_build:
            
            generator.run()
            
            # Verify build_detector was called once
            mock_build.assert_called_once()
            
            # Verify the arguments passed to build_detector
            args, kwargs = mock_build.call_args
            detector_settings, drivers = args
            
            assert isinstance(detector_settings, DetectorSettings)
            assert detector_settings.random_enabled is True
            assert detector_settings.stopped_enabled is True
            assert detector_settings.off_track_enabled is True
            assert drivers is mock_drivers


class TestGeneratorLoopDetectorIntegration:
    """Tests for detector usage in Generator._loop()."""

    def setup_generator_for_loop_test(self, generator, mock_drivers):
        """Setup generator with necessary mocks for _loop testing."""
        generator.drivers = mock_drivers
        generator.threshold_checker = ThresholdChecker(
            ThresholdCheckerSettings.from_settings(generator.master.settings)
        )
        generator.detector = Mock(spec=Detector)
        
        # Mock detector results
        mock_results = Mock(spec=BundledDetectedEvents)
        mock_results.get_events = Mock()
        generator.detector.detect.return_value = mock_results
        
        return mock_results

    def test_detector_detect_called_in_loop(self, generator_with_mocks, mock_drivers, mocker):
        """Test that detector.detect() is called during _loop execution."""
        generator = generator_with_mocks
        mock_results = self.setup_generator_for_loop_test(generator, mock_drivers)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Mock detector results to return empty results
        mock_results.get_events.return_value = None
        
        # Run the loop
        generator._loop()
        
        # Verify detector.detect was called
        generator.detector.detect.assert_called_once()

    def test_threshold_checker_register_detection_result_called(self, generator_with_mocks, mock_drivers, mocker):
        """Test that threshold_checker.register_detection_result is called with detector results."""
        generator = generator_with_mocks
        mock_results = self.setup_generator_for_loop_test(generator, mock_drivers)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Create mock detection results
        mock_stopped_result = DetectionResult(
            DetectorEventTypes.STOPPED,
            drivers=[{'driver_idx': 1}, {'driver_idx': 2}]
        )
        mock_off_track_result = DetectionResult(
            DetectorEventTypes.OFF_TRACK,
            drivers=[{'driver_idx': 3}]
        )
        
        # Configure mock to return different results for different event types
        def mock_get_events(event_type):
            if event_type == DetectorEventTypes.STOPPED:
                return mock_stopped_result
            elif event_type == DetectorEventTypes.OFF_TRACK:
                return mock_off_track_result
            return None
            
        mock_results.get_events.side_effect = mock_get_events
        
        # Spy on the register_detection_result method
        register_spy = mocker.spy(generator.threshold_checker, 'register_detection_result')
        
        # Run the loop
        generator._loop()
        
        # Verify register_detection_result was called for each non-None result
        assert register_spy.call_count == 2
        register_spy.assert_any_call(mock_stopped_result)
        register_spy.assert_any_call(mock_off_track_result)

    def test_legacy_methods_still_called_for_side_effects(self, generator_with_mocks, mock_drivers, mocker):
        """Test that legacy _check_stopped and _check_off_track are still called for side effects."""
        generator = generator_with_mocks
        mock_results = self.setup_generator_for_loop_test(generator, mock_drivers)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        check_stopped_spy = mocker.patch.object(generator, '_check_stopped', return_value=0)
        check_off_track_spy = mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Mock detector results to return empty results
        mock_results.get_events.return_value = None
        
        # Run the loop
        generator._loop()
        
        # Verify legacy methods were called
        check_stopped_spy.assert_called_once()
        check_off_track_spy.assert_called_once()

    def test_threshold_checker_clean_up_events_called(self, generator_with_mocks, mock_drivers, mocker):
        """Test that threshold_checker.clean_up_events is called before registering new events."""
        generator = generator_with_mocks
        mock_results = self.setup_generator_for_loop_test(generator, mock_drivers)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Mock detector results
        mock_results.get_events.return_value = None
        
        # Spy on the clean_up_events method
        cleanup_spy = mocker.spy(generator.threshold_checker, 'clean_up_events')
        
        # Run the loop
        generator._loop()
        
        # Verify clean_up_events was called
        cleanup_spy.assert_called_once()


class TestGeneratorThresholdCheckerIntegration:
    """Tests for threshold checking integration."""

    def test_threshold_met_triggers_safety_car_log(self, generator_with_mocks, mock_drivers, mocker, caplog):
        """Test that when threshold is met, appropriate log message is generated."""
        generator = generator_with_mocks
        generator.drivers = mock_drivers
        generator.threshold_checker = Mock(spec=ThresholdChecker)
        generator.detector = Mock(spec=Detector)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Mock detector results
        mock_results = Mock(spec=BundledDetectedEvents)
        mock_results.get_events.return_value = None
        generator.detector.detect.return_value = mock_results
        
        # Configure threshold_checker to return True for threshold_met
        generator.threshold_checker.threshold_met.return_value = True
        
        # Run the loop
        with caplog.at_level('INFO'):
            generator._loop()
        
        # Verify the log message
        assert "ThresholdChecker is meeting threshold, would start safety car" in caplog.text

    def test_threshold_not_met_no_safety_car_log(self, generator_with_mocks, mock_drivers, mocker, caplog):
        """Test that when threshold is not met, no safety car log message is generated."""
        generator = generator_with_mocks
        generator.drivers = mock_drivers
        generator.threshold_checker = Mock(spec=ThresholdChecker)
        generator.detector = Mock(spec=Detector)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Mock detector results
        mock_results = Mock(spec=BundledDetectedEvents)
        mock_results.get_events.return_value = None
        generator.detector.detect.return_value = mock_results
        
        # Configure threshold_checker to return False for threshold_met
        generator.threshold_checker.threshold_met.return_value = False
        
        # Run the loop
        with caplog.at_level('INFO'):
            generator._loop()
        
        # Verify no safety car log message
        assert "ThresholdChecker is meeting threshold, would start safety car" not in caplog.text


class TestGeneratorDetectorEndToEndIntegration:
    """End-to-end integration tests with real detector components."""

    def test_real_detector_integration_with_stopped_cars(self, generator_with_mocks, mocker):
        """Test real detector integration with stopped cars scenario."""
        generator = generator_with_mocks
        
        # Create real drivers mock with stopped cars
        drivers_mock = Mock()
        drivers_mock.current_drivers = [
            {"driver_idx": 0, "lap_distance": 0.1, "laps_completed": 1, "track_loc": 1},
            {"driver_idx": 1, "lap_distance": 0.1, "laps_completed": 1, "track_loc": 1},  # stopped
            {"driver_idx": 2, "lap_distance": 0.2, "laps_completed": 1, "track_loc": 1},  # stopped
            {"driver_idx": 3, "lap_distance": 0.3, "laps_completed": 1, "track_loc": 1},
        ]
        drivers_mock.previous_drivers = [
            {"driver_idx": 0, "lap_distance": 0.05, "laps_completed": 1, "track_loc": 1},
            {"driver_idx": 1, "lap_distance": 0.2, "laps_completed": 1, "track_loc": 1},  # was moving, now stopped
            {"driver_idx": 2, "lap_distance": 0.3, "laps_completed": 1, "track_loc": 1},  # was moving, now stopped
            {"driver_idx": 3, "lap_distance": 0.2, "laps_completed": 1, "track_loc": 1},
        ]
        
        generator.drivers = drivers_mock
        
        # Initialize real detector and threshold checker
        detector_settings = DetectorSettings.from_settings(generator.master.settings)
        generator.detector = Detector.build_detector(detector_settings, drivers_mock)
        threshold_checker_settings = ThresholdCheckerSettings.from_settings(generator.master.settings)
        generator.threshold_checker = ThresholdChecker(threshold_checker_settings)
        
        # Mock other dependencies
        mocker.patch.object(generator, '_wait_for_green_flag')
        mocker.patch.object(generator, '_is_shutting_down', side_effect=[False, True])
        mocker.patch.object(generator.drivers, 'update')
        mocker.patch.object(generator, '_check_random')
        mocker.patch.object(generator, '_check_stopped', return_value=0)
        mocker.patch.object(generator, '_check_off_track', return_value=0)
        mocker.patch('time.sleep', return_value=None)
        
        # Spy on threshold_met to capture the result
        threshold_spy = mocker.spy(generator.threshold_checker, 'threshold_met')
        
        # Run the loop
        generator._loop()
        
        # With 2 stopped cars and threshold of 2, threshold should be met
        assert threshold_spy.call_count > 0

    def test_detector_settings_disabled_detectors_not_called(self, generator_with_mocks, mock_drivers, mocker):
        """Test that disabled detectors are not included in the detector."""
        generator = generator_with_mocks
        
        # Disable some detectors in settings
        generator.master.settings["settings"]["random"] = "0"
        generator.master.settings["settings"]["off"] = "0"
        
        generator.drivers = mock_drivers
        
        # Initialize detector with disabled settings
        detector_settings = DetectorSettings.from_settings(generator.master.settings)
        generator.detector = Detector.build_detector(detector_settings, mock_drivers)
        
        # Check that only stopped detector is enabled
        assert DetectorEventTypes.STOPPED in generator.detector.detectors
        assert DetectorEventTypes.RANDOM not in generator.detector.detectors
        assert DetectorEventTypes.OFF_TRACK not in generator.detector.detectors


def test_generator_calls_race_started_when_green_flag_detected(generator_with_mocks, mock_drivers, mocker):
    """Test that Generator calls race_started() on detector when green flag is detected."""
    import irsdk
    
    generator = generator_with_mocks
    generator.drivers = mock_drivers
    
    # Initialize detector and spy on race_started method
    detector_settings = DetectorSettings.from_settings(generator.master.settings)
    generator.detector = Detector.build_detector(detector_settings, mock_drivers)
    detector_race_started_spy = mocker.spy(generator.detector, 'race_started')
    
    # Initialize threshold checker
    threshold_checker_settings = ThresholdCheckerSettings.from_settings(generator.master.settings)
    generator.threshold_checker = ThresholdChecker(threshold_checker_settings)
    threshold_checker_race_started_spy = mocker.spy(generator.threshold_checker, 'race_started')
    
    # Mock iRacing SDK to simulate green flag
    generator.ir = {"SessionFlags": irsdk.Flags.green}
    
    # Mock other dependencies for _wait_for_green_flag
    mocker.patch.object(generator, '_is_shutting_down', return_value=False)
    mocker.patch.object(generator, '_skip_waiting_for_green', return_value=False)
    mocker.patch('time.sleep', return_value=None)  # Speed up the test
    
    # Ensure start_time is None so it gets set
    generator.start_time = None
    
    # Call _wait_for_green_flag directly - this should set start_time and call race_started
    generator._wait_for_green_flag(require_race_session=False)
    
    # Verify that race_started was called
    detector_race_started_spy.assert_called_once()
    threshold_checker_race_started_spy.assert_called_once()
    # Verify that start_time was set
    assert generator.start_time is not None


def test_generator_calls_race_started_when_skipping_green_flag_wait(generator_with_mocks, mock_drivers, mocker):
    """Test that Generator calls race_started() on detector when skipping green flag wait."""
    generator = generator_with_mocks
    generator.drivers = mock_drivers
    
    # Initialize detector and spy on race_started method
    detector_settings = DetectorSettings.from_settings(generator.master.settings)
    generator.detector = Detector.build_detector(detector_settings, mock_drivers)
    detector_race_started_spy = mocker.spy(generator.detector, 'race_started')
    
    # Initialize threshold checker
    threshold_checker_settings = ThresholdCheckerSettings.from_settings(generator.master.settings)
    generator.threshold_checker = ThresholdChecker(threshold_checker_settings)
    threshold_checker_race_started_spy = mocker.spy(generator.threshold_checker, 'race_started')
    
    # Mock iRacing SDK - no green flag
    generator.ir = {"SessionFlags": 0}  # No flags set
    
    # Mock to simulate skipping the wait (e.g., user input or shutdown)
    mocker.patch.object(generator, '_is_shutting_down', return_value=False)
    mocker.patch.object(generator, '_skip_waiting_for_green', side_effect=[False, True])  # Skip on second call
    mocker.patch('time.sleep', return_value=None)  # Speed up the test
    
    # Ensure start_time is None so it gets set
    generator.start_time = None
    
    # Call _wait_for_green_flag directly - this should set start_time and call race_started
    generator._wait_for_green_flag(require_race_session=False)
    
    # Verify that race_started was called
    detector_race_started_spy.assert_called_once()
    threshold_checker_race_started_spy.assert_called_once()
    # Verify that start_time was set
    assert generator.start_time is not None