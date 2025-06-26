import logging
from enum import Enum
from typing import List, Dict, Any

from util.generator_utils import positions_from_safety_car

logger = logging.getLogger(__name__)
class WaveAroundType(Enum):
    WAVE_LAPPED_CARS = "wave_lapped_cars"
    WAVE_AHEAD_OF_CLASS_LEAD = "wave_ahead_of_class_lead"

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
        case _:
            raise ValueError(f"Invalid wave around type: {wave_around_type}")

def wave_lapped_cars(
    drivers: List[Dict[str, Any]], 
    car_positions: List[float], 
    on_pit_road: List[bool], 
    pace_car_idx: int
) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars that are lapped.
        
        Args:
            drivers: The list of cars as provided by the irSDK DriverInfo->Drivers property.
            car_positions: The list of car positions as provided by the irSDK CarIdxLapDistPct property.
            on_pit_road: The list booleans indicating if cars are on pit road (CarIdxOnPitRoad)
            pace_car_idx: The index of the pacecar in car_positions as provided by the irSDK DriverInfo->PaceCarIdx property.

        Returns:
            List[str]: The commands to send, in order, for the cars to be waved.
    """

    raise NotImplementedError("wave_lapped_cars is not implemented yet.")

def wave_ahead_of_class_lead(
    drivers: List[Dict[str, Any]], 
    car_positions: List[float], 
    on_pit_road: List[bool], 
    pace_car_idx: int
) -> List[str]:
    """ Provide the commands that need to be sent to wave around the cars ahead of their class 
        lead in the running order behind the safety car.
        
        Args:
            drivers: The list of cars as provided by the irSDK DriverInfo->Drivers property.
            car_positions: The list of car positions as provided by the irSDK CarIdxLapDistPct property.
            on_pit_road: The list booleans indicating if cars are on pit road (CarIdxOnPitRoad)
            pace_car_idx: The index of the pacecar in car_positions as provided by the irSDK DriverInfo->PaceCarIdx property.

        Returns:
            List[str]: The commands to send, in order, for the cars to be waved.
    """
    logger.debug("Wave around ahead of class lead")
    logger.debug(f"Drivers: {drivers}")
    logger.debug(f"Car positions: {car_positions}")
    logger.debug(f"On pit road: {on_pit_road}")
    logger.debug(f"Pace car index: {pace_car_idx}")

    commands = []
    class_leads = {}
    relative_to_sc = positions_from_safety_car(car_positions, pace_car_idx)
    logger.debug(f"Relative positions to SC: {relative_to_sc}")

    # Identify the class leader for each class
    for idx, driver in enumerate(drivers):
        if idx == pace_car_idx:
            continue
        car_class = driver['CarClassID']
        if car_class not in class_leads or car_positions[idx] > car_positions[class_leads[car_class][0]]:
            class_leads[car_class] = (idx, relative_to_sc[idx])

    logger.debug(f"Class leads: {class_leads}")

    # Get positions relative to overall lead
    lead_idx = 0
    lead_position = 0
    for idx, position in enumerate(car_positions):
        if position > lead_position:
            lead_idx = idx
            lead_position = position

    # Identify cars ahead of their class leader and behind the overall lead
    for idx, driver in enumerate(drivers):
        if idx == pace_car_idx or on_pit_road[idx]:
            continue

        car_class = driver['CarClassID']
        class_lead_idx, class_lead_position = class_leads.get(car_class)

        if (class_lead_idx is not None # Should always be true
            and relative_to_sc[idx] < class_lead_position # They are ahead of their class lead
            and relative_to_sc[idx] > relative_to_sc[lead_idx] # and behind the overall lead
            ):
            car_number = driver['CarNumber']
            commands.append(f"!w {car_number}")

    logger.debug(f"Commands: {commands}")
    return commands

