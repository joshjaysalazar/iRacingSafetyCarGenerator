import random
import threading
import time

import irsdk
import pyautogui


class Generator:
    def __init__(self, master=None):
        self.master = master

    def _loop(self):
        # Wait for green flag
        self.master.add_message("Waiting for green flag...")
        while True:
            if self.ir["SessionFlags"] & irsdk.Flags.green:
                self.start_time = self.ir["SessionTime"]
                self.master.add_message(
                    "Race has started. Green flag is out."
                )
                self.master.add_message(
                    "Waiting for safety car events..."
                )
                break

            # Wait 1 second before checking again
            time.sleep(1)

        # Loop through safety car events
        while True:
            # If there are no more safety car events, break
            if len(self.sc_times) == 0:
                break

            # If the current time is past the next safety car event, trigger it
            if self.ir["SessionTime"] > self.start_time + (
                self.sc_times[0] * 60
            ):
                self.master.add_message(
                    f"Safety car event triggered at {self.ir['SessionTime']}"
                )

                # Send yellow flag chat command
                self.ir.chat_command(1)
                time.sleep(0.05)
                pyautogui.write("!yellow", interval=0.01)
                time.sleep(0.05)
                pyautogui.press("enter")

                # Remove the safety car event from the list
                self.sc_times.pop(0)

                # Get the max value from all cars' lap started count
                lap_at_yellow = max(self.ir["CarIdxLap"])

                # Wait for specified number of laps to be completed
                while True:
                    if max(self.ir["CarIdxLap"]) >= lap_at_yellow + 2:
                        # Send the pacelaps chat command
                        laps = int(
                            self.master.settings["settings"]["laps_under_sc"]
                        )
                        self.ir.chat_command(1)
                        time.sleep(0.05)
                        pyautogui.write(
                            f"!pacelaps {laps - 1}", interval=0.01
                        )
                        time.sleep(0.05)
                        pyautogui.press("enter")
                        break

                    # Wait 1 second before checking again
                    time.sleep(1)

            # Wait 1 second before checking again
            time.sleep(1)

        # All safety car events have been triggered
        self.master.add_message("All safety car events triggered.")
        self.ir.shutdown()

    def run(self):
        # Proxy variables for settings
        min_safety_cars = int(
            self.master.settings["settings"]["min_safety_cars"]
        )
        max_safety_cars = int(
            self.master.settings["settings"]["max_safety_cars"]
        )
        start_minute = float(
            self.master.settings["settings"]["start_minute"]
        )
        end_minute = float(
            self.master.settings["settings"]["end_minute"]
        )
        min_time_between = float(
            self.master.settings["settings"]["min_time_between"]
        )

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
        self.master.add_message("Generated safety car event times.")

        # Connect to iRacing
        self.ir = irsdk.IRSDK()

        # Attempt to connect and tell user if successful
        if self.ir.startup():
            self.master.add_message("Connected to iRacing.")
            self.master.add_message(
                "Be sure to click on the iRacing window to give it focus!"
            )
        else:
            self.master.add_message("Error connecting to iRacing.")
            return
        
        # Run the loop in a separate thread
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()