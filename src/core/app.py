import configparser
import tkinter as tk


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Load settings from config file
        self.settings = configparser.ConfigParser()
        self.settings = self.settings.read("settings.ini")

        from pprint import pprint
        pprint(self.settings)
        print(self.settings)

        # Set window properties
        self.title("iRacing Safety Car Generator")

        # Create widgets
        # self._create_widgets()

    def _create_widgets(self):
        # Create a two column grid
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Create and grid widgets for each setting
        self.min_sc_label = tk.Label(self, text="Minimum Safety Cars")
        self.min_sc_entry = tk.Entry(self)
        self.min_sc_entry.insert(0, self.settings["settings"]["min_safety_cars"])
        self.min_sc_label.grid(row=0, column=0)
        self.min_sc_entry.grid(row=0, column=1)

        self.max_sc_label = tk.Label(self, text="Maximum Safety Cars")
        self.max_sc_entry = tk.Entry(self)
        self.max_sc_entry.insert(0, self.settings["max_safety_cars"])
        self.max_sc_label.grid(row=1, column=0)
        self.max_sc_entry.grid(row=1, column=1)

        self.start_minute_label = tk.Label(self, text="Start Minute")
        self.start_minute_entry = tk.Entry(self)
        self.start_minute_entry.insert(0, self.settings["start_minute"])
        self.start_minute_label.grid(row=2, column=0)
        self.start_minute_entry.grid(row=2, column=1)

        self.end_minute_label = tk.Label(self, text="End Minute")
        self.end_minute_entry = tk.Entry(self)
        self.end_minute_entry.insert(0, self.settings["end_minute"])
        self.end_minute_label.grid(row=3, column=0)
        self.end_minute_entry.grid(row=3, column=1)

        self.min_time_between_label = tk.Label(self, text="Minimum Minutes Between SC Events")
        self.min_time_between_entry = tk.Entry(self)
        self.min_time_between_entry.insert(0, self.settings["min_time_between"])
        self.min_time_between_label.grid(row=4, column=0)
        self.min_time_between_entry.grid(row=4, column=1)

        self.laps_under_sc_label = tk.Label(self, text="Laps Under Safety Car")
        self.laps_under_sc_entry = tk.Entry(self)
        self.laps_under_sc_entry.insert(0, self.settings["laps_under_sc"])
        self.laps_under_sc_label.grid(row=5, column=0)
        self.laps_under_sc_entry.grid(row=5, column=1)

        # Create a save settings button
        self.save_button = tk.Button(self, text="Save Settings", command=self._save_settings)
        self.save_button.grid(row=6, column=0, columnspan=2)

        # Create a button to generate safety car events
        self.generate_button = tk.Button(self, text="Generate Safety Car Events", command=self.generate)
        self.generate_button.grid(row=7, column=0, columnspan=2)

        # Create a disabled text box to display the generated safety car events
        self.sc_text = tk.Text(self, height=10, width=50, state="disabled")
        self.sc_text.grid(row=8, column=0, columnspan=2)




        
        # # Create widgets for each setting
        # self.min_sc_label = tk.Label(self, text="Minimum Safety Cars")
        # self.min_sc_entry = tk.Entry(self)
        # self.min_sc_entry.insert(0, self.settings["min_safety_cars"])

        # self.max_sc_label = tk.Label(self, text="Maximum Safety Cars")
        # self.max_sc_entry = tk.Entry(self)
        # self.max_sc_entry.insert(0, self.settings["max_safety_cars"])

        # self.start_minute_label = tk.Label(self, text="Start Minute")
        # self.start_minute_entry = tk.Entry(self)
        # self.start_minute_entry.insert(0, self.settings["start_minute"])

        # self.end_minute_label = tk.Label(self, text="End Minute")
        # self.end_minute_entry = tk.Entry(self)
        # self.end_minute_entry.insert(0, self.settings["end_minute"])

        # self.min_time_between_label = tk.Label(self, text="Minimum Time Between SC Events")
        # self.min_time_between_entry = tk.Entry(self)
        # self.min_time_between_entry.insert(0, self.settings["min_time_between"])

        # self.laps_under_sc_label = tk.Label(self, text="Laps Under Safety Car")
        # self.laps_under_sc_entry = tk.Entry(self)
        # self.laps_under_sc_entry.insert(0, self.settings["laps_under_sc"])

        # # Create a save settings button
        # self.save_button = tk.Button(self, text="Save Settings", command=self._save_settings)

        # # Create a button to generate safety car events
        # self.generate_button = tk.Button(self, text="Generate Safety Car Events", command=self.generate)

        # # Create a text box to display the generated safety car events
        # self.sc_text = tk.Text(self, height=10, width=50)

        # # Pack the widgets
        # self.min_sc_label.pack()
        # self.min_sc_entry.pack()
        # self.max_sc_label.pack()
        # self.max_sc_entry.pack()
        # self.start_minute_label.pack()
        # self.start_minute_entry.pack()
        # self.end_minute_label.pack()
        # self.end_minute_entry.pack()
        # self.min_time_between_label.pack()
        # self.min_time_between_entry.pack()
        # self.laps_under_sc_label.pack()
        # self.laps_under_sc_entry.pack()
        # self.save_button.pack()
        # self.generate_button.pack()
        # self.sc_text.pack()

    def _save_settings(self):
        # Save the settings to the config file
        self.settings["min_safety_cars"] = self.min_sc_entry.get()
        self.settings["max_safety_cars"] = self.max_sc_entry.get()
        self.settings["start_minute"] = self.start_minute_entry.get()
        self.settings["end_minute"] = self.end_minute_entry.get()
        self.settings["min_time_between"] = self.min_time_between_entry.get()
        self.settings["laps_under_sc"] = self.laps_under_sc_entry.get()

        with open("settings.ini", "w") as configfile:
            self.settings.write(configfile)

    def generate(self):
        pass