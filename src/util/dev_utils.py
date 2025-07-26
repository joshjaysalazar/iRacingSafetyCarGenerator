import irsdk
import json
import pyperclip

from core.interactions.interaction_factories import CommandSenderFactory

def copy_sdk_data_to_clipboard():
    """Takes a snapshot of data provided by the SDK and copies it to your clipboard
    
    Args: 
        None
    """
    ir = irsdk.IRSDK()
    connected = False
    try:
        if not ir.startup():
            pyperclip.copy("Could not connect through the SDK")
            return
        
        connected = True
        
        data = {
            "SessionNum": ir["SessionNum"],
            "SessionInfo": ir["SessionInfo"],
            "SessionFlags": ir["SessionFlags"],
            "DriverInfo": ir["DriverInfo"],
            "CarIdxLap": ir["CarIdxLap"],
            "CarIdxLapDistPct": ir["CarIdxLapDistPct"],
            "CarIdxClass": ir["CarIdxClass"],
            "CarIdxOnPitRoad": ir["CarIdxOnPitRoad"],
            "CarIdxTrackSurface": ir["CarIdxTrackSurface"],
        }
        
        pyperclip.copy(json.dumps(data, indent=4))

    finally:
        if connected:
            ir.shutdown()

def send_test_commands():
    ir = irsdk.IRSDK()
    connected = False
    try:
        if not ir.startup():
            print("Could not connect through the SDK")
            return
        connected = True

        arguments = lambda: None
        arguments.dry_run = False
        arguments.disable_window_interactions = False

        command_sender = CommandSenderFactory(arguments, ir) # type: ignore
        for i in range(1, 60):
            command_sender.send_command(f"Test Command {i}", 1.0)
            print(f"Sent command: Test Command {i}")

    finally:
        if connected:
            ir.shutdown()