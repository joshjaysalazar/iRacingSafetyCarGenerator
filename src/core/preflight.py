import logging

import irsdk

logger = logging.getLogger(__name__)

# Telemetry values the generator and the Drivers model read. When code starts relying on a
# new SDK value or assumption, add a check for it here.
REQUIRED_TELEMETRY = [
    "CarIdxLap",
    "CarIdxLapCompleted",
    "CarIdxLapDistPct",
    "CarIdxTrackSurface",
    "CarIdxOnPitRoad",
    "CarIdxSessionFlags",
    "SessionFlags",
    "SessionNum",
    "SessionState",
]

# Per-car telemetry arrays, indexed by CarIdx
CAR_IDX_ARRAYS = [name for name in REQUIRED_TELEMETRY if name.startswith("CarIdx")]

# Keys of the DriverInfo:Drivers entries read by Drivers.update()
REQUIRED_DRIVER_KEYS = ["CarIdx", "CarNumber", "CarClassID", "CarClassEstLapTime", "CarIsPaceCar"]

def _constant_values(constants) -> set[int]:
    """The values of an irsdk constants class such as irsdk.TrkLoc."""
    return {value for name, value in vars(constants).items() if not name.startswith("_")}

KNOWN_TRACK_SURFACES = _constant_values(irsdk.TrkLoc)
KNOWN_SESSION_STATES = _constant_values(irsdk.SessionState)

def run_preflight_checks(ir) -> list[str]:
    """Check that the iRacing SDK data still looks the way the generator assumes.

    iRacing updates can change how the SDK reports data (e.g. the pace car moving to
    CarIdx 62 in 2026), which can silently break the safety car procedures. These checks
    only report problems; the caller decides what to do with them.

    Args:
        ir: A connected irsdk.IRSDK instance.

    Returns:
        list[str]: A readable warning per broken assumption; empty if everything checks out.
    """
    warnings = []
    for check in (_check_telemetry, _check_sessions, _check_drivers):
        try:
            warnings += check(ir)
        except Exception as e:
            # A check tripping over the data is itself a sign that the data changed
            logger.exception(f"Preflight check {check.__name__} failed")
            warnings.append(f"Could not check the iRacing data ({check.__name__}): {e}")

    for warning in warnings:
        logger.warning(f"Preflight: {warning}")
    if not warnings:
        logger.info("Preflight: iRacing SDK data looks as expected")

    return warnings

def _check_telemetry(ir) -> list[str]:
    """Check the telemetry values we read exist and the per-car arrays line up."""
    warnings = [f"Telemetry value {name} is not available" for name in REQUIRED_TELEMETRY if ir[name] is None]

    lengths = {name: len(ir[name]) for name in CAR_IDX_ARRAYS if ir[name] is not None}
    if len(set(lengths.values())) > 1:
        warnings.append(f"The per-car telemetry arrays differ in length: {lengths}")

    session_state = ir["SessionState"]
    if session_state is not None and session_state not in KNOWN_SESSION_STATES:
        warnings.append(f"Unknown SessionState value {session_state}")

    return warnings

def _check_sessions(ir) -> list[str]:
    """Check the session list used to wait for the race session."""
    sessions = (ir["SessionInfo"] or {}).get("Sessions")
    if not sessions:
        return ["Session info has no SessionInfo:Sessions list"]

    warnings = [f"Session {i} has no {key}" for i, session in enumerate(sessions)
                for key in ("SessionName", "SessionType") if key not in session]

    session_num = ir["SessionNum"]
    if session_num is not None and not 0 <= session_num < len(sessions):
        warnings.append(f"SessionNum {session_num} is not one of the {len(sessions)} sessions in SessionInfo")

    return warnings

def _event_has_race_session(ir) -> bool:
    """Whether any session of the current event is a race session, per its SessionType."""
    sessions = (ir["SessionInfo"] or {}).get("Sessions") or []
    return any(session.get("SessionType") == "Race" for session in sessions)

def _check_drivers(ir) -> list[str]:
    """Check the driver entries, their CarIdx values and the pace car."""
    driver_info = ir["DriverInfo"]
    if not driver_info or not driver_info.get("Drivers"):
        return ["Session info has no DriverInfo:Drivers list"]
    drivers = driver_info["Drivers"]

    warnings = []
    for driver in drivers:
        missing = [key for key in REQUIRED_DRIVER_KEYS if key not in driver]
        if missing:
            warnings.append(f"Driver entry CarIdx {driver.get('CarIdx', '?')} is missing {', '.join(missing)}")
    if warnings:
        # The checks below rely on these keys
        return warnings

    # Drivers.update() reads every telemetry array at each driver's CarIdx
    car_idxs = [driver["CarIdx"] for driver in drivers]
    duplicates = sorted({car_idx for car_idx in car_idxs if car_idxs.count(car_idx) > 1})
    if duplicates:
        warnings.append(f"CarIdx values appear more than once in DriverInfo: {duplicates}")

    lap_distance = ir["CarIdxLapDistPct"]
    if lap_distance is not None:
        outside = [car_idx for car_idx in car_idxs if not 0 <= car_idx < len(lap_distance)]
        if outside:
            warnings.append(f"CarIdx {outside} fall outside the {len(lap_distance)}-entry telemetry arrays")

    # The safety car procedures assume exactly one pace car, found through PaceCarIdx. An event
    # with a race session lists the pace car from its first session on, but an event without one
    # (e.g. a standalone pre-race practice) has no pace car entry at all (both seen live).
    pace_car_idx = driver_info.get("PaceCarIdx")
    pace_cars = [driver["CarIdx"] for driver in drivers if driver["CarIsPaceCar"] == 1]
    if pace_car_idx is None:
        warnings.append("DriverInfo has no PaceCarIdx")
    elif not _event_has_race_session(ir):
        logger.info("Preflight: this event has no race session, skipping the pace car checks")
    elif len(pace_cars) != 1:
        warnings.append(f"Expected one pace car, found {len(pace_cars)} (CarIdx {pace_cars}); "
                        f"wave arounds and class splits assume a single pace car")
    elif pace_cars[0] != pace_car_idx:
        warnings.append(f"PaceCarIdx {pace_car_idx} does not point at the pace car entry (CarIdx {pace_cars[0]})")

    # Detectors and procedures compare CarIdxTrackSurface against the irsdk.TrkLoc constants
    track_surfaces = ir["CarIdxTrackSurface"]
    if track_surfaces is not None:
        seen = {track_surfaces[car_idx] for car_idx in car_idxs if 0 <= car_idx < len(track_surfaces)}
        unknown = sorted(seen - KNOWN_TRACK_SURFACES)
        if unknown:
            warnings.append(f"Unknown CarIdxTrackSurface values {unknown}")

    return warnings
