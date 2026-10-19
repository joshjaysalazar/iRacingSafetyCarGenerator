import logging
import queue
import threading
import time

import irsdk

from core import drivers
from core.detection.threshold_checker import ThresholdChecker, ThresholdCheckerSettings, DetectorEventTypes
from core.detection.detector import Detector, DetectorSettings
from core.interactions.interaction_factories import CommandSenderFactory
from core.preflight import run_preflight_checks
from core.procedures.wave_arounds import wave_around_type_from_selection, wave_arounds_factory
from core.procedures.class_split import get_split_class_commands

from codetiming import Timer
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

class GeneratorState(Enum):
    STOPPED = 1
    CONNECTING_TO_IRACING = 2
    CONNECTED = 3
    ERROR_CONNECTING = 4
    WAITING_FOR_RACE_SESSION = 5
    WAITING_FOR_GREEN = 6
    MONITORING_FOR_INCIDENTS = 7
    SAFETY_CAR_DEPLOYED = 8
    UNCAUGHT_EXCEPTION = 9

@dataclass(frozen=True)
class GeneratorSettings:
    """Settings used by the generator thread.

    A snapshot is taken when the generator starts, so settings saved in the UI during a
    race don't half-apply to a running safety car procedure.
    """
    detection_start_minute: float = 0.0
    detection_end_minute: float = 30.0
    max_safety_cars: int = 2
    min_time_between_safety_cars_minutes: float = 3.0
    laps_under_safety_car: int = 2
    wave_arounds_enabled: bool = True
    laps_before_wave_arounds: int = 0
    wave_around_rules_index: int = 0
    class_split_enabled: bool = False

    @staticmethod
    def from_settings(settings):
        return GeneratorSettings(
            detection_start_minute=settings.detection_start_minute,
            detection_end_minute=settings.detection_end_minute,
            max_safety_cars=settings.max_safety_cars,
            min_time_between_safety_cars_minutes=settings.min_time_between_safety_cars_minutes,
            laps_under_safety_car=settings.laps_under_safety_car,
            wave_arounds_enabled=settings.wave_arounds_enabled,
            laps_before_wave_arounds=settings.laps_before_wave_arounds,
            wave_around_rules_index=settings.wave_around_rules_index,
            class_split_enabled=settings.class_split_enabled,
        )

@dataclass(frozen=True)
class StateChanged:
    """UI event: the generator moved to a new state."""
    state: GeneratorState

@dataclass(frozen=True)
class ClassSplitConfirmationRequested:
    """UI event: the user has to confirm these class-split commands, answered via confirm_class_split()."""
    commands: list[str]

@dataclass(frozen=True)
class PreflightWarnings:
    """UI event: the iRacing SDK data broke some of our assumptions. Only a warning, the run continues."""
    warnings: list[str]

class Generator:
    """Generates safety car events in iRacing.

    Threading model: run() is called from the UI thread and only starts the generator
    thread. Connecting to iRacing, monitoring and the safety car procedures all happen on
    that thread, which is the only one using the iRacing SDK connection.

    The generator thread never calls Tkinter. It posts StateChanged, PreflightWarnings and
    ClassSplitConfirmationRequested events to `ui_events`, which the App processes on the
    main thread. The UI talks to the generator through stop(), throw_manual_safety_car(),
    skip_wait_for_green() and confirm_class_split(), which only set threading events.
    """
    def __init__(self, arguments):
        """Initialize the generator object.

        Args:
            arguments: Launch arguments, used to pick the (mock) command sender
        """
        logger.info("Initializing safety car generator")
        self.arguments = arguments
        self.thread = None

        # Events for the UI thread to process (see class docstring)
        self.ui_events = queue.Queue()
        self._state = GeneratorState.STOPPED

        # Per-run objects, created when the generator starts
        self.settings = GeneratorSettings()
        self.ir = None
        self.command_sender = None
        self.drivers = None
        self.detector = None
        self.threshold_checker = None

        # Variables to track safety car events
        logger.debug("Initializing safety car variables")
        self._init_state_variables()

        # Signals from the UI thread
        self.shutdown_event = threading.Event()
        self.throw_manual_sc_event = threading.Event()
        self.skip_wait_for_green_event = threading.Event()

        # Class split confirmation (cross-thread communication)
        self.confirm_class_split_event = threading.Event()
        self._class_split_confirmed = False

    @property
    def state(self) -> GeneratorState:
        """The current state of the generator."""
        return self._state

    def _set_state(self, state: GeneratorState):
        """Move to a new state and tell the UI about it.

        Args:
            state: The new state
        """
        logger.debug(f"Generator state changed to {state}")
        self._state = state
        self.ui_events.put(StateChanged(state))

    def _init_state_variables(self):
        """ (Re)set generator state variables, called whenever we start the generator

        Args:
            None
        """
        logger.debug(f"Initializing the state variables.")
        self.start_time = None
        self.total_sc_events = 0
        self.last_sc_time = None
        self.total_random_sc_events = 0
        self.lap_at_sc = None
        self.current_lap_under_sc = None

    def _is_shutting_down(self):
        """ Returns True if shutdown_event event was triggered

        Args:
            None
        """
        return self.shutdown_event.is_set()

    def _throw_manual_safety_car(self):
        """ Returns True if throw_manual_sc_event event was triggered

        Args:
            None
        """
        return self.throw_manual_sc_event.is_set()

    def _skip_waiting_for_green(self):
        """ Returns True if skip_wait_for_green_event event was triggered

        Args:
            None
        """
        return self.skip_wait_for_green_event.is_set()

    def _request_class_split_confirmation(self, commands: list[str]) -> bool:
        """Request confirmation from the UI before sending class-split EOL commands.

        Blocks the generator thread until the user confirms or cancels.
        Returns True if confirmed, False if cancelled or shutting down.
        """
        self.confirm_class_split_event.clear()
        self._class_split_confirmed = False

        # The UI thread shows the dialog and answers via confirm_class_split()
        self.ui_events.put(ClassSplitConfirmationRequested(commands))

        # Block until the user responds (check shutdown periodically)
        while not self.confirm_class_split_event.is_set():
            if self._is_shutting_down():
                return False
            self.confirm_class_split_event.wait(timeout=0.5)

        return self._class_split_confirmed

    def _check_manual_event(self):
        """Checks for the manual SC button to be pressed and starts the SC if so.

        Args:
            None

        Returns:
            True if a manual safety car was thrown, False otherwise
        """
        if not self._throw_manual_safety_car():
            return False

        # Clear before starting, so a press during this safety car doesn't queue another one
        self.throw_manual_sc_event.clear()
        self._start_safety_car()
        return True

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

    def _run(self, detector_settings: DetectorSettings, threshold_checker_settings: ThresholdCheckerSettings):
        """Body of the generator thread: connect to iRacing, run the loop and clean up.

        The final state is published last, after the iRacing connection is shut down, so the
        UI only offers to start again once this run has completely finished.

        Args:
            detector_settings: Snapshot of the detector settings for this run
            threshold_checker_settings: Snapshot of the threshold checker settings for this run
        """
        final_state = GeneratorState.STOPPED
        try:
            self._init_state_variables()

            # run() already published CONNECTING_TO_IRACING
            if not self._connect():
                final_state = GeneratorState.ERROR_CONNECTING
                return
            self._set_state(GeneratorState.CONNECTED)

            # Warn the user, without stopping, if iRacing changed how it reports data we rely on
            preflight_warnings = run_preflight_checks(self.ir)
            if preflight_warnings:
                self.ui_events.put(PreflightWarnings(preflight_warnings))

            # Create the Drivers object
            self.drivers = drivers.Drivers(self)

            # Create the detectors and the ThresholdChecker
            self.detector = Detector.build_detector(detector_settings, self.drivers)
            self.threshold_checker = ThresholdChecker(threshold_checker_settings)

            self._loop()

        except Exception:
            logger.exception("Generator thread threw an exception")
            final_state = GeneratorState.UNCAUGHT_EXCEPTION

        finally:
            # Clean up before publishing the final state, and always publish it so the UI
            # never keeps showing a running generator
            try:
                self._disconnect()
                self._log_loop_timer_stats()
            except Exception:
                logger.exception("Error while cleaning up the generator thread")

            logger.info(f"Generator thread finished with state {final_state}")
            self._set_state(final_state)

    def _connect(self):
        """Connect to the iRacing SDK and the iRacing window. Runs on the generator thread.

        Every run uses its own SDK instance, which only the generator thread starts and
        shuts down.

        Args:
            None

        Returns:
            True if connected, False otherwise
        """
        logger.info("Connecting to iRacing")
        self.ir = irsdk.IRSDK()
        if not self.ir.startup():
            logger.info("Could not connect to the iRacing SDK")
            return False

        try:
            # Connect the command sender to the iRacing application window
            self.command_sender = CommandSenderFactory(self.arguments, self.ir)
            self.command_sender.connect()
        except Exception:
            logger.exception("Could not connect to the iRacing window")
            return False

        return True

    def _disconnect(self):
        """Shut down this run's iRacing SDK connection. Runs on the generator thread.

        Args:
            None
        """
        if self.ir is not None:
            self.ir.shutdown()
            self.ir = None

    def _log_loop_timer_stats(self):
        """Log performance stats of the generator loop.

        Args:
            None
        """
        # The timer only exists once the loop has run at least once
        if "GeneratorLoopTimer" not in Timer.timers:
            return

        logger.debug(f"GeneratorLoopTimer (count): {Timer.timers.count("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (total): {Timer.timers.total("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (min): {Timer.timers.min("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (max): {Timer.timers.max("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (mean): {Timer.timers.mean("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (median): {Timer.timers.median("GeneratorLoopTimer")}")
        logger.debug(f"GeneratorLoopTimer (stdev): {Timer.timers.stdev("GeneratorLoopTimer")}")

    def _loop(self):
        """Main loop for the safety car generator.

        Args:
            None
        """
        logger.debug("Starting safety car loop")

        # Get relevant settings from this run's settings snapshot
        start_minute = self.settings.detection_start_minute
        end_minute = self.settings.detection_end_minute
        max_events = self.settings.max_safety_cars
        min_time = self.settings.min_time_between_safety_cars_minutes

        # Adjust start minute if < 3s to avoid triggering on standing start
        if start_minute < 0.05:
            logger.debug("Adjusting start minute to 0.05")
            start_minute = 0.05

        # Wait for the green flag
        self._wait_for_green_flag()

        # Loop until the max number of safety car events is reached
        while self.total_sc_events < max_events and not self._is_shutting_down():

            # Start the performance timer
            # We do this in a context manager to ensure it is stopped whatever exit point this loop reaches
            with Timer(name="GeneratorLoopTimer", text="{name}: {:.4f}s", logger=logger.debug):

                # Update the drivers object
                self.drivers.update()

                # A manual safety car is thrown right away, regardless of the eligibility window
                if self._check_manual_event():
                    continue

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

                # Use new detector system for threshold checking
                try:
                    detector_results = self.detector.detect()

                    # Clean up events outside the sliding window
                    self.threshold_checker.clean_up_events()

                    # Register events from detector results
                    for event_type in DetectorEventTypes:
                        detection_result = detector_results.get_events(event_type)
                        if detection_result:
                            self.threshold_checker.register_detection_result(detection_result)

                    if self.threshold_checker.threshold_met():
                        logger.info("Threshold met, starting safety car")
                        self._start_safety_car("Incident on track")

                except Exception as e:
                    logger.error(f"Detection system failed: {e}", exc_info=True)

                # Wait 1 second before checking again
                time.sleep(1)

    def _send_pacelaps(self):
        """Send a pacelaps chat command to iRacing.

        Args:
            None

        Returns:
            True if pace laps are done, False otherwise
        """
        # Get relevant settings from this run's settings snapshot
        laps_under_sc = int(
            self.settings.laps_under_safety_car
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
                self.command_sender.send_command(f"!p {laps_under_sc - 1}")

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
        # Get relevant settings from this run's settings snapshot
        wave_arounds = self.settings.wave_arounds_enabled
        laps_before = self.settings.laps_before_wave_arounds

        # If immediate waveby is disabled, return True (no wave arounds)
        if not wave_arounds:
            logger.debug("Wave arounds disabled, skipping wave arounds")
            return True

        # If not time for wave arounds, return False
        wave_lap = self.lap_at_sc + laps_before + 1
        if self.current_lap_under_sc < wave_lap:
            logger.debug("Haven't reached wave lap, skipping wave arounds")
            return False

        wave_around_type = wave_around_type_from_selection(self.settings.wave_around_rules_index)
        wave_around_func = wave_arounds_factory(wave_around_type)

        logger.info(f"Sending wave arounds using {wave_around_type.value}")

        # Get the commands for the wave arounds using our data models
        commands = wave_around_func(
            self.drivers.current_drivers,
            self.drivers.session_info["pace_car_idx"]
        )

        # Send the commands in order
        self.command_sender.send_commands(commands)

        # Return True when wave arounds are done
        return True

    def _split_classes(self):
        """Split the classes by sending EOL chat commands for the slower class.
            This functionality is experimental, manually triggered and limited to
            races with only two classes.

        Args:
            None
        """

        # Check if class splitting is enabled
        if not self.settings.class_split_enabled:
            logger.info("Class splits disabled, skipping")
            return True

        # Check if we are one to green
        laps_under_sc = max(self.settings.laps_under_safety_car, 3)

        logger.debug(
            f"Checking if we need to split classes: "
            f"current_lap_under_sc={self.current_lap_under_sc}, "
            f"lap_at_sc={self.lap_at_sc}, laps_under_sc={laps_under_sc}, "
            f"laps_elapsed_check={self.current_lap_under_sc - self.lap_at_sc < laps_under_sc}"
        )
        if self.current_lap_under_sc - self.lap_at_sc < laps_under_sc:
            # Wait longer
            return False

        # Now is the right time to send the commands
        logger.info("Determining if we need to split classes")

        # Get the commands
        commands = get_split_class_commands(
            self.drivers.current_drivers,
            self.drivers.session_info["pace_car_idx"]
        )

        if len(commands) == 0:
            logger.info("No class splitting needed")
            return True

        # Request confirmation from the user
        if not self._request_class_split_confirmation(commands):
            logger.info("Class split cancelled by user")
            return True

        # User confirmed — send the commands
        self.command_sender.send_commands(commands)

        logger.info("Done splitting classes")
        return True

    def _start_safety_car(self, message=""):
        """Send a yellow flag to iRacing.

        Args:
            message: The message to send with the yellow flag command
        """
        logger.info("Deploying safety car")

        # Send yellow flag chat command
        self.command_sender.send_command(f"!y {message}")

        # Move to SC deployed state
        self._set_state(GeneratorState.SAFETY_CAR_DEPLOYED)

        # Increment the total safety car events
        self.total_sc_events += 1

        # Set the last safety car time
        self.last_sc_time = time.time()

        # Set the lap at yellow flag
        self.lap_at_sc = max(self.ir["CarIdxLap"])

        # Manage wave arounds and pace laps
        logger.info("Waiting to do wave arounds and pace lap signal")
        waves_done = False
        pace_done = False
        while not waves_done or not pace_done:
            # Update driver data to ensure we have current positions, pit status, etc.
            self.drivers.update()

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

        # Manage splitting classes
        logger.info("Waiting to split the classes")
        while True:
            # Update the current lap behind safety car
            self._get_current_lap_under_sc()

            if self._split_classes():
                break

            # Break the loop if we are shutting down the thread
            if self._is_shutting_down():
                break

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

            # Progress state to waiting for race session
            self._set_state(GeneratorState.WAITING_FOR_RACE_SESSION)

            # Loop until in a race session
            while True:
                # Get the current session index
                current_idx = self.ir["SessionNum"]

                # Break the loop if we are shutting down the thread or skipping the wait
                if self._is_shutting_down() or self._skip_waiting_for_green():
                    logger.debug("Skip waiting for race session because of a threading event")
                    break

                # If the current session is PRACTICE, QUALIFY, or WARMUP
                if sessions[current_idx] in ["PRACTICE", "QUALIFY", "WARMUP"]:
                    # Wait 1 second before checking again
                    time.sleep(1)

                # If the current session is anything else, break the loop
                else:
                    break


        # Progress state to waiting for green
        self._set_state(GeneratorState.WAITING_FOR_GREEN)

        # Loop until the green flag is displayed
        while True:
            # Check if the green flag is displayed
            green_flag = self.ir["SessionFlags"] & irsdk.Flags.green

            # Check if race is already in progress (only for initial race start, not SC restart)
            # SessionState stays 'racing' during SC periods, so we only check this when
            # require_race_session=True to avoid false triggers during SC restart waits
            race_already_in_progress = require_race_session and \
                                       self.ir["SessionState"] == irsdk.SessionState.racing

            if green_flag or race_already_in_progress:
                if green_flag:
                    logger.info("Green flag detected")
                elif race_already_in_progress:
                    logger.info("Race already in progress - skipping green flag wait")

                self._start_monitoring()
                break

            # Break the loop if we are shutting down the thread or skipping the wait
            if self._is_shutting_down() or self._skip_waiting_for_green():
                logger.debug("Skipping wait for green because of a threading event")
                self._start_monitoring()
                break

            # Wait 1 second before checking again
            time.sleep(1)

    def _start_monitoring(self):
        """Move to monitoring for incidents once the wait for the green flag is over.

        Args:
            None
        """
        # Set the start time if it hasn't been set yet
        if self.start_time is None:
            self.start_time = time.time()
            self._notify_race_started(self.start_time)

        # Requests made while waiting (e.g. during a safety car) don't carry over: a manual
        # safety car press would otherwise throw another one right after the restart, and a
        # skip press would skip every later wait for green
        self.throw_manual_sc_event.clear()
        self.skip_wait_for_green_event.clear()

        # Progress to monitoring for SC state
        self._set_state(GeneratorState.MONITORING_FOR_INCIDENTS)

    def run(self, settings):
        """Start the generator thread.

        Connecting to iRacing happens on the generator thread, so this returns right away.
        Progress and failures are reported through state changes.

        Args:
            settings: The application settings; this run uses a snapshot of them

        Returns:
            True if the generator thread was started, False if the previous run is still active
        """
        if self.is_running():
            # A finished run publishes its final state just before its thread exits
            self.thread.join(timeout=1.0)
            if self.thread.is_alive():
                logger.warning("Not starting the generator thread because the previous one is still running")
                return False

        # Clear signals left over from a previous run
        self.shutdown_event.clear()
        self.throw_manual_sc_event.clear()
        self.skip_wait_for_green_event.clear()
        self.confirm_class_split_event.clear()

        # Snapshot the settings for this run
        self.settings = GeneratorSettings.from_settings(settings)
        detector_settings = DetectorSettings.from_settings(settings)
        threshold_checker_settings = ThresholdCheckerSettings.from_settings(settings)

        # Publish the new state before starting the thread, so a second click on the
        # button right away already sees a running generator
        self._set_state(GeneratorState.CONNECTING_TO_IRACING)

        logger.info("Starting the generator thread")
        self.thread = threading.Thread(
            target=self._run,
            args=(detector_settings, threshold_checker_settings),
            name="GeneratorThread",
        )
        self.thread.start()
        return True

    def is_running(self) -> bool:
        """Returns True while the generator thread is alive."""
        return self.thread is not None and self.thread.is_alive()

    def is_stopping(self) -> bool:
        """Returns True once stop() was called, until the next run() starts."""
        return self._is_shutting_down()

    def _notify_race_started(self, start_time: float):
        """Notify all race-aware components that the race has started."""
        logger.debug(f"Notifying components that race started at {start_time}")
        self.detector.race_started(start_time)
        self.threshold_checker.race_started(start_time)

    def stop(self):
        logger.info("Triggering shutdown event to stop generator")
        self.shutdown_event.set()

    def throw_manual_safety_car(self):
        logger.info("Setting manual SC threading flag")
        self.throw_manual_sc_event.set()

    def skip_wait_for_green(self):
        logger.info("Setting skip wait for green threading flag")
        self.skip_wait_for_green_event.set()

    def confirm_class_split(self, confirmed: bool):
        """Answer a ClassSplitConfirmationRequested event. Called from the UI thread.

        Args:
            confirmed: True if the user confirmed sending the class-split commands
        """
        self._class_split_confirmed = confirmed
        self.confirm_class_split_event.set()
