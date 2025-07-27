from irsdk import TrkLoc
from core.drivers import Drivers

class OffTrackDetector:
    def __init__(self, drivers: Drivers):
        """Initialize the OffTrackDetector.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.
        """
        self.drivers = drivers

    def detect(self):
        """Detect if any driver is off track.

        Args:
            drivers (Drivers): The Drivers object containing the current state of drivers.

        Returns:
            list: A list of drivers that are off track.
        """
        off_track_drivers = []
        for driver in self.drivers.current_drivers:
            if driver["track_loc"] == TrkLoc.off_track and \
               driver["laps_completed"] >= 0:
               
               # driver is off track and is active in the session
               off_track_drivers.append(driver)
        
        return off_track_drivers
    