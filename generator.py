import irsdk
import random
import configparser
import time

# Function to read settings from an ini file
def read_settings():
    config = configparser.ConfigParser()
    config.read('settings.ini')
    min_safety_cars = config.getint('settings', 'min_safety_cars')
    max_safety_cars = config.getint('settings', 'max_safety_cars')
    start_minute = config.getint('settings', 'start_minute')
    end_minute = config.getint('settings', 'end_minute')
    return min_safety_cars, max_safety_cars, start_minute, end_minute

# Function to connect to iRacing
def connect_to_iracing():
    ir = pyirsdk.IRSDK()
    try:
        ir.startup()
        print("Connected to iRacing.")
    except Exception as e:
        print(f"Error connecting to iRacing: {e}")
    return ir

# Function to monitor race status
def wait_for_green_flag(ir):
    while True:
        ir.freeze_var_buffer_latest()
        if ir['SessionFlags'] & irsdk.Flags.green:  # Check if the green flag is on
            print("Race has started. Green flag is on.")
            break
        time.sleep(1)

# Function to generate random safety car events
def generate_safety_car_events(min_safety_cars, max_safety_cars, start_minute, end_minute, race_length):
    number_of_safety_cars = random.randint(min_safety_cars, max_safety_cars)
    safety_car_times = sorted([random.randint(start_minute * 60, end_minute * 60) for _ in range(number_of_safety_cars)])
    return safety_car_times

# Main program
def main():
    min_safety_cars, max_safety_cars, start_minute, end_minute = read_settings()
    ir = connect_to_iracing()
    wait_for_green_flag(ir)
    
    # Placeholder for race length in seconds (to be determined)
    race_length = 3600  # Example: 1 hour race
    safety_car_events = generate_safety_car_events(min_safety_cars, max_safety_cars, start_minute, end_minute, race_length)
    print("Safety Car Events Times (in seconds):", safety_car_events)

    # Add logic to handle safety car events during the race

if __name__ == "__main__":
    main()
