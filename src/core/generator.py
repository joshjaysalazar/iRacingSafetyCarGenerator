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
        self.info("Initializing safety car generator")
        self.master = master

        # Variables to track safety car events
        logging.debug("Initializing safety car variables")
        self.ir_window = None
        self.start_time = None
        self.total_sc_events = 0
        self.last_sc_time = None
        self.total_random_sc_events = 0

        # Create a shutdown event
        self.shutdown_event = threading.Event()

    def _is_shutting_down(self):
        """ Returns True if shutdown_event event was triggered
        
        Args:
            None
        """
        return self.shutdown_event.is_set()

    def _check_random(self):
        """Check to see if a random safety car event should be triggered.
        
        Args:
            None
        """
        logging.debug("Checking random safety car event")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["random"]
        chance = float(self.master.settings["settings"]["random_prob"])
        max_occ = int(self.master.settings["settings"]["random_max_occ"])
        start_minute = float(self.master.settings["settings"]["start_minute"])
        end_minute = float(self.master.settings["settings"]["end_minute"])
        message = self.master.settings["settings"]["random_message"]

        # If random events are disabled, return
        if enabled == "0":
            return

        # If the random chance is 0, return
        if chance == 0:
            return
        
        # If the max occurrences is reached, return
        if self.total_random_sc_events >= max_occ:
            return

        # Generate a random number between 0 and 1
        rng = random.random()

        # Calculate the chance of triggering a safety car event this check
        len_of_window = (end_minute - start_minute) * 60
        chance = 1 - ((1 - chance) ** (1 / len_of_window))

        # If the random number is less than or equal to the chance, trigger
        if rng <= chance:
            self.total_random_sc_events += 1
            self._start_safety_car(message) 

    def _check_stopped(self):
        """Check to see if a stopped car safety car event should be triggered.
        
        Args:
            None
        """
        logging.debug("Checking stopped car safety car event")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["stopped"]
        threshold = float(self.master.settings["settings"]["stopped_min"])
        message = self.master.settings["settings"]["stopped_message"]

        # If stopped car events are disabled, return
        if enabled == "0":
            return

        # Get the indices of the stopped cars
        stopped_cars = []
        for i in range(len(self.drivers.current_drivers)):
            current_comp = self.drivers.current_drivers[i]["laps_completed"]
            current_dist = self.drivers.current_drivers[i]["lap_distance"]
            prev_comp = self.drivers.previous_drivers[i]["laps_completed"]
            prev_dist = self.drivers.previous_drivers[i]["lap_distance"]
            current_total = current_comp + current_dist
            prev_total = prev_comp + prev_dist
            if current_total <= prev_total:
                stopped_cars.append(i)

        # If length of stopped cars is entire field, clear list (lag fix)
        if len(stopped_cars) >= len(self.drivers.current_drivers) - 1:
            stopped_cars = []

        # For each stopped car, check if they're in pits, remove if so
        cars_to_remove = []
        for car in stopped_cars:
            if self.drivers.current_drivers[car]["track_loc"] == 1:
                cars_to_remove.append(car)
            if self.drivers.current_drivers[car]["track_loc"] == 2:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)

        # For each, check if not in world, remove if so
        cars_to_remove = []
        for car in stopped_cars:
            if self.drivers.current_drivers[car]["track_loc"] == -1:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)

        # For each, check if lap distance < 0, remove if so
        cars_to_remove = []
        for car in stopped_cars:
            if self.drivers.current_drivers[car]["lap_distance"] < 0:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            stopped_cars.remove(car)

        # Trigger the safety car event if threshold is met
        if len(stopped_cars) >= threshold:
            self._start_safety_car(message)

    def _check_off_track(self):
        """Check to see if an off track safety car event should be triggered.
        
        Args:
            None
        """
        logging.debug("Checking off track safety car event")

        # Get relevant settings from the settings file
        enabled = self.master.settings["settings"]["off"]
        threshold = float(self.master.settings["settings"]["off_min"])
        message = self.master.settings["settings"]["off_message"]

        # If off track events are disabled, return
        if enabled == "0":
            return

        # Get the indices of the off track cars
        off_track_cars = []
        for i in range(len(self.drivers.current_drivers)):
            if self.drivers.current_drivers[i]["track_loc"] == 0:
                off_track_cars.append(i)

        # For each off track car, check if lap distance < 0, remove if so
        cars_to_remove = []
        for car in off_track_cars:
            if self.drivers.current_drivers[car]["lap_distance"] < 0:
                cars_to_remove.append(car)
        for car in cars_to_remove:
            off_track_cars.remove(car)

        # Trigger the safety car event if threshold is met
        if len(off_track_cars) >= threshold:
            self._start_safety_car(message)

    def _get_driver_number(self, id):
        """Get the driver number from the iRacing SDK.

        Args:
            id: The iRacing driver ID

        Returns:
            The driver number, or None if not found
        """
        logging.debug(f"Getting driver number for ID {id}")

        # Get the driver number from the iRacing SDK
        for driver in self.ir["DriverInfo"]["Drivers"]:
            if driver["CarIdx"] == id:
                return driver["CarNumber"]
                
        # If the driver number wasn't found, return None
        return None
    
    def _loop(self):
        """Main loop for the safety car generator.
        
        Args:
            None
        """
        logging.debug("Starting safety car loop")

        # Get relevant settings from the settings file
        start_minute = float(self.master.settings["settings"]["start_minute"])
        end_minute = float(self.master.settings["settings"]["end_minute"])
        max_events = int(self.master.settings["settings"]["max_safety_cars"])
        min_time = float(self.master.settings["settings"]["min_time_between"])

        # Adjust start minute if < 3s to avoid triggering on standing start
        if start_minute < 0.05:
            logging.debug("Adjusting start minute to 0.05")
            start_minute = 0.05

        # Wait for the green flag
        self._wait_for_green_flag()

        # Loop until the max number of safety car events is reached
        while self.total_sc_events < max_events:
            # Update the drivers object
            self.drivers.update()

            logging.debug("Checking time")

            # If it hasn't reached the start minute, wait
            if time.time() - self.start_time < start_minute * 60:
                time.sleep(1)
                continue

            # If it has reached the end minute, break the loop
            if time.time() - self.start_time > end_minute * 60:
                break

            # If it hasn't been long enough since the last event, wait
            if self.last_sc_time is not None:
                if time.time() - self.last_sc_time < min_time * 60:
                    time.sleep(1)
                    continue

            # If all checks are passed, check for events
            self._check_random()
            self._check_stopped()
            self._check_off_track()

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                break

            # Wait 1 second before checking again
            time.sleep(1)

        # Shutdown the iRacing SDK after all safety car events are complete
        self.ir.shutdown()

    def _send_pacelaps(self):
        """Send a pacelaps chat command to iRacing.
        
        Args:
            None
        """
        logging.info("Sending pacelaps command")

        # Get relevant settings from the settings file
        laps_under_sc = int(
            self.master.settings["settings"]["laps_under_sc"]
        )

        # Get the max value from all cars' lap started count
        lap_at_yellow = max(self.ir["CarIdxLap"])

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
            if max(laps_started) >= lap_at_yellow + 2:
                # Only send if laps is greater than 1
                if laps_under_sc > 1:
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
                break
            
            # Wait 1 second before checking again
            time.sleep(1)

    def _send_wave_arounds(self):
        """Send the wave around chat commands to iRacing.

        Args:
            None
        """
        logging.info("Sending wave around commands")

        # Get relevant settings from the settings file
        wave_around = self.master.settings["settings"]["imm_wave_around"]

        # If immediate waveby is disabled, return
        if wave_around == "0":
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

        # Zip together number of laps started, position on track, and class
        drivers = zip(
            self.ir["CarIdxLap"],
            self.ir["CarIdxLapDistPct"],
            self.ir["CarIdxClass"]
        )
        drivers = tuple(drivers)

        # Get the highest started lap for each class
        highest_lap = {}
        for class_id in class_ids:
            # Get the highest lap and track position for the current class
            max_lap = (0, 0)
            for driver in drivers:
                if driver[2] == class_id:
                    if driver[0] > max_lap[0]:
                        max_lap = (driver[0], driver[1])

            # Add the highest lap to the dictionary
            highest_lap[class_id] = max_lap

        # Create an empty list of cars to wave around
        cars_to_wave = []

        # For each driver, check if they're eligible for a wave around
        for i, driver in enumerate(drivers):
            # Get the class ID for the current driver
            driver_class = driver[2]

            # If the class ID isn't in the class IDs list, skip the driver
            if driver_class not in class_ids:
                continue

            driver_number = None

            # If driver started 2 or fewer laps than class leader, wave them
            lap_target = highest_lap[driver_class][0] - 2
            if driver[0] <= lap_target:
                driver_number = self._get_driver_number(i)

            # If they started 1 fewer laps & are behind on track, wave them
            lap_target = highest_lap[driver_class][0] - 1
            track_pos_target = highest_lap[driver_class][1]
            if driver[0] == lap_target and driver[1] < track_pos_target:
                driver_number = self._get_driver_number(i)

            # If the driver number is not None, add it to the list
            if driver_number is not None:
                cars_to_wave.append(driver_number)

        # Send the wave chat command for each car
        if len(cars_to_wave) > 0:
            for car in cars_to_wave:
                logging.info(f"Sending wave around command for car {car}")
                self.ir_window.set_focus()
                self.ir.chat_command(1)
                time.sleep(0.5)
                self.ir_window.type_keys(
                    f"!w {car}{{ENTER}}", with_spaces=True
                )

    def _start_safety_car(self, message=""):
        """Send a yellow flag to iRacing.

        Args:
            message: The message to send with the yellow flag command
        """
        logging.info("Deploying safety car")

        # Set the UI message
        self.master.set_message(
            "Connected to iRacing\nSafety car deployed."
        )

        # Increment the total safety car events
        self.total_sc_events += 1

        # Set the last safety car time
        self.last_sc_time = time.time()

        # Send yellow flag chat command
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
        logging.info("Waiting for green flag")

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

                # Set the UI message
                self.master.set_message(
                    "Connected to iRacing\nGenerating safety cars..."
                )

                # Break the loop
                break

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                break

            # Wait 1 second before checking again
            time.sleep(1)

    def run(self):
        """Run the safety car generator.

        Args:
            None
        """
        logging.info("Connecting to iRacing")
        
        # Create the iRacing SDK object
        self.ir = irsdk.IRSDK()

        # Attempt to connect and tell user if successful
        if self.ir.startup():
            # Get reference to simulator window if successful
            self.ir_window = Application().connect(
                title="iRacing.com Simulator"
            ).top_window()
            
            self.master.set_message("Connected to iRacing\n")
        else:
            self.master.set_message("Error connecting to iRacing\n")
            return
    
        # Create the Drivers object
        self.drivers = drivers.Drivers(self)
        
        # Run the loop in a separate thread
        self.thread = threading.Thread(target=self._loop)
        self.thread.start()