import logging

logger = logging.getLogger(__name__)

class MockWindow():
    """ We are mocking the iRacing instance when we pass arg --disable-window-interactions. """
    def __init__(self):
        logger.debug("Instantiating MockWindow")
        
    def connect(self):
        logger.debug("Connect to the iRacing application window and save ref for future interactions")
        
    def focus(self):
        logger.debug("Set focus to iRacing Application window")
        
    def send_message(self, message):
        logger.debug(f"Sending message to iRacing window: {message}")