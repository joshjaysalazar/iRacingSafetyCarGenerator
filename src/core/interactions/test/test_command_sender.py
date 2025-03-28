import pytest
from unittest.mock import Mock, call 

from core.interactions.command_sender import CommandSender

@pytest.fixture
def command_sender():
    return CommandSender(iracing_window=Mock(), irsdk=Mock())

def test_send_command(command_sender):
    # This is not a very interesting test as it covers implementation details, but we want to assert that we at least
    # sent a chat command through the SDK to initiate a chat and then sent the actual message ending with an {ENTER}.
    command_sender.send_command("!y throwing yellows for test", delay=0.01)
    command_sender.irsdk.chat_command.assert_called_once_with(1)
    command_sender.iracing_window.send_message.assert_called_once_with(f"!y throwing yellows for test{{ENTER}}")

def test_send_commands(command_sender):
    command_sender.send_commands(['!y throw it', '!y another?'], delay=0.01)
    command_sender.irsdk.chat_command.assert_has_calls([call(1), call(1)])
    command_sender.iracing_window.send_message.assert_has_calls([
        call(f"!y throw it{{ENTER}}"),
        call(f"!y another?{{ENTER}}"),
    ])