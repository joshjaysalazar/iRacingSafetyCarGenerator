from core.interactions import command_sender
from core.interactions import iracing_window
from core.interactions import mock_window
from core.interactions import mock_sender

def WindowFactory(arguments):
    """ Create an IRacingWindow instance, possibly a mock one, based on the provided arguments.

    Args:
        arguments: Launch arguments indicating if we want to disable window interactions.

    Returns:
        IRacingWindow: An instance of IRacingWindow or MockWindow based on the arguments.
    """
    if arguments and arguments.disable_window_interactions:
        return mock_window.MockWindow()
    return iracing_window.IRacingWindow()

def CommandSenderFactory(arguments, ir):
    """ Create a CommandSender instance, possibly a mock one, based on the provided arguments.

    Args:
        arguments: Launch arguments indicating if we want to use a mock sender or not.
        ir (irSDK): An instance of irSDK to used for interacting with iRacing.

    Returns:
        CommandSender: An instance of CommandSender or MockSender based on the arguments.
    """
    if arguments and arguments.dry_run:
        return mock_sender.MockSender()
    
    iracing_window = WindowFactory(arguments)
    return command_sender.CommandSender(iracing_window, ir)