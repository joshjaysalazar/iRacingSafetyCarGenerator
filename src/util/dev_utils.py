import irsdk
import json
import pyperclip

def copy_sdk_data_to_clipboard():
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
        }
        
        pyperclip.copy(json.dumps(data, indent=4))

    finally:
        if connected:
            ir.shutdown()
