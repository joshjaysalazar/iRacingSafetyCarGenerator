import configparser
import tkinter as tk
from tkinter import ttk
from tkinter import scrolledtext

from core import generator


class App(tk.Tk):
    """Main application window for the safety car generator."""
    def __init__(self):
        """Initialize the main application window.
        
        Args:
            None
        """
        super().__init__()

        # Load settings from config file
        self.settings = configparser.ConfigParser()
        self.settings.read("settings.ini")

        # Set window properties
        self.title("iRacing Safety Car Generator")

        # Create generator object
        self.generator = generator.Generator(self)

        # Create widgets
        self._create_widgets()

    def _create_widgets(self):
        """Create widgets for the main application window.

        Args:
            None
        """
        # Configure
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        # Create Safety Car Types frame
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
        self.frm_general = ttk.LabelFrame(self, text="General")
        self.frm_general.grid(row=0, column=1, sticky="nesw", padx=5, pady=5)

        # Create variable to hold the current row in the frame
        general_row = 0

        # Create maximum safety cars spinbox
        self.lbl_max_sc = ttk.Label(
            self.frm_general,
            text="Maximum safety cars"
        )
        self.lbl_max_sc.grid(
            row=general_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_max_sc = ttk.Entry(self.frm_general, width=5)
        self.ent_max_sc.grid(
            row=general_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        general_row += 1

        # Create earliest possible minute spinbox
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
        self.frm_controls = ttk.Frame(self)
        self.frm_controls.grid(row=1, column=1, sticky="nesw", padx=5, pady=5)
        self.frm_controls.columnconfigure(0, weight=1)

        # Create variable to hold the current row in the frame
        controls_row = 0

        # Create save settings button
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
        self.btn_run = ttk.Button(
            self.frm_controls,
            text="Run",
            command=self.generator.run
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
        self.lbl_status = ttk.Label(
            self.frm_controls,
            text="Ready to run...",
            anchor=tk.CENTER
        )
        self.lbl_status.grid(
            row=controls_row,
            column=0,
            sticky="ew",
            padx=5,
            pady=5
        )        

    def _save_settings(self):
        """Save the settings to the config file.

        Args:
            None
        """
        # Get settings from the entry widgets
        min_sc_entry = self.min_sc_entry.get()
        max_sc_entry = self.ent_max_sc.get()
        start_minute_entry = self.ent_start_minute.get()
        end_minute_entry = self.ent_end_minute.get()
        min_time_between_entry = self.ent_min_time_between.get()
        laps_under_sc_entry = self.ent_laps_under_sc.get()
        immediate_waveby_entry = str(self.immediate_waveby_var.get())

        # Save the settings to the config file
        self.settings["settings"]["min_safety_cars"] = min_sc_entry
        self.settings["settings"]["max_safety_cars"] = max_sc_entry
        self.settings["settings"]["start_minute"] = start_minute_entry
        self.settings["settings"]["end_minute"] = end_minute_entry
        self.settings["settings"]["min_time_between"] = min_time_between_entry
        self.settings["settings"]["laps_under_sc"] = laps_under_sc_entry
        self.settings["settings"]["immediate_waveby"] = immediate_waveby_entry

        with open("settings.ini", "w") as configfile:
            self.settings.write(configfile)

    def add_message(self, message):
        """Add a message to the scrolled text box.

        Args:
            message (str): The message to add to the scrolled text box.
        """
        self.sc_text.configure(state="normal")
        self.sc_text.insert("end", f"{message}\n")
        self.sc_text.configure(state="disabled")
        self.sc_text.see("end")