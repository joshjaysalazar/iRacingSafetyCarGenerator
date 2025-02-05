import logging
import random
import threading
import time
import traceback

import irsdk

from core import drivers
from core import iracing_window
from core import mock_window

from enum import Enum

logger = logging.getLogger(__name__)

def WindowFactory(arguments):
    if arguments.disable_window_interactions:
        return mock_window.MockWindow()
    return iracing_window.IRacingWindow()


class GeneratorState(Enum):
    STOPPED = 1
    RUNNING = 2

class Generator:
    """Generates safety car events in iRacing."""
    def __init__(self, arguments, master=None):
        """Initialize the generator object.

        Args:
            master: The parent window object
        """
        logger.info("Initializing safety car generator")
        self.master = master
        self.thread = None

        # Variables to track safety car events
        logger.debug("Initializing safety car variables")

        self.ir_window = WindowFactory(arguments)
        self.start_time = None
        self.total_sc_events = 0
        self.last_sc_time = None
        self.total_random_sc_events = 0
        self.lap_at_sc = None
        self.current_lap_under_sc = None

        # Create a shutdown event
        self.shutdown_event = threading.Event()
        self.skip_wait_for_green_event = threading.Event()

    def _is_shutting_down(self):
        """ Returns True if shutdown_event event was triggered
        
        Args:
            None
        """
        return self.shutdown_event.is_set()
    
    def _skip_waiting_for_green(self):
        """ Returns True if skip_wait_for_green_event event was triggered
        
        Args:
            None
        """
        return self.skip_wait_for_green_event.is_set()

    def _check_random(self):
        """Check to see if a random safety car event should be triggered.
        
        Args:
            None
        """
        logger.debug("Checking random safety car event")

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
        logger.debug("Checking stopped car safety car event")

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
        logger.debug("Checking off track safety car event")

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
        logger.debug(f"Getting driver number for ID {id}")

        # Get the driver number from the iRacing SDK
        for driver in self.ir["DriverInfo"]["Drivers"]:
            if driver["CarIdx"] == id:
                return driver["CarNumber"]
                
        # If the driver number wasn't found, return None
        return None
    
    def _get_current_lap_under_sc(self):
        """Get the current lap under safety car for each car on the track.
        
        Args:
            None
        """
        logger.debug("Getting current laps under safety car")

        # Zip the CarIdxLap and CarIdxOnPitRoad arrays together
        current_lap_numbers = zip(
            self.ir["CarIdxLap"],
            self.ir["CarIdxOnPitRoad"]
        )

        # If pit road value is True, remove it, keeping only laps
        current_lap_numbers = [
            car[0] for car in current_lap_numbers if car[1] == False
        ]

        # Find the highest value in the list
        self.current_lap_under_sc = max(current_lap_numbers)

    def _loop(self):
        """Main loop for the safety car generator.
        
        Args:
            None
        """
        logger.debug("Starting safety car loop")

        # Get relevant settings from the settings file
        start_minute = float(self.master.settings["settings"]["start_minute"])
        end_minute = float(self.master.settings["settings"]["end_minute"])
        max_events = int(self.master.settings["settings"]["max_safety_cars"])
        min_time = float(self.master.settings["settings"]["min_time_between"])

        # Adjust start minute if < 3s to avoid triggering on standing start
        if start_minute < 0.05:
            logger.debug("Adjusting start minute to 0.05")
            start_minute = 0.05

        # Wait for the green flag
        self._wait_for_green_flag()

        # Loop until the max number of safety car events is reached
        while self.total_sc_events < max_events:
            # Update the drivers object
            self.drivers.update()

            logger.debug("Checking time")

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

        Returns:
            True if pace laps are done, False otherwise
        """
        # Get relevant settings from the settings file
        laps_under_sc = int(
            self.master.settings["settings"]["laps_under_sc"]
        )

        # If laps under safety car is 0, return
        logger.debug("Laps under safety car set too low, skipping command")
        if laps_under_sc < 2:
            return True
        
        # If the max value is 2 laps greater than the lap at yellow
        if self.current_lap_under_sc >= self.lap_at_sc + 2:
            # Get all cars on lead lap at check
            lead_lap = []
            for i, lap in enumerate(self.ir["CarIdxLap"]):
                if lap >= self.current_lap_under_sc:
                    lead_lap.append(i)

            # Before next check, wait 1s to make sure leader is across line
            time.sleep(1)

            # Wait for max value in lap distance of the lead cars to be 50%
            logger.debug("Checking if lead car is halfway around track")
            lead_dist = [
                self.ir["CarIdxLapDistPct"][car] for car in lead_lap
            ]

            # If any lead car is at 50%, send the pacelaps command
            if max(lead_dist) >= 0.5:
                logger.info("Sending pacelaps command")
                self.ir_window.focus()
                self.ir.chat_command(1)
                time.sleep(0.5)
                self.ir_window.send_message(f"!p {laps_under_sc - 1}{{ENTER}}")

                # Return True when pace laps are done
                return True
        
        # If we haven't reached the conditions to send command, return False
        return False

    def _send_wave_arounds(self):
        """Send the wave around chat commands to iRacing.

        Args:
            None

        Returns:
            True if wave arounds are done, False otherwise
        """
        # Get relevant settings from the settings file
        wave_arounds = self.master.settings["settings"]["wave_arounds"]
        laps_before = int(
            self.master.settings["settings"]["laps_before_wave_arounds"]
        )

        # If immediate waveby is disabled, return True (no wave arounds)
        if wave_arounds == "0":
            logger.debug("Wave arounds disabled, skipping wave arounds")
            return True
        
        # If not time for wave arounds, return False
        wave_lap = self.lap_at_sc + laps_before + 1
        if self.current_lap_under_sc < wave_lap:
            logger.debug("Haven't reached wave lap, skipping wave arounds")
            return False
        
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
                logger.info(f"Sending wave around command for car {car}")
                self.ir_window.focus()
                self.ir.chat_command(1)
                time.sleep(0.5)
                self.ir_window.send_message(f"!w {car}{{ENTER}}")

        # Return True when wave arounds are done
        return True

    def _start_safety_car(self, message=""):
        """Send a yellow flag to iRacing.

        Args:
            message: The message to send with the yellow flag command
        """
        logger.info("Deploying safety car")

        # Send yellow flag chat command
        self.ir_window.focus()
        self.ir.chat_command(1)
        time.sleep(0.5)
        self.ir_window.send_message(f"!y {message}{{ENTER}}")

        # Set the UI message
        self.master.set_message(
            "Connected to iRacing\nSafety car deployed."
        )

        # Increment the total safety car events
        self.total_sc_events += 1

        # Set the last safety car time
        self.last_sc_time = time.time()

        # Set the lap at yellow flag
        self.lap_at_sc = max(self.ir["CarIdxLap"])

        # Manage wave arounds and pace laps
        waves_done = False
        pace_done = False
        while not waves_done or not pace_done:
            # Get the current lap behind safety car
            self._get_current_lap_under_sc()

            # If wave arounds aren't done, send the wave arounds
            if not waves_done:
                waves_done = self._send_wave_arounds()

            # If pace laps aren't done, send the pace laps
            if not pace_done:
                pace_done = self._send_pacelaps()

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                break

            # Wait 1 second before checking again
            time.sleep(1)

        # Wait for the green flag to be displayed
        self._wait_for_green_flag(require_race_session=False)

    def _wait_for_green_flag(self, require_race_session=True):
        """Wait for the green flag to be displayed.

        Args:
            None
        """
        logger.info("Waiting for green flag")

        # If required, wait for the session to be a race session
        if require_race_session:
            logger.info("Waiting for race session")

            # Get the list of sessions
            session_list = self.ir["SessionInfo"]["Sessions"]

            # Create a dict of session names by index
            sessions = {}
            for i, session in enumerate(session_list):
                sessions[i] = session["SessionName"]

            # Loop until in a race session
            while True:
                # Get the current session index
                current_idx = self.ir["SessionNum"]

                # Break the loop if we are shutting down the thread or skipping the wait
                if self._is_shutting_down() or self._skip_waiting_for_green():
                    logger.debug("Skipping wait for green because of a threading event")
                    break

                # If the current session is PRACTICE, QUALIFY, or WARMUP
                if sessions[current_idx] in ["PRACTICE", "QUALIFY", "WARMUP"]:
                    # Add message to text box
                    self.master.set_message(
                        "Connected to iRacing\nWaiting for race session..."
                    )

                    # Wait 1 second before checking again
                    time.sleep(1)
                
                # If the current session is anything else, break the loop
                else:
                    break


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

            # Break the loop if we are shutting down the thread or skipping the wait
            if self._is_shutting_down() or self._skip_waiting_for_green():
                logger.debug("Skipping wait for green because of a threading event")
                if self.start_time is None:
                    self.start_time = time.time()

                # Set the UI message
                self.master.set_message(
                    "Connected to iRacing\nGenerating safety cars..."
                )
                break

            # Wait 1 second before checking again
            time.sleep(1)

    def generator_thread_excepthook(self, args):
        logger.critical("Uncaught exception:", exc_info=args)

    def run(self):
        """Run the safety car generator.

        Args:
            None
        """
        logger.info("Connecting to iRacing")
        
        # Create the iRacing SDK object
        self.ir = irsdk.IRSDK()

        # Attempt to connect and tell user if successful
        if self.ir.startup():
            # Get reference to simulator window if successfulir
            self.ir_window.connect()
            self.master.set_message("Connected to iRacing\n")
        else:
            self.master.set_message("Error connecting to iRacing\n")
            return False
    
        # Create the Drivers object
        self.drivers = drivers.Drivers(self)
        
        threading.excepthook = self.generator_thread_excepthook

        # Run the loop in a separate thread
        if self.thread == None or not self.thread.is_alive():
            logger.info("Starting the loop thread")
            self.thread = threading.Thread(target=self._loop)
            self.thread.start()
            return True
        else:
            logger.warning("Not starting the loop thread because it is still alive")
            return False

    def stop(self):
        logger.info("Triggering shutdown event to stop generator")
        self.shutdown_event.set()