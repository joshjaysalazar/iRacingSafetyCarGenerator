import configparser
import logging
import tkinter as tk
from tkinter import ttk

from core import generator


class App(tk.Tk):
    """Main application window for the safety car generator."""
    def __init__(self):
        """Initialize the main application window.
        
        Args:
            None
        """
        super().__init__()
        logging.info("Initializing main application window")
        
        try:
            # Load settings from config file
            logging.info("Loading settings from settings.ini")
            self.settings = configparser.ConfigParser()
            self.settings.read("settings.ini")
        except Exception as e:
            logging.exception("An error occurred loading settings")
            raise e

        try:
            # Set window properties
            logging.debug("Setting window properties")
            self.title("iRacing Safety Car Generator")
        except Exception as e:
            logging.exception("An error occurred setting window properties")
            raise e

        # Create generator object
        self.generator = generator.Generator(self)
        self.shutdown_event = self.generator.shutdown_event

        # Set handler for closing main window event
        self.protocol('WM_DELETE_WINDOW', self.handle_delete_window)

        # Create widgets
        self._create_widgets()
            
    def handle_delete_window(self):
        """ Event handler to trigger shutdown_event and destroy the main window
        
        Args:
            None
        """
        try:
            logging.info("Closing main application window")
            self.shutdown_event.set()
            self.destroy()
        except Exception as e:
            logging.exception("An error occurred during window close")
            raise e

    def _create_widgets(self):
        """Create widgets for the main application window.

        Args:
            None
        """
        try:
            logging.info("Creating widgets for main application window")

            # Configure
            logging.debug("Configuring main application window")
            self.columnconfigure(0, weight=1)
            self.columnconfigure(1, weight=1)
            self.rowconfigure(0, weight=1)
            self.rowconfigure(1, weight=1)

            # Create Safety Car Types frame
            logging.debug("Creating Safety Car Types frame widget")
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
            logging.debug("Creating random checkbox widget")
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
            sc_types_row += 1

            # Create maximum occurences spinbox
            logging.debug("Creating maximum occurences spinbox widget")
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
            sc_types_row += 1

            # Create probability entry
            logging.debug("Creating probability entry widget")
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
            sc_types_row += 1

            # Create message entry
            logging.debug("Creating message entry widget")
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
            sc_types_row += 1

            # Create horizontal separator
            logging.debug("Creating horizontal separator widget")
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
            logging.debug("Creating cars stopped on track checkbox widget")
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
            sc_types_row += 1

            # Create minimum to trigger spinbox
            logging.debug("Creating minimum to trigger spinbox widget")
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
            sc_types_row += 1

            # Create message entry
            logging.debug("Creating message entry widget")
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
            sc_types_row += 1

            # Create horizontal separator
            logging.debug("Creating horizontal separator widget")
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
            logging.debug("Creating cars off track checkbox widget")
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
            sc_types_row += 1

            # Create minimum to trigger spinbox
            logging.debug("Creating minimum to trigger spinbox widget")
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
            sc_types_row += 1

            # Create message entry
            logging.debug("Creating message entry widget")
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

            # Create General frame
            logging.debug("Creating General frame widget")
            self.frm_general = ttk.LabelFrame(self, text="General")
            self.frm_general.grid(
                row=0,
                column=1,
                sticky="nesw",
                padx=5,
                pady=5
            )

            # Create variable to hold the current row in the frame
            general_row = 0

            # Create maximum safety cars spinbox
            logging.debug("Creating maximum safety cars spinbox widget")
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
            general_row += 1

            # Create earliest possible minute spinbox
            logging.debug("Creating earliest possible minute spinbox widget")
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
            general_row += 1

            # Create latest possible minute spinbox
            logging.debug("Creating latest possible minute spinbox widget")
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
            general_row += 1

            # Create minimum minutes between spinbox
            logging.debug("Creating minimum minutes between spinbox widget")
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
            general_row += 1

            # Create laps under safety car spinbox
            logging.debug("Creating laps under safety car spinbox widget")
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
            general_row += 1

            # Create immediate wave arounds checkbox
            logging.debug("Creating immediate wave arounds checkbox widget")
            self.var_immediate_wave_around = tk.IntVar()
            self.var_immediate_wave_around.set(1)
            self.chk_immediate_wave_around = ttk.Checkbutton(
                self.frm_general,
                text="Immediate wave arounds",
                variable=self.var_immediate_wave_around
            )
            self.chk_immediate_wave_around.grid(
                row=general_row,
                column=0,
                columnspan=2,
                sticky="w",
                padx=5,
                pady=5
            )

            # Create Controls frame
            logging.debug("Creating Controls frame widget")
            self.frm_controls = ttk.Frame(self)
            self.frm_controls.grid(
                row=1,
                column=1,
                sticky="nesw",
                padx=5,
                pady=5
            )
            self.frm_controls.columnconfigure(0, weight=1)

            # Create variable to hold the current row in the frame
            controls_row = 0

            # Create save settings button
            logging.debug("Creating save settings button widget")
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
            logging.debug("Creating run button widget")
            self.btn_run = ttk.Button(
                self.frm_controls,
                text="Run",
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

            # Create status label
            logging.debug("Creating status label widget")
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

            # Fill in the widgets with the settings from the config file
            logging.debug("Filling in widgets with settings from config file")
            self.var_random.set(self.settings["settings"].getboolean("random"))
            self.spn_random_max_occ.delete(0, "end")
            self.spn_random_max_occ.insert(
                0,
                self.settings["settings"]["random_max_occ"]
            )
            self.ent_random_prob.delete(0, "end")
            self.ent_random_prob.insert(
                0,
                self.settings["settings"]["random_prob"]
            )
            self.ent_random_message.delete(0, "end")
            self.ent_random_message.insert(
                0,
                self.settings["settings"]["random_message"]
            )
            self.var_stopped.set(
                self.settings["settings"].getboolean("stopped")
            )
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
            self.ent_off_message.insert(
                0,
                self.settings["settings"]["off_message"]
            )
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
            self.ent_end_minute.insert(
                0,
                self.settings["settings"]["end_minute"]
            )
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
            self.var_immediate_wave_around.set(
                self.settings["settings"].getboolean("imm_wave_around")
            )

            logging.info("Widgets created")

        except Exception as e:
            logging.exception("An error occurred creating widgets")
            raise e

    def _save_and_run(self):
        """Save the settings to the config file and run the generator.

        Args:
            None
        """
        self._save_settings()
        self.generator.run()

    def _save_settings(self):
        """Save the settings to the config file.

        Args:
            None
        """
        try:
            logging.info("Saving settings to config file")

            # Get all the settings from the widgets
            logging.debug("Getting settings from widgets")
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
            imm_wave_around = self.var_immediate_wave_around.get()

            # Save the settings to the config file
            logging.debug("Saving settings to config file")
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
            self.settings["settings"]["imm_wave_around"] = str(imm_wave_around)

            with open("settings.ini", "w") as configfile:
                self.settings.write(configfile)
        
        except Exception as e:
            logging.exception("An error occurred saving settings")
            raise e

    def set_message(self, message):
        """Set the status label to a message.

        Args:
            message (str): The message to set the status label to.
        """
        try:
            logging.info(f"Setting status label to: {message}")
            self.lbl_status["text"] = message
            self.update_idletasks()
        except Exception as e:
            logging.exception("An error occurred setting the status label")
            raise e