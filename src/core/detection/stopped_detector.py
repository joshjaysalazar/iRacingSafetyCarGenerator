from irsdk import TrkLoc
from core.drivers import Drivers

class StoppedDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the StoppedDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current and previous state of drivers.
        """
        self.drivers = drivers

    def detect(self):
        """Detect if any driver is stopped.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.

        Returns:
            list: A list of drivers that are stopped.
        """
        
        # Get the indices of the stopped cars
        stopped_cars = []
        for current, previous in zip(self.drivers.current_drivers, self.drivers.previous_drivers):
            if current["track_loc"] in [TrkLoc.aproaching_pits, 
                                        TrkLoc.in_pit_stall, 
                                        TrkLoc.not_in_world]:
                continue  # Skip cars that are not driving around

            if current["lap_distance"] < 0:
                continue # Skip unexpected data
            
            current_position = current["laps_completed"] + current["lap_distance"]
            previous_position = previous["laps_completed"] + previous["lap_distance"]
            if current_position <= previous_position:
                stopped_cars.append(current)

        # If length of stopped cars is entire field, clear list (lag fix)
        if len(stopped_cars) >= len(self.drivers.current_drivers) - 1:
            stopped_cars = []

        return stopped_cars
    