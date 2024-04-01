from copy import deepcopy
import time


class Drivers:
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
        self._update()

    def _loop(self):
        pass

    def _update(self):
        """Update the current drivers with the latest data from the iRacing API.
        
        This method is called at the beginning of each loop to update the
        current drivers with the latest data from the iRacing API.
        
        Args:
            None
        """
        # Copy the current drivers to the previous drivers
        self.previous_drivers = deepcopy(self.current_drivers)

        # Clear the current drivers
        self.current_drivers = []

        # Gather the updated driver data
        in_pits = self.master.ir["CarIdxOnPitRoad"]
        lap_distance = self.master.ir["CarIdxLapDistPct"]
        track_surface = self.master.ir["CarIdxTrackSurfaceMaterial"]

        # Organize the updated driver data and update the current drivers
        for i in range(len(in_pits)):
            self.current_drivers.append(
                {
                "in_pits": in_pits[i],
                "lap_distance": lap_distance[i],
                "track_surface": track_surface[i]
                }
            )

    def run(self):
        pass
        