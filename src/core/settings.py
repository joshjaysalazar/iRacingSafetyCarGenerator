import configparser

class Settings:
    """Typed wrapper for application settings with type-safe property access."""
    
    def __init__(self, config_file: str = "settings.ini"):
        """Initialize settings from config file.
        
        Args:
            config_file: Path to the INI configuration file
        """
        self._config = configparser.ConfigParser()
        self._config_file = config_file
        self._config.read(config_file)
        
        # Ensure settings section exists
        if "settings" not in self._config:
            self._config.add_section("settings")
    
    def save(self) -> None:
        """Save current settings to the config file."""
        with open(self._config_file, "w") as configfile:
            self._config.write(configfile)
    
    # Random safety car settings
    @property
    def random_detector_enabled(self) -> bool:
        """Enable random safety cars."""
        return self._config["settings"].getboolean("random_detector_enabled", fallback=True)
    
    @random_detector_enabled.setter
    def random_detector_enabled(self, value: bool) -> None:
        self._config.set("settings", "random_detector_enabled", str(int(value)))
    
    @property
    def random_max_safety_cars(self) -> int:
        """Maximum random safety car occurrences."""
        return self._config["settings"].getint("random_max_safety_cars", fallback=1)
    
    @random_max_safety_cars.setter
    def random_max_safety_cars(self, value: int) -> None:
        self._config.set("settings", "random_max_safety_cars", str(value))
    
    @property
    def random_probability(self) -> float:
        """Probability for random safety car events."""
        return self._config["settings"].getfloat("random_probability", fallback=0.1)
    
    @random_probability.setter
    def random_probability(self, value: float) -> None:
        self._config.set("settings", "random_probability", str(value))
    
    @property
    def random_message(self) -> str:
        """Message for random safety car events."""
        return self._config["settings"].get("random_message", fallback="Hazard on track.")
    
    @random_message.setter
    def random_message(self, value: str) -> None:
        self._config.set("settings", "random_message", value)
    
    # Cars stopped on track settings
    @property
    def stopped_detector_enabled(self) -> bool:
        """Enable safety car for cars stopped on track."""
        return self._config["settings"].getboolean("stopped_detector_enabled", fallback=True)
    
    @stopped_detector_enabled.setter
    def stopped_detector_enabled(self, value: bool) -> None:
        self._config.set("settings", "stopped_detector_enabled", str(int(value)))
    
    @property
    def stopped_cars_threshold(self) -> int:
        """Minimum stopped cars to trigger safety car."""
        return self._config["settings"].getint("stopped_cars_threshold", fallback=2)
    
    @stopped_cars_threshold.setter
    def stopped_cars_threshold(self, value: int) -> None:
        self._config.set("settings", "stopped_cars_threshold", str(value))
    
    @property
    def stopped_message(self) -> str:
        """Message for stopped cars safety car."""
        return self._config["settings"].get("stopped_message", fallback="Cars stopped on track")
    
    @stopped_message.setter
    def stopped_message(self, value: str) -> None:
        self._config.set("settings", "stopped_message", value)
    
    # Cars off track settings
    @property
    def off_track_detector_enabled(self) -> bool:
        """Enable safety car for cars off track."""
        return self._config["settings"].getboolean("off_track_detector_enabled", fallback=True)
    
    @off_track_detector_enabled.setter
    def off_track_detector_enabled(self, value: bool) -> None:
        self._config.set("settings", "off_track_detector_enabled", str(int(value)))
    
    @property
    def off_track_cars_threshold(self) -> int:
        """Minimum off-track cars to trigger safety car."""
        return self._config["settings"].getint("off_track_cars_threshold", fallback=4)
    
    @off_track_cars_threshold.setter
    def off_track_cars_threshold(self, value: int) -> None:
        self._config.set("settings", "off_track_cars_threshold", str(value))
    
    @property
    def off_track_message(self) -> str:
        """Message for off-track cars safety car."""
        return self._config["settings"].get("off_track_message", fallback="Multiple cars off track")
    
    @off_track_message.setter
    def off_track_message(self, value: str) -> None:
        self._config.set("settings", "off_track_message", value)

    # Towing detector settings
    @property
    def towing_detector_enabled(self) -> bool:
        """Enable safety car for cars towing to pits."""
        return self._config["settings"].getboolean("towing_detector_enabled", fallback=True)

    @towing_detector_enabled.setter
    def towing_detector_enabled(self, value: bool) -> None:
        self._config.set("settings", "towing_detector_enabled", str(int(value)))

    @property
    def towing_cars_threshold(self) -> int:
        """Minimum towing cars to trigger safety car."""
        return self._config["settings"].getint("towing_cars_threshold", fallback=1)

    @towing_cars_threshold.setter
    def towing_cars_threshold(self, value: int) -> None:
        self._config.set("settings", "towing_cars_threshold", str(value))

    @property
    def towing_message(self) -> str:
        """Message for towing cars safety car."""
        return self._config["settings"].get("towing_message", fallback="Towing detected")

    @towing_message.setter
    def towing_message(self, value: str) -> None:
        self._config.set("settings", "towing_message", value)

    @property
    def towing_max_pit_entry_delta(self) -> float:
        """Maximum lap distance delta for normal pit entry (0.0-1.0)."""
        return self._config["settings"].getfloat("towing_max_pit_entry_delta", fallback=0.05)

    @towing_max_pit_entry_delta.setter
    def towing_max_pit_entry_delta(self, value: float) -> None:
        self._config.set("settings", "towing_max_pit_entry_delta", str(value))

    @property
    def towing_weight(self) -> float:
        """Weight for towing events in combined calculation."""
        return self._config["settings"].getfloat("towing_weight", fallback=2.0)

    @towing_weight.setter
    def towing_weight(self, value: float) -> None:
        self._config.set("settings", "towing_weight", str(value))

    # Race start multiplier settings
    @property
    def race_start_threshold_multiplier(self) -> float:
        """Safety car threshold multiplier for race start."""
        return self._config["settings"].getfloat("race_start_threshold_multiplier", fallback=1.0)
    
    @race_start_threshold_multiplier.setter
    def race_start_threshold_multiplier(self, value: float) -> None:
        self._config.set("settings", "race_start_threshold_multiplier", str(value))
    
    @property
    def race_start_threshold_multiplier_time_seconds(self) -> float:
        """Time in minutes that start multiplier is active."""
        return self._config["settings"].getfloat("race_start_threshold_multiplier_time_seconds", fallback=30.0)
    
    @race_start_threshold_multiplier_time_seconds.setter
    def race_start_threshold_multiplier_time_seconds(self, value: float) -> None:
        self._config.set("settings", "race_start_threshold_multiplier_time_seconds", str(value))
    
    # General race settings
    @property
    def max_safety_cars(self) -> int:
        """Maximum number of safety car events per race."""
        return self._config["settings"].getint("max_safety_cars", fallback=2)
    
    @max_safety_cars.setter
    def max_safety_cars(self, value: int) -> None:
        self._config.set("settings", "max_safety_cars", str(value))
    
    @property
    def detection_start_minute(self) -> float:
        """Earliest minute when safety car can be deployed."""
        return self._config["settings"].getfloat("detection_start_minute", fallback=0.0)
    
    @detection_start_minute.setter
    def detection_start_minute(self, value: float) -> None:
        self._config.set("settings", "detection_start_minute", str(value))
    
    @property
    def detection_end_minute(self) -> float:
        """Latest minute when safety car can be deployed."""
        return self._config["settings"].getfloat("detection_end_minute", fallback=30.0)
    
    @detection_end_minute.setter
    def detection_end_minute(self, value: float) -> None:
        self._config.set("settings", "detection_end_minute", str(value))
    
    @property
    def min_time_between_safety_cars_minutes(self) -> float:
        """Minimum time between safety car events in minutes."""
        return self._config["settings"].getfloat("min_time_between_safety_cars_minutes", fallback=3.0)
    
    @min_time_between_safety_cars_minutes.setter
    def min_time_between_safety_cars_minutes(self, value: float) -> None:
        self._config.set("settings", "min_time_between_safety_cars_minutes", str(value))
    
    @property
    def laps_under_safety_car(self) -> int:
        """Number of laps under safety car."""
        return self._config["settings"].getint("laps_under_safety_car", fallback=2)
    
    @laps_under_safety_car.setter
    def laps_under_safety_car(self, value: int) -> None:
        self._config.set("settings", "laps_under_safety_car", str(value))
    
    # Wave around settings
    @property
    def wave_arounds_enabled(self) -> bool:
        """Enable automatic wave arounds."""
        return self._config["settings"].getboolean("wave_arounds_enabled", fallback=True)
    
    @wave_arounds_enabled.setter
    def wave_arounds_enabled(self, value: bool) -> None:
        self._config.set("settings", "wave_arounds_enabled", str(int(value)))
    
    @property
    def laps_before_wave_arounds(self) -> int:
        """Number of laps before wave arounds."""
        return self._config["settings"].getint("laps_before_wave_arounds", fallback=0)

    @laps_before_wave_arounds.setter
    def laps_before_wave_arounds(self, value: int) -> None:
        self._config.set("settings", "laps_before_wave_arounds", str(value))

    @property
    def wave_around_rules_index(self) -> int:
        """Index for wave around rules selection (0=Wave lapped cars, 1=Wave ahead of class lead)."""
        return self._config["settings"].getint("wave_around_rules_index", fallback=0)

    @wave_around_rules_index.setter
    def wave_around_rules_index(self, value: int) -> None:
        self._config.set("settings", "wave_around_rules_index", str(value))

    # Proximity-based yellow flag settings
    @property
    def proximity_filter_enabled(self) -> bool:
        """Enable proximity-based yellow flags."""
        return self._config["settings"].getboolean("proximity_filter_enabled", fallback=True)
    
    @proximity_filter_enabled.setter
    def proximity_filter_enabled(self, value: bool) -> None:
        self._config.set("settings", "proximity_filter_enabled", str(int(value)))
    
    @property
    def proximity_filter_distance_percentage(self) -> float:
        """Distance threshold for proximity-based yellows."""
        return self._config["settings"].getfloat("proximity_filter_distance_percentage", fallback=0.25)
    
    @proximity_filter_distance_percentage.setter
    def proximity_filter_distance_percentage(self, value: float) -> None:
        self._config.set("settings", "proximity_filter_distance_percentage", str(value))

    # Event time window setting
    @property
    def event_time_window_seconds(self) -> float:
        """Time window in seconds to consider events for threshold checking."""
        return self._config["settings"].getfloat("event_time_window_seconds", fallback=5.0)

    @event_time_window_seconds.setter
    def event_time_window_seconds(self, value: float) -> None:
        self._config.set("settings", "event_time_window_seconds", str(value))

    # Accumulative threshold settings
    @property
    def accumulative_threshold(self) -> float:
        """Minimum combined weighted score to trigger safety car."""
        return self._config["settings"].getfloat("accumulative_threshold", fallback=7.0)

    @accumulative_threshold.setter
    def accumulative_threshold(self, value: float) -> None:
        self._config.set("settings", "accumulative_threshold", str(value))

    @property
    def off_track_weight(self) -> float:
        """Weight for off-track cars in combined calculation."""
        return self._config["settings"].getfloat("off_track_weight", fallback=2.0)

    @off_track_weight.setter
    def off_track_weight(self, value: float) -> None:
        self._config.set("settings", "off_track_weight", str(value))

    @property
    def stopped_weight(self) -> float:
        """Weight for stopped cars in combined calculation."""
        return self._config["settings"].getfloat("stopped_weight", fallback=3.0)

    @stopped_weight.setter
    def stopped_weight(self, value: float) -> None:
        self._config.set("settings", "stopped_weight", str(value))

    # Accumulative detection settings
    @property
    def accumulative_detector_enabled(self) -> bool:
        """Enable accumulative detection (weighted scoring)."""
        return self._config["settings"].getboolean("accumulative_detector_enabled", fallback=False)

    @accumulative_detector_enabled.setter
    def accumulative_detector_enabled(self, value: bool) -> None:
        self._config.set("settings", "accumulative_detector_enabled", str(int(value)))

    @property
    def accumulative_message(self) -> str:
        """Message for accumulative detection safety car."""
        return self._config["settings"].get("accumulative_message", fallback="Multiple hazards detected")

    @accumulative_message.setter
    def accumulative_message(self, value: str) -> None:
        self._config.set("settings", "accumulative_message", value)