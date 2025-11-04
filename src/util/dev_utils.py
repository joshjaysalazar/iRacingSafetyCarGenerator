import irsdk
import json
import pyperclip
import os
import re
import csv
from datetime import datetime
from collections import defaultdict

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

def parse_log_events_to_csv(log_file_path):
    """Parse a single log file to extract off track and stopped car events and generate CSV.
    
    This function searches through a log file to find events related to off track 
    incidents and stopped cars, then generates a CSV file with timestamps and event 
    counts for graphing in Google Docs.
    
    Args:
        log_file_path (str): Path to the log file to parse
        
    Returns:
        str: Path to the generated CSV file
    """
    if not os.path.exists(log_file_path):
        raise FileNotFoundError(f"Log file '{log_file_path}' not found")
    
    # Generate CSV filename by replacing .log with .csv
    csv_file_path = log_file_path.rsplit('.', 1)[0] + '.csv'
    
    # Dictionary to store events by timestamp
    events_by_time = defaultdict(lambda: {"off_track": 0, "stopped": 0})
    
    # Pattern to match threshold checking log entries with events_dict
    threshold_pattern = re.compile(r'Checking threshold, events_dict=\{<ThresholdCheckerEventTypes\.OFF_TRACK.*?>\: (\{[^}]*\}), <ThresholdCheckerEventTypes\.STOPPED.*?>\: (\{[^}]*\})\}')
    
    print(f"Processing {log_file_path}...")
    
    try:
        with open(log_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                # Extract timestamp from log line
                timestamp_match = re.match(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                if not timestamp_match:
                    continue
                
                timestamp_str = timestamp_match.group(1)
                
                # Check for threshold checking logs with events_dict
                threshold_match = threshold_pattern.search(line)
                if threshold_match:
                    off_track_dict_str = threshold_match.group(1)
                    stopped_dict_str = threshold_match.group(2)
                    
                    # Count unique drivers for off track (number of keys in dict)
                    # Empty dict is "{}", non-empty will have driver IDs as keys
                    off_track_count = 0 if off_track_dict_str == '{}' else len([x for x in off_track_dict_str.split(',') if ':' in x])
                    
                    # Count unique drivers for stopped cars
                    stopped_count = 0 if stopped_dict_str == '{}' else len([x for x in stopped_dict_str.split(',') if ':' in x])
                    
                    # Record all threshold checking events, including when counts are 0
                    events_by_time[timestamp_str]["off_track"] = off_track_count
                    events_by_time[timestamp_str]["stopped"] = stopped_count
                    
    except Exception as e:
        raise Exception(f"Error reading log file: {e}")
    
    if not events_by_time:
        # Create an empty CSV with headers if no events found
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['Timestamp', 'Date', 'Time', 'Off Track Events', 'Stopped Car Events', 'Total Events'])
        print("No events found in log file, created empty CSV with headers")
        return csv_file_path
    
    # Sort events by timestamp
    sorted_events = sorted(events_by_time.items())
    
    # Write to CSV
    try:
        with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow(['Timestamp', 'Date', 'Time', 'Off Track Events', 'Stopped Car Events', 'Total Events'])
            
            # Write data rows
            for timestamp_str, events in sorted_events:
                try:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                    date_str = dt.strftime('%Y-%m-%d')
                    time_str = dt.strftime('%H:%M:%S')
                    off_track_count = events["off_track"]
                    stopped_count = events["stopped"]
                    total_count = off_track_count + stopped_count
                    
                    writer.writerow([
                        timestamp_str,
                        date_str,
                        time_str,
                        off_track_count,
                        stopped_count,
                        total_count
                    ])
                except ValueError as e:
                    print(f"Error parsing timestamp {timestamp_str}: {e}")
                    continue
        
        # Print summary statistics
        total_off_track = sum(events["off_track"] for events in events_by_time.values())
        total_stopped = sum(events["stopped"] for events in events_by_time.values())
        
        print(f"Successfully created {csv_file_path}")
        print(f"Found {len(sorted_events)} time points with events")
        print(f"Summary:")
        print(f"  Total Off Track Events: {total_off_track}")
        print(f"  Total Stopped Car Events: {total_stopped}")
        print(f"  Total Events: {total_off_track + total_stopped}")
        
        return csv_file_path
        
    except Exception as e:
        raise Exception(f"Error writing CSV file: {e}")