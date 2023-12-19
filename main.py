import configparser
import os
import random
import time

import irsdk
import pyautogui


# Read settings file
config = configparser.ConfigParser()
config.read('settings.ini')
min_sc = config.getint('settings', 'min_safety_cars')
max_sc = config.getint('settings', 'max_safety_cars')
start_minute = config.getfloat('settings', 'start_minute')
end_minute = config.getfloat('settings', 'end_minute')
min_time_between = config.getfloat('settings', 'min_time_between')
print("Loaded settings.")

# Randomly determine number of safety car events
number_sc = random.randint(min_sc, max_sc)

# Randomly determine safety car event times in minutes
sc_times = []
if number_sc > 0:
    for i in range(number_sc):
        # If first safety car event, choose a random time between start and end
        if i == 0:
            start = start_minute
            end = end_minute
        # If not, choose a random time between the previous SC event and the end
        else:
            # If there's not enough time left for another SC event, break
            if sc_times[i - 1] + min_time_between > end_minute:
                break
            start = sc_times[i - 1] + min_time_between
            end = end_minute
        sc_times.append(random.uniform(start, end))
print("Generated safety car event times.")

# Connect to iRacing
ir = irsdk.IRSDK()

# Attempt to connect and tell user if successful
if ir.startup():
    print("Connected to iRacing.")
    print("Be sure to click on the iRacing window to give it focus!")
else:
    print(f"Error connecting to iRacing.")
    os.system("pause")
    exit()

# Wait for green flag
print("Waiting for green flag...")
while True:
    if ir["SessionFlags"] & irsdk.Flags.green:
        start_time = ir["SessionTime"]
        print("Race has started. Green flag is out.")
        print("Waiting for safety car events...")
        break

    # Wait 1 second before checking again
    time.sleep(1)

# Loop through safety car events
while True:
    # If there are no more safety car events, break
    if len(sc_times) == 0:
        break
    # If the current time is past the next safety car event, trigger it
    if ir["SessionTime"] > start_time + (sc_times[0] * 60):
        print(f"Safety car event triggered at {ir['SessionTime']}")
        ir.chat_command(1)
        time.sleep(0.05)
        pyautogui.write("!yellow", interval = 0.01)
        time.sleep(0.05)
        pyautogui.press("enter")

        # Remove the safety car event from the list
        sc_times.pop(0)
    
    # Wait 1 second before checking again
    time.sleep(1)

# All safety car events have been triggered
print("All safety car events triggered. Exiting...")

# Disconnect from iRacing
ir.shutdown()

# Pause before exiting
os.system("pause")