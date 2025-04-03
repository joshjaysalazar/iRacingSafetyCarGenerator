
from enum import Enum

class WaveAroundType(Enum):
    WAVE_LAPPED_CARS = "wave_lapped_cars"
    WAVE_AHEAD_OF_CLASS_LEAD = "wave_ahead_of_class_lead"

def wave_arounds_factory(wave_around_type: WaveAroundType):
    cases = {
        WaveAroundType.WAVE_LAPPED_CARS: wave_lapped_cars,
        WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD: wave_ahead_of_class_lead,
    }
    if wave_around_type not in cases:
        raise ValueError(f"Invalid wave around type: {wave_around_type}")
    return cases[wave_around_type]

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
    raise NotImplementedError("wave_ahead_of_lead is not implemented yet.")

