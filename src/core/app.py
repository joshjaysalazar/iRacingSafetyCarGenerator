import configparser
import json
import logging
import tkinter as tk
from tkinter import ttk

from core import generator
from core import tooltip
from core.generator import GeneratorState
from util.state_utils import generator_state_messages, is_stopped_state

logger = logging.getLogger(__name__)

class App(tk.Tk):
    """Main application window for the safety car generator."""
    def __init__(self, arguments):
        """Initialize the main application window.
        
        Args:
            None
        """
        logger.info("Initializing main application window")
        super().__init__()
        self.arguments = arguments

        # Tooltips text
        self.load_tooltips_text()

        # Load settings from config file
        logger.info("Loading settings from settings.ini")
        self.settings = configparser.ConfigParser()
        self.settings.read("settings.ini")

        # Set window properties
        self.title("iRacing Safety Car Generator")

        # Trace state variables
        self._generator_state = GeneratorState.STOPPED
        
        # Create generator object
        self.generator = generator.Generator(arguments, self)
        self.shutdown_event = self.generator.shutdown_event
        self.skip_wait_for_green_event = self.generator.skip_wait_for_green_event

        # Set handler for closing main window event
        self.protocol('WM_DELETE_WINDOW', self.handle_delete_window)

        # Create widgets
        self._create_widgets()

    # Advanced features toggle
    def _toggle_advanced_features(self):
        if self.var_advanced_features.get():
            self.btn_start_sc.grid(
                row=self._throw_yellow_row,
                column=0,
                sticky="ew",
                padx=5,
                pady=5
            )
        else:
            self.btn_start_sc.grid_remove()

    def load_tooltips_text(self):
        logger.info("Loading tooltips text")
        try:
            with open("tooltips_text.json", "r") as file:
                self.tooltips_text = json.load(file)
        except Exception as e:
            self.tooltips_text = {}

    def handle_delete_window(self):
        """ Event handler to trigger shutdown_event and destroy the main window
        
        Args:
            None
        """
        logger.info("Closing main application window")
        self.shutdown_event.set()
        self.destroy()

    def _create_widgets(self):
        """Create widgets for the main application window.

        Args:
            None
        """
        logger.info("Creating widgets for main application window")

        # Checkbox for advanced features
        self.var_advanced_features = tk.IntVar()
        self.var_advanced_features.set(0)

        # Configure
        logger.debug("Configuring main application window")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Create Safety Car Types frame
        logger.debug("Creating Safety Car Types frame")
        self.frm_sc_types = ttk.LabelFrame(self, text="Safety Car Types")
        self.frm_sc_types.grid(
            row=0,
            column=0,
            rowspan=2,
            sticky="nesw",
            padx=5,
            pady=5
        )

        # Create variable to hold the current row in the frame
        sc_types_row = 0

        # Create random checkbox
        logger.debug("Creating random checkbox")
        self.var_random = tk.IntVar()
        self.var_random.set(1)
        self.chk_random = ttk.Checkbutton(
            self.frm_sc_types,
            text="Random",
            variable=self.var_random
        )
        self.chk_random.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(self.chk_random, self.tooltips_text.get("random"))
        sc_types_row += 1

        # Create maximum occurences spinbox
        logger.debug("Creating maximum occurences spinbox")
        self.lbl_random_max_occ = ttk.Label(
            self.frm_sc_types,
            text="Maximum occurences"
        )
        self.lbl_random_max_occ.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_random_max_occ = ttk.Spinbox(
            self.frm_sc_types,
            from_=0,
            to=100,
            width=5
        )
        self.spn_random_max_occ.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_random_max_occ,
            self.tooltips_text.get("random_max_occ")
        )
        tooltip.CreateToolTip(
            self.spn_random_max_occ,
            self.tooltips_text.get("random_max_occ")
        )
        sc_types_row += 1

        # Create probability entry
        logger.debug("Creating probability entry")
        self.lbl_random_prob = ttk.Label(
            self.frm_sc_types,
            text="Probability"
        )
        self.lbl_random_prob.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_random_prob = ttk.Entry(self.frm_sc_types, width=7)
        self.ent_random_prob.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_random_prob,
            self.tooltips_text.get("random_prob")
        )
        tooltip.CreateToolTip(
            self.ent_random_prob,
            self.tooltips_text.get("random_prob")
        )
        sc_types_row += 1

        # Create message entry
        logger.debug("Creating message entry")
        self.ent_random_message = ttk.Entry(
            self.frm_sc_types,
            width=32
        )
        self.ent_random_message.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.ent_random_message,
            self.tooltips_text.get("message")
        )
        sc_types_row += 1

        # Create horizontal separator
        logger.debug("Creating horizontal separator")
        separator = ttk.Separator(self.frm_sc_types, orient="horizontal")
        separator.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )
        sc_types_row += 1

        # Create cars stopped on track checkbox
        logger.debug("Creating cars stopped on track checkbox")
        self.var_stopped = tk.IntVar()
        self.var_stopped.set(1)
        self.chk_stopped = ttk.Checkbutton(
            self.frm_sc_types,
            text="Cars stopped on track",
            variable=self.var_stopped
        )
        self.chk_stopped.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.chk_stopped,
            self.tooltips_text.get("stopped")
        )
        sc_types_row += 1

        # Create minimum to trigger spinbox
        logger.debug("Creating minimum to trigger spinbox")
        self.lbl_stopped_min = ttk.Label(
            self.frm_sc_types,
            text="Minimum to trigger"
        )
        self.lbl_stopped_min.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_stopped_min = ttk.Spinbox(
            self.frm_sc_types,
            from_=0,
            to=100,
            width=5
        )
        self.spn_stopped_min.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_stopped_min,
            self.tooltips_text.get("stopped_min")
        )
        tooltip.CreateToolTip(
            self.spn_stopped_min,
            self.tooltips_text.get("stopped_min")
        )
        sc_types_row += 1

        # Create message entry
        logger.debug("Creating message entry")
        self.ent_stopped_message = ttk.Entry(
            self.frm_sc_types,
            width=32
        )
        self.ent_stopped_message.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.ent_stopped_message,
            self.tooltips_text.get("message")
        )
        sc_types_row += 1

        # Create horizontal separator
        logger.debug("Creating horizontal separator")
        separator = ttk.Separator(self.frm_sc_types, orient="horizontal")
        separator.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )
        sc_types_row += 1

        # Create cars off track checkbox
        logger.debug("Creating cars off track checkbox")
        self.var_off = tk.IntVar()
        self.var_off.set(1)
        self.chk_off = ttk.Checkbutton(
            self.frm_sc_types,
            text="Cars off track",
            variable=self.var_off
        )
        self.chk_off.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(self.chk_off, self.tooltips_text.get("off"))
        sc_types_row += 1

        # Create minimum to trigger spinbox
        logger.debug("Creating minimum to trigger spinbox")
        self.lbl_off_min = ttk.Label(
            self.frm_sc_types,
            text="Minimum to trigger"
        )
        self.lbl_off_min.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_off_min = ttk.Spinbox(
            self.frm_sc_types,
            from_=0,
            to=100,
            width=5
        )
        self.spn_off_min.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_off_min,
            self.tooltips_text.get("off_min")
        )
        tooltip.CreateToolTip(
            self.spn_off_min,
            self.tooltips_text.get("off_min")
        )
        sc_types_row += 1

        # Create message entry
        logger.debug("Creating message entry")
        self.ent_off_message = ttk.Entry(
            self.frm_sc_types,
            width=32
        )
        self.ent_off_message.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.ent_off_message,
            self.tooltips_text.get("message")
        )

        # Create General frame
        logger.debug("Creating General frame")
        self.frm_general = ttk.LabelFrame(self, text="General")
        self.frm_general.grid(row=0, column=1, sticky="nesw", padx=5, pady=5)

        # Create variable to hold the current row in the frame
        general_row = 0

        # Create maximum safety cars entry
        logger.debug("Creating maximum safety cars entry")
        self.lbl_max_safety_cars = ttk.Label(
            self.frm_general,
            text="Maximum safety cars"
        )
        self.lbl_max_safety_cars.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_max_safety_cars = ttk.Entry(self.frm_general, width=5)
        self.ent_max_safety_cars.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_max_safety_cars,
            self.tooltips_text.get("max_safety_cars")
        )
        tooltip.CreateToolTip(
            self.ent_max_safety_cars,
            self.tooltips_text.get("max_safety_cars")
        )
        general_row += 1

        # Create earliest possible minute entry
        logger.debug("Creating earliest possible minute entry")
        self.lbl_start_minute = ttk.Label(
            self.frm_general,
            text="Earliest possible minute"
        )
        self.lbl_start_minute.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_start_minute = ttk.Entry(self.frm_general, width=5)
        self.ent_start_minute.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_start_minute,
            self.tooltips_text.get("start_minute")
        )
        tooltip.CreateToolTip(
            self.ent_start_minute,
            self.tooltips_text.get("start_minute")
        )
        general_row += 1

        # Create latest possible minute entry
        logger.debug("Creating latest possible minute entry")
        self.lbl_end_minute = ttk.Label(
            self.frm_general,
            text="Latest possible minute"
        )
        self.lbl_end_minute.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_end_minute = ttk.Entry(self.frm_general, width=5)
        self.ent_end_minute.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_end_minute,
            self.tooltips_text.get("end_minute")
        )
        tooltip.CreateToolTip(
            self.ent_end_minute,
            self.tooltips_text.get("end_minute")
        )
        general_row += 1

        # Create minimum minutes between entry
        logger.debug("Creating minimum minutes between entry")
        self.lbl_min_time_between = ttk.Label(
            self.frm_general,
            text="Minimum minutes between"
        )
        self.lbl_min_time_between.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_min_time_between = ttk.Entry(self.frm_general, width=5)
        self.ent_min_time_between.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_min_time_between,
            self.tooltips_text.get("min_time_between")
        )
        tooltip.CreateToolTip(
            self.ent_min_time_between,
            self.tooltips_text.get("min_time_between")
        )
        general_row += 1

        # Create laps under safety car entry
        logger.debug("Creating laps under safety car entry")
        self.lbl_laps_under_sc = ttk.Label(
            self.frm_general,
            text="Laps under safety car"
        )
        self.lbl_laps_under_sc.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_laps_under_sc = ttk.Entry(self.frm_general, width=5)
        self.ent_laps_under_sc.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_laps_under_sc,
            self.tooltips_text.get("laps_under_sc")
        )
        tooltip.CreateToolTip(
            self.ent_laps_under_sc,
            self.tooltips_text.get("laps_under_sc")
        )
        general_row += 1

        # Create wave arounds checkbox
        logger.debug("Creating automatic wave arounds checkbox")
        self.var_wave_arounds = tk.IntVar()
        self.var_wave_arounds.set(1)
        self.chk_wave_arounds = ttk.Checkbutton(
            self.frm_general,
            text="Automatic wave arounds",
            variable=self.var_wave_arounds
        )
        self.chk_wave_arounds.grid(
            row=general_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.chk_wave_arounds,
            self.tooltips_text.get("wave_arounds")
        )
        general_row += 1

        # Create laps before wave arounds entry
        logger.debug("Creating laps before wave arounds entry")
        self.lbl_laps_before_wave_arounds = ttk.Label(
            self.frm_general,
            text="Laps before wave arounds"
        )
        self.lbl_laps_before_wave_arounds.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_laps_before_wave_arounds = ttk.Entry(self.frm_general, width=5)
        self.ent_laps_before_wave_arounds.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_laps_before_wave_arounds,
            self.tooltips_text.get("laps_before_wave_arounds")
        )
        tooltip.CreateToolTip(
            self.ent_laps_before_wave_arounds,
            self.tooltips_text.get("laps_before_wave_arounds")
        )

        # Create Controls frame
        logger.debug("Creating Controls frame")
        self.frm_controls = ttk.Frame(self)
        self.frm_controls.grid(row=1, column=1, sticky="nesw", padx=5, pady=5)
        self.frm_controls.columnconfigure(0, weight=1)

        # Create variable to hold the current row in the frame
        controls_row = 0

        # Create save settings button
        logger.debug("Creating save settings button")
        self.btn_save_settings = ttk.Button(
            self.frm_controls,
            text="Save Settings",
            command=self._save_settings
        )
        self.btn_save_settings.grid(
            row=controls_row,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )
        controls_row += 1

        # Create run button
        logger.debug("Creating run button")

        play_icon = tk.PhotoImage(file='assets/play.png')
        play_icon = play_icon.subsample(2)
        stop_icon = tk.PhotoImage(file='assets/stop.png')
        stop_icon = stop_icon.subsample(2)

        self.generator_state_messages = generator_state_messages(play_icon, stop_icon)

        self.btn_run = ttk.Button(
            self.frm_controls,
            text=self.generator_state_messages[GeneratorState.STOPPED]['btn_run_text'],
            image=self.generator_state_messages[GeneratorState.STOPPED]['btn_run_icon'],
            compound=tk.LEFT,
            command=self._save_and_run
        )
        self.btn_run.grid(
            row=controls_row,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )
        controls_row += 1

    

        self.chk_advanced_features = ttk.Checkbutton(
            self.frm_controls,
            text="Advanced Features",
            variable=self.var_advanced_features,
            command=self._toggle_advanced_features
        )
        self.chk_advanced_features.grid(
            row=controls_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        controls_row += 1

        self._throw_yellow_row = controls_row
        controls_row += 1


        #Throw Double Yellows
        self.btn_start_sc = ttk.Button(
            self.frm_controls,
            text="Throw Double Yellows",
            command=self._start_safety_car,
        )
        
        # Create status label
        logger.debug("Creating status label")
        self.lbl_status = ttk.Label(
            self.frm_controls,
            text="Ready\n",
            anchor=tk.CENTER
        )
        self.lbl_status.grid(
            row=controls_row,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )
        controls_row += 1

        # Add dev mode controls
        if self.arguments.developer_mode:
            logger.debug("Creating developer_mode UI")
            self.frm_dev_mode = ttk.LabelFrame(self.frm_controls, text="DEVELOPER MODE")
            self.frm_dev_mode.grid(
                row=controls_row,
                column=0,
                sticky="ew", 
                padx=5,
                pady=5
            )

            self.btn_skip_wait_for_green = ttk.Button(
                self.frm_dev_mode,
                text="Skip Wait for Green",
                command=self._skip_wait_for_green
            )
            self.btn_skip_wait_for_green.grid(
                row=0,
                column=0,
                sticky="ew",
                padx=5,
                pady=5
            )

        # Fill in the widgets with the settings from the config file
        logger.debug("Filling in widgets with settings from config file")
        self.var_random.set(self.settings["settings"].getboolean("random"))
        self.spn_random_max_occ.delete(0, "end")
        self.spn_random_max_occ.insert(
            0,
            self.settings["settings"]["random_max_occ"]
        )
        self.ent_random_prob.delete(0, "end")
        self.ent_random_prob.insert(0, self.settings["settings"]["random_prob"])
        self.ent_random_message.delete(0, "end")
        self.ent_random_message.insert(
            0,
            self.settings["settings"]["random_message"]
        )
        self.var_stopped.set(self.settings["settings"].getboolean("stopped"))
        self.spn_stopped_min.delete(0, "end")
        self.spn_stopped_min.insert(
            0,
            self.settings["settings"]["stopped_min"]
        )
        self.ent_stopped_message.delete(0, "end")
        self.ent_stopped_message.insert(
            0,
            self.settings["settings"]["stopped_message"]
        )
        self.var_off.set(self.settings["settings"].getboolean("off"))
        self.spn_off_min.delete(0, "end")
        self.spn_off_min.insert(0, self.settings["settings"]["off_min"])
        self.ent_off_message.delete(0, "end")
        self.ent_off_message.insert(0, self.settings["settings"]["off_message"])
        self.ent_max_safety_cars.delete(0, "end")
        self.ent_max_safety_cars.insert(
            0,
            self.settings["settings"]["max_safety_cars"]
        )
        self.ent_start_minute.delete(0, "end")
        self.ent_start_minute.insert(
            0,
            self.settings["settings"]["start_minute"]
        )
        self.ent_end_minute.delete(0, "end")
        self.ent_end_minute.insert(0, self.settings["settings"]["end_minute"])
        self.ent_min_time_between.delete(0, "end")
        self.ent_min_time_between.insert(
            0,
            self.settings["settings"]["min_time_between"]
        )
        self.ent_laps_under_sc.delete(0, "end")
        self.ent_laps_under_sc.insert(
            0,
            self.settings["settings"]["laps_under_sc"]
        )
        self.var_wave_arounds.set(
            self.settings["settings"].getboolean("wave_arounds")
        )
        self.ent_laps_before_wave_arounds.delete(0, "end")
        self.ent_laps_before_wave_arounds.insert(
            0,
            self.settings["settings"]["laps_before_wave_arounds"]
        )

    def _save_and_run(self):
        """Save the settings to the config file and run the generator.

        Args:
            None
        """
        if is_stopped_state(self.generator_state):
            logger.info('Saving settings and starting the generator')
            self._save_settings()
            started = self.generator.run()
            if not started:
                logger.info('Could not start generator')
        else:
            logger.info('Shutting down generator due to manual stop')
            self.generator.stop()

    def _start_safety_car(self):
        """Starts a safety car procedure controlled by the software.

        Args:
            None
        """
        if not is_stopped_state(self.generator_state):
            logger.info('Starting a manual safety car')
            self.generator.throw_manual_safety_car()
        else:
            logger.info('Tried to throw a manual SC, but generator not running')

    def _save_settings(self):
        """Save the settings to the config file.

        Args:
            None
        """
        logger.info("Saving settings to config file")

        # Get all the settings from the widgets
        random = self.var_random.get()
        random_max_occ = self.spn_random_max_occ.get()
        random_prob = self.ent_random_prob.get()
        random_message = self.ent_random_message.get()
        stopped = self.var_stopped.get()
        stopped_min = self.spn_stopped_min.get()
        stopped_message = self.ent_stopped_message.get()
        off = self.var_off.get()
        off_min = self.spn_off_min.get()
        off_message = self.ent_off_message.get()
        max_safety_cars = self.ent_max_safety_cars.get()
        start_minute = self.ent_start_minute.get()
        end_minute = self.ent_end_minute.get()
        min_time_between = self.ent_min_time_between.get()
        laps_under_sc = self.ent_laps_under_sc.get()
        wave_arounds = self.var_wave_arounds.get()
        laps_before_wave_arounds = self.ent_laps_before_wave_arounds.get()

        # Save the settings to the config file
        self.settings["settings"]["random"] = str(random)
        self.settings["settings"]["random_max_occ"] = str(random_max_occ)
        self.settings["settings"]["random_prob"] = str(random_prob)
        self.settings["settings"]["random_message"] = str(random_message)
        self.settings["settings"]["stopped"] = str(stopped)
        self.settings["settings"]["stopped_min"] = str(stopped_min)
        self.settings["settings"]["stopped_message"] = str(stopped_message)
        self.settings["settings"]["off"] = str(off)
        self.settings["settings"]["off_min"] = str(off_min)
        self.settings["settings"]["off_message"] = str(off_message)
        self.settings["settings"]["max_safety_cars"] = str(max_safety_cars)
        self.settings["settings"]["start_minute"] = str(start_minute)
        self.settings["settings"]["end_minute"] = str(end_minute)
        self.settings["settings"]["min_time_between"] = str(min_time_between)
        self.settings["settings"]["laps_under_sc"] = str(laps_under_sc)
        self.settings["settings"]["wave_arounds"] = str(wave_arounds)
        self.settings["settings"]["laps_before_wave_arounds"] = str(
            laps_before_wave_arounds
        )

        with open("settings.ini", "w") as configfile:
            self.settings.write(configfile)

    def set_message(self, message):
        """Set the status label to a message.

        Args:
            message (str): The message to set the status label to.
        """
        logger.debug(f"Setting status label to: {message}")
        self.lbl_status["text"] = message
        self.update_idletasks()

    @property
    def generator_state(self):
        return self._generator_state
    
    @generator_state.setter
    def generator_state(self, new_state):
        self._generator_state = new_state
        self.on_generator_state_change()

    def on_generator_state_change(self):
        logger.debug(f"Updating state to {self.generator_state} state")
        
        if self.generator_state not in self.generator_state_messages:
            logger.error(f"Unexpected generator_state value: {self.generator_state}")
            return

        self.btn_run['text'] = self.generator_state_messages[self.generator_state]['btn_run_text']
        self.btn_run['image'] = self.generator_state_messages[self.generator_state]['btn_run_icon']
        self.set_message(self.generator_state_messages[self.generator_state]['message'])

    def _skip_wait_for_green(self):
        """Move from waiting for green to monitoring session state.

        Args:
            None
        """
        self.skip_wait_for_green_event.set()