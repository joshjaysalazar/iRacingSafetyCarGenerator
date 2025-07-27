from irsdk import TrkLoc

class MockDrivers:
    def __init__(self, current = [], previous = []):
        self.current_drivers = current
        self.previous_drivers = previous

        # This is a fix to account for the SC entry in the drivers list
        # Ideally, we filter this out in the Drivers class so we don't have to account for this in all of our logic.
        self.current_drivers.append(make_driver(TrkLoc.not_in_world))
        self.previous_drivers.append(make_driver(TrkLoc.not_in_world))

def make_driver(track_loc, laps_completed = 0, lap_distance = 0.0):
    return {
        "track_loc": track_loc,
        "laps_completed": laps_completed,
        "lap_distance": lap_distance
    }
