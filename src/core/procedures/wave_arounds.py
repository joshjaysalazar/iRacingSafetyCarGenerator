
from enum import Enum
from util.generator_utils import positions_from_safety_car

class WaveAroundType(Enum):
    WAVE_LAPPED_CARS = "wave_lapped_cars"
    WAVE_AHEAD_OF_CLASS_LEAD = "wave_ahead_of_class_lead"

def wave_arounds_factory(wave_around_type: WaveAroundType):
    match wave_around_type:
        case WaveAroundType.WAVE_LAPPED_CARS:
            return wave_lapped_cars
        case WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD:
            return wave_ahead_of_class_lead
        case _:
            raise ValueError(f"Invalid wave around type: {wave_around_type}")

def wave_lapped_cars(drivers, car_positions, on_pit_road, pace_car_idx):
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

def wave_ahead_of_class_lead(drivers, car_positions, on_pit_road, pace_car_idx):
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
    commands = []
    class_leads = {}
    relative_to_sc = positions_from_safety_car(car_positions, pace_car_idx)

    # Identify the class leader for each class
    for idx, driver in enumerate(drivers):
        if idx == pace_car_idx:
            continue
        car_class = driver['CarClassID']
        if car_class not in class_leads or car_positions[idx] > car_positions[class_leads[car_class][0]]:
            class_leads[car_class] = (idx, relative_to_sc[idx])

    # Identify cars ahead of their class leader and behind the pace car
    for idx, driver in enumerate(drivers):
        if idx == pace_car_idx or on_pit_road[idx]:
            continue

        car_class = driver['CarClassID']
        class_lead_idx, class_lead_position = class_leads.get(car_class)

        if class_lead_idx is not None and relative_to_sc[idx] < class_lead_position:
            car_number = driver['CarNumber']
            commands.append(f"!w {car_number}")

    return commands

