from copy import deepcopy


class Drivers:
    def __init__(self, master=None):
        self.master = master

        # Dictionaries to track the state of the drivers
        self.current_drivers = {}
        self.previous_drivers = {}

    def _loop(self):
        pass

    def _update(self):
        # Copy the current drivers to the previous drivers
        self.previous_drivers = deepcopy(self.current_drivers)

        # Update the current drivers
        

    def run(self):
        pass
        