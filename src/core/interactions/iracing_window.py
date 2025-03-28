import importlib
import logging

logger = logging.getLogger(__name__)

class IRacingWindow():
    """ Used to keep a reference to your iRacing application window to send events. """
    def __init__(self):
        logger.debug("Instantiating IRacingWindow, importing pywinauto.application")
        self.ir_window = None
        self.Application = importlib.import_module('pywinauto.application').Application

    def connect(self):
        """ Find the iRacing application window and keep a handle. """
        logger.debug("Connect to the iRacing application window and save ref for future interactions")
        self.ir_window = self.Application().connect(
            title="iRacing.com Simulator"
        ).top_window()

    def focus(self):
        """ Bring the iRacing application window into focus. """
        logger.debug("Set focus to iRacing Application window")
        self.ir_window.set_focus()

    def send_message(self, message):
        """ Send input in message to the iRacing application window. 
        
        Args:
            message: The message to send.
        """
        logger.debug(f"Sending message to iRacing window: {message}")
        self.ir_window.type_keys(
            message,
            with_spaces=True)