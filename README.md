# iRacing Safety Car Generator

This script is designed to trigger safety car events in iRacing at random intervals during a race. It reads settings from a configuration file and connects to iRacing to trigger safety car events as generated.

## Usage

1. Make sure you have Python 3.x installed on your system.

2. Install the required libraries by running the following command:

   ```bash
   pip install irsdk pyautogui
   ```

3. You can use the default `settings.ini` file provided in the repo, or create your own with the following content:

   ```ini
   [settings]
   # Minimum number of safety cars to appear during the race
   min_safety_cars = 0

   # Maximum number of safety cars to appear during the race
   max_safety_cars = 2

   # Start minute for possible safety car appearance
   # This is the earliest time a safety car can appear in the race, in minutes
   start_minute = 5

   # End minute for possible safety car appearance
   # This is the latest time a safety car can appear in the race, in minutes
   end_minute = 40

   # Minimum amount of time between safety car appearances
   # This is the minimum amount of time between safety car appearances, in minutes
   min_time_between = 10
   ```

   You can adjust these settings to your preferences.

4. To run the script, double-click on `main.py`. The script should be run while cars are gridding for the race to ensure it doesn't start counting down time too early!

5. Make sure to click on the iRacing window to give it focus.

## License

This script is licensed under the [GNU General Public License Version 3](https://www.gnu.org/licenses/gpl-3.0.html).

## Author

This script was created by [Joshua Abbott Salazar](https://github.com/joshjaysalazar).

If you encounter any issues or have questions, please [report them on GitHub](https://github.com/joshjaysalazar/iRacing-Safety-Car-Trigger/issues).
