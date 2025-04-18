from datetime import datetime
import logging
import logging.config
import json
import os

from core.app import App


def setup_logging():
    """Set up logging configuration."""
    # Create logs directory if it doesn't exist
    if not os.path.exists("logs"):
        os.makedirs("logs")

    logger = logging.getLogger(__name__)

    # Configure logging
    with open("logging.json") as logging_conf_file:
        logging_conf = json.load(logging_conf_file)

    # Dynamically set log file name to current time
    current_datetime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    logfile = logging_conf["handlers"]["file"]["filename"]
    logging_conf["handlers"]["file"]["filename"] = logfile.replace("{current_datetime}", current_datetime)

    logging.config.dictConfig(logging_conf)

    # Log the start of the program
    logger.info("Program started")

def parse_arguments():
    import argparse
    parser = argparse.ArgumentParser(
        prog='iRacingSafetyCarGenerator',
        description='Trigger automated safety car events in iRacing')
    parser.add_argument('-dwi', '--disable-window-interactions', action='store_true')
    parser.add_argument('-dev', '--developer-mode', action='store_true')
    parser.add_argument('-dry', '--dry-run', action='store_true')
    args = parser.parse_args()
    
    return args

def main(arguments):
    """Main function for the safety car generator."""
    # Set up logging
    setup_logging()

    # Try to create and run the app, and log exceptions
    try:
        app = App(arguments)
        app.mainloop()
    except Exception as e:
        logging.exception("A fatal error has occurred")
        raise e

if __name__ == "__main__":
    arguments = parse_arguments()
    main(arguments)