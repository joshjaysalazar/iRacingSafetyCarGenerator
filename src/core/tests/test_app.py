import argparse
import configparser
import logging
import os
import shutil
import sys
import time
import tkinter as tk
from pathlib import Path

import pytest

from core import generator
from core.app import App
from core.generator import GeneratorState
from core.tests.test_utils import FakeIRSDK, load_dump_frame
from util.state_utils import generator_state_messages

SRC_DIR = Path(__file__).resolve().parents[2]

# A recorded race in progress: the generator goes straight to monitoring for incidents
RACING_FRAME = load_dump_frame("local_session_start_race_plus_two_laps.ndjson")

real_sleep = time.sleep

# Non-default values for every setting shown in the UI, so a field that is not loaded
# from or saved back to settings.ini shows up as a changed value
UI_SETTINGS = {
    "random_max_safety_cars": "3",
    "random_probability": "0.25",
    "random_message": "Debris on track",
    "stopped_cars_threshold": "3",
    "stopped_message": "Car stopped",
    "event_time_window_seconds": "7.0",
    "race_start_threshold_multiplier": "1.5",
    "race_start_threshold_multiplier_time_seconds": "45.0",
    "off_track_cars_threshold": "5",
    "off_track_message": "Cars off track",
    "max_safety_cars": "4",
    "detection_start_minute": "1.0",
    "detection_end_minute": "40.0",
    "min_time_between_safety_cars_minutes": "5.0",
    "laps_under_safety_car": "3",
    "laps_before_wave_arounds": "1",
    "wave_around_rules_index": "2",
    "proximity_filter_distance_percentage": "0.1",
    "accumulative_threshold": "8.0",
    "stopped_weight": "2.5",
    "off_track_weight": "1.5",
    "accumulative_message": "Multiple hazards",
}

CHECKBOX_SETTINGS = [
    "random_detector_enabled",
    "stopped_detector_enabled",
    "off_track_detector_enabled",
    "wave_arounds_enabled",
    "class_split_enabled",
    "proximity_filter_enabled",
    "accumulative_detector_enabled",
]

CHECKBOX_COMBINATIONS = [
    pytest.param({name: "1" for name in CHECKBOX_SETTINGS}, id="all_on"),
    pytest.param({name: "0" for name in CHECKBOX_SETTINGS}, id="all_off"),
] + [
    pytest.param({other: "0" if other == name else "1" for other in CHECKBOX_SETTINGS}, id=f"{name}_off")
    for name in CHECKBOX_SETTINGS
]


pytestmark = pytest.mark.skipif(
    sys.platform.startswith("linux") and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")),
    reason="Tk needs a display to create windows",
)


@pytest.fixture
def showerror(mocker):
    """Mock error dialogs so they never block the test run."""
    return mocker.patch("core.app.messagebox.showerror")


@pytest.fixture
def make_app(tmp_path, monkeypatch, capsys, showerror):
    """Build the real App against a settings.ini in a temporary working directory."""
    shutil.copytree(SRC_DIR / "assets", tmp_path / "assets")
    monkeypatch.chdir(tmp_path)
    apps = []

    def _make_app(settings: dict[str, str]) -> App:
        write_settings_file(tmp_path / "settings.ini", settings)
        arguments = argparse.Namespace(disable_window_interactions=True, developer_mode=False, dry_run=True)
        # On Windows, pytest's fd-level output capture intermittently breaks Tcl interpreter
        # initialization ("invalid command name tcl_findLibrary"), so suspend it while creating Tk
        with capsys.disabled():
            app = App(arguments)
        app.withdraw()
        apps.append(app)
        return app

    yield _make_app

    for app in apps:
        # Don't leave a generator thread behind if a test failed: it would keep the test process alive
        app.generator.stop()
        if app.generator.thread is not None:
            app.generator.thread.join(timeout=5)
        try:
            app.destroy()
        except tk.TclError:
            pass  # The test already closed the window


@pytest.fixture
def read_settings_file(tmp_path):
    """Read back the [settings] section of the settings.ini in the working directory."""
    def _read_settings_file() -> dict[str, str]:
        config = configparser.ConfigParser(interpolation=None)
        config.read(tmp_path / "settings.ini")
        return dict(config["settings"])

    return _read_settings_file


def write_settings_file(path: Path, settings: dict[str, str]):
    config = configparser.ConfigParser(interpolation=None)
    config["settings"] = settings
    with open(path, "w") as f:
        config.write(f)


def set_entry(widget, value: str):
    widget.delete(0, "end")
    widget.insert(0, value)


@pytest.mark.parametrize("checkboxes", CHECKBOX_COMBINATIONS)
def test_settings_round_trip_through_the_ui(make_app, read_settings_file, checkboxes):
    """Every value loaded into the UI is saved back unchanged, whichever checkboxes are off."""
    expected = {**UI_SETTINGS, **checkboxes}
    app = make_app(expected)

    assert app._save_settings() is True
    assert read_settings_file() == expected


def test_start_runs_generator_with_wave_arounds_disabled(make_app, showerror, mocker):
    """Regression: with wave arounds off in settings.ini, Start silently did nothing (v0.3.0 - v0.5.1).

    The checkbox disabled the laps field before it was filled, leaving it empty.
    """
    app = make_app({**UI_SETTINGS, "wave_arounds_enabled": "0", "laps_before_wave_arounds": "2"})
    run = mocker.patch.object(app.generator, "run", return_value=True)

    assert str(app.ent_laps_before_wave_arounds["state"]) == "disabled"
    assert app.ent_laps_before_wave_arounds.get() == "2"

    app._save_and_run()

    run.assert_called_once()
    showerror.assert_not_called()


def test_invalid_values_show_error_and_do_not_start(make_app, read_settings_file, showerror, mocker):
    app = make_app(UI_SETTINGS)
    run = mocker.patch.object(app.generator, "run")
    set_entry(app.ent_max_safety_cars, "two")
    set_entry(app.spn_off_min, "")

    app._save_and_run()

    run.assert_not_called()
    showerror.assert_called_once()
    message = showerror.call_args.args[1]
    assert "Maximum safety cars: 'two'" in message
    assert "Minimum to trigger (Cars off track): ''" in message
    # Nothing is written when any value is invalid
    assert read_settings_file() == UI_SETTINGS


def test_decimal_comma_is_accepted(make_app, read_settings_file):
    app = make_app(UI_SETTINGS)
    set_entry(app.ent_random_prob, "0,5")

    assert app._save_settings() is True
    assert read_settings_file()["random_probability"] == "0.5"


def test_percent_sign_in_message_is_saved(make_app, read_settings_file):
    app = make_app(UI_SETTINGS)
    set_entry(app.ent_random_message, "50% of the field is off track")

    assert app._save_settings() is True
    assert read_settings_file()["random_message"] == "50% of the field is off track"


@pytest.mark.parametrize("index", ["-1", "3", "99"])
def test_invalid_wave_around_rules_index_falls_back_to_first_option(make_app, index):
    """Regression: an out-of-range index in settings.ini made the app crash on launch."""
    app = make_app({**UI_SETTINGS, "wave_around_rules_index": index})

    assert app.cmb_wave_around_rules.current() == 0


def test_wave_around_rules_stay_readonly_after_toggling_wave_arounds(make_app):
    """Regression: re-enabling wave arounds made the rules combobox accept free text."""
    app = make_app({**UI_SETTINGS, "wave_arounds_enabled": "1"})

    app.var_wave_arounds.set(0)
    app.var_wave_arounds.set(1)

    assert str(app.cmb_wave_around_rules["state"]) == "readonly"


def test_exception_in_button_callback_is_logged_and_shown(make_app, showerror, mocker, caplog):
    app = make_app(UI_SETTINGS)
    mocker.patch.object(app, "_save_settings", side_effect=RuntimeError("boom"))

    app.btn_run.invoke()

    assert "Unhandled exception in UI callback" in caplog.text
    assert "RuntimeError: boom" in caplog.text
    showerror.assert_called_once()
    assert "boom" in showerror.call_args.args[1]


def pump_until(app, condition, timeout=5.0):
    """Process Tk events until condition() is true."""
    deadline = time.monotonic() + timeout
    while not condition():
        assert time.monotonic() < deadline, "Timed out waiting for the condition"
        app.update()
        real_sleep(0.01)


def test_generator_state_changes_update_the_ui(make_app):
    app = make_app(UI_SETTINGS)
    app.generator.ui_events.put(generator.StateChanged(GeneratorState.CONNECTING_TO_IRACING))
    app.generator.ui_events.put(generator.StateChanged(GeneratorState.MONITORING_FOR_INCIDENTS))

    app._process_generator_events()

    expected = generator_state_messages(None, None)[GeneratorState.MONITORING_FOR_INCIDENTS]
    assert app.generator_state == GeneratorState.MONITORING_FOR_INCIDENTS
    assert app.btn_run["text"] == expected["btn_run_text"]
    assert app.lbl_status["text"] == expected["message"]


def test_class_split_request_is_answered_through_a_dialog(make_app, mocker):
    app = make_app(UI_SETTINGS)
    askokcancel = mocker.patch("core.app.messagebox.askokcancel", return_value=True)
    confirm = mocker.patch.object(app.generator, "confirm_class_split")
    app.generator.ui_events.put(generator.ClassSplitConfirmationRequested(["!eol 12", "!eol 34"]))

    app._process_generator_events()

    assert "!eol 12" in askokcancel.call_args.args[1]
    confirm.assert_called_once_with(True)


def test_preflight_warnings_are_shown_without_stopping_the_generator(make_app, mocker):
    app = make_app(UI_SETTINGS)
    showwarning = mocker.patch("core.app.messagebox.showwarning")
    stop = mocker.patch.object(app.generator, "stop")
    app.generator.ui_events.put(generator.PreflightWarnings(["Unknown SessionState value 42", "DriverInfo has no PaceCarIdx"]))

    app._process_generator_events()

    message = showwarning.call_args.args[1]
    assert "  - Unknown SessionState value 42" in message
    assert "  - DriverInfo has no PaceCarIdx" in message
    stop.assert_not_called()


def test_generator_events_are_still_processed_after_an_error(make_app, showerror, mocker):
    """An error while applying an event must not end the polling, or the UI would freeze on that state."""
    app = make_app(UI_SETTINGS)
    mocker.patch.object(app, "on_generator_state_change", side_effect=[RuntimeError("boom"), None])

    # The scheduled poll fails on this event (reported via report_callback_exception)...
    app.generator.ui_events.put(generator.StateChanged(GeneratorState.CONNECTING_TO_IRACING))
    pump_until(app, lambda: showerror.called)

    # ...and keeps polling, so later events still reach the UI
    app.generator.ui_events.put(generator.StateChanged(GeneratorState.CONNECTED))
    pump_until(app, lambda: app.generator_state == GeneratorState.CONNECTED)


def test_skip_wait_for_green_button_signals_the_generator(make_app, mocker):
    app = make_app(UI_SETTINGS)
    skip_wait_for_green = mocker.patch.object(app.generator, "skip_wait_for_green")

    app._skip_wait_for_green()

    skip_wait_for_green.assert_called_once_with()


@pytest.mark.parametrize("state, expected_calls", [
    (GeneratorState.MONITORING_FOR_INCIDENTS, 1),
    (GeneratorState.WAITING_FOR_GREEN, 0),
    (GeneratorState.SAFETY_CAR_DEPLOYED, 0),
    (GeneratorState.STOPPED, 0),
])
def test_manual_safety_car_is_only_requested_while_monitoring(make_app, mocker, state, expected_calls):
    app = make_app(UI_SETTINGS)
    throw_manual_safety_car = mocker.patch.object(app.generator, "throw_manual_safety_car")
    app.generator._set_state(state)

    app._start_safety_car()

    assert throw_manual_safety_car.call_count == expected_calls


def test_class_split_request_from_a_stopping_generator_is_ignored(make_app, mocker):
    app = make_app(UI_SETTINGS)
    askokcancel = mocker.patch("core.app.messagebox.askokcancel")
    app.generator.stop()
    app.generator.ui_events.put(generator.ClassSplitConfirmationRequested(["!eol 12"]))

    app._process_generator_events()

    askokcancel.assert_not_called()


def test_quick_second_click_stops_the_generator(make_app, mocker, caplog):
    """The second click must act on the generator's state, not on the UI's copy that lags behind."""
    mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: FakeIRSDK(RACING_FRAME))
    mocker.patch("core.generator.time.sleep", side_effect=lambda seconds: real_sleep(0.01))
    app = make_app(UI_SETTINGS)
    run = mocker.spy(app.generator, "run")

    with caplog.at_level(logging.INFO, logger="core.app"):
        app.btn_run.invoke()
        app.btn_run.invoke()
        pump_until(app, lambda: not app.generator.is_running()
                   and app.generator_state == GeneratorState.STOPPED)

    run.assert_called_once()
    assert "Shutting down generator due to manual stop" in caplog.text


def test_closing_the_window_waits_for_the_generator_thread(make_app, mocker, caplog):
    """Regression: closing the window while the generator ran destroyed Tk right away, after which the
    generator thread still updated the UI and failed with "main thread is not in main loop"."""
    mocker.patch("core.generator.irsdk.IRSDK", side_effect=lambda: FakeIRSDK(RACING_FRAME))
    mocker.patch("core.generator.time.sleep", side_effect=lambda seconds: real_sleep(0.01))
    app = make_app(UI_SETTINGS)

    # Make the generator thread take a while to clean up after being stopped
    disconnect = app.generator._disconnect
    mocker.patch.object(app.generator, "_disconnect", side_effect=lambda: (real_sleep(0.3), disconnect()))

    app.btn_run.invoke()
    pump_until(app, lambda: app.generator_state == GeneratorState.MONITORING_FOR_INCIDENTS)

    generator_running_at_destroy = []
    destroy = app.destroy
    mocker.patch.object(app, "destroy", side_effect=lambda: (
        generator_running_at_destroy.append(app.generator.is_running()), destroy()))

    app.handle_delete_window()
    pump_until(app, lambda: generator_running_at_destroy)

    assert generator_running_at_destroy == [False]
    assert [record.getMessage() for record in caplog.records if record.levelno >= logging.ERROR] == []
