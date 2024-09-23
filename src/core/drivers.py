from copy import deepcopy
import logging


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
        self.current_drivers = []
        self.previous_drivers = []

        # Do the initial update
        self.update()

    def update(self):
        """Update the current drivers with the latest data from the iRacing API.
        
        This method is called at the beginning of each loop to update the
        current drivers with the latest data from the iRacing API.
        
        Args:
            None
        """
        try:
            # Copy the current drivers to the previous drivers
            self.previous_drivers = deepcopy(self.current_drivers)

            # Clear the current drivers
            self.current_drivers = []

        except Exception as e:
            logging.exception(
                "An error occurred copying current drivers to previous drivers."
            )
            raise e

        try:
            # Gather the updated driver data
            laps_completed = self.master.ir["CarIdxLapCompleted"]
            lap_distance = self.master.ir["CarIdxLapDistPct"]
            track_loc = self.master.ir["CarIdxTrackSurface"]
        except Exception as e:
            logging.exception(
                "An error occurred gathering updated driver data."
            )
            raise e

        try:
            # Organize the updated driver data and update the current drivers
            for i in range(len(laps_completed)):
                self.current_drivers.append(
                    {
                    "laps_completed": laps_completed[i],
                    "lap_distance": lap_distance[i],
                    "track_loc": track_loc[i],
                    }
                )
        except Exception as e:
            logging.exception(
                "An error occurred organizing updated driver data."
            )
            raise e