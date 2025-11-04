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

def wave_lapped_cars(drivers: List[Driver], pace_car_idx: int) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars that are lapped.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[str]: The commands to send, in order, for the cars to be waved.
    """
    logger.debug("Wave around lapped cars")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")
    logger.debug(f"Drivers: {drivers}")
    
    commands = []

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

        car_number = None

        # If driver started 2 or fewer laps than class leader, wave them
        lap_target = highest_lap[driver_class][0] - 2
        if driver["laps_started"] <= lap_target:
            car_number = driver["car_number"]

        # If they started 1 fewer laps & are behind on track, wave them
        lap_target = highest_lap[driver_class][0] - 1
        track_pos_target = highest_lap[driver_class][1]
        if driver["laps_started"] == lap_target and driver["lap_distance"] < track_pos_target:
            car_number = driver["car_number"]

        # If the car number is not None, add it to the list
        if car_number is not None:
            commands.append(f"!w {car_number}")

    logger.debug(f"Commands: {commands}")
    return commands

def wave_ahead_of_class_lead(drivers: List[Driver], pace_car_idx: int) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars ahead of their class
        lead in the running order behind the safety car.

        Args:
            drivers: The list of Driver objects from the Drivers data model.
            pace_car_idx: The index of the pacecar.

        Returns:
            List[str]: The commands to send, in order, for the cars to be waved.
    """
    logger.debug("Wave around ahead of class lead")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")
    logger.debug(f"Drivers: {drivers}")

    commands = []
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
            car_number = driver["car_number"]
            commands.append(f"!w {car_number}")

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
            List[str]: The commands to send, in order, for the cars to be waved.
    """
    logger.debug("Wave around combined (lapped + ahead of class lead)")
    logger.debug(f"Number of drivers: {len(drivers)}")
    logger.debug(f"Pace car index: {pace_car_idx}")

    # Get commands from both methods
    lapped_commands = wave_lapped_cars(drivers, pace_car_idx)
    ahead_commands = wave_ahead_of_class_lead(drivers, pace_car_idx)

    logger.debug(f"Lapped commands: {lapped_commands}")
    logger.debug(f"Ahead commands: {ahead_commands}")

    # Combine and deduplicate while preserving order
    # Use a set to track car numbers we've already added
    seen_cars = set()
    combined_commands = []

    for cmd in lapped_commands + ahead_commands:
        if cmd not in seen_cars:
            seen_cars.add(cmd)
            combined_commands.append(cmd)

    logger.debug(f"Combined commands: {combined_commands}")
    return combined_commands

