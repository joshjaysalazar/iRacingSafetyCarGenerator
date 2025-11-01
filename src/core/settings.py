import configparser
from typing import Optional


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
    def random(self) -> bool:
        """Enable random safety cars."""
        return self._config["settings"].getboolean("random", fallback=True)
    
    @random.setter
    def random(self, value: bool) -> None:
        self._config.set("settings", "random", str(int(value)))
    
    @property
    def random_max_occ(self) -> int:
        """Maximum random safety car occurrences."""
        return self._config["settings"].getint("random_max_occ", fallback=3)
    
    @random_max_occ.setter
    def random_max_occ(self, value: int) -> None:
        self._config.set("settings", "random_max_occ", str(value))
    
    @property
    def random_prob(self) -> float:
        """Probability for random safety car events."""
        return self._config["settings"].getfloat("random_prob", fallback=0.1)
    
    @random_prob.setter
    def random_prob(self, value: float) -> None:
        self._config.set("settings", "random_prob", str(value))
    
    @property
    def random_message(self) -> str:
        """Message for random safety car events."""
        return self._config["settings"].get("random_message", fallback="Random safety car")
    
    @random_message.setter
    def random_message(self, value: str) -> None:
        self._config.set("settings", "random_message", value)
    
    # Cars stopped on track settings
    @property
    def stopped(self) -> bool:
        """Enable safety car for cars stopped on track."""
        return self._config["settings"].getboolean("stopped", fallback=True)
    
    @stopped.setter
    def stopped(self, value: bool) -> None:
        self._config.set("settings", "stopped", str(int(value)))
    
    @property
    def stopped_min(self) -> int:
        """Minimum stopped cars to trigger safety car."""
        return self._config["settings"].getint("stopped_min", fallback=2)
    
    @stopped_min.setter
    def stopped_min(self, value: int) -> None:
        self._config.set("settings", "stopped_min", str(value))
    
    @property
    def stopped_message(self) -> str:
        """Message for stopped cars safety car."""
        return self._config["settings"].get("stopped_message", fallback="Cars stopped on track")
    
    @stopped_message.setter
    def stopped_message(self, value: str) -> None:
        self._config.set("settings", "stopped_message", value)
    
    # Cars off track settings
    @property
    def off(self) -> bool:
        """Enable safety car for cars off track."""
        return self._config["settings"].getboolean("off", fallback=True)
    
    @off.setter
    def off(self, value: bool) -> None:
        self._config.set("settings", "off", str(int(value)))
    
    @property
    def off_min(self) -> int:
        """Minimum off-track cars to trigger safety car."""
        return self._config["settings"].getint("off_min", fallback=3)
    
    @off_min.setter
    def off_min(self, value: int) -> None:
        self._config.set("settings", "off_min", str(value))
    
    @property
    def off_message(self) -> str:
        """Message for off-track cars safety car."""
        return self._config["settings"].get("off_message", fallback="Cars off track")
    
    @off_message.setter
    def off_message(self, value: str) -> None:
        self._config.set("settings", "off_message", value)

    # Time range setting
    @property
    def time_range(self) -> float:
        """Time range in minutes to consider cars off or stopped."""
        return self._config["settings"].getfloat("time_range", fallback=5.0)
    
    @time_range.setter
    def time_range(self, value: float) -> None:
        self._config.set("settings", "time_range", str(value))
    
    # Race start multiplier settings
    @property
    def start_multi_val(self) -> float:
        """Safety car threshold multiplier for race start."""
        return self._config["settings"].getfloat("start_multi_val", fallback=2.0)
    
    @start_multi_val.setter
    def start_multi_val(self, value: float) -> None:
        self._config.set("settings", "start_multi_val", str(value))
    
    @property
    def start_multi_time(self) -> float:
        """Time in minutes that start multiplier is active."""
        return self._config["settings"].getfloat("start_multi_time", fallback=10.0)
    
    @start_multi_time.setter
    def start_multi_time(self, value: float) -> None:
        self._config.set("settings", "start_multi_time", str(value))
    
    # General race settings
    @property
    def max_safety_cars(self) -> int:
        """Maximum number of safety car events per race."""
        return self._config["settings"].getint("max_safety_cars", fallback=5)
    
    @max_safety_cars.setter
    def max_safety_cars(self, value: int) -> None:
        self._config.set("settings", "max_safety_cars", str(value))
    
    @property
    def start_minute(self) -> float:
        """Earliest minute when safety car can be deployed."""
        return self._config["settings"].getfloat("start_minute", fallback=5.0)
    
    @start_minute.setter
    def start_minute(self, value: float) -> None:
        self._config.set("settings", "start_minute", str(value))
    
    @property
    def end_minute(self) -> float:
        """Latest minute when safety car can be deployed."""
        return self._config["settings"].getfloat("end_minute", fallback=120.0)
    
    @end_minute.setter
    def end_minute(self, value: float) -> None:
        self._config.set("settings", "end_minute", str(value))
    
    @property
    def min_time_between(self) -> float:
        """Minimum time between safety car events in minutes."""
        return self._config["settings"].getfloat("min_time_between", fallback=15.0)
    
    @min_time_between.setter
    def min_time_between(self, value: float) -> None:
        self._config.set("settings", "min_time_between", str(value))
    
    @property
    def laps_under_sc(self) -> int:
        """Number of laps under safety car."""
        return self._config["settings"].getint("laps_under_sc", fallback=3)
    
    @laps_under_sc.setter
    def laps_under_sc(self, value: int) -> None:
        self._config.set("settings", "laps_under_sc", str(value))
    
    # Wave around settings
    @property
    def wave_arounds(self) -> bool:
        """Enable automatic wave arounds."""
        return self._config["settings"].getboolean("wave_arounds", fallback=True)
    
    @wave_arounds.setter
    def wave_arounds(self, value: bool) -> None:
        self._config.set("settings", "wave_arounds", str(int(value)))
    
    @property
    def laps_before_wave_arounds(self) -> int:
        """Number of laps before wave arounds."""
        return self._config["settings"].getint("laps_before_wave_arounds", fallback=2)
    
    @laps_before_wave_arounds.setter
    def laps_before_wave_arounds(self, value: int) -> None:
        self._config.set("settings", "laps_before_wave_arounds", str(value))
    
    # Proximity-based yellow flag settings
    @property
    def proximity_yellows(self) -> bool:
        """Enable proximity-based yellow flags."""
        return self._config["settings"].getboolean("proximity_yellows", fallback=True)
    
    @proximity_yellows.setter
    def proximity_yellows(self, value: bool) -> None:
        self._config.set("settings", "proximity_yellows", str(int(value)))
    
    @property
    def proximity_yellows_distance(self) -> float:
        """Distance threshold for proximity-based yellows."""
        return self._config["settings"].getfloat("proximity_yellows_distance", fallback=0.3)
    
    @proximity_yellows_distance.setter
    def proximity_yellows_distance(self, value: float) -> None:
        self._config.set("settings", "proximity_yellows_distance", str(value))

    @property
    def combined_min(self) -> float:
        """Minimum combined off and stopped cars to trigger safety car."""
        return self._config["settings"].getfloat("combined_min", fallback=7.0)
    
    @combined_min.setter
    def combined_min(self, value: float) -> None:
        self._config.set("settings", "combined_min", str(value))

    @property
    def off_weight(self) -> float:
        """Weight for off-track cars in combined calculation."""
        return self._config["settings"].getfloat("off_weight", fallback=2.0)
    
    @off_weight.setter
    def off_weight(self, value: float) -> None:
        self._config.set("settings", "off_weight", str(value))

    @property
    def stopped_weight(self) -> float:
        """Weight for stopped cars in combined calculation."""
        return self._config["settings"].getfloat("stopped_weight", fallback=3.0)
