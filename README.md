# iRacing Safety Car Generator

This program is designed to trigger safety car events in iRacing with more control than the built-in automatic yellows in iRacing, with adjustable settings.

![Screenshot of the main window](screenshot.png)

## Usage

1. Set your settings in the applicaiton window, then click the `Save Settings` button. This will write your settings to a file and load them back up next time you launch the app.

2. Launch your iRacing simulator session.

3. Once in the simulator, click the `Start SC Generator` button. The app should indicate it is "Connected to iRacing".

4. The app will wait for the race to start and then monitor for any of the incident thresholds to be met to throw a Safety Car event.

5. Important: do not use chat while the generator is running as it uses automated chat inputs to send commands to the simulator. When yellows are thrown, also make sure to not alt-tab around your running programs as iRacing will need to maintain focus to send the commands.

## Inner workings of the generator (aka developer documentation)

The desciptions below go into the nitty gritty of how the app functions and is documented to help users and other developers understand some of the mechanics utilized to make the app work around some of the SDK limitations.

### High level execution

At a high level, the app waits for the race to start, then checks against all conditions as configured in the app, looping approximately every second. "Approximately" because we wait for a second at the end of a loop, but the loop itself obviously also takes some time.

Steps:
* Update the latest information on all drivers
* Check if we are in an eligible window to throw a Safety Car
* Check the thresholds set for random events, stopped cars and offtrack cars
* If any of the thresholds are met, start the Safety Car procedure
* After the procedure, start looping again

### Waiting for green

* Waits for the race session to begin
* Waits for the green flag to be thrown
* Note that in its current iteration, the app will not work when started _after_ the green flag is shown.

### Driver updates

* On each iteration, we update all of the info we track of all drivers
* Before doing so, we keep a copy of the current information so that we can look at the delta
* The information gathered is:
    * Laps completed
    * The current lap distance (as a fraction of the total lap - _To be confirmed_)
    * The surface the car is on (on or off track, pit, etc.)

### Eligible Safety Car window

**Start and end time**: The start time of the race is recorded when the green flag is shown. Safety cars will only be thrown between the start ("Earliest possible minute") and end ("Latest possible minute") time.

**Time since last Safety Car**: Safety Cars will not be thrown when the last Safety Car occurred within the set "Minimum minutes between" time. Note that this time is currently recorded _at the start_ of a Safety Car event, not when it ends.

**Max Safety Car events**: When the "Maximum safety cars" has been reached, the app stops monitor for Safety Car events.

### Random events

We generate a random number and then check if that number is smaller than the odds of the event occurring at any second. Takes into account the overall window length.

### Stopped cars events

* For each driver, we check their laps completed and current lap distance to calculated their total distance. Note: Based on the logic, I believe current lap distance is represented as a fraction of the total lap rather than the actual distance, but I have not confirmed this.
* We compare this to their total distance from the previous loop iteration. If it is the same, the car is stopped.
* When the threshold of stopped cars is met, we throw a Safety Car event.

We account for:
* Any lag issues (resulting in all cars being marked as stopped)
* Cars in the pit
* Cars not currently active
* Cars with negative lap progress (possibly caused by an SDK glitch?)

### Off track events

* For each driver, we check their track location which indicates whether they're off track.
* We account for any negative lap progress, which may indicate an SDK glitch(?).
* When the threshold of off-track cars is met, we throw a Safety Car event.

### Safety Car procedure

TODO

## References

Basic irSDK usage: https://github.com/kutu/pyirsdk/tree/master/tutorials
A list of variables available through the SDK: https://github.com/kutu/pyirsdk/blob/master/vars.txt
Unofficial, more comprehensive, SDK docs: https://sajax.github.io/irsdkdocs/yaml

## License

This program is licensed under the [GNU General Public License Version 3](https://www.gnu.org/licenses/gpl-3.0.html).

## Author

This program was created by [Joshua Abbott Salazar](https://github.com/joshjaysalazar).

If you encounter any issues or have questions, please [report them on GitHub](https://github.com/joshjaysalazar/iRacing-Safety-Car-Trigger/issues).
