import random

from core.detection.detector_common_types import DetectionResult, DetectorEventTypes, DetectorState


class RandomDetector:
    def __init__(self, chance: float, start_minute: float, end_minute: float, max_occurrences: int = float('inf')):
        """Initialize the RandomDetector.

        Args:
            chance (float): The probability of triggering a random event throughout the race.
            start_minute (int): The minute at which the detector starts checking for random events.
            end_minute (int): The minute at which the detector stops checking for random events.
            max_occurrences (int): Maximum number of random events allowed.
        """
        self.chance = chance
        self.start_minute = start_minute
        self.end_minute = end_minute
        self.max_occurrences = max_occurrences
        self.len_of_window = (end_minute - start_minute) * 60

    def should_run(self, state: DetectorState) -> bool:
        """Check if this detector should run given current state."""
        # Check time bounds
        if not (self.start_minute * 60 <= state.current_time_since_start <= self.end_minute * 60):
            return False
        
        # Check occurrence limit
        current_count = state.safety_car_event_counts.get(DetectorEventTypes.RANDOM, 0)
        if current_count >= self.max_occurrences:
            return False
            
        return True

    def detect(self):
        """Used to generate random safety cars.

        Returns:
            DetectionResult: Result indicating if a random event should be triggered.
        """
        if self.len_of_window <= 0:
            return DetectionResult(DetectorEventTypes.RANDOM, detected_flag=False)
        
        # Generate a random number between 0 and 1
        rng = random.random()

        # Calculate the chance of triggering a safety car event this check
        current_chance = 1 - ((1 - self.chance) ** (1 / self.len_of_window))

        # If the random number is less than or equal to the chance, trigger
        result = rng <= current_chance
        return DetectionResult(DetectorEventTypes.RANDOM, detected_flag=result)
