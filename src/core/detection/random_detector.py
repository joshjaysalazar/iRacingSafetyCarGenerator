import random

class RandomDetector:
    def __init__(self, chance: float, start_minute: int, end_minute: int):
        """Initialize the RandomDetector.

        Args:
            chance (float): The probability of triggering a random event throughout the race.
            start_minute (int): The minute at which the detector starts checking for random events.
            end_minute (int): The minute at which the detector stops checking for random events.
        """
        self.chance = chance
        self.len_of_window = (end_minute - start_minute) * 60

    def detect(self):
        """Used to generate random safety cars.

        Returns:
            bool: True if a random event should be triggered, False otherwise.
        """
        if self.len_of_window <= 0:
            return False
        
        # Generate a random number between 0 and 1
        rng = random.random()

        # Calculate the chance of triggering a safety car event this check
        current_chance = 1 - ((1 - self.chance) ** (1 / self.len_of_window))

        # If the random number is less than or equal to the chance, trigger
        return rng <= current_chance
