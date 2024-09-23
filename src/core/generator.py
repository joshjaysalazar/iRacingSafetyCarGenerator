import logging
import random
import threading
import time

import irsdk
from pywinauto.application import Application

from core import drivers


class Generator:
    """Generates safety car events in iRacing."""
    def __init__(self, master=None):
        """Initialize the generator object.

        Args:
            master: The parent window object
        """
        self.master = master
        logging.info("Initializing Generator class.")

        # Variables to track safety car events
        self.ir_window = None
        self.start_time = None
        self.total_sc_events = 0
        self.last_sc_time = None
        self.total_random_sc_events = 0

        self.shutdown_event = threading.Event()
        logging.debug("Generator variables initialized.")

    def _is_shutting_down(self):
        """Returns True if shutdown_event event was triggered

        Args:
            None
        """
        return self.shutdown_event.is_set()

    def _check_random(self):
        """Check to see if a random safety car event should be triggered.

        Args:
            None
        """
        logging.debug("Checking for random safety car event.")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["random"]
        chance = float(self.master.settings["settings"]["random_prob"])
        max_occ = int(self.master.settings["settings"]["random_max_occ"])
        start_minute = float(self.master.settings["settings"]["start_minute"])
        end_minute = float(self.master.settings["settings"]["end_minute"])
        message = self.master.settings["settings"]["random_message"]

        logging.debug(f"Random SC settings: enabled={enabled}, chance={chance}, max_occ={max_occ}, start_minute={start_minute}, end_minute={end_minute}, message='{message}'")

        # If random events are disabled, return
        if enabled == "0":
            logging.debug("Random safety car events are disabled.")
            return

        # If the random chance is 0, return
        if chance == 0:
            logging.debug("Random chance is 0; skipping random safety car event.")
            return

        # If the max occurrences is reached, return
        if self.total_random_sc_events >= max_occ:
            logging.debug("Maximum random safety car events reached.")
            return

        # Generate a random number between 0 and 1
        rng = random.random()
        logging.debug(f"Random number generated: {rng}")

        # Calculate the chance of triggering a safety car event this check
        len_of_window = (end_minute - start_minute) * 60
        chance_per_second = 1 - ((1 - chance) ** (1 / len_of_window))
        logging.debug(f"Chance per second: {chance_per_second}")

        # If the random number is less than or equal to the chance, trigger
        if rng <= chance_per_second:
            logging.info("Random safety car event triggered.")
            self.total_random_sc_events += 1
            self._start_safety_car(message)
        else:
            logging.debug("Random safety car event not triggered this time.")

    def _check_stopped(self):
        """Check to see if a stopped car safety car event should be triggered.

        Args:
            None
        """
        logging.debug("Checking for stopped cars.")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["stopped"]
        threshold = float(self.master.settings["settings"]["stopped_min"])
        message = self.master.settings["settings"]["stopped_message"]

        logging.debug(f"Stopped cars settings: enabled={enabled}, threshold={threshold}, message='{message}'")

        # If stopped car events are disabled, return
        if enabled == "0":
            logging.debug("Stopped car events are disabled.")
            return

        # Get the indices of the stopped cars
        stopped_cars = []
        for i in range(len(self.drivers.current_drivers)):
            current_comp = self.drivers.current_drivers[i]["laps_completed"]
            current_dist = self.drivers.current_drivers[i]["lap_distance"]
            previous_comp = self.drivers.previous_drivers[i]["laps_completed"]
            previous_dist = self.drivers.previous_drivers[i]["lap_distance"]
            current_total = current_comp + current_dist
            previous_total = previous_comp + previous_dist
            if current_total <= previous_total:
                stopped_cars.append(i)

        logging.debug(f"Initial stopped cars detected: {stopped_cars}")

        # If length of stopped cars is entire field, clear list (lag spike fix)
        if len(stopped_cars) >= len(self.drivers.current_drivers) - 1:
            logging.debug("Detected lag spike, clearing stopped cars list.")
            stopped_cars = []

        # Remove cars in pits or pit exit
        cars_to_remove = []
        for car in stopped_cars:
            track_loc = self.drivers.current_drivers[car]["track_loc"]
            if track_loc == 1 or track_loc == 2:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)
        logging.debug(f"Stopped cars after removing those in pits: {stopped_cars}")

        # Remove cars not in world
        cars_to_remove = []
        for car in stopped_cars:
            if self.drivers.current_drivers[car]["track_loc"] == -1:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)
        logging.debug(f"Stopped cars after removing those not in world: {stopped_cars}")

        # Remove cars with negative lap distance
        cars_to_remove = []
        for car in stopped_cars:
            if self.drivers.current_drivers[car]["lap_distance"] < 0:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)
        logging.debug(f"Stopped cars after removing those with negative lap distance: {stopped_cars}")

        # Trigger the safety car event if threshold is met
        if len(stopped_cars) >= threshold:
            logging.info(f"Threshold met for stopped cars: {len(stopped_cars)} >= {threshold}")
            self._start_safety_car(message)
        else:
            logging.debug(f"Threshold not met for stopped cars: {len(stopped_cars)} < {threshold}")

    def _check_off_track(self):
        """Check to see if an off track safety car event should be triggered.

        Args:
            None
        """
        logging.debug("Checking for off-track cars.")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["off"]
        threshold = float(self.master.settings["settings"]["off_min"])
        message = self.master.settings["settings"]["off_message"]

        logging.debug(f"Off-track settings: enabled={enabled}, threshold={threshold}, message='{message}'")

        # If off track events are disabled, return
        if enabled == "0":
            logging.debug("Off-track events are disabled.")
            return

        # Get the indices of the off track cars
        off_track_cars = []
        for i in range(len(self.drivers.current_drivers)):
            if self.drivers.current_drivers[i]["track_loc"] == 0:
                off_track_cars.append(i)

        logging.debug(f"Initial off-track cars detected: {off_track_cars}")

        # Remove cars with negative lap distance
        cars_to_remove = []
        for car in off_track_cars:
            if self.drivers.current_drivers[car]["lap_distance"] < 0:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            off_track_cars.remove(car)
        logging.debug(f"Off-track cars after removing those with negative lap distance: {off_track_cars}")

        # Trigger the safety car event if threshold is met
        if len(off_track_cars) >= threshold:
            logging.info(f"Threshold met for off-track cars: {len(off_track_cars)} >= {threshold}")
            self._start_safety_car(message)
        else:
            logging.debug(f"Threshold not met for off-track cars: {len(off_track_cars)} < {threshold}")

    def _get_driver_number(self, id):
        """Get the driver number from the iRacing SDK.

        Args:
            id: The iRacing driver ID

        Returns:
            The driver number, or None if not found
        """
        logging.debug(f"Getting driver number for CarIdx {id}")
        # Get the driver number from the iRacing SDK
        for driver in self.ir["DriverInfo"]["Drivers"]:
            if driver["CarIdx"] == id:
                logging.debug(f"Found driver number: {driver['CarNumber']} for CarIdx {id}")
                return driver["CarNumber"]

        # If the driver number wasn't found, return None
        logging.warning(f"Driver number not found for CarIdx {id}")
        return None

    def _loop(self):
        """Main loop for the safety car generator.

        Args:
            None
        """
        logging.info("Starting main loop for safety car generator.")

        # Get relevant settings from the settings file
        start_minute = float(self.master.settings["settings"]["start_minute"])
        end_minute = float(self.master.settings["settings"]["end_minute"])
        max_events = int(self.master.settings["settings"]["max_safety_cars"])
        min_time = float(self.master.settings["settings"]["min_time_between"])

        logging.debug(f"Loop settings: start_minute={start_minute}, end_minute={end_minute}, max_events={max_events}, min_time={min_time}")

        # Adjust start minute if < 3s to avoid triggering on standing start
        if start_minute < 0.05:
            logging.debug("Adjusting start_minute to 0.05 to avoid triggering on standing start.")
            start_minute = 0.05

        # Wait for the green flag
        self._wait_for_green_flag()

        # Loop until the max number of safety car events is reached
        while self.total_sc_events < max_events:
            # Update the drivers object
            self.drivers.update()
            logging.debug("Drivers updated.")

            # If it hasn't reached the start minute, wait
            elapsed_time = (time.time() - self.start_time) / 60  # in minutes
            if elapsed_time < start_minute:
                logging.debug(f"Waiting for start minute: elapsed_time={elapsed_time}, start_minute={start_minute}")
                time.sleep(1)
                continue

            # If it has reached the end minute, break the loop
            if elapsed_time > end_minute:
                logging.info("End minute reached. Exiting main loop.")
                break

            # If it hasn't been long enough since the last event, wait
            if self.last_sc_time is not None:
                time_since_last_sc = (time.time() - self.last_sc_time) / 60  # in minutes
                if time_since_last_sc < min_time:
                    logging.debug(f"Waiting for min_time_between: time_since_last_sc={time_since_last_sc}, min_time={min_time}")
                    time.sleep(1)
                    continue

            # If all checks are passed, check for events
            self._check_random()
            self._check_stopped()
            self._check_off_track()

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                logging.info("Shutdown event detected. Exiting main loop.")
                break

            # Wait 1 second before checking again
            time.sleep(1)

        # Shutdown the iRacing SDK after all safety car events are complete
        logging.info("Safety car events complete. Shutting down iRacing SDK.")
        self.ir.shutdown()

    def _send_pacelaps(self):
        """Send a pacelaps chat command to iRacing.

        Args:
            None
        """
        logging.info("Sending pacelaps command.")

        # Get relevant settings from the settings file
        laps_under_sc = int(
            self.master.settings["settings"]["laps_under_sc"]
        )
        logging.debug(f"Laps under safety car: {laps_under_sc}")

        # Get the max value from all cars' lap started count
        lap_at_yellow = max(self.ir["CarIdxLap"])
        logging.debug(f"Lap at yellow: {lap_at_yellow}")

        # Wait for specified number of laps to be completed
        while True:
            # Zip the CarIdxLap and CarIdxOnPitRoad arrays together
            laps_started = zip(
                self.ir["CarIdxLap"],
                self.ir["CarIdxOnPitRoad"]
            )

            # If pit road value is True, remove it, keeping only laps
            laps_started = [
                car[0] for car in laps_started if car[1] == False
            ]

            # If the max value is 2 laps greater than the lap at yellow
            if max(laps_started, default=0) >= lap_at_yellow + 2:
                logging.debug("Reached target lap for pacelaps command.")
                # Only send if laps is greater than 1
                if laps_under_sc > 1:
                    logging.info("Sending pacelaps command to iRacing.")
                    self.ir_window.set_focus()
                    self.ir.chat_command(1)
                    time.sleep(0.5)
                    self.ir_window.type_keys(
                        f"!p {laps_under_sc - 1}{{ENTER}}",
                        with_spaces=True
                    )
                # Break the loop
                break

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                logging.info("Shutdown event detected. Exiting pacelaps loop.")
                break

            # Wait 1 second before checking again
            time.sleep(1)

    def _send_wave_arounds(self):
        """Send the wave around chat commands to iRacing.

        Args:
            None
        """
        logging.info("Sending wave around commands.")

        # Get relevant settings from the settings file
        wave_around = self.master.settings["settings"]["imm_wave_around"]
        logging.debug(f"Immediate wave around setting: {wave_around}")

        # If immediate waveby is disabled, return
        if wave_around == "0":
            logging.debug("Immediate wave arounds are disabled.")
            return

        # Get all class IDs (except safety car)
        class_ids = []
        for driver in self.ir["DriverInfo"]["Drivers"]:
            # Skip the safety car
            if driver["CarIsPaceCar"] == 1:
                continue
            # If the class ID isn't already in the list, add it
            else:
                if driver["CarClassID"] not in class_ids:
                    class_ids.append(driver["CarClassID"])
        logging.debug(f"Class IDs: {class_ids}")

        # Zip together the number of laps started, position on track, and class
        drivers_data = list(zip(
            self.ir["CarIdxLap"],
            self.ir["CarIdxLapDistPct"],
            self.ir["CarIdxClass"]
        ))

        # Get the highest started lap for each class
        highest_lap = {}
        for class_id in class_ids:
            # Get the highest lap and track position for the current class
            max_lap = (0, 0)
            for idx, driver in enumerate(drivers_data):
                if driver[2] == class_id:
                    if driver[0] > max_lap[0]:
                        max_lap = (driver[0], driver[1])
            # Add the highest lap to the dictionary
            highest_lap[class_id] = max_lap
        logging.debug(f"Highest lap per class: {highest_lap}")

        # Create an empty list of cars to wave around
        cars_to_wave = []

        # For each driver, check if they're eligible for a wave around
        for i, driver in enumerate(drivers_data):
            # Get the class ID for the current driver
            driver_class = driver[2]

            # If the class ID isn't in the class IDs list, skip the driver
            if driver_class not in class_ids:
                continue

            driver_number = None

            # If driver has started 2 or fewer laps than class leader, wave them
            lap_target = highest_lap[driver_class][0] - 2
            if driver[0] <= lap_target:
                driver_number = self._get_driver_number(i)

            # If they've started 1 fewer laps and are behind on track, wave them
            lap_target = highest_lap[driver_class][0] - 1
            track_pos_target = highest_lap[driver_class][1]
            if driver[0] == lap_target and driver[1] < track_pos_target:
                driver_number = self._get_driver_number(i)

            # If the driver number is not None, add it to the list
            if driver_number is not None:
                cars_to_wave.append(driver_number)

        logging.debug(f"Cars to wave around: {cars_to_wave}")

        # Send the wave chat command for each car
        if len(cars_to_wave) > 0:
            logging.info(f"Sending wave around commands for cars: {cars_to_wave}")
            for car in cars_to_wave:
                self.ir_window.set_focus()
                self.ir.chat_command(1)
                time.sleep(0.5)
                self.ir_window.type_keys(f"!w {car}{{ENTER}}", with_spaces=True)
        else:
            logging.debug("No cars to wave around.")

    def _start_safety_car(self, message=""):
        """Send a yellow flag to iRacing.

        Args:
            message: The message to send with the yellow flag command
        """
        logging.info("Starting safety car procedure.")

        # Set the UI message
        self.master.set_message(
            "Connected to iRacing\nSafety car deployed."
        )

        # Increment the total safety car events
        self.total_sc_events += 1
        logging.debug(f"Total safety car events: {self.total_sc_events}")

        # Set the last safety car time
        self.last_sc_time = time.time()

        # Send yellow flag chat command
        logging.info("Sending yellow flag command to iRacing.")
        self.ir_window.set_focus()
        self.ir.chat_command(1)
        time.sleep(0.5)
        self.ir_window.type_keys(f"!y {message}{{ENTER}}", with_spaces=True)

        # Send the wave commands
        self._send_wave_arounds()

        # Send pacelaps command when the time is right
        self._send_pacelaps()

        # Wait for the green flag to be displayed
        self._wait_for_green_flag()

    def _wait_for_green_flag(self):
        """Wait for the green flag to be displayed.

        Args:
            None
        """
        logging.info("Waiting for green flag.")

        # Add message to text box
        self.master.set_message(
            "Connected to iRacing\nWaiting for green flag..."
        )

        # Loop until the green flag is displayed
        while True:
            # Check if the green flag is displayed
            if self.ir["SessionFlags"] & irsdk.Flags.green:
                # Set the start time if it hasn't been set yet
                if self.start_time is None:
                    self.start_time = time.time()
                    logging.info("Green flag detected. Start time set.")

                # Set the UI message
                self.master.set_message(
                    "Connected to iRacing\nGenerating safety cars..."
                )

                # Break the loop
                break

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                logging.info("Shutdown event detected. Exiting wait for green flag.")
                break

            # Wait 1 second before checking again
            time.sleep(1)

    def run(self):
        """Run the safety car generator.

        Args:
            None
        """
        logging.info("Running safety car generator.")

        # Connect to iRacing
        self.ir = irsdk.IRSDK()

        # Attempt to connect and tell user if successful
        if self.ir.startup():
            logging.info("Connected to iRacing SDK.")
            # Get reference to simulator window if successful
            self.ir_window = Application().connect(
                title="iRacing.com Simulator"
            ).top_window()
            logging.debug("Simulator window connected.")

            self.master.set_message("Connected to iRacing\n")
        else:
            logging.error("Error connecting to iRacing SDK.")
            self.master.set_message("Error connecting to iRacing\n")
            return

        # Create the Drivers object
        self.drivers = drivers.Drivers(self)
        logging.info("Drivers object created.")

        # Run the loop in a separate thread
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()
        logging.info("Main loop thread started.")