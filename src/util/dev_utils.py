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
    """This util was written to test the limits of iRacing receiving chat commands. We 
    noticed if delays between messages were too short, iRacing would drop some of the 
    messages, which is detrimental to a lot of our procedures.
    Testing showed that with a delay of 0.1 seconds, we would see a drop after every 
    16th message. This was resolved with a 0.2 second delay, so we are using 0.5 seconds 
    in our application to be safe.
    
    Other notes:
        - Performance was worse when sitting in the car than when just in the garage view.
        - We moved the delay until after the chat command was sent, which seemed to help.
    """
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
        command_sender.connect()
        
        # Uncomment for sending regular chat commands
        # for i in range(1, 100):
        #     command_sender.send_command(f"Test Command {i}", 0.5)
        #     print(f"Sent command: Test Command {i}")
        
        cars_to_wave = []
        for driver in ir["DriverInfo"]["Drivers"]:
            cars_to_wave.append(driver["CarNumber"])
            
        for car in cars_to_wave:
            command_sender.send_command(f"!w {car}")
            print(f"!w {car}")

    finally:
        if connected:
            ir.shutdown()