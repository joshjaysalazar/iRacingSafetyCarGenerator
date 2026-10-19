import copy
import logging
import queue
import tempfile
import threading
import time
import pytest
import irsdk

from codetiming import Timer
from dataclasses import FrozenInstanceError, replace
from unittest.mock import MagicMock, Mock, patch
from core.detection.threshold_checker import ThresholdChecker
from core.detection.detector import Detector, DetectorSettings
from core.generator import (
    ClassSplitConfirmationRequested,
    Generator,
    GeneratorSettings,
    GeneratorState,
    PreflightWarnings,
    StateChanged,
)
from core.interactions.command_sender import CommandSender
from core.interactions.mock_sender import MockSender
from core.settings import Settings
from core.tests.test_utils import FakeIRSDK, create_mock_drivers, dict_to_config, load_dump_frame

# A recorded race in progress: the generator goes straight to monitoring for incidents
RACING_FRAME = load_dump_frame("local_session_start_race_plus_two_laps.ndjson")

real_sleep = time.sleep


def configure(generator, **settings):
    """Override some of the generator's settings snapshot."""
    generator.settings = replace(generator.settings, **settings)


@pytest.fixture
def generator():
    mock_arguments = Mock()
    mock_arguments.disable_window_interactions = True
    mock_arguments.dry_run = True

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
    mock_settings.laps_under_safety_car = 2
    mock_settings.wave_arounds_enabled = True
    mock_settings.laps_before_wave_arounds = 0
    mock_settings.wave_around_rules_index = 0
    mock_settings.class_split_enabled = False
    gen = Generator(arguments=mock_arguments)
    gen.settings = GeneratorSettings.from_settings(mock_settings)
    gen.command_sender = MockSender()
    gen.start_time = 0  # Simulate the start time as 0 for testing

    # Setup mock drivers
    mock_drivers = create_mock_drivers()
    gen.drivers = mock_drivers

    # Setup detector
    detector_settings = DetectorSettings.from_settings(mock_settings)
    gen.detector = Detector.build_detector(detector_settings, mock_drivers)

    return gen

@pytest.mark.parametrize("dry_run, sender_type", [(False, CommandSender), (True, MockSender)])
def test_connect_creates_command_sender(mocker, dry_run, sender_type):
    """Test that connecting creates the right CommandSender for the launch arguments."""
    mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: FakeIRSDK(RACING_FRAME))
    mock_arguments = Mock()
    # This needs to be True to make tests work on MacOS
    mock_arguments.disable_window_interactions = True
    mock_arguments.dry_run = dry_run

    generator = Generator(arguments=mock_arguments)

    assert generator._connect() is True
    assert isinstance(generator.command_sender, sender_type)


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
    configure(generator, wave_arounds_enabled=False, laps_before_wave_arounds=2)
    result = generator._send_wave_arounds()
    assert result is True

def test_send_wave_arounds_not_time_yet(generator):
    """Test when it's not time for wave arounds."""
    configure(generator, wave_arounds_enabled=True, laps_before_wave_arounds=2)
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 6  # Not yet at wave lap
    result = generator._send_wave_arounds()
    assert result is False

def test_send_wave_arounds_wave_ahead_of_class_lead(mocker, generator):
    """Test wave arounds for cars ahead of class lead."""
    # wave_around_rules_index 1 = Wave ahead of class lead
    configure(generator, wave_arounds_enabled=True, laps_before_wave_arounds=1, wave_around_rules_index=1)
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7
    generator.ir = MagicMock()

    # Mock drivers with session_info
    generator.drivers.current_drivers = []
    generator.drivers.session_info = {"pace_car_idx": 0}

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: ["!w 1", "!w 2"])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_commands")

    result = generator._send_wave_arounds()

    # Assert waves were actually sent
    mock_wave_around_func.assert_called_once()
    mock_command_sender.assert_called_once_with(["!w 1", "!w 2"])
    assert result is True

def test_send_wave_arounds_no_eligible_cars(generator, mocker):
    """Test wave arounds when no cars are eligible."""
    # wave_around_rules_index 1 = Wave ahead of class lead
    configure(generator, wave_arounds_enabled=True, laps_before_wave_arounds=1, wave_around_rules_index=1)
    generator.lap_at_sc = 5
    generator.current_lap_under_sc = 7  # At wave lap

    # Mock drivers with session_info
    generator.drivers.current_drivers = []
    generator.drivers.session_info = {"pace_car_idx": 0}

    mock_wave_around_func = mocker.patch("core.generator.wave_arounds_factory", return_value=lambda *args: [])
    mock_command_sender = mocker.patch.object(generator.command_sender, "send_commands")

    generator.ir = MagicMock()

    result = generator._send_wave_arounds()
    mock_command_sender.assert_called_once_with([])
    assert result is True


class TestSplitClasses:
    """Tests for _split_classes() method with confirmation flow."""

    def test_split_classes_disabled(self, generator):
        """Test when class splitting is disabled."""
        configure(generator, class_split_enabled=False)
        result = generator._split_classes()
        assert result is True

    def test_split_classes_not_time_yet(self, generator):
        """Test when laps elapsed < laps_under_sc."""
        configure(generator, class_split_enabled=True, laps_under_safety_car=5)
        generator.lap_at_sc = 10
        generator.current_lap_under_sc = 12  # Only 2 laps elapsed, need 5
        result = generator._split_classes()
        assert result is False

    def test_split_classes_no_commands_needed(self, generator, mocker):
        """Test when get_split_class_commands returns empty list."""
        configure(generator, class_split_enabled=True, laps_under_safety_car=3)
        generator.lap_at_sc = 10
        generator.current_lap_under_sc = 13
        generator.drivers.session_info = {"pace_car_idx": 0}

        mocker.patch("core.generator.get_split_class_commands", return_value=[])
        mock_request = mocker.patch.object(generator, "_request_class_split_confirmation")
        mock_send = mocker.patch.object(generator.command_sender, "send_commands")

        result = generator._split_classes()

        assert result is True
        mock_request.assert_not_called()
        mock_send.assert_not_called()

    def test_split_classes_confirmed(self, generator, mocker):
        """Test when user confirms the class split commands."""
        configure(generator, class_split_enabled=True, laps_under_safety_car=3)
        generator.lap_at_sc = 10
        generator.current_lap_under_sc = 13
        generator.drivers.session_info = {"pace_car_idx": 0}

        commands = ["!eol #1", "!eol #2"]
        mocker.patch("core.generator.get_split_class_commands", return_value=commands)
        mocker.patch.object(generator, "_request_class_split_confirmation", return_value=True)
        mock_send = mocker.patch.object(generator.command_sender, "send_commands")

        result = generator._split_classes()

        assert result is True
        mock_send.assert_called_once_with(commands)

    def test_split_classes_cancelled(self, generator, mocker):
        """Test when user cancels the class split commands."""
        configure(generator, class_split_enabled=True, laps_under_safety_car=3)
        generator.lap_at_sc = 10
        generator.current_lap_under_sc = 13
        generator.drivers.session_info = {"pace_car_idx": 0}

        commands = ["!eol #1", "!eol #2"]
        mocker.patch("core.generator.get_split_class_commands", return_value=commands)
        mocker.patch.object(generator, "_request_class_split_confirmation", return_value=False)
        mock_send = mocker.patch.object(generator.command_sender, "send_commands")

        result = generator._split_classes()

        assert result is True
        mock_send.assert_not_called()

    def test_split_classes_shutdown_during_confirmation(self, generator, mocker):
        """Test shutdown event set while waiting for confirmation."""
        configure(generator, class_split_enabled=True, laps_under_safety_car=3)
        generator.lap_at_sc = 10
        generator.current_lap_under_sc = 13
        generator.drivers.session_info = {"pace_car_idx": 0}

        commands = ["!eol #1", "!eol #2"]
        mocker.patch("core.generator.get_split_class_commands", return_value=commands)
        mock_send = mocker.patch.object(generator.command_sender, "send_commands")

        # Nobody answers the confirmation request, but the generator is shutting down
        generator.shutdown_event.set()

        result = generator._split_classes()

        assert result is True
        mock_send.assert_not_called()

    def test_confirmation_is_requested_through_ui_events(self, generator):
        """The confirmation request reaches the UI as an event and the answer comes back through confirm_class_split()."""
        result = []
        requester = threading.Thread(
            target=lambda: result.append(generator._request_class_split_confirmation(["!eol #1"])),
            daemon=True,
        )
        requester.start()

        try:
            event = generator.ui_events.get(timeout=5)
            assert event == ClassSplitConfirmationRequested(["!eol #1"])

            generator.confirm_class_split(True)
            requester.join(timeout=5)
        finally:
            # Never leave the requester waiting if the test fails
            generator.stop()
            requester.join(timeout=5)

        assert result == [True]


class TestWaitForGreenFlag:
    """Tests for _wait_for_green_flag() method."""

    @pytest.fixture
    def generator_for_green_flag(self):
        """Create a generator configured for green flag tests."""
        mock_arguments = Mock()
        mock_arguments.disable_window_interactions = True

        gen = Generator(arguments=mock_arguments)
        gen.start_time = None

        # Mock the iRacing SDK
        gen.ir = MagicMock()
        gen.ir.__getitem__ = MagicMock()

        # Mock detector and threshold_checker for _notify_race_started
        gen.detector = Mock()
        gen.threshold_checker = Mock()

        return gen

    def test_green_flag_detected(self, generator_for_green_flag):
        """Test that green flag detection works (existing behavior)."""
        gen = generator_for_green_flag

        # Setup: Race session, green flag is set
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": irsdk.Flags.green,
            "SessionState": irsdk.SessionState.racing,
        }.get(key)

        gen._wait_for_green_flag(require_race_session=True)

        assert gen.start_time is not None
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_race_already_in_progress_with_require_race_session_true(self, generator_for_green_flag):
        """Test that SessionState==racing is detected when require_race_session=True."""
        gen = generator_for_green_flag

        # Setup: Race session, NO green flag, but SessionState is racing
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": 0,  # No flags set (green flag already cleared)
            "SessionState": irsdk.SessionState.racing,
        }.get(key)

        gen._wait_for_green_flag(require_race_session=True)

        assert gen.start_time is not None
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_race_already_in_progress_ignored_with_require_race_session_false(self, generator_for_green_flag, mocker):
        """Test that SessionState==racing is ignored when require_race_session=False (SC restart)."""
        gen = generator_for_green_flag
        mocker.patch("time.sleep", return_value=None)
        call_count = 0

        def mock_getitem(key):
            nonlocal call_count
            call_count += 1
            # First few calls return no green flag, then return green flag
            # This simulates waiting for actual green flag during SC restart
            if key == "SessionFlags":
                if call_count <= 3:
                    return 0  # No flags
                else:
                    return irsdk.Flags.green  # Green flag on 4th+ call
            return {
                "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
                "SessionNum": 0,
                "SessionState": irsdk.SessionState.racing,
            }.get(key)

        gen.ir.__getitem__.side_effect = mock_getitem

        gen._wait_for_green_flag(require_race_session=False)

        # Should have waited for actual green flag, not just SessionState
        assert call_count >= 4
        assert gen.start_time is not None
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_waits_for_race_session_before_checking_green(self, generator_for_green_flag, mocker):
        """Test that it waits for race session before checking green flag."""
        gen = generator_for_green_flag
        mocker.patch("time.sleep", return_value=None)
        session_checks = []

        def mock_getitem(key):
            if key == "SessionNum":
                session_checks.append(len(session_checks))
                # Return practice for first call, then race
                if len(session_checks) <= 1:
                    return 0  # Practice session
                return 1  # Race session
            if key == "SessionInfo":
                return {"Sessions": [
                    {"SessionName": "PRACTICE"},
                    {"SessionName": "RACE"}
                ]}
            if key == "SessionFlags":
                return irsdk.Flags.green
            if key == "SessionState":
                return irsdk.SessionState.racing
            return None

        gen.ir.__getitem__.side_effect = mock_getitem

        gen._wait_for_green_flag(require_race_session=True)

        # Should have checked session at least twice (once for practice, once for race)
        assert len(session_checks) >= 2
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_shutdown_event_exits_early(self, generator_for_green_flag):
        """Test that shutdown event causes early exit."""
        gen = generator_for_green_flag

        # Setup: Race session, no green flag, not racing
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": 0,
            "SessionState": irsdk.SessionState.parade_laps,
        }.get(key)

        # Set shutdown event
        gen.shutdown_event.set()

        gen._wait_for_green_flag(require_race_session=True)

        # Should have exited and set start_time
        assert gen.start_time is not None
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_skip_wait_event_exits_early(self, generator_for_green_flag):
        """Test that skip_wait_for_green_event causes early exit."""
        gen = generator_for_green_flag

        # Setup: Race session, no green flag, not racing
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": 0,
            "SessionState": irsdk.SessionState.parade_laps,
        }.get(key)

        # Set skip event
        gen.skip_wait_for_green()

        gen._wait_for_green_flag(require_race_session=True)

        # Should have exited and set start_time
        assert gen.start_time is not None
        assert gen.state == GeneratorState.MONITORING_FOR_INCIDENTS

    def test_skip_wait_is_consumed_and_does_not_skip_the_restart_after_a_safety_car(self, generator_for_green_flag, mocker):
        """Regression: the skip event was never cleared, so every later wait for green was skipped too."""
        gen = generator_for_green_flag
        mocker.patch("time.sleep", return_value=None)
        flag_checks = 0

        def mock_getitem(key):
            nonlocal flag_checks
            if key == "SessionFlags":
                flag_checks += 1
                # The restart after the safety car only goes green on the 3rd check
                return irsdk.Flags.green if flag_checks >= 3 else 0
            return {
                "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
                "SessionNum": 0,
                "SessionState": irsdk.SessionState.parade_laps,
            }.get(key)

        gen.ir.__getitem__.side_effect = mock_getitem

        # Skip the initial wait
        gen.skip_wait_for_green()
        gen._wait_for_green_flag(require_race_session=True)
        assert not gen.skip_wait_for_green_event.is_set()

        # The restart after a safety car waits for the actual green flag
        flag_checks = 0
        gen._wait_for_green_flag(require_race_session=False)
        assert flag_checks == 3

    def test_manual_safety_car_requested_while_waiting_is_dropped(self, generator_for_green_flag):
        """A manual safety car request made while waiting (e.g. during a safety car) doesn't carry over."""
        gen = generator_for_green_flag
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionFlags": irsdk.Flags.green,
        }.get(key)

        gen.throw_manual_safety_car()
        gen._wait_for_green_flag(require_race_session=False)

        assert not gen.throw_manual_sc_event.is_set()

    def test_green_flag_preferred_over_session_state(self, generator_for_green_flag, caplog):
        """Test that green flag is logged when both conditions are true."""
        gen = generator_for_green_flag

        # Setup: Both green flag AND racing state
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": irsdk.Flags.green,
            "SessionState": irsdk.SessionState.racing,
        }.get(key)

        import logging
        with caplog.at_level(logging.INFO):
            gen._wait_for_green_flag(require_race_session=True)

        # Green flag message should appear (checked first)
        assert "Green flag detected" in caplog.text
        assert "Race already in progress" not in caplog.text

    def test_race_in_progress_logging(self, generator_for_green_flag, caplog):
        """Test that race already in progress is logged correctly."""
        gen = generator_for_green_flag

        # Setup: No green flag, but racing state
        gen.ir.__getitem__.side_effect = lambda key: {
            "SessionInfo": {"Sessions": [{"SessionName": "RACE"}]},
            "SessionNum": 0,
            "SessionFlags": 0,
            "SessionState": irsdk.SessionState.racing,
        }.get(key)

        import logging
        with caplog.at_level(logging.INFO):
            gen._wait_for_green_flag(require_race_session=True)

        assert "Race already in progress" in caplog.text


def test_manual_safety_car_is_thrown_right_away_regardless_of_eligibility_window(generator, mocker):
    """Regression: a manual SC press before the earliest minute stayed latched and fired minutes later."""
    configure(generator, detection_start_minute=10.0)
    generator.start_time = time.time()  # Race just started, well before the earliest minute
    mocker.patch.object(generator, "_wait_for_green_flag")
    mocker.patch.object(generator, "_is_shutting_down", side_effect=[False, True])
    mocker.patch.object(generator.drivers, "update", create=True)
    start_safety_car = mocker.patch.object(generator, "_start_safety_car")
    mocker.patch("time.sleep", return_value=None)

    generator.throw_manual_safety_car()
    generator._loop()

    start_safety_car.assert_called_once_with()
    assert not generator.throw_manual_sc_event.is_set()


def test_start_safety_car_runs_the_procedure(generator, mocker):
    generator.ir = FakeIRSDK(RACING_FRAME)
    generator.ir.startup()
    send_command = mocker.patch.object(generator.command_sender, "send_command")
    mocker.patch.object(generator.drivers, "update", create=True)
    send_wave_arounds = mocker.patch.object(generator, "_send_wave_arounds", return_value=True)
    send_pacelaps = mocker.patch.object(generator, "_send_pacelaps", return_value=True)
    split_classes = mocker.patch.object(generator, "_split_classes", return_value=True)
    wait_for_green_flag = mocker.patch.object(generator, "_wait_for_green_flag")
    mocker.patch("time.sleep", return_value=None)

    generator._start_safety_car("Debris on track")

    send_command.assert_called_once_with("!y Debris on track")
    assert generator.ui_events.get_nowait() == StateChanged(GeneratorState.SAFETY_CAR_DEPLOYED)
    assert generator.state == GeneratorState.SAFETY_CAR_DEPLOYED
    assert generator.total_sc_events == 1
    assert generator.last_sc_time is not None
    assert generator.lap_at_sc == max(RACING_FRAME["telemetry"]["CarIdxLap"])
    send_wave_arounds.assert_called_once()
    send_pacelaps.assert_called_once()
    split_classes.assert_called_once()
    wait_for_green_flag.assert_called_once_with(require_race_session=False)


class TestSendPacelaps:
    """Tests for _send_pacelaps(), which reads laps_under_safety_car from the settings snapshot."""

    @pytest.fixture
    def pacelaps_generator(self, generator, mocker):
        mocker.patch("time.sleep", return_value=None)
        generator.lap_at_sc = 5
        generator.ir = MagicMock()
        generator.ir.__getitem__.side_effect = lambda key: {
            "CarIdxLap": [7, 7, 6],
            "CarIdxLapDistPct": [0.6, 0.4, 0.9],
        }[key]
        return generator

    def test_fewer_than_two_laps_under_safety_car_sends_nothing(self, pacelaps_generator, mocker):
        configure(pacelaps_generator, laps_under_safety_car=1)
        pacelaps_generator.current_lap_under_sc = 7
        send_command = mocker.patch.object(pacelaps_generator.command_sender, "send_command")

        assert pacelaps_generator._send_pacelaps() is True
        send_command.assert_not_called()

    def test_waits_until_two_laps_after_the_safety_car(self, pacelaps_generator, mocker):
        configure(pacelaps_generator, laps_under_safety_car=4)
        pacelaps_generator.current_lap_under_sc = 6
        send_command = mocker.patch.object(pacelaps_generator.command_sender, "send_command")

        assert pacelaps_generator._send_pacelaps() is False
        send_command.assert_not_called()

    def test_sends_pace_laps_once_the_leader_is_halfway_around(self, pacelaps_generator, mocker):
        configure(pacelaps_generator, laps_under_safety_car=4)
        pacelaps_generator.current_lap_under_sc = 7
        send_command = mocker.patch.object(pacelaps_generator.command_sender, "send_command")

        assert pacelaps_generator._send_pacelaps() is True
        send_command.assert_called_once_with("!p 3")


def test_generator_settings_from_settings_maps_every_field():
    """Each field comes from its own setting (distinct values, so swapped fields are caught)."""
    settings = dict_to_config({"settings": {
        "detection_start_minute": "1.5",
        "detection_end_minute": "45.5",
        "max_safety_cars": "5",
        "min_time_between_safety_cars_minutes": "6.5",
        "laps_under_safety_car": "4",
        "wave_arounds_enabled": "0",
        "laps_before_wave_arounds": "3",
        "wave_around_rules_index": "2",
        "class_split_enabled": "1",
    }})

    assert GeneratorSettings.from_settings(settings) == GeneratorSettings(
        detection_start_minute=1.5,
        detection_end_minute=45.5,
        max_safety_cars=5,
        min_time_between_safety_cars_minutes=6.5,
        laps_under_safety_car=4,
        wave_arounds_enabled=False,
        laps_before_wave_arounds=3,
        wave_around_rules_index=2,
        class_split_enabled=True,
    )


def test_generator_settings_defaults_match_settings_fallbacks():
    """GeneratorSettings() defaults are the same as an empty settings.ini."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        assert GeneratorSettings.from_settings(Settings(f"{tmp_dir}/settings.ini")) == GeneratorSettings()


class TestGeneratorThread:
    """Tests for run() and the lifecycle of the generator thread."""

    @pytest.fixture(autouse=True)
    def fast_sleep(self, mocker):
        """Make the generator loops spin quickly."""
        mocker.patch("core.generator.time.sleep", side_effect=lambda seconds: real_sleep(0.01))

    @pytest.fixture
    def settings(self):
        # Detection only starts after a minute, so no safety car is thrown during these tests
        return dict_to_config({"settings": {"detection_start_minute": "1.0", "max_safety_cars": "5"}})

    @pytest.fixture
    def sdks(self, mocker):
        """Every SDK instance the generator creates, serving a race already in progress."""
        created = []

        def create_sdk():
            created.append(FakeIRSDK(RACING_FRAME))
            return created[-1]

        mocker.patch("core.generator.irsdk.IRSDK", side_effect=create_sdk)
        return created

    @pytest.fixture
    def generator(self):
        mock_arguments = Mock()
        mock_arguments.disable_window_interactions = True
        mock_arguments.dry_run = True
        gen = Generator(arguments=mock_arguments)
        yield gen
        gen.stop()
        if gen.thread is not None:
            gen.thread.join(timeout=5)

    @staticmethod
    def wait_for_state(generator, state, timeout=5.0):
        deadline = time.monotonic() + timeout
        while generator.state != state:
            assert time.monotonic() < deadline, f"Timed out waiting for {state}, state is {generator.state}"
            real_sleep(0.01)

    @staticmethod
    def stop_and_join(generator):
        generator.stop()
        generator.thread.join(timeout=5)
        assert not generator.thread.is_alive()

    @staticmethod
    def published_events(generator):
        events = []
        while True:
            try:
                events.append(generator.ui_events.get_nowait())
            except queue.Empty:
                return events

    @classmethod
    def published_states(cls, generator):
        return [event.state for event in cls.published_events(generator) if isinstance(event, StateChanged)]

    def test_run_returns_immediately_and_connects_on_the_generator_thread(self, generator, settings, mocker):
        """Connecting can block (HTTP request, window lookup), so it must not happen on the UI thread."""
        release_startup = threading.Event()
        startup_threads = []

        class SlowSDK(FakeIRSDK):
            def startup(self):
                startup_threads.append(threading.current_thread().name)
                release_startup.wait(timeout=5)
                return super().startup()

        mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: SlowSDK(RACING_FRAME))

        assert generator.run(settings) is True
        self.wait_for_state(generator, GeneratorState.CONNECTING_TO_IRACING)

        release_startup.set()
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
        self.stop_and_join(generator)

        assert startup_threads == ["GeneratorThread"]

    def test_full_run_publishes_states_in_order(self, generator, settings, sdks):
        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
        self.stop_and_join(generator)

        assert self.published_states(generator) == [
            GeneratorState.CONNECTING_TO_IRACING,
            GeneratorState.CONNECTED,
            GeneratorState.WAITING_FOR_RACE_SESSION,
            GeneratorState.WAITING_FOR_GREEN,
            GeneratorState.MONITORING_FOR_INCIDENTS,
            GeneratorState.STOPPED,
        ]
        assert sdks[0].shutdown_calls == 1

    def test_recorded_race_raises_no_preflight_warnings(self, generator, settings, sdks):
        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
        self.stop_and_join(generator)

        assert not any(isinstance(event, PreflightWarnings) for event in self.published_events(generator))

    def test_preflight_warnings_are_published_and_the_run_continues(self, generator, settings, mocker):
        frame = copy.deepcopy(RACING_FRAME)
        frame["session_info"]["DriverInfo"]["PaceCarIdx"] = 0
        mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: FakeIRSDK(frame))

        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
        self.stop_and_join(generator)

        events = self.published_events(generator)
        warning = PreflightWarnings(["PaceCarIdx 0 does not point at the pace car entry (CarIdx 16)"])
        assert warning in events
        # Checked right after connecting, before the run builds anything on top of the data
        assert events.index(warning) == events.index(StateChanged(GeneratorState.CONNECTED)) + 1

    def test_sdk_connection_failure_reports_error_connecting(self, generator, settings, mocker):
        sdk = FakeIRSDK(RACING_FRAME, startup_result=False)
        mocker.patch("core.generator.irsdk.IRSDK", return_value=sdk)

        generator.run(settings)
        generator.thread.join(timeout=5)

        assert self.published_states(generator) == [
            GeneratorState.CONNECTING_TO_IRACING,
            GeneratorState.ERROR_CONNECTING,
        ]
        assert sdk.shutdown_calls == 1

    def test_window_connection_failure_reports_error_connecting(self, settings, sdks, mocker, caplog):
        """Regression: an error finding the iRacing window left the UI stuck on "Connecting to iRacing..."."""
        mocker.patch(
            "core.interactions.mock_window.MockWindow.connect",
            side_effect=RuntimeError("ElementNotFoundError: {'title': 'iRacing.com Simulator'}"),
        )
        mock_arguments = Mock()
        mock_arguments.disable_window_interactions = True
        mock_arguments.dry_run = False
        generator = Generator(arguments=mock_arguments)

        generator.run(settings)
        generator.thread.join(timeout=5)

        assert self.published_states(generator) == [
            GeneratorState.CONNECTING_TO_IRACING,
            GeneratorState.ERROR_CONNECTING,
        ]
        assert "Could not connect to the iRacing window" in caplog.text
        assert sdks[0].shutdown_calls == 1

    def test_setup_failure_reports_uncaught_exception_and_disconnects(self, generator, settings, sdks, mocker, caplog):
        """Regression: errors after connecting left the UI showing a running generator without a thread."""
        mocker.patch("core.drivers.Drivers", side_effect=TypeError("'NoneType' object is not subscriptable"))

        generator.run(settings)
        generator.thread.join(timeout=5)

        assert self.published_states(generator) == [
            GeneratorState.CONNECTING_TO_IRACING,
            GeneratorState.CONNECTED,
            GeneratorState.UNCAUGHT_EXCEPTION,
        ]
        assert "Generator thread threw an exception" in caplog.text
        assert sdks[0].shutdown_calls == 1

    def test_final_state_is_published_after_disconnecting(self, generator, settings, mocker):
        """Regression: STOPPED was shown before the SDK was shut down, so a quick restart could have its
        new connection closed by the previous run."""
        states_at_shutdown = []

        class RecordingSDK(FakeIRSDK):
            def shutdown(self):
                states_at_shutdown.append(generator.state)
                super().shutdown()

        mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: RecordingSDK(RACING_FRAME))

        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
        self.stop_and_join(generator)

        assert states_at_shutdown == [GeneratorState.MONITORING_FOR_INCIDENTS]
        assert generator.state == GeneratorState.STOPPED

    def test_each_run_uses_its_own_sdk_connection(self, generator, settings, sdks):
        for _ in range(2):
            generator.run(settings)
            self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)
            self.stop_and_join(generator)

        assert len(sdks) == 2
        assert sdks[0] is not sdks[1]
        assert [sdk.shutdown_calls for sdk in sdks] == [1, 1]

    def test_run_refuses_to_start_while_the_previous_run_is_active(self, generator, settings, sdks, mocker):
        release_loop = threading.Event()
        mocker.patch.object(generator, "_loop", side_effect=lambda: release_loop.wait(timeout=5))

        assert generator.run(settings) is True
        self.wait_for_state(generator, GeneratorState.CONNECTED)

        assert generator.run(settings) is False

        release_loop.set()
        generator.thread.join(timeout=5)
        assert generator.run(settings) is True

    def test_signals_left_over_from_a_previous_run_are_cleared(self, generator, settings, sdks):
        """Regression: pressing Stop when no thread was running left shutdown_event set."""
        generator.stop()
        generator.throw_manual_safety_car()
        generator.skip_wait_for_green()
        generator.confirm_class_split_event.set()

        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)

        assert generator.is_running()
        assert not generator.throw_manual_sc_event.is_set()
        assert not generator.confirm_class_split_event.is_set()
        self.stop_and_join(generator)

    def test_stop_before_the_loop_runs_does_not_raise(self, generator, settings, mocker, caplog):
        """Regression: logging the loop timer stats raised KeyError when the loop never ran."""
        not_started_frame = copy.deepcopy(RACING_FRAME)
        not_started_frame["telemetry"]["SessionFlags"] = 0
        not_started_frame["telemetry"]["SessionState"] = irsdk.SessionState.parade_laps
        mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: FakeIRSDK(not_started_frame))
        # Fresh timer registry, as other tests may already have run the loop in this process
        mocker.patch.object(Timer, "timers", type(Timer.timers)())

        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.WAITING_FOR_GREEN)
        self.stop_and_join(generator)

        assert generator.state == GeneratorState.STOPPED
        assert [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR] == []

    def test_settings_are_snapshotted_when_starting(self, generator, settings, sdks):
        generator.run(settings)
        self.wait_for_state(generator, GeneratorState.MONITORING_FOR_INCIDENTS)

        settings.laps_under_safety_car = 7

        assert generator.settings == GeneratorSettings.from_settings(dict_to_config({"settings": {
            "detection_start_minute": "1.0", "max_safety_cars": "5",
        }}))
        with pytest.raises(FrozenInstanceError):
            generator.settings.laps_under_safety_car = 7
        self.stop_and_join(generator)
