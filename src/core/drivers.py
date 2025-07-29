from copy import deepcopy
from typing import TypedDict
from irsdk import TrkLoc
import logging

logger = logging.getLogger(__name__)

class Driver(TypedDict):
    driver_idx: int
    laps_completed: int
    lap_distance: float
    track_loc: TrkLoc

class Drivers:
    """The Drivers class is responsible for tracking the state of the drivers.
    
    The Drivers class is responsible for tracking the state of the drivers in
    the current session. It uses the iRacing API to gather the latest data
    about the drivers and stores it in a dictionary.
    """
    def __init__(self, master=None):
        """Initialize the Drivers class.
        
        Args:
            master (object): The master object that is responsible for the
                connection to the iRacing API.
        """
        self.master = master

        # Dictionaries to track the state of the drivers
        logger.debug("Creating drivers dictionaries")
        self.current_drivers: list[Driver] = []
        self.previous_drivers: list[Driver] = []

        # Do the initial update
        self.update()

    def update(self):
        """Update the current drivers with the latest data from the iRacing API.
        
        This method is called at the beginning of each loop to update the
        current drivers with the latest data from the iRacing API.
        
        Args:
            None
        """
        # Copy the current drivers to the previous drivers
        logger.debug("Copying current drivers to previous drivers")
        self.previous_drivers = deepcopy(self.current_drivers)

        # Clear the current drivers
        logger.debug("Clearing current drivers")
        self.current_drivers = []

        # Gather the updated driver data
        logger.debug("Gathering updated driver data")
        laps_completed = self.master.ir["CarIdxLapCompleted"]
        lap_distance = self.master.ir["CarIdxLapDistPct"]
        track_loc = self.master.ir["CarIdxTrackSurface"]

        # Organize the updated driver data and update the current drivers
        logger.debug("Organizing updated driver data")
        for i in range(len(laps_completed)):
            self.current_drivers.append(
                {
                "driver_idx": i,
                "laps_completed": laps_completed[i],
                "lap_distance": lap_distance[i],
                "track_loc": track_loc[i],
                }
            )