import irsdk
import json
import pyperclip

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
        
        lap_list = ir["CarIdxLap"]
        lap_distance_list = ir["CarIdxLapDistPct"]
        total_distance = [t[0] + t[1] for t in zip(lap_list, lap_distance_list)]
        
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
            "total_distance_computed": total_distance,
        }
        
        pyperclip.copy(json.dumps(data, indent=4))

    finally:
        if connected:
            ir.shutdown()
