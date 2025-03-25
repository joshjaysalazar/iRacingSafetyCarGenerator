import logging
import time

from interactions import iracing_window
from interactions import mock_window

logger = logging.getLogger(__name__)

def WindowFactory(arguments):
    if arguments.disable_window_interactions:
        return mock_window.MockWindow()
    return iracing_window.IRacingWindow()

class CommandSender:
    """ Sends commands to the iRacing application. """

    def __init__(self, arguments, irsdk):
        """Initialize the CommandSender object.

        Args:
            arguments: arguments passed to the application during startup.
            irsdk: a reference to an irSDK instance.
        """
        logger.info("Initializing CommandSender")
        self.iracing_window = WindowFactory(arguments)
        self.irsdk = irsdk


    def connect(self):
        """ Find the iRacing application window and keep a handle. """
        self.iracing_window.connect()
    

    def send_command(self, command):
        """ Sends the provided command to the iRacing application window.

        Args:
            command: The command to send. Should include the {ENTER} character!
        """
        logger.info(f"Sending command: {command}")

        self.iracing_window.focus()
        self.irsdk.chat_command(1)
        self.iracing_window.send_message(f"{command}{{ENTER}}")

    def send_commands(self, commands, delay = 0.5):
        """ Sends the list of commands in order with the provided delay.
        
        Args:
            commands: List of commands to send. Should include the {ENTER} character!
        """
        for command in commands:
            self.send_command(command)
            if delay > 0:
                logger.debug(f"Adding delay of: {delay}")
                time.sleep(delay)

