import logging
import time
import configparser

logger = logging.getLogger(__name__)

class CommandSender:
    """ Sends commands to the iRacing application. """

    def __init__(self, iracing_window, irsdk):
        """Initialize the CommandSender object.

        Args:
            iracing_window: The window object used to interact with the iRacing application.
            irsdk: A reference to an irSDK instance.
        """
        logger.info("Initializing CommandSender")
        self.iracing_window = iracing_window
        self.irsdk = irsdk

        self.settings = configparser.ConfigParser()
        self.settings.read("settings.ini")
        self.var_dry_run=bool(self.settings["settings"].getboolean("dry_run"))

    def connect(self):
        """ Find the iRacing application window and keep a handle. """
        self.iracing_window.connect()
    

    def send_command(self, command, delay = 0.5):
        """ Sends the provided command to the iRacing application window.

        Args:
            command: The command to send. Should NOT include the {ENTER} character!
        """
        logger.info(f"Sending command: {command}")

        if self.var_dry_run:
            return

        self.iracing_window.focus()
        self.irsdk.chat_command(1)
        if delay > 0:
            logger.debug(f"Adding delay between chat command and send_message of: {delay}")
            time.sleep(delay)
        self.iracing_window.send_message(f"{command}{{ENTER}}")

    def send_commands(self, commands, delay = 0.5):
        """ Sends the list of commands in order with the provided delay.
        
        Args:
            commands: List of commands to send. Should NOT include the {ENTER} character!
            delay: How much delay to add (in seconds) between each command
        """
        if self.var_dry_run:
            return
    
        for command in commands:
            self.send_command(command, delay)

