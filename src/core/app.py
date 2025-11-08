import json
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from core import generator
from core import tooltip
from core.generator import GeneratorState
from core.settings import Settings
from util.state_utils import generator_state_messages, is_stopped_state
from util.dev_utils import copy_sdk_data_to_clipboard, send_test_commands

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
        self.settings = Settings()

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
        self.columnconfigure(2, weight=1)
        self.rowconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(2, weight=1)

        # Create Safety Car Types frame
        logger.debug("Creating Safety Car Types frame")
        self.frm_sc_types = ttk.LabelFrame(self, text="Safety Car Types")
        self.frm_sc_types.grid(
            row=0,
            column=0,
            rowspan=3,
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

        # Create towing detector checkbox
        logger.debug("Creating towing detector checkbox")
        self.var_towing = tk.IntVar()
        self.var_towing.set(1)
        self.chk_towing = ttk.Checkbutton(
            self.frm_sc_types,
            text="Cars towing to pits",
            variable=self.var_towing
        )
        self.chk_towing.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(self.chk_towing, self.tooltips_text.get("towing", "Detect when cars tow to pits instead of driving there"))
        sc_types_row += 1

        # Create minimum to trigger spinbox
        logger.debug("Creating towing minimum to trigger spinbox")
        self.lbl_towing_min = ttk.Label(
            self.frm_sc_types,
            text="Minimum to trigger"
        )
        self.lbl_towing_min.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_towing_min = ttk.Spinbox(
            self.frm_sc_types,
            from_=0,
            to=100,
            width=5
        )
        self.spn_towing_min.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_towing_min,
            self.tooltips_text.get("towing_min", "Minimum number of cars towing to trigger safety car")
        )
        tooltip.CreateToolTip(
            self.spn_towing_min,
            self.tooltips_text.get("towing_min", "Minimum number of cars towing to trigger safety car")
        )
        sc_types_row += 1

        # Create towing message entry
        logger.debug("Creating towing message entry")
        self.ent_towing_message = ttk.Entry(
            self.frm_sc_types,
            width=32
        )
        self.ent_towing_message.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.ent_towing_message,
            self.tooltips_text.get("message")
        )
        sc_types_row += 1

        # Create max pit entry delta spinbox
        logger.debug("Creating max pit entry delta spinbox")
        self.lbl_towing_max_delta = ttk.Label(
            self.frm_sc_types,
            text="Max pit entry delta"
        )
        self.lbl_towing_max_delta.grid(
            row=sc_types_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_towing_max_delta = ttk.Spinbox(
            self.frm_sc_types,
            from_=0.01,
            to=0.5,
            increment=0.01,
            width=5
        )
        self.spn_towing_max_delta.grid(
            row=sc_types_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_towing_max_delta,
            self.tooltips_text.get("towing_max_delta", "Maximum lap distance delta (0.0-1.0) for normal pit entry")
        )
        tooltip.CreateToolTip(
            self.spn_towing_max_delta,
            self.tooltips_text.get("towing_max_delta", "Maximum lap distance delta (0.0-1.0) for normal pit entry")
        )
        sc_types_row += 1

        # Create pit entry statistics display
        logger.debug("Creating pit entry statistics display")
        self.lbl_pit_entry_stats = ttk.Label(
            self.frm_sc_types,
            text="Pit entry: No data",
            font=("TkDefaultFont", 8)
        )
        self.lbl_pit_entry_stats.grid(
            row=sc_types_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_pit_entry_stats,
            "Estimated pit entry location and confidence interval based on observed entries"
        )

        # Create Safety Car Settings frame
        logger.debug("Creating Safety Car Settings frame")
        self.frm_sc_settings = ttk.LabelFrame(self, text="Safety Car Threshold checks")
        self.frm_sc_settings.grid(row=0, column=1, sticky="nesw", padx=5, pady=5, rowspan=3)
        settings_row = 0

        # Create Event Time Window spinbox
        logger.debug("Creating event time window spinbox")
        self.lbl_time_range = ttk.Label(
            self.frm_sc_settings,
            text="Event Time Window (s)"
        )
        self.lbl_time_range.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_time_range = ttk.Spinbox(
            self.frm_sc_settings,
            from_=1,
            to=15,
            increment=0.5,
            width=5
        )
        self.spn_time_range.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_time_range,
            "Time window in seconds to consider recent events for threshold calculations"
        )
        tooltip.CreateToolTip(
            self.spn_time_range,
            "Time window in seconds to consider recent events for threshold calculations"
        )
        settings_row += 1

        # Create horizontal separator
        logger.debug("Creating horizontal separator")
        separator = ttk.Separator(self.frm_sc_settings, orient="horizontal")
        separator.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )
        settings_row += 1

        # Create Race Start Multiplier spinbox
        logger.debug("Creating race start SC multiplier spinbox")
        self.lbl_start_multiplier = ttk.Label(
            self.frm_sc_settings,
            text="Race Start multiplier"
        )
        self.lbl_start_multiplier.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_start_multiplier = ttk.Spinbox(
            self.frm_sc_settings,
            from_=1,
            to=10,
            width=5
        )
        self.spn_start_multiplier.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_start_multiplier,
            self.tooltips_text.get("start_multi_val")
        )
        tooltip.CreateToolTip(
            self.spn_start_multiplier,
            self.tooltips_text.get("start_multi_val")
        )
        settings_row += 1

        # Create Race Start Multiplier Time spinbox
        logger.debug("Creating race start SC multiplier active time spinbox")
        self.lbl_start_multi_time = ttk.Label(
            self.frm_sc_settings,
            text="Multiplier active time"
        )
        self.lbl_start_multi_time.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_start_multi_time = ttk.Spinbox(
            self.frm_sc_settings,
            from_=0,
            to=999,
            width=5
        )
        self.spn_start_multi_time.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_start_multi_time,
            self.tooltips_text.get("start_multi_time")
        )
        tooltip.CreateToolTip(
            self.spn_start_multi_time,
            self.tooltips_text.get("start_multi_time")
        )
        settings_row += 1

        # Create horizontal separator
        logger.debug("Creating horizontal separator")
        separator = ttk.Separator(self.frm_sc_settings, orient="horizontal")
        separator.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )
        settings_row += 1
        
        # Create proximity-based yellows checkbox
        logger.debug("Creating proximity-based yellows checkbox")
        self.var_proximity_yellows = tk.IntVar()
        self.var_proximity_yellows.set(1)
        self.chk_proximity_yellows = ttk.Checkbutton(
            self.frm_sc_settings,
            text="Proximity-based yellows",
            variable=self.var_proximity_yellows
        )
        self.chk_proximity_yellows.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.chk_proximity_yellows,
            self.tooltips_text.get("proximity_yellows")
        )
        settings_row += 1

        # Create proximity yellows distance setting spinbox
        logger.debug("Creating proximity yellows distance spinbox")
        self.lbl_proximity_dist = ttk.Label(
            self.frm_sc_settings,
            text="Proximity distance"
        )
        self.lbl_proximity_dist.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_proximity_dist = ttk.Spinbox(
            self.frm_sc_settings,
            increment=0.01,
            from_=0,
            to=1,
            width=5
        )
        self.spn_proximity_dist.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_proximity_dist,
            self.tooltips_text.get("proximity_yellows_distance")
        )
        tooltip.CreateToolTip(
            self.spn_proximity_dist,
            self.tooltips_text.get("proximity_yellows_distance")
        )
        settings_row += 1

        # Create horizontal separator
        logger.debug("Creating horizontal separator")
        separator = ttk.Separator(self.frm_sc_settings, orient="horizontal")
        separator.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="ew",
            padx=5,
            pady=5
        )
        settings_row += 1

        logger.debug("Creating combined yellows checkbox")
        self.var_combined = tk.IntVar()
        self.var_combined.set(1)
        self.chk_combined_yellows = ttk.Checkbutton(
            self.frm_sc_settings,
            text="Combined/Weighted Yellows",
            variable=self.var_combined
        )
        self.chk_combined_yellows.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.chk_combined_yellows,
            self.tooltips_text.get("combined_yellows")
        )
        settings_row += 1

        logger.debug("Creating combined threshold spinbox")
        self.lbl_combined_min = ttk.Label(
            self.frm_sc_settings,
            text="Combined threshold"
        )
        self.lbl_combined_min.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_combined_min = ttk.Spinbox(
            self.frm_sc_settings,
            increment=1,
            from_=1,
            to=100,
            width=5
        )
        self.spn_combined_min.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_combined_min,
            self.tooltips_text.get("combined_min")
        )
        tooltip.CreateToolTip(
            self.spn_combined_min,
            self.tooltips_text.get("combined_min")
        )
        settings_row += 1

        logger.debug("Creating off-track weight spinbox")
        self.lbl_off_weight = ttk.Label(
            self.frm_sc_settings,
            text="Off-track weight"
        )
        self.lbl_off_weight.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_off_weight = ttk.Spinbox(
            self.frm_sc_settings,
            increment=1,
            from_=1,
            to=10,
            width=5
        )
        self.spn_off_weight.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_off_weight,
            self.tooltips_text.get("off_weight")
        )
        tooltip.CreateToolTip(
            self.spn_off_weight,
            self.tooltips_text.get("off_weight")
        )
        settings_row += 1

        logger.debug("Creating stopped weight spinbox")
        self.lbl_stopped_weight = ttk.Label(
            self.frm_sc_settings,
            text="Stopped weight"
        )
        self.lbl_stopped_weight.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_stopped_weight = ttk.Spinbox(
            self.frm_sc_settings,
            increment=1,
            from_=1,
            to=10,
            width=5
        )
        self.spn_stopped_weight.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_stopped_weight,
            self.tooltips_text.get("stopped_weight")
        )
        tooltip.CreateToolTip(
            self.spn_stopped_weight,
            self.tooltips_text.get("stopped_weight")
        )
        settings_row += 1

        logger.debug("Creating towing weight spinbox")
        self.lbl_towing_weight = ttk.Label(
            self.frm_sc_settings,
            text="Towing weight"
        )
        self.lbl_towing_weight.grid(
            row=settings_row,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.spn_towing_weight = ttk.Spinbox(
            self.frm_sc_settings,
            increment=1,
            from_=1,
            to=10,
            width=5
        )
        self.spn_towing_weight.grid(
            row=settings_row,
            column=1,
            sticky="e",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.lbl_towing_weight,
            self.tooltips_text.get("towing_weight", "Weight for towing events in combined threshold")
        )
        tooltip.CreateToolTip(
            self.spn_towing_weight,
            self.tooltips_text.get("towing_weight", "Weight for towing events in combined threshold")
        )
        settings_row += 1

        logger.debug("Creating combined message entry")
        self.ent_combined_message = ttk.Entry(
            self.frm_sc_settings,
            width=32
        )
        self.ent_combined_message.grid(
            row=settings_row,
            column=0,
            columnspan=2,
            sticky="w",
            padx=5,
            pady=5
        )
        tooltip.CreateToolTip(
            self.ent_combined_message,
            self.tooltips_text.get("message")
        )

        # Create General frame
        logger.debug("Creating General frame")
        self.frm_general = ttk.LabelFrame(self, text="Eligibility window")
        self.frm_general.grid(row=0, column=2, sticky="nesw", padx=5, pady=5)

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


        # Safety car procedure specifics
        logger.debug("Creating SC procedure settings frame")
        self.frm_procedures = ttk.LabelFrame(self, text="Safety Car Procedures")
        self.frm_procedures.grid(row=1, column=2, sticky="nesw", padx=5, pady=5)

        # Create laps under safety car entry
        logger.debug("Creating laps under safety car entry")
        self.lbl_laps_under_sc = ttk.Label(
            self.frm_procedures,
            text="Laps under safety car"
        )
        self.lbl_laps_under_sc.grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_laps_under_sc = ttk.Entry(self.frm_procedures, width=5)
        self.ent_laps_under_sc.grid(
            row=0,
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

        # Create wave arounds checkbox
        logger.debug("Creating automatic wave arounds checkbox")
        self.var_wave_arounds = tk.IntVar()
        self.var_wave_arounds.set(1)
        self.chk_wave_arounds = ttk.Checkbutton(
            # self.frm_procedures,
            text="Automatic wave arounds",
            variable=self.var_wave_arounds
        )
        self.var_wave_arounds.trace_add("write", self.toggle_wave_around_config)

        tooltip.CreateToolTip(
            self.chk_wave_arounds,
            self.tooltips_text.get("wave_arounds")
        )
        
        # Wave arounds config
        logger.debug("Creating Wave arounds config panel")
        self.frm_wave_arounds = ttk.LabelFrame(self.frm_procedures, labelwidget=self.chk_wave_arounds)
        self.frm_wave_arounds.grid(row=1, column=0, columnspan=2, sticky="nesw", padx=5, pady=5)

        # Create laps before wave arounds entry
        logger.debug("Creating laps before wave arounds entry")
        self.lbl_laps_before_wave_arounds = ttk.Label(
            self.frm_wave_arounds,
            text="Laps before wave arounds"
        )
        self.lbl_laps_before_wave_arounds.grid(
            row=0,
            column=0,
            sticky="w",
            padx=5,
            pady=5
        )
        self.ent_laps_before_wave_arounds = ttk.Entry(self.frm_wave_arounds, width=5)
        self.ent_laps_before_wave_arounds.grid(
            row=0,
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

        logger.debug("Creating wave around rules picker")
        self.cmb_wave_around_rules = ttk.Combobox(
            self.frm_wave_arounds,
            width=24,
            state="readonly"
        )
        self.cmb_wave_around_rules.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky="we",
            padx=5,
            pady=5
        )
        self.cmb_wave_around_rules['values'] = (
            "Wave lapped cars",
            "Wave ahead of class lead",
            "Wave both (combined)",
        )
        tooltip.CreateToolTip(
            self.cmb_wave_around_rules,
            self.tooltips_text.get("wave_around_rules")
        )

        # Create Controls frame
        logger.debug("Creating Controls frame")
        self.frm_controls = ttk.Frame(self)
        self.frm_controls.grid(row=2, column=2, sticky="nesw", padx=5, pady=5)
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

        ### put visual warning here about dev mode if in dev mode
        if self.arguments.dry_run:
            logger.debug("Creating dry mode warning due to starting in dry mode")
            dry_run_style = ttk.Style()
            dry_run_style.configure("Dry.TLabel", foreground="red", font="bold")
            self.lbl_dry_run = ttk.Label(
                self.frm_controls,
                text="irSCG is in Dry Run mode!",
                style="Dry.TLabel",
                anchor=tk.CENTER
            )
            self.lbl_dry_run.grid(
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

            self.btn_copy_sdk_data = ttk.Button(
                self.frm_dev_mode,
                text="Copy SDK data",
                command=self._copy_sdk_data
            )
            self.btn_copy_sdk_data.grid(
                row=1,
                column=0,
                sticky="ew",
                padx=5,
                pady=5
            )

            self.btn_send_test_commands = ttk.Button(
                self.frm_dev_mode,
                text="Send test commands",
                command=self._send_test_commands
            )
            self.btn_send_test_commands.grid(
                row=2,
                column=0,
                sticky="ew",
                padx=5,
                pady=5
            )

            self.btn_parse_log_to_csv = ttk.Button(
                self.frm_dev_mode,
                text="Parse log to CSV",
                command=self._parse_log_to_csv
            )
            self.btn_parse_log_to_csv.grid(
                row=3,
                column=0,
                sticky="ew",
                padx=5,
                pady=5
            )

        # Fill in the widgets with the settings from the config file
        logger.debug("Filling in widgets with settings from config file")
        self.var_random.set(self.settings.random_detector_enabled)
        self.spn_random_max_occ.delete(0, "end")
        self.spn_random_max_occ.insert(0, str(self.settings.random_max_safety_cars))
        self.ent_random_prob.delete(0, "end")
        self.ent_random_prob.insert(0, str(self.settings.random_probability))
        self.ent_random_message.delete(0, "end")
        self.ent_random_message.insert(0, self.settings.random_message)
        self.var_stopped.set(self.settings.stopped_detector_enabled)
        self.spn_stopped_min.delete(0, "end")
        self.spn_stopped_min.insert(0, str(self.settings.stopped_cars_threshold))
        self.ent_stopped_message.delete(0, "end")
        self.ent_stopped_message.insert(0, self.settings.stopped_message)
        self.var_off.set(self.settings.off_track_detector_enabled)
        self.spn_off_min.delete(0, "end")
        self.spn_off_min.insert(0, str(self.settings.off_track_cars_threshold))
        self.ent_off_message.delete(0, "end")
        self.ent_off_message.insert(0, self.settings.off_track_message)
        self.spn_time_range.delete(0, "end")
        self.spn_time_range.insert(0, str(self.settings.event_time_window_seconds))
        self.spn_start_multi_time.delete(0, "end")
        self.spn_start_multi_time.insert(0, str(self.settings.race_start_threshold_multiplier_time_seconds))
        self.spn_start_multiplier.delete(0, "end")
        self.spn_start_multiplier.insert(0, str(self.settings.race_start_threshold_multiplier))
        self.ent_max_safety_cars.delete(0, "end")
        self.ent_max_safety_cars.insert(0, str(self.settings.max_safety_cars))
        self.ent_start_minute.delete(0, "end")
        self.ent_start_minute.insert(0, str(self.settings.detection_start_minute))
        self.ent_end_minute.delete(0, "end")
        self.ent_end_minute.insert(0, str(self.settings.detection_end_minute))
        self.ent_min_time_between.delete(0, "end")
        self.ent_min_time_between.insert(0, str(self.settings.min_time_between_safety_cars_minutes))
        self.ent_laps_under_sc.delete(0, "end")
        self.ent_laps_under_sc.insert(0, str(self.settings.laps_under_safety_car))
        self.var_wave_arounds.set(self.settings.wave_arounds_enabled)
        self.ent_laps_before_wave_arounds.delete(0, "end")
        self.ent_laps_before_wave_arounds.insert(0, str(self.settings.laps_before_wave_arounds))
        self.cmb_wave_around_rules.current(self.settings.wave_around_rules_index)
        self.var_proximity_yellows.set(self.settings.proximity_filter_enabled)
        self.spn_proximity_dist.delete(0, "end")
        self.spn_proximity_dist.insert(0, str(self.settings.proximity_filter_distance_percentage))
        self.var_combined.set(self.settings.accumulative_detector_enabled)
        self.spn_combined_min.delete(0, "end")
        self.spn_combined_min.insert(0, str(self.settings.accumulative_threshold))
        self.spn_off_weight.delete(0, "end")
        self.spn_off_weight.insert(0, str(self.settings.off_track_weight))
        self.spn_stopped_weight.delete(0, "end")
        self.spn_stopped_weight.insert(0, str(self.settings.stopped_weight))
        self.var_towing.set(getattr(self.settings, 'towing_detector_enabled', True))
        self.spn_towing_min.delete(0, "end")
        self.spn_towing_min.insert(0, str(getattr(self.settings, 'towing_cars_threshold', 1)))
        self.ent_towing_message.delete(0, "end")
        self.ent_towing_message.insert(0, getattr(self.settings, 'towing_message', 'Towing detected'))
        self.spn_towing_max_delta.delete(0, "end")
        self.spn_towing_max_delta.insert(0, str(getattr(self.settings, 'towing_max_pit_entry_delta', 0.05)))
        self.spn_towing_weight.delete(0, "end")
        self.spn_towing_weight.insert(0, str(getattr(self.settings, 'towing_weight', 2.0)))
        self.ent_combined_message.delete(0, "end")
        self.ent_combined_message.insert(0, self.settings.accumulative_message)

        # self.ent_laps_before_wave_arounds.config(state="disabled")

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
        time_range = self.spn_time_range.get()
        start_multi_val = self.spn_start_multiplier.get()
        start_multi_time = self.spn_start_multi_time.get()
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
        wave_around_rules = self.cmb_wave_around_rules.current()
        proximity_yellows = self.var_proximity_yellows.get()
        proximity_yellows_distance = self.spn_proximity_dist.get()
        combined = self.var_combined.get()
        combined_min = self.spn_combined_min.get()
        stopped_weight = self.spn_stopped_weight.get()
        off_weight = self.spn_off_weight.get()
        towing = self.var_towing.get()
        towing_min = self.spn_towing_min.get()
        towing_message = self.ent_towing_message.get()
        towing_max_delta = self.spn_towing_max_delta.get()
        towing_weight = self.spn_towing_weight.get()
        combined_message = self.ent_combined_message.get()

        # Save the settings to the config file
        # IntVar.get() returns int (0 or 1), bool() converts correctly
        self.settings.random_detector_enabled = bool(random)
        self.settings.random_max_safety_cars = int(random_max_occ)
        self.settings.random_probability = float(random_prob)
        self.settings.random_message = str(random_message)
        self.settings.stopped_detector_enabled = bool(stopped)
        self.settings.stopped_cars_threshold = int(stopped_min)
        self.settings.stopped_message = str(stopped_message)
        self.settings.event_time_window_seconds = float(time_range)
        self.settings.race_start_threshold_multiplier = float(start_multi_val)
        self.settings.race_start_threshold_multiplier_time_seconds = float(start_multi_time)
        self.settings.off_track_detector_enabled = bool(off)
        self.settings.off_track_cars_threshold = int(off_min)
        self.settings.off_track_message = str(off_message)
        self.settings.max_safety_cars = int(max_safety_cars)
        self.settings.detection_start_minute = float(start_minute)
        self.settings.detection_end_minute = float(end_minute)
        self.settings.min_time_between_safety_cars_minutes = float(min_time_between)
        self.settings.laps_under_safety_car = int(laps_under_sc)
        self.settings.wave_arounds_enabled = bool(wave_arounds)
        self.settings.laps_before_wave_arounds = int(laps_before_wave_arounds)
        self.settings.wave_around_rules_index = int(wave_around_rules)
        self.settings.proximity_filter_enabled = bool(proximity_yellows)
        self.settings.proximity_filter_distance_percentage = float(proximity_yellows_distance)
        self.settings.accumulative_threshold = float(combined_min)
        self.settings.stopped_weight = float(stopped_weight)
        self.settings.off_track_weight = float(off_weight)
        self.settings.towing_detector_enabled = bool(towing)
        self.settings.towing_cars_threshold = int(towing_min)
        self.settings.towing_message = str(towing_message)
        self.settings.towing_max_pit_entry_delta = float(towing_max_delta)
        self.settings.towing_weight = float(towing_weight)
        self.settings.accumulative_detector_enabled = bool(combined)
        self.settings.accumulative_message = str(combined_message)

        self.settings.save()

    def set_message(self, message):
        """Set the status label to a message.

        Args:
            message (str): The message to set the status label to.
        """
        logger.debug(f"Setting status label to: {message}")
        self.lbl_status["text"] = message
        self.update_idletasks()

    def update_pit_entry_stats(self, statistics):
        """Update the pit entry statistics display.

        Args:
            statistics (PitEntryStatistics): The pit entry statistics to display.
        """
        if statistics.estimated_location is None:
            self.lbl_pit_entry_stats["text"] = "Pit entry: No data"
        else:
            location_pct = statistics.estimated_location * 100
            ci_pct = statistics.confidence_interval * 100
            self.lbl_pit_entry_stats["text"] = f"Pit entry: {location_pct:.1f}% ±{ci_pct:.1f}% (n={statistics.observation_count})"
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

    def toggle_wave_around_config(self, *args):
        """Toggle the state of the wave arounds config panel.

        Args:

        """
        logger.debug("Toggling wave arounds config panel")
        if self.var_wave_arounds.get() == 1:
            self.lbl_laps_before_wave_arounds.config(state="normal")
            self.ent_laps_before_wave_arounds.config(state="normal")
            self.cmb_wave_around_rules.config(state="normal")
        else:
            self.lbl_laps_before_wave_arounds.config(state="disabled")
            self.ent_laps_before_wave_arounds.config(state="disabled")
            self.cmb_wave_around_rules.config(state="disabled")

    def _skip_wait_for_green(self):
        """Move from waiting for green to monitoring session state.

        Args:
            None
        """
        self.skip_wait_for_green_event.set()

    def _copy_sdk_data(self):
        """Copy current SDK data to clipboard

        Args:
            None
        """
        copy_sdk_data_to_clipboard()

    def _send_test_commands(self):
        """Send test commands to iRacing to understand rate limiting.

        Args:
            None
        """
        send_test_commands()

    def _parse_log_to_csv(self):
        """Open file dialog to select log file and parse events to CSV.

        Args:
            None
        """
        # Open file dialog to select log file
        log_file = filedialog.askopenfilename(
            title="Select log file to parse",
            initialdir="logs",
            filetypes=[("Log files", "*.log"), ("All files", "*.*")]
        )

        if log_file:
            try:
                from util.dev_utils import parse_log_events_to_csv
                csv_file = parse_log_events_to_csv(log_file)
                messagebox.showinfo(
                    "Success",
                    f"Log parsed successfully!\nCSV file created: {csv_file}"
                )
            except Exception as e:
                logger.error(f"Error parsing log file: {e}")
                messagebox.showerror("Error", f"Failed to parse log file:\n{str(e)}")

