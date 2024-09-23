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
        logging.info("Drivers class initialized with master: %s", master)

        # Dictionaries to track the state of the drivers
        self.current_drivers = []
        self.previous_drivers = []

        # Do the initial update
        logging.debug("Performing initial update of driver data.")
        self.update()

    def update(self):
        """Update the current drivers with the latest data from the iRacing API.
        
        This method is called at the beginning of each loop to update the
        current drivers with the latest data from the iRacing API.
        
        Args:
            None
        """
        logging.debug("Updating driver data from iRacing API.")

        # Copy the current drivers to the previous drivers
        self.previous_drivers = deepcopy(self.current_drivers)
        logging.debug("Previous drivers data updated.")

        # Clear the current drivers
        self.current_drivers = []
        logging.debug("Current drivers list cleared.")

        # Gather the updated driver data
        laps_completed = self.master.ir["CarIdxLapCompleted"]
        lap_distance = self.master.ir["CarIdxLapDistPct"]
        track_loc = self.master.ir["CarIdxTrackSurface"]
        logging.debug("Fetched driver data from iRacing API.")

        # Organize the updated driver data and update the current drivers
        for i in range(len(laps_completed)):
            driver_data = {
                "laps_completed": laps_completed[i],
                "lap_distance": lap_distance[i],
                "track_loc": track_loc[i],
            }
            self.current_drivers.append(driver_data)
        logging.info("Current drivers data updated with %d drivers.", len(self.current_drivers))
