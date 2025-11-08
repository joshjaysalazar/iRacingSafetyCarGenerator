import logging
import threading
import time
import irsdk

logger = logging.getLogger(__name__)

class SessionInfoPoller:
    """Polls iRacing SDK for session information independently of the generator."""

    def __init__(self, callback):
        """Initialize the session info poller.

        Args:
            callback: Function to call with session data dict
        """
        self.callback = callback
        self.ir = irsdk.IRSDK()
        self.shutdown_event = threading.Event()
        self.thread = None
        self._last_data = None

    def start(self):
        """Start the polling thread."""
        if self.thread is None or not self.thread.is_alive():
            self.shutdown_event.clear()
            self.thread = threading.Thread(target=self._poll_loop, daemon=True)
            self.thread.start()
            logger.info("SessionInfoPoller started")

    def stop(self):
        """Stop the polling thread."""
        self.shutdown_event.set()
        if self.thread:
            self.thread.join(timeout=2)
        logger.info("SessionInfoPoller stopped")

    def _poll_loop(self):
        """Main polling loop that runs every 10 seconds."""
        while not self.shutdown_event.is_set():
            try:
                # Try to connect if not connected
                if not self.ir.startup():
                    # Not connected, send None to clear UI
                    if self._last_data is not None:
                        self._last_data = None
                        self.callback(None)
                else:
                    # Connected, try to get session data
                    session_data = self._get_session_data()
                    if session_data != self._last_data:
                        self._last_data = session_data
                        self.callback(session_data)

            except Exception as e:
                logger.error(f"Error in SessionInfoPoller: {e}")
                if self._last_data is not None:
                    self._last_data = None
                    self.callback(None)

            # Wait 10 seconds before next poll
            self.shutdown_event.wait(10)

    def _get_session_data(self):
        """Get current session data from iRacing SDK.

        Returns:
            dict with session info or None if data unavailable
        """
        try:
            # Get session info (YAML data)
            session_info = self.ir['SessionInfo']
            if not session_info:
                return None

            weekend_info = session_info.get('WeekendInfo', {})

            # Get current session index
            session_num = self.ir['SessionNum']
            if session_num is None:
                return None

            sessions = session_info.get('Sessions', [])
            if session_num >= len(sessions):
                return None

            current_session = sessions[session_num]

            # Get session state
            session_state = self.ir['SessionState']

            # Map session state to readable string
            state_names = {
                0: "Invalid",
                1: "Get in Car",
                2: "Warmup",
                3: "Parade Laps",
                4: "Racing",
                5: "Checkered",
                6: "Cool Down"
            }

            return {
                'track_name': weekend_info.get('TrackDisplayShortName', 'Unknown'),
                'track_length': weekend_info.get('TrackLength', ''),
                'track_config': weekend_info.get('TrackConfigName', ''),
                'session_type': current_session.get('SessionName', 'Unknown'),
                'session_state': state_names.get(session_state, 'Unknown'),
                'track_length_km': self._parse_track_length_km(weekend_info.get('TrackLength', ''))
            }

        except Exception as e:
            logger.error(f"Error getting session data: {e}")
            return None

    def _parse_track_length_km(self, track_length_str):
        """Parse track length string to kilometers.

        Args:
            track_length_str: String like "3.56 km" or "2.28 mi"

        Returns:
            float: Track length in kilometers, or None if parse fails
        """
        try:
            if not track_length_str:
                return None

            parts = track_length_str.strip().split()
            if len(parts) != 2:
                return None

            value = float(parts[0])
            unit = parts[1].lower()

            if unit == 'km':
                return value
            elif unit == 'mi':
                # Convert miles to kilometers
                return value * 1.60934
            else:
                return None

        except Exception as e:
            logger.error(f"Error parsing track length '{track_length_str}': {e}")
            return None
