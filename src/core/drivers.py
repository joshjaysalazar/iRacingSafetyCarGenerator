from copy import deepcopy
from typing import TypedDict, Optional
from irsdk import TrkLoc
import logging

logger = logging.getLogger(__name__)

class Driver(TypedDict):
    """Driver state containing all relevant iRacing SDK data for a single driver."""
    driver_idx: int
    car_number: str
    car_class_id: int
    is_pace_car: bool
    laps_completed: int
    laps_started: int
    lap_distance: float
    total_distance: float
    track_loc: TrkLoc
    on_pit_road: bool

class SessionInfo(TypedDict):
    """Session-level information from iRacing SDK."""
    pace_car_idx: int

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
        self.session_info: SessionInfo = {"pace_car_idx": -1}

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

        # Gather the updated driver data from SDK
        logger.debug("Gathering updated driver data")
        laps_completed = self.master.ir["CarIdxLapCompleted"]
        laps_started = self.master.ir["CarIdxLap"]
        lap_distance = self.master.ir["CarIdxLapDistPct"]
        track_loc = self.master.ir["CarIdxTrackSurface"]
        on_pit_road = self.master.ir["CarIdxOnPitRoad"]
        driver_info = self.master.ir["DriverInfo"]["Drivers"]

        # Update session info
        self.session_info = {
            "pace_car_idx": self.master.ir["DriverInfo"]["PaceCarIdx"]
        }

        # Organize the updated driver data and update the current drivers
        # Loop over actual drivers and fetch corresponding values from idx arrays
        logger.debug("Organizing updated driver data")
        for driver_details in driver_info:
            car_idx = driver_details["CarIdx"]
            self.current_drivers.append(
                {
                    "driver_idx": car_idx,
                    "car_number": driver_details["CarNumber"],
                    "car_class_id": driver_details["CarClassID"],
                    "is_pace_car": driver_details["CarIsPaceCar"] == 1,
                    "laps_completed": laps_completed[car_idx],
                    "laps_started": laps_started[car_idx],
                    "lap_distance": lap_distance[car_idx],
                    "total_distance": laps_completed[car_idx] + lap_distance[car_idx],
                    "track_loc": track_loc[car_idx],
                    "on_pit_road": on_pit_road[car_idx],
                }
            )