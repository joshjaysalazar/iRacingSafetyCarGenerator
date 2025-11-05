import logging
from enum import Enum
from typing import List

from core.drivers import Driver
from util.generator_utils import positions_from_safety_car

logger = logging.getLogger(__name__)
class WaveAroundType(Enum):
    WAVE_LAPPED_CARS = "wave_lapped_cars"
    WAVE_AHEAD_OF_CLASS_LEAD = "wave_ahead_of_class_lead"
    WAVE_COMBINED = "wave_combined"

def wave_around_type_from_selection(selection: int) -> WaveAroundType:
    """ Convert the selection from the GUI to a WaveAroundType.

        Args:
            selection (int): The selection from the GUI.

        Returns:
            WaveAroundType: The corresponding WaveAroundType.
    """
    if selection == 0:
        return WaveAroundType.WAVE_LAPPED_CARS
    elif selection == 1:
        return WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD
    elif selection == 2:
        return WaveAroundType.WAVE_COMBINED
    else:
        raise ValueError(f"Invalid selection: {selection}")

def wave_arounds_factory(wave_around_type: WaveAroundType):
    """Get the appropriate wave around function based on the type of wave arounds.

        Args:
            wave_around_type (WaveAroundType): The type of wave arounds.

        Returns:
            Callable: The function to use for the wave arounds.
    """
    match wave_around_type:
        case WaveAroundType.WAVE_LAPPED_CARS:
            return wave_lapped_cars
        case WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD:
            return wave_ahead_of_class_lead
        case WaveAroundType.WAVE_COMBINED:
            return wave_combined
        case _:
            raise ValueError(f"Invalid wave around type: {wave_around_type}")

def drivers_to_wave_commands(drivers: List[Driver], pace_car_idx: int, eligible_driver_indices: List[int]) -> List[str]:
    """Convert a list of eligible driver indices to wave commands, sorted by running order.

        Args:
            drivers: The full list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.
            eligible_driver_indices: List of driver_idx values for eligible drivers.

        Returns:
            List[str]: The wave commands, sorted by running order behind the safety car.
    """
    if not eligible_driver_indices:
        return []

    # Calculate relative positions to safety car
    car_positions = [driver["lap_distance"] for driver in drivers]
    relative_to_sc = positions_from_safety_car(car_positions, pace_car_idx)

    # Collect eligible cars with their positions
    eligible_cars = []
    for idx in eligible_driver_indices:
        driver = drivers[idx]
        eligible_cars.append((relative_to_sc[idx], driver["car_number"]))

    # Sort by position (smallest = closest behind SC) and create commands
    eligible_cars.sort(key=lambda x: x[0])
    commands = [f"!w {car_number}" for _, car_number in eligible_cars]

    return commands

def _get_lapped_car_indices(drivers: List[Driver], pace_car_idx: int) -> List[int]:
    """Internal helper to get indices of cars that are lapped.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[int]: Driver indices of eligible cars.
    """
    # Get all class IDs (except safety car)
    class_ids = []
    for driver in drivers:
        # Skip the safety car
        if driver["is_pace_car"]:
            continue

        # If the class ID isn't already in the list, add it
        if driver["car_class_id"] not in class_ids:
            class_ids.append(driver["car_class_id"])

    # Get the highest started lap for each class
    highest_lap = {}
    for class_id in class_ids:
        # Get the highest lap and track position for the current class
        max_lap = (0, 0.0)
        for driver in drivers:
            if driver["car_class_id"] == class_id:
                if driver["laps_started"] > max_lap[0]:
                    max_lap = (driver["laps_started"], driver["lap_distance"])

        # Add the highest lap to the dictionary
        highest_lap[class_id] = max_lap

    logger.debug(f"Class leaders: {highest_lap}")

    # Collect eligible driver indices
    eligible_driver_indices = []

    # For each driver, check if they're eligible for a wave around
    for driver in drivers:
        # Skip pace car
        if driver["driver_idx"] == pace_car_idx or driver["on_pit_road"]:
            continue

        # Get the class ID for the current driver
        driver_class = driver["car_class_id"]

        # If the class ID isn't in the class IDs list, skip the driver
        if driver_class not in class_ids:
            continue

        is_eligible = False

        # If driver started 2 or fewer laps than class leader, wave them
        lap_target = highest_lap[driver_class][0] - 2
        if driver["laps_started"] <= lap_target:
            is_eligible = True

        # If they started 1 fewer laps & are behind on track, wave them
        lap_target = highest_lap[driver_class][0] - 1
        track_pos_target = highest_lap[driver_class][1]
        if driver["laps_started"] == lap_target and driver["lap_distance"] < track_pos_target:
            is_eligible = True

        # If eligible, add driver index to the list
        if is_eligible:
            eligible_driver_indices.append(driver["driver_idx"])

    return eligible_driver_indices

def wave_lapped_cars(drivers: List[Driver], pace_car_idx: int) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars that are lapped.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[str]: The commands to send, in running order behind the safety car.
    """
    logger.debug("Wave around lapped cars")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")
    logger.debug(f"Drivers: {drivers}")

    # Get eligible driver indices
    eligible_driver_indices = _get_lapped_car_indices(drivers, pace_car_idx)

    # Convert eligible drivers to wave commands in running order
    commands = drivers_to_wave_commands(drivers, pace_car_idx, eligible_driver_indices)
    logger.debug(f"Commands: {commands}")
    return commands

def _get_ahead_of_class_lead_indices(drivers: List[Driver], pace_car_idx: int) -> List[int]:
    """Internal helper to get indices of cars ahead of their class lead.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[int]: Driver indices of eligible cars.
    """
    class_leads = {}

    # Extract lap distances for positions_from_safety_car
    car_positions = [driver["lap_distance"] for driver in drivers]
    relative_to_sc = positions_from_safety_car(car_positions, pace_car_idx)
    logger.debug(f"Relative positions to SC: {relative_to_sc}")

    # Identify the class leader for each class
    for driver in drivers:
        idx = driver["driver_idx"]
        if idx == pace_car_idx:
            continue
        car_class = driver["car_class_id"]
        if car_class not in class_leads or driver["total_distance"] > drivers[class_leads[car_class][0]]["total_distance"]:
            class_leads[car_class] = (idx, relative_to_sc[idx])

    logger.debug(f"Class leads: {class_leads}")

    # Get positions relative to overall lead
    lead_idx = 0
    lead_position = 0.0
    for driver in drivers:
        if driver["total_distance"] > lead_position:
            lead_idx = driver["driver_idx"]
            lead_position = driver["total_distance"]

    # Collect eligible driver indices
    eligible_driver_indices = []

    # Identify cars ahead of their class leader and behind the overall lead
    for driver in drivers:
        idx = driver["driver_idx"]
        if idx == pace_car_idx or driver["on_pit_road"]:
            logger.debug(f"Skipping driver idx {idx} (pace car or on pit road)")
            continue

        car_class = driver["car_class_id"]
        class_lead_idx, class_lead_position = class_leads.get(car_class)
        logger.debug(f"Driver idx {idx} class lead idx {class_lead_idx}")
        logger.debug(f"Driver idx {idx} relative to SC: {relative_to_sc[idx]}")
        logger.debug(f"Class lead position: {class_lead_position}")

        if (class_lead_idx is not None # Should always be true
            and relative_to_sc[idx] < class_lead_position # They are ahead of their class lead
            and relative_to_sc[idx] > relative_to_sc[lead_idx] # and behind the overall lead
            ):
            eligible_driver_indices.append(idx)

    return eligible_driver_indices

def wave_ahead_of_class_lead(drivers: List[Driver], pace_car_idx: int) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars ahead of their class
        lead in the running order behind the safety car.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[str]: The commands to send, in running order behind the safety car.
    """
    logger.debug("Wave around ahead of class lead")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")
    logger.debug(f"Drivers: {drivers}")

    # Get eligible driver indices
    eligible_driver_indices = _get_ahead_of_class_lead_indices(drivers, pace_car_idx)

    # Convert eligible drivers to wave commands in running order
    commands = drivers_to_wave_commands(drivers, pace_car_idx, eligible_driver_indices)
    logger.debug(f"Commands: {commands}")
    return commands

def wave_combined(drivers: List[Driver], pace_car_idx: int) -> List[str]:
    """ Provide the commands that need to be sent to wave around cars that are either lapped
        OR ahead of their class lead. This is a combination of both wave_lapped_cars and
        wave_ahead_of_class_lead methods.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[str]: The commands to send, in running order behind the safety car.
    """
    logger.debug("Wave around combined (lapped + ahead of class lead)")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")

    # Get eligible driver indices from both methods
    lapped_indices = _get_lapped_car_indices(drivers, pace_car_idx)
    ahead_indices = _get_ahead_of_class_lead_indices(drivers, pace_car_idx)

    logger.debug(f"Lapped indices: {lapped_indices}")
    logger.debug(f"Ahead indices: {ahead_indices}")

    # Combine and deduplicate indices
    combined_indices = list(set(lapped_indices + ahead_indices))

    logger.debug(f"Combined unique indices: {combined_indices}")

    # Convert all eligible drivers to wave commands in running order
    commands = drivers_to_wave_commands(drivers, pace_car_idx, combined_indices)
    logger.debug(f"Commands: {commands}")
    return commands

