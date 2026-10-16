import argparse
import configparser
import os
import shutil
import sys
from pathlib import Path

import pytest

from core.app import App

SRC_DIR = Path(__file__).resolve().parents[2]

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
        app.destroy()


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

