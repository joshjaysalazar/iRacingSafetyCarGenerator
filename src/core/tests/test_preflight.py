import copy

import pytest

from core.preflight import run_preflight_checks
from core.tests.test_utils import DUMPS_DIR, FakeIRSDK, load_dump_frame

# A recorded race in progress: 16 cars at CarIdx 0-15, the pace car at CarIdx 16
RACING_FRAME = load_dump_frame("local_session_start_race_plus_two_laps.ndjson")
PACE_CAR_IDX = 16


def connected_sdk(frame):
    sdk = FakeIRSDK(frame)
    sdk.startup()
    return sdk


@pytest.fixture
def frame():
    return copy.deepcopy(RACING_FRAME)


def drivers_of(frame):
    return frame["session_info"]["DriverInfo"]["Drivers"]


def move_car(frame, from_idx, to_idx):
    """Give a car another CarIdx, in DriverInfo and in every per-car telemetry array."""
    for driver in drivers_of(frame):
        if driver["CarIdx"] == from_idx:
            driver["CarIdx"] = to_idx
    for name, values in frame["telemetry"].items():
        if name.startswith("CarIdx") and isinstance(values, list):
            values[to_idx], values[from_idx] = values[from_idx], values[to_idx]


@pytest.mark.parametrize("dump_path", sorted(DUMPS_DIR.glob("*.ndjson")), ids=lambda path: path.stem)
@pytest.mark.parametrize("frame_index", [0, -1])
def test_recorded_sessions_pass(dump_path, frame_index):
    """Real SDK data must not raise false alarms."""
    assert run_preflight_checks(connected_sdk(load_dump_frame(dump_path.name, frame_index))) == []


def test_pace_car_at_car_idx_62_passes(frame):
    """Current iRacing builds put the pace car at CarIdx 62, after a gap; that is fine."""
    move_car(frame, PACE_CAR_IDX, 62)
    frame["session_info"]["DriverInfo"]["PaceCarIdx"] = 62

    assert run_preflight_checks(connected_sdk(frame)) == []


def test_missing_telemetry_value(frame):
    del frame["telemetry"]["CarIdxOnPitRoad"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Telemetry value CarIdxOnPitRoad is not available"]


def test_per_car_arrays_of_different_lengths(frame):
    frame["telemetry"]["CarIdxLap"] = frame["telemetry"]["CarIdxLap"][:63]

    warnings = run_preflight_checks(connected_sdk(frame))

    assert len(warnings) == 1
    assert warnings[0].startswith("The per-car telemetry arrays differ in length")
    assert "'CarIdxLap': 63" in warnings[0]


def test_unknown_session_state(frame):
    frame["telemetry"]["SessionState"] = 42

    assert run_preflight_checks(connected_sdk(frame)) == ["Unknown SessionState value 42"]


def test_missing_session_list(frame):
    del frame["session_info"]["SessionInfo"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Session info has no SessionInfo:Sessions list"]


def test_session_without_name(frame):
    del frame["session_info"]["SessionInfo"]["Sessions"][0]["SessionName"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Session 0 has no SessionName"]


def test_session_num_outside_session_list(frame):
    frame["telemetry"]["SessionNum"] = 3

    assert run_preflight_checks(connected_sdk(frame)) == ["SessionNum 3 is not one of the 1 sessions in SessionInfo"]


def test_missing_driver_list(frame):
    del frame["session_info"]["DriverInfo"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Session info has no DriverInfo:Drivers list"]


def test_driver_entry_missing_keys(frame):
    del drivers_of(frame)[3]["CarClassEstLapTime"]
    del drivers_of(frame)[3]["CarNumber"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Driver entry CarIdx 3 is missing CarNumber, CarClassEstLapTime"]


def test_duplicate_car_idx(frame):
    drivers_of(frame)[5]["CarIdx"] = 4

    assert run_preflight_checks(connected_sdk(frame)) == ["CarIdx values appear more than once in DriverInfo: [4]"]


def test_car_idx_outside_telemetry_arrays(frame):
    """e.g. more entries than the 64-slot arrays, without [Misc] irsdkLogAllCars=1."""
    drivers_of(frame)[PACE_CAR_IDX]["CarIdx"] = 70
    frame["session_info"]["DriverInfo"]["PaceCarIdx"] = 70

    assert run_preflight_checks(connected_sdk(frame)) == ["CarIdx [70] fall outside the 64-entry telemetry arrays"]


def test_more_than_one_pace_car(frame):
    move_car(frame, 15, 63)
    drivers_of(frame)[15]["CarIsPaceCar"] = 1

    warnings = run_preflight_checks(connected_sdk(frame))

    assert warnings == ["Expected one pace car, found 2 (CarIdx [63, 16]); "
                        "wave arounds and class splits assume a single pace car"]


def test_no_pace_car(frame):
    drivers_of(frame)[PACE_CAR_IDX]["CarIsPaceCar"] = 0
    frame["session_info"]["DriverInfo"]["PaceCarIdx"] = -1

    assert run_preflight_checks(connected_sdk(frame))[0].startswith("Expected one pace car, found 0")


def practice_session(number):
    return {"SessionNum": number, "SessionName": "PRACTICE", "SessionType": "Practice"}


def remove_pace_car(frame, pace_car_idx):
    frame["session_info"]["DriverInfo"]["Drivers"] = [d for d in drivers_of(frame) if d["CarIsPaceCar"] != 1]
    frame["session_info"]["DriverInfo"]["PaceCarIdx"] = pace_car_idx


@pytest.mark.parametrize("pace_car_idx", [62, -1])
def test_practice_only_event_without_pace_car_passes(frame, pace_car_idx):
    """An event without a race session has no pace car entry, while PaceCarIdx is 62, or -1 with
    irsdkLogAllCars=1 (both seen live)."""
    frame["session_info"]["SessionInfo"]["Sessions"] = [practice_session(0)]
    remove_pace_car(frame, pace_car_idx)

    assert run_preflight_checks(connected_sdk(frame)) == []


def test_practice_session_of_a_race_event_passes(frame):
    """A race event lists the pace car from its practice session on (seen live)."""
    frame["session_info"]["SessionInfo"]["Sessions"].insert(0, practice_session(0))
    frame["telemetry"]["SessionNum"] = 0

    assert run_preflight_checks(connected_sdk(frame)) == []


def test_practice_session_of_a_race_event_without_pace_car(frame):
    """The pace car checks also run before the race session, where people usually press Start."""
    frame["session_info"]["SessionInfo"]["Sessions"].insert(0, practice_session(0))
    frame["telemetry"]["SessionNum"] = 0
    remove_pace_car(frame, -1)

    assert run_preflight_checks(connected_sdk(frame))[0].startswith("Expected one pace car, found 0")


def test_session_without_type(frame):
    del frame["session_info"]["SessionInfo"]["Sessions"][0]["SessionType"]

    assert run_preflight_checks(connected_sdk(frame)) == ["Session 0 has no SessionType"]


def test_pace_car_idx_not_pointing_at_the_pace_car(frame):
    frame["session_info"]["DriverInfo"]["PaceCarIdx"] = 0

    assert run_preflight_checks(connected_sdk(frame)) == ["PaceCarIdx 0 does not point at the pace car entry (CarIdx 16)"]


def test_missing_pace_car_idx(frame):
    del frame["session_info"]["DriverInfo"]["PaceCarIdx"]

    assert run_preflight_checks(connected_sdk(frame)) == ["DriverInfo has no PaceCarIdx"]


def test_unknown_track_surface(frame):
    frame["telemetry"]["CarIdxTrackSurface"][2] = 9

    assert run_preflight_checks(connected_sdk(frame)) == ["Unknown CarIdxTrackSurface values [9]"]


def test_a_check_failing_on_unexpected_data_becomes_a_warning(frame):
    frame["session_info"]["DriverInfo"]["Drivers"] = [None]

    warnings = run_preflight_checks(connected_sdk(frame))

    assert len(warnings) == 1
    assert warnings[0].startswith("Could not check the iRacing data (_check_drivers)")


def test_warnings_are_logged(frame, caplog):
    frame["telemetry"]["SessionState"] = 42

    run_preflight_checks(connected_sdk(frame))

    assert "Preflight: Unknown SessionState value 42" in caplog.text
