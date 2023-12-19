import configparser
import random
import time

import irsdk


# Read settings file
config = configparser.ConfigParser()
config.read('settings.ini')
min_sc = config.getint('settings', 'min_safety_cars')
max_sc = config.getint('settings', 'max_safety_cars')
start_minute = config.getfloat('settings', 'start_minute')
end_minute = config.getfloat('settings', 'end_minute')
min_time_between = config.getfloat('settings', 'min_time_between')

# Randomly determine number of safety car events
number_sc = random.randint(min_sc, max_sc)

# Randomly determine safety car event times in minutes
sc_times = []
if number_sc > 0:
    for i in range(number_sc - 1):
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
        sc_times.append(random.randint(start, end))

# Connect to iRacing
ir = irsdk.IRSDK()
try:
    ir.startup()
    print("Connected to iRacing.")
except Exception as e:
    print(f"Error connecting to iRacing: {e}")

# Wait for green flag
while True:
    ir.freeze_var_buffer_latest()
    if ir["SessionFlags"] & ir.Flags.green:  # Check if the green flag is on
        print("Race has started. Green flag is on.")
        break
    time.sleep(1)

# Loop through safety car events