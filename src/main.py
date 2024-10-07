from datetime import datetime
import logging
import os

from core.app import App


def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    # Get current datetime formatted as a string
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Set up logging
    logging.basicConfig(
        filename=f"logs/{current_datetime}.log",
        filemode="w",
        format="%(asctime)s (%(module)s.py) [%(levelname)s] %(message)s",
        level=logging.DEBUG
    )

    # Log the start of the program
    logging.info("Program started")

def main():
    """Main function for the safety car generator."""
    # Set up logging
    setup_logging()

    # Create and run the app
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()