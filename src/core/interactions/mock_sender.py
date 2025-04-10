import logging
import time

logger = logging.getLogger(__name__)

class MockSender:
    """ Mocks sending commands to the iRacing application. """

    def __init__(self):
        """Initialize the MockSender object.

        Args: None
        """
        logger.debug("Initializing MockSender")

    def connect(self):
        """ Find the iRacing application window and keep a handle. """
        return

    def send_command(self, command, delay = 0.5):
        """ Sends the provided command to the iRacing application window.

        Args:
            command: The command to send. Should NOT include the {ENTER} character!
        """
        logger.debug(f"Sending command: {command}")

        if delay > 0:
            logger.debug(f"Adding delay between chat command and send_message of: {delay}")
            time.sleep(delay)

    def send_commands(self, commands, delay = 0.5):
        """ Sends the list of commands in order with the provided delay.
        
        Args:
            commands: List of commands to send. Should NOT include the {ENTER} character!
            delay: How much delay to add (in seconds) between each command
        """
        for command in commands:
            self.send_command(command, delay)

