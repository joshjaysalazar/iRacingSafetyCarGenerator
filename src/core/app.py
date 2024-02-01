import configparser
import tkinter as tk


class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # Load settings from config file
        self.settings = self._read_config()

        # Set window properties
        self.title("iRacing Safety Car Generator")

    def _read_config(self, file="settings.ini"):
        # Initialize configparser
        config = configparser.ConfigParser()
        config.read(file)

        # Create a dictionary to store the settings
        settings = {
            "min_safety_cars": config.getint("settings", "min_safety_cars"),
            "max_safety_cars": config.getint("settings", "max_safety_cars"),
            "start_minute": config.getfloat("settings", "start_minute"),
            "end_minute": config.getfloat("settings", "end_minute"),
            "min_time_between": config.getfloat("settings", "min_time_between"),
            "laps_under_sc": config.getint("settings", "laps_under_sc")
        }

        # Return the settings
        return settings

