import random

import irsdk


class Generator:
    def __init__(self, master=None):
        self.master = master

    def setup(self):
        # Proxy variables for settings
        min_safety_cars = self.master.settings["settings"]["min_safety_cars"]
        max_safety_cars = self.master.settings["settings"]["max_safety_cars"]
        start_minute = self.master.settings["settings"]["start_minute"]
        end_minute = self.master.settings["settings"]["end_minute"]
        min_time_between = self.master.settings["settings"]["min_time_between"]

        # Randomly determine number of safety car events
        self.number_sc = random.randint(min_safety_cars, max_safety_cars) 

        # Randomly determine safety car event times in minutes
        self.sc_times = []
        if self.number_sc > 0:
            for i in range(self.number_sc):
                # If 1st safety car event, pick random time between start & end
                if i == 0:
                    start = start_minute
                    end = end_minute
                # If not, pick random time between previous SC event and the end
                else:
                    # If there's not enough time for another SC event, break
                    if self.sc_times[i - 1] + min_time_between > end_minute:
                        break
                    start = self.sc_times[i - 1] + min_time_between
                    end = end_minute
                self.sc_times.append(random.uniform(start, end))

        # Add message to text box
        self.master.sc_text.insert(
            "end",
            f"Generated safety car event times.\n"
        )

        # Connect to iRacing
        ir = irsdk.IRSDK()

        # Attempt to connect and tell user if successful
        if ir.startup():
            self.master.sc_text.insert(
                "end",
                f"Connected to iRacing.\n"
            )
            self.master.sc_text.insert(
                "end",
                f"Be sure to click on the iRacing window to give it focus!\n"
            )
        else:
            self.master.sc_text.insert(
                "end",
                f"Error connecting to iRacing.\n"
            )

    def run(self):
        pass