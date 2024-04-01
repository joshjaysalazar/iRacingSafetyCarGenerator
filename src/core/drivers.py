from copy import deepcopy
import threading
import time


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

        # Track whether the class is running
        self.running = False

        # Dictionaries to track the state of the drivers
        self.current_drivers = []
        self.previous_drivers = []

        # Do the initial update
        self._update()

    def _loop(self):
        """The main loop for the Drivers class.
        
        Args:
            None
        """
        while self.running:
            # Update the current drivers
            self._update()

            # Wait 1 second before the next loop
            time.sleep(1)

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
        """Start the Drivers class.
        
        This method starts the Drivers class by setting the running flag to
        True and running the main loop in a separate thread.
        
        Args:
            None
        """
        # Set the running flag to True
        self.running = True

        # Run the loop in a separate thread
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()