# Architecture Documentation

## System Overview

### High-Level Design

```
┌─────────────────────────────────────────────────────────────────┐
│                          Main Thread                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  App (Tkinter GUI)                                       │   │
│  │  - State machine display                                 │   │
│  │  - Settings management                                   │   │
│  │  - Generator lifecycle control                           │   │
│  └─────────────────┬────────────────────────────────────────┘   │
│                    │ Creates & Controls                         │
└────────────────────┼────────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│                       Generator Thread                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Generator                                               │   │
│  │  ┌────────────┐  ┌──────────────┐  ┌─────────────────┐  │   │
│  │  │  Drivers   │  │  Detector    │  │ ThresholdChecker│  │   │
│  │  │ (current/  │→ │ - Random     │→ │ - Sliding window│→ │   │
│  │  │  previous) │  │ - Stopped    │  │ - Proximity     │  │   │
│  │  │            │  │ - OffTrack   │  │ - Thresholds    │  │   │
│  │  │            │  │ - Meatball   │  │                 │  │   │
│  │  └────────────┘  └──────────────┘  └─────────────────┘  │   │
│  │                                              │            │   │
│  │                                              ▼            │   │
│  │                                      ┌──────────────┐    │   │
│  │                                      │ CommandSender│    │   │
│  │                                      │ - Chat cmds  │    │   │
│  │                                      │ - Yellows    │    │   │
│  │                                      │ - Wave cmds  │    │   │
│  │                                      └──────────────┘    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Coordination via threading.Event:                              │
│  - shutdown_event, throw_manual_sc_event, skip_wait_event       │
└─────────────────────────────────────────────────────────────────┘
                     │
                     ▼
              iRacing SDK (pyirsdk)
              Windows Automation (pywinauto)
```

### Design Principles

1. **Separation of Concerns**
   - Detection logic isolated from execution procedures
   - GUI separated from core engine (different threads)
   - Windows-specific code abstracted behind interfaces

2. **Type Safety**
   - Extensive use of type hints throughout
   - TypedDict for data models (Driver)
   - Dataclasses for configuration (immutable settings)
   - Protocol-based structural typing (SupportsDetect)

3. **Testability**
   - Dependency injection for all major components
   - Mock implementations for Windows-only features
   - Comprehensive test coverage (unit, integration, e2e)

4. **Extensibility**
   - Protocol-based detector system allows easy addition of new detectors
   - Factory pattern for platform-specific implementations
   - Plugin-style architecture for wave around strategies

## Core Subsystems

### 1. Detection System (`src/core/detection/`)

#### Component Diagram

```
Detector (Composite)
    │
    ├─► RandomDetector
    │   └─ Calculates probability per second
    │
    ├─► StoppedDetector
    │   └─ Compares total_distance between frames
    │
    ├─► OffTrackDetector
    │   └─ Checks TrkLoc.off_track status
    │
    └─► MeatballDetector
        └─ Checks CarIdxSessionFlags for irsdk.Flags.repair
            ↓
        All results bundled into BundledDetectedEvents
            ↓
        ThresholdChecker (Aggregator)
        └─ Sliding time window with proximity clustering
            ↓
        Generator (Orchestrator)
        └─ Decides when to throw safety car
```

#### Data Flow

```
1. Drivers.update(ir) → Fetch latest from iRacing SDK
                         ↓
2. Detector.detect() → Run each enabled detector
   - RandomDetector: Check probability window
   - StoppedDetector: Compare current vs previous total_distance
   - OffTrackDetector: Check track_loc status
   - MeatballDetector: Detect transition to repair flag (previous→current)
                         ↓
3. BundledDetectedEvents → Bundle all results
                         ↓
4. ThresholdChecker.register_detection_result() → Add events to queue
                         ↓
5. ThresholdChecker.clean_up_events() → Remove expired events
                         ↓
6. ThresholdChecker.threshold_met() → Check if thresholds exceeded
   - Per-event-type thresholds (e.g., 2 stopped cars)
   - Accumulative threshold (weighted sum)
   - Proximity clustering (optional)
   - Dynamic threshold scaling (during race start)
                         ↓
7. Generator._start_safety_car() → Throw yellow and execute procedure
```

#### Key Patterns

**Builder Pattern:**
```python
# src/core/detection/detector.py — build_detector()
@staticmethod
def build_detector(settings: DetectorSettings, drivers: Drivers):
    """Each detector is instantiated if individually enabled OR if its
    accumulative weight is non-zero (contributes to weighted thresholds)."""
    detectors = {}

    if settings.random_detector_enabled or settings.accumulative_weights.get(DetectorEventTypes.RANDOM, 0) > 0:
        detectors[DetectorEventTypes.RANDOM] = RandomDetector(...)

    if settings.stopped_detector_enabled or settings.accumulative_weights.get(DetectorEventTypes.STOPPED, 0) > 0:
        detectors[DetectorEventTypes.STOPPED] = StoppedDetector(drivers)

    if settings.off_track_detector_enabled or settings.accumulative_weights.get(DetectorEventTypes.OFF_TRACK, 0) > 0:
        detectors[DetectorEventTypes.OFF_TRACK] = OffTrackDetector(drivers)

    if settings.meatball_detector_enabled or settings.accumulative_weights.get(DetectorEventTypes.MEATBALL, 0) > 0:
        detectors[DetectorEventTypes.MEATBALL] = MeatballDetector(drivers)

    return Detector(detectors)
```

**Protocol Pattern:**
```python
# src/core/detection/detector_common_types.py:41-49
class SupportsDetect(Protocol):
    def detect(self) -> DetectionResult:
        """Run detection and return results."""
        ...

    def should_run(self, state: DetectorState) -> bool:
        """Check if detector should run based on current state."""
        ...
```

**Composite Pattern:** Multiple independent detectors composed into single Detector that coordinates their execution.

**Strategy Pattern:** Each detector type implements different detection logic while adhering to the same interface.

### 2. State Management

#### State Machine

```python
# src/core/generator.py:15-23
class GeneratorState(Enum):
    STOPPED = 1
    CONNECTING_TO_IRACING = 2
    CONNECTED = 3
    WAITING_FOR_RACE_SESSION = 5
    WAITING_FOR_GREEN = 6
    MONITORING_FOR_INCIDENTS = 7
    SAFETY_CAR_DEPLOYED = 8
    UNCAUGHT_EXCEPTION = 9
```

#### State Transitions

```
┌──────────┐
│ STOPPED  │ User clicks "Start"
└────┬─────┘
     │
     ▼
┌───────────────────────┐
│ CONNECTING_TO_IRACING │ SDK connection attempt
└───────┬───────────────┘
        │
        ▼
┌───────────┐
│ CONNECTED │ Connection verified
└─────┬─────┘
      │
      ▼
┌─────────────────────────┐
│ WAITING_FOR_RACE_SESSION│ Wait for RACE session (not PRACTICE/QUALIFY)
└──────────┬──────────────┘
           │
           ▼
┌──────────────────┐
│ WAITING_FOR_GREEN│ Wait for green flag
└────────┬─────────┘
         │
         ▼
┌───────────────────────────┐
│ MONITORING_FOR_INCIDENTS  │◄───┐
└─────────────┬─────────────┘    │
              │                   │
              │ Threshold met     │ Green flag
              ▼                   │
┌──────────────────────┐          │
│ SAFETY_CAR_DEPLOYED  │──────────┘
└──────────────────────┘

Any state → UNCAUGHT_EXCEPTION (on unhandled error)
Any state → STOPPED (user clicks "Stop")
```

#### Property-Based State Transitions

State changes trigger automatic GUI updates:

```python
# src/core/app.py:161-165
@property
def generator_state(self) -> GeneratorState:
    return self._generator_state

@generator_state.setter
def generator_state(self, value: GeneratorState):
    self._generator_state = value
    self.on_generator_state_change()  # Updates GUI labels, button states
```

### 3. Threading Model

#### Thread Architecture

**Main Thread (Tkinter GUI):**
- Runs `App` class with Tkinter mainloop
- Handles user interactions (button clicks, settings changes)
- Polls `generator.state` property for status updates
- Does NOT directly modify Generator state

**Generator Thread:**
- Started via `Generator.start()` → creates `threading.Thread(target=self.run)`
- Runs detection loop at ~1 Hz
- Manages iRacing SDK connection
- Executes safety car procedures
- Updates own state via property setter

#### Thread Coordination

```python
# src/core/generator.py:37-40
self.shutdown_event = threading.Event()          # Signals generator to stop
self.throw_manual_sc_event = threading.Event()   # Manual SC button pressed
self.skip_wait_for_green_event = threading.Event()  # Developer mode skip
```

**Communication Pattern:**
- Main thread → Generator: Sets Event flags
- Generator → Main thread: Updates `self.state` property
- No shared mutable state (thread-safe)

#### Thread Safety

- **iRacing SDK:** Thread-safe, can be read from Generator thread
- **Generator.state:** Read by main thread, written by Generator thread (atomic property)
- **No locks needed:** Clean separation prevents race conditions

### 4. Data Models

#### Driver (TypedDict)

```python
# src/core/drivers.py:5-14
class Driver(TypedDict):
    driver_idx: int          # SDK array index (0-63)
    car_number: str          # Visible car number (e.g., "42")
    car_class_id: int        # Class for multi-class racing
    is_pace_car: bool        # True for pace car
    laps_completed: int      # Full laps crossed at start/finish
    laps_started: int        # Current lap in progress
    lap_distance: float      # Fraction of lap (0.0-1.0)
    total_distance: float    # laps_completed + lap_distance
    track_loc: TrkLoc        # SDK enum: on_track, off_track, in_pit_stall, etc.
    on_pit_road: bool        # On pit entry/exit road
    session_flags: int       # Per-car session flags (e.g., irsdk.Flags.repair for meatball)
```

**Key Field: total_distance**
- Calculated as `laps_completed + lap_distance`
- Used for stopped car detection (compare between frames)
- Used for position calculations (sort drivers by total_distance)

#### Double-Buffering Pattern

```python
# src/core/drivers.py:11-18
class Drivers:
    def __init__(self):
        self.current_drivers: list[Driver] = []
        self.previous_drivers: list[Driver] = []

    def update(self, ir):
        self.previous_drivers = self.current_drivers.copy()
        self.current_drivers = self._build_drivers(ir)
```

**Purpose:** Enable stopped car detection by comparing `total_distance` between frames:

```python
# src/core/detection/stopped_detector.py:44-57
for current_driver in self.drivers.current_drivers:
    # Find matching driver in previous frame
    previous_driver = self._find_previous_driver(current_driver)

    # Compare total_distance
    if previous_driver and current_driver["total_distance"] == previous_driver["total_distance"]:
        # Car hasn't moved → stopped
        stopped_drivers.append(current_driver)
```

### 5. Configuration System

#### Settings (Type-Safe ConfigParser Wrapper)

```python
# src/core/settings.py:7-250
class Settings:
    def __init__(self, config: configparser.ConfigParser):
        self.config = config

    @property
    def max_sc_events(self) -> int:
        return self.config.getint("General", "max_sc_events", fallback=5)

    @max_sc_events.setter
    def max_sc_events(self, value: int):
        self.config.set("General", "max_sc_events", str(value))
```

**Pattern:** Properties with getters/setters for type-safe access with fallback defaults.

**File Location:** `src/settings.ini`

**Type Conversions:**
- `getboolean()` for bool values (stored as 0/1)
- `getint()` for integers
- `getfloat()` for floats
- `get()` for strings

#### Settings Dataclasses

Configuration objects built from Settings:

```python
# src/core/detection/detector_common_types.py:53-60
@dataclass(frozen=True)
class DetectorSettings:
    random_detector_enabled: bool = False
    random_detector_settings: RandomDetectorSettings = field(default_factory=RandomDetectorSettings)
    stopped_detector_enabled: bool = False
    stopped_detector_settings: StoppedDetectorSettings = field(default_factory=StoppedDetectorSettings)
    off_track_detector_enabled: bool = False
    off_track_detector_settings: OffTrackDetectorSettings = field(default_factory=OffTrackDetectorSettings)
    meatball_detector_enabled: bool = True

    @classmethod
    def from_settings(cls, settings: Settings) -> "DetectorSettings":
        """Build from Settings object."""
        ...
```

**Benefits:**
- Immutable (frozen=True) prevents accidental modification
- Type hints enable IDE autocomplete and type checking
- Factory method pattern for construction from Settings

### 6. Windows Automation

#### Command Sender Factory

```python
# src/core/interactions/interaction_factories.py:7-14
def CommandSenderFactory(arguments: argparse.Namespace, ir: irsdk.IRSDK) -> SupportsCommandSending:
    """Create appropriate command sender based on arguments."""
    if arguments.dont_use_windows_interactions:
        return MockSender()  # Cross-platform development
    else:
        iracing_window = IracingWindow()
        return CommandSender(ir, iracing_window)  # Production Windows automation
```

**Production Path (Windows):**
```python
# src/core/interactions/command_sender.py:18-36
def send_command(self, command: str):
    """Send chat command to iRacing via window automation."""
    self.ir.chat_command(1)  # Open chat via SDK
    time.sleep(0.1)  # Wait for UI

    self.iracing_window.set_focus()  # Focus window via pywinauto
    pyperclip.copy(command)  # Copy command to clipboard
    keyboard.send_keys("^v")  # Paste
    keyboard.send_keys("{ENTER}")  # Send

    time.sleep(0.5)  # Rate limiting delay
```

**Development Path (Cross-Platform):**
```python
# src/core/interactions/mock_sender.py:6-10
class MockSender(SupportsCommandSending):
    def send_command(self, command: str):
        logger.info(f"[MOCK] Would send command: {command}")
        # No actual window interaction
```

#### Chat Command Protocol

iRacing accepts commands via chat interface:
- `!y <message>` → Throw full-course yellow
- `!p <laps>` → Set pace laps remaining
- `!w <car_number>` → Wave around specific car
- `!eol <car_number>` → Send car to end of longest line (class splitting)

## Key Workflows

### 1. Application Startup

```
main.py
│
├─► setup_logging()
│   ├─ Create logs/ directory
│   ├─ Load logging.json config
│   └─ Create timestamped log file
│
├─► parse_arguments()
│   ├─ -dev: Enable developer panel
│   ├─ -dwi: Don't use Windows interactions (mock sender)
│   └─ -dry: Dry run mode (show warning)
│
└─► App.__init__()
    ├─ Load Settings from settings.ini
    ├─ Create Generator(arguments, self)
    ├─ Build GUI widgets (3-column layout)
    │   ├─ Column 1: Safety car types (Random, Stopped, Off Track)
    │   ├─ Column 2: Settings (thresholds, timing)
    │   └─ Column 3: Controls (Start/Stop, manual SC)
    ├─ Fill widgets from settings
    └─ App.mainloop() → Start Tkinter event loop
```

### 2. Start Generator

```
User clicks "Start SC Generator" button
│
├─► App._start_generator()
│   ├─ App._save_and_run()
│   │   ├─ Save settings from GUI to settings.ini
│   │   └─ Generator.start()
│   │
│   └─► Generator.start()
│       ├─ Create thread: threading.Thread(target=self.run)
│       └─ thread.start()
│
└─► Generator.run() [In separate thread]
    ├─ State: STOPPED → CONNECTING_TO_IRACING
    │
    ├─► _connect_to_iracing()
    │   ├─ ir.startup() → Connect to SDK
    │   ├─ Wait for connection (retry loop)
    │   └─ State: CONNECTING_TO_IRACING → CONNECTED
    │
    ├─► _connect_command_sender()
    │   └─ CommandSenderFactory creates sender (real or mock)
    │
    ├─ Create Drivers object
    ├─ Build Detector from settings
    ├─ Create ThresholdChecker from settings
    │
    ├─ State: CONNECTED → WAITING_FOR_RACE_SESSION
    │
    ├─► _wait_for_race_session()
    │   ├─ Skip PRACTICE, QUALIFY, WARMUP sessions
    │   ├─ Wait for RACE session
    │   └─ State: WAITING_FOR_RACE_SESSION → WAITING_FOR_GREEN
    │
    ├─► _wait_for_green_flag()
    │   ├─ Wait for SessionFlags & Flags.green
    │   ├─ State: WAITING_FOR_GREEN → MONITORING_FOR_INCIDENTS
    │   └─ Notify components: detector.race_started(), threshold_checker.race_started()
    │
    └─► _loop() → Main detection loop
```

### 3. Detection Loop (~1 Hz)

```
while not shutdown_event.is_set() and total_sc_events < max_events:
    │
    ├─► drivers.update(ir)
    │   ├─ previous_drivers ← current_drivers
    │   └─ current_drivers ← _build_drivers(ir)
    │
    ├─► Check eligibility window
    │   ├─ Time >= detection_start_minute?
    │   ├─ Time <= detection_end_minute?
    │   └─ Time since last SC >= min_time_between?
    │
    ├─► _check_manual_event()
    │   └─ If manual SC button pressed → throw yellow immediately
    │
    ├─► detector.detect()
    │   ├─ detector_state ← DetectorState(time, lap, counts)
    │   │
    │   └─ For each detector:
    │       ├─ if detector.should_run(detector_state):
    │       │   └─ result ← detector.detect()
    │       │       ├─ RandomDetector: Check probability
    │       │       ├─ StoppedDetector: Compare total_distance
    │       │       ├─ OffTrackDetector: Check track_loc
    │       │       └─ MeatballDetector: Detect repair flag transition
    │       │
    │       └─ Bundle all results → BundledDetectedEvents
    │
    ├─► threshold_checker.clean_up_events(current_time)
    │   └─ Remove events older than time_range seconds from queue
    │
    ├─► For each detector result:
    │   └─ threshold_checker.register_detection_result(result)
    │       ├─ Add (timestamp, event_type, driver) to queue
    │       └─ Update driver_event_counts dict
    │
    ├─► if threshold_checker.threshold_met():
    │   │
    │   └─► _start_safety_car(message)
    │
    └─ time.sleep(1.0) → Loop at ~1 Hz
```

### 4. Safety Car Procedure

```
_start_safety_car(message)
│
├─► command_sender.send_command(f"!y {message}")
│   └─ Throw full-course yellow
│
├─ Update state:
│   ├─ total_sc_events += 1
│   ├─ last_sc_time ← current_time
│   ├─ lap_at_sc ← max(CarIdxLap)  # Current lap number
│   └─ State: MONITORING_FOR_INCIDENTS → SAFETY_CAR_DEPLOYED
│
├─ Calculate target laps:
│   ├─ wave_around_lap ← lap_at_sc + laps_before_wave_arounds + 1
│   └─ pace_lap ← lap_at_sc + 2
│
└─► While not (waves_done AND pace_done):
    │
    ├─► drivers.update(ir)
    │
    ├─► current_lap ← _get_current_lap_under_sc()
    │   └─ max(driver["laps_completed"]) for non-pit drivers
    │
    ├─► if current_lap >= wave_around_lap AND not waves_done:
    │   │
    │   └─► _send_wave_arounds()
    │       ├─ strategy ← wave_arounds_factory(wave_around_type)
    │       ├─ commands ← strategy(drivers, pace_car_idx)
    │       │   └─ Returns list of "!w CAR_NUMBER" commands
    │       │
    │       ├─ Sort commands by position relative to SC (closest first)
    │       │
    │       └─ command_sender.send_commands(commands, delay=0.5s)
    │
    ├─► _split_classes() (if class_split_enabled):
    │   │
    │   └─► get_split_class_commands(drivers, car_positions, on_pit_road, pace_car_idx)
    │       ├─ Calculate positions relative to SC
    │       ├─ Group drivers by CarClassID, sort classes by CarClassEstLapTime
    │       ├─ Walk grid to find classes out of order
    │       ├─ Generate "!eol CAR_NUMBER" commands for out-of-order classes
    │       └─ command_sender.send_commands(commands)
    │
    ├─► if current_lap >= pace_lap AND leader at 50% lap distance AND not pace_done:
    │   │
    │   └─► _send_pace_laps()
    │       └─ command_sender.send_command(f"!p {laps_under_sc - 1}")
    │
    └─ time.sleep(1.0)

After wave arounds and pace laps sent:
│
└─► _wait_for_green_flag(require_race_session=False)
    ├─ Wait for green flag
    ├─ State: SAFETY_CAR_DEPLOYED → MONITORING_FOR_INCIDENTS
    └─ Resume detection loop
```

### 5. Threshold Checking Deep Dive

```
threshold_checker.threshold_met()
│
├─► _get_proximity_clusters()  [cluster first, dedupe after]
│   │
│   ├─ Collect ALL events from queue as (timestamp, driver_idx, event_type, driver_obj)
│   │   (Events stay at their original positions for clustering)
│   │
│   └─► if proximity_yellows_enabled:
│       │
│       └─► _create_proximity_clusters(all_events, proximity_distance)
│           ├─ Extract list of (lap_distance, timestamp, driver_idx, event_type, driver_obj)
│           ├─ Sort by lap_distance
│           │
│           ├─► Extend list with +1 lap positions (wrap-around handling)
│           │   └─ If event at lap_distance 0.95, also add at 1.95
│           │       (Handles finish line wrap-around)
│           │
│           ├─► Sliding window clustering
│           │   ├─ Start with first event
│           │   ├─ Add events within proximity_distance
│           │   ├─ When gap > proximity_distance, start new cluster
│           │   └─ A driver CAN appear in multiple clusters at different positions
│           │
│           └─► _dedupe_cluster() on each raw cluster
│               └─ Keep only latest event per (driver_idx, event_type)
│
├─► Calculate dynamic_multiplier
│   └─ If race_start_time and within dynamic_threshold_time:
│       └─ multiplier ← dynamic_threshold_multiplier
│       (Higher threshold during race start to avoid false positives)
│
└─► For each cluster (or all events if proximity disabled):
    │
    └─► _cluster_meets_threshold(cluster, dynamic_multiplier)
        ├─ Count events per type in cluster: {STOPPED: 2, OFF_TRACK: 1}
        │
        ├─► Check per-event-type thresholds (only for individually enabled detectors)
        │   └─ For each individually-enabled event type: count >= (threshold * multiplier)?
        │       (Detectors running only for accumulative weight skip this check)
        │
        ├─► Check accumulative threshold (per-driver max weight)
        │   ├─ For each driver, use only the highest-weighted event type
        │   ├─ weighted_sum ← sum(max weight per driver)
        │   └─ weighted_sum >= (accumulative_threshold * multiplier)?
        │
        └─ Return True if either check passes
```

## Testing Strategy

### Test Organization

Tests are co-located with source code in `tests/` subdirectories:

```
src/core/
├── app.py
├── generator.py
├── drivers.py
├── settings.py
├── tests/
│   ├── __init__.py
│   ├── test_app.py
│   ├── test_generator.py
│   ├── test_generator_detector_integration.py
│   ├── test_settings.py
│   └── test_utils.py  ← Common fixtures and utilities
│
└── detection/
    ├── detector.py
    ├── threshold_checker.py
    ├── stopped_detector.py
    ├── off_track_detector.py
    ├── random_detector.py
    ├── meatball_detector.py
    └── tests/
        ├── __init__.py
        ├── test_detector.py
        ├── test_threshold_checker.py
        ├── test_stopped_detector.py
        ├── test_off_track_detector.py
        ├── test_random_detector.py
        ├── test_meatball_detector.py
        └── test_end_to_end_integration.py
```

### Common Test Utilities

**`src/core/tests/test_utils.py` provides:**

```python
def make_driver(
    driver_idx: int = 0,
    car_number: str = "1",
    car_class_id: int = 0,
    is_pace_car: bool = False,
    laps_completed: int = 0,
    laps_started: int = 0,
    lap_distance: float = 0.0,
    track_loc: TrkLoc = TrkLoc.on_track,
    on_pit_road: bool = False
) -> Driver:
    """Create a Driver with specified properties (defaults for others)."""
    ...

def dict_to_config(config_dict: dict) -> configparser.ConfigParser:
    """Convert dict to ConfigParser for testing Settings."""
    ...
```

### Testing Patterns

#### Unit Tests

Test individual components in isolation:

```python
# src/core/detection/tests/test_stopped_detector.py
def test_stopped_detector_detects_stopped_car(mocker):
    """Test that StoppedDetector identifies a car that hasn't moved."""
    drivers = Drivers()

    # Setup: Car at same position in current and previous
    stopped_driver = make_driver(driver_idx=1, laps_completed=5, lap_distance=0.5)
    drivers.current_drivers = [stopped_driver]
    drivers.previous_drivers = [stopped_driver]  # Same position

    detector = StoppedDetector(drivers, StoppedDetectorSettings())
    result = detector.detect()

    assert result.has_drivers()
    assert len(result.drivers) == 1
    assert result.drivers[0]["driver_idx"] == 1
```

#### Integration Tests

Test interactions between components:

```python
# src/core/tests/test_generator_detector_integration.py
def test_generator_calls_race_started_when_green_flag_detected(mocker):
    """Test that Generator notifies detector when race starts."""
    # Setup mocks
    mock_ir = mocker.Mock()
    mock_ir["SessionInfo"]["Sessions"] = [{"SessionType": "Race"}]
    mock_ir["SessionFlags"] = Flags.green

    # Create generator
    generator = Generator(...)

    # Spy on detector.race_started()
    spy = mocker.spy(generator.detector, "race_started")

    # Run generator
    generator._wait_for_green_flag()

    # Verify detector was notified
    spy.assert_called_once()
```

#### End-to-End Tests

Test complete workflows:

```python
# src/core/detection/tests/test_end_to_end_integration.py
def test_single_detector_end_to_end_workflow(mocker):
    """Test complete flow from detection to threshold met."""
    # Setup
    drivers = Drivers()
    settings = DetectorSettings(
        stopped_detector_enabled=True,
        stopped_detector_settings=StoppedDetectorSettings()
    )
    detector = Detector.build_detector(settings, drivers)
    threshold_checker = ThresholdChecker(
        ThresholdCheckerSettings(stopped_car_threshold=2)
    )

    # Create 2 stopped cars
    stopped1 = make_driver(driver_idx=1, total_distance=10.0)
    stopped2 = make_driver(driver_idx=2, total_distance=15.0)

    drivers.current_drivers = [stopped1, stopped2]
    drivers.previous_drivers = [stopped1, stopped2]  # Same positions

    # Run detection
    results = detector.detect()

    # Register with threshold checker
    for result in results.results:
        threshold_checker.register_detection_result(result, 100.0)

    # Verify threshold met
    assert threshold_checker.threshold_met(100.0, {})
```

### Mocking the iRacing SDK

Use `pytest-mock` to simulate SDK behavior:

```python
def test_something(mocker):
    # Mock time for deterministic tests
    mocker.patch("time.time", return_value=1000.0)

    # Mock SDK instance
    mock_ir = mocker.Mock()

    # Mock array data (indexed by CarIdx)
    mock_ir["CarIdxLap"] = [0, 10, 11, 9]  # Laps completed per car
    mock_ir["CarIdxLapDistPct"] = [0.0, 0.5, 0.75, 0.25]  # Lap progress
    mock_ir["CarIdxTrackSurface"] = [
        TrkLoc.not_in_world,
        TrkLoc.on_track,
        TrkLoc.on_track,
        TrkLoc.off_track
    ]

    # Mock driver info
    mock_ir["DriverInfo"]["Drivers"] = [
        {"CarIdx": 0, "CarNumber": "0", "CarIsPaceCar": 1},
        {"CarIdx": 1, "CarNumber": "42", "CarIsPaceCar": 0},
        {"CarIdx": 2, "CarNumber": "7", "CarIsPaceCar": 0},
        {"CarIdx": 3, "CarNumber": "99", "CarIsPaceCar": 0},
    ]

    # Use mock_ir in test
    drivers = Drivers()
    drivers.update(mock_ir)
```

## Extension Points

### Adding a New Detector

**Step-by-step guide:**

1. **Create detector file:** `src/core/detection/your_detector.py`

```python
from core.detection.detector_common_types import (
    DetectionResult, DetectorEventTypes, DetectorState, SupportsDetect
)
from dataclasses import dataclass

@dataclass(frozen=True)
class YourDetectorSettings:
    some_threshold: int = 5

class YourDetector(SupportsDetect):
    def __init__(self, drivers: Drivers, settings: YourDetectorSettings):
        self.drivers = drivers
        self.settings = settings

    def detect(self) -> DetectionResult:
        """Implement detection logic."""
        detected_drivers = []

        for driver in self.drivers.current_drivers:
            if self._should_detect(driver):
                detected_drivers.append(driver)

        return DetectionResult(DetectorEventTypes.YOUR_EVENT, drivers=detected_drivers)

    def should_run(self, state: DetectorState) -> bool:
        """Check if detector should run (time window, lap range, etc.)."""
        return True  # Or add conditional logic

    def _should_detect(self, driver: Driver) -> bool:
        """Your detection logic here."""
        return False
```

2. **Add event type to enum:** `src/core/detection/detector_common_types.py`

```python
class DetectorEventTypes(Enum):
    RANDOM = 1
    STOPPED = 2
    OFF_TRACK = 3
    YOUR_EVENT = 4  # Add new type
```

3. **Update DetectorSettings:** `src/core/detection/detector_common_types.py`

```python
@dataclass(frozen=True)
class DetectorSettings:
    # ... existing fields ...
    your_detector_enabled: bool = False
    your_detector_settings: YourDetectorSettings = field(default_factory=YourDetectorSettings)

    @classmethod
    def from_settings(cls, settings: Settings) -> "DetectorSettings":
        return cls(
            # ... existing fields ...
            your_detector_enabled=settings.your_detector_enabled,
            your_detector_settings=YourDetectorSettings(
                some_threshold=settings.your_detector_threshold
            )
        )
```

4. **Update builder:** `src/core/detection/detector.py`

```python
@staticmethod
def build_detector(settings: DetectorSettings, drivers: Drivers) -> "Detector":
    detectors: list[SupportsDetect] = []

    # ... existing detectors ...

    if settings.your_detector_enabled:
        detectors.append(YourDetector(drivers, settings.your_detector_settings))

    return Detector(detectors)
```

5. **Add threshold settings:** `src/core/detection/detector_common_types.py`

```python
@dataclass(frozen=True)
class ThresholdCheckerSettings:
    # ... existing fields ...
    your_event_threshold: int = 2
    your_event_weight: int = 2  # For accumulative threshold

    event_type_thresholds: dict[DetectorEventTypes, int] = field(default_factory=dict)
    event_type_weights: dict[DetectorEventTypes, int] = field(default_factory=dict)

    def __post_init__(self):
        # ... existing mappings ...
        self.event_type_thresholds[DetectorEventTypes.YOUR_EVENT] = self.your_event_threshold
        self.event_type_weights[DetectorEventTypes.YOUR_EVENT] = self.your_event_weight
```

6. **Add GUI controls:** `src/core/app.py`

```python
# In App.__init__(), add widgets for your detector
# Follow pattern of existing detector checkboxes and settings
```

7. **Add settings properties:** `src/core/settings.py`

```python
@property
def your_detector_enabled(self) -> bool:
    return self.config.getboolean("YourDetector", "enabled", fallback=False)

@your_detector_enabled.setter
def your_detector_enabled(self, value: bool):
    self.config.set("YourDetector", "enabled", str(int(value)))
```

8. **Create tests:** `src/core/detection/tests/test_your_detector.py`

```python
import pytest
from core.detection.your_detector import YourDetector, YourDetectorSettings
from core.tests.test_utils import make_driver

def test_your_detector_detects_condition():
    """Test that your detector identifies the condition."""
    drivers = Drivers()
    # ... setup test scenario ...

    detector = YourDetector(drivers, YourDetectorSettings())
    result = detector.detect()

    assert result.event_type == DetectorEventTypes.YOUR_EVENT
    # ... additional assertions ...
```

### Adding a New Wave Around Strategy

**Step-by-step guide:**

1. **Add enum value:** `src/core/procedures/wave_arounds.py`

```python
class WaveAroundType(Enum):
    WAVE_LAPPED_CARS = 1
    WAVE_AHEAD_OF_CLASS_LEAD = 2
    WAVE_COMBINED = 3
    YOUR_STRATEGY = 4  # Add new strategy
```

2. **Implement strategy function:**

```python
def get_your_strategy_wave_around_commands(drivers: Drivers, pace_car_idx: int) -> list[str]:
    """
    Your wave around strategy.

    Args:
        drivers: Drivers object with current driver data
        pace_car_idx: Index of pace car

    Returns:
        List of "!w CAR_NUMBER" commands sorted by position relative to SC
    """
    commands = []

    # Your logic here to determine which cars to wave around
    for driver in drivers.current_drivers:
        if your_condition(driver):
            commands.append(f"!w {driver['car_number']}")

    return commands
```

3. **Update factory:** `src/core/procedures/wave_arounds.py`

```python
def wave_arounds_factory(wave_around_type: WaveAroundType):
    if wave_around_type == WaveAroundType.WAVE_LAPPED_CARS:
        return get_lapped_cars_wave_around_commands
    elif wave_around_type == WaveAroundType.WAVE_AHEAD_OF_CLASS_LEAD:
        return get_ahead_of_class_lead_wave_around_commands
    elif wave_around_type == WaveAroundType.WAVE_COMBINED:
        return get_combined_wave_around_commands
    elif wave_around_type == WaveAroundType.YOUR_STRATEGY:
        return get_your_strategy_wave_around_commands
    else:
        raise ValueError(f"Unknown wave around type: {wave_around_type}")
```

4. **Add GUI option:** `src/core/app.py`

```python
# Add radio button or dropdown option for your strategy
```

5. **Add settings:** `src/core/settings.py`

```python
# If your strategy needs settings, add properties
```

6. **Create tests:** `src/core/procedures/tests/test_wave_arounds.py`

```python
def test_your_strategy():
    """Test your wave around strategy."""
    drivers = Drivers()
    # ... setup test scenario ...

    commands = get_your_strategy_wave_around_commands(drivers, pace_car_idx=0)

    assert len(commands) == expected_count
    # ... additional assertions ...
```

## Platform-Specific Considerations

### Windows-Only Components

**pywinauto (Window Automation):**
- Used in `CommandSender` to focus iRacing window
- Required for sending chat commands
- Only works on Windows

**irsdk (iRacing SDK):**
- iRacing simulator is Windows-only
- SDK only available on Windows

### Cross-Platform Development

**Development Mode (`-dwi` flag):**
```python
# Command-line usage
python src/main.py -dwi  # Don't use Windows interactions
```

**Mock Implementations:**
- `MockSender` (src/core/interactions/mock_sender.py): Logs commands instead of sending
- `MockWindow` (src/core/interactions/mock_window.py): No-op window operations

**Benefits:**
- Develop and test on macOS/Linux
- Run unit/integration tests without Windows
- Debug detection logic without running iRacing

**Limitations of mocks:**
- Cannot test actual Windows automation
- Cannot test with real iRacing SDK data
- End-to-end testing requires Windows

## Performance Characteristics

### Loop Frequency

**Detection Loop:** ~1 Hz (1 second sleep + loop execution time)
- `time.sleep(1.0)` at end of loop
- Actual frequency slightly lower due to processing time
- Sufficient for safety car detection (incidents last multiple seconds)

### SDK Polling

**Every loop iteration:**
- Reads all driver data from SDK arrays
- Processes ~50-60 drivers (typical iRacing field size)
- Fast: array access is O(1), driver processing is O(n)

### Memory Usage

**Minimal:**
- Stores 2 copies of driver list: `current_drivers` + `previous_drivers`
- ~50 drivers × 2 copies × ~200 bytes per driver = ~20 KB
- Event queue in ThresholdChecker: limited by time window (5s default)
- Total memory footprint: < 1 MB

### CPU Usage

**Low:**
- Most time spent sleeping (`time.sleep(1.0)`)
- Detection logic is lightweight (simple comparisons)
- No heavy computation or image processing
- Expected: < 1% CPU on modern hardware

## Known Limitations & SDK Quirks

### iRacing SDK Issues

**1. Negative lap progress:**
```python
# SDK occasionally returns negative CarIdxLapDistPct
# Always filter these out
if driver["lap_distance"] < 0:
    continue
```

**2. Lag detection (all cars stopped):**
```python
# If SDK lags, all cars show as stopped
# Use lag protection threshold
if len(stopped_drivers) > lag_threshold:
    logger.warning("Possible lag detected")
    return DetectionResult(DetectorEventTypes.STOPPED, drivers=[])
```

**3. Pace car in arrays:**
```python
# Pace car included in all driver arrays
# Must filter by is_pace_car flag
if driver["is_pace_car"]:
    continue
```

**4. Array indices don't match positions:**
- CarIdx (array index) is fixed assignment, not running position
- Must calculate positions from lap_distance and laps_completed

### Application Limitations

**1. Must start before green flag:**
- Current implementation waits for green flag before monitoring
- Cannot join mid-race (would miss initial state)

**2. Window focus required:**
- pywinauto needs iRacing window focused for chat commands
- Users cannot alt-tab during safety car procedures
- Commands may fail if focus is lost

**3. Chat interference:**
- Application uses chat interface for commands
- Users should avoid using chat while generator active
- May conflict with other chat-based tools

**4. No remote control:**
- Must run on same machine as iRacing
- Cannot control from different computer

**5. Single safety car at a time:**
- Cannot queue multiple safety cars
- If threshold met during existing SC, second SC is ignored

### Threading Limitations

**No mid-procedure interruption:**
- Once safety car procedure starts, runs to completion
- Cannot stop during wave around / pace lap sending
- Shutdown event only checked at top of loop

### Race Format Limitations

**Assumes standard rules:**
- Detection logic assumes standard racing rules
- May not work correctly for:
  - Oval vs road course differences
  - Special event formats
  - Custom server rules

## Additional Resources

- **Project Documentation:**
  - `.ai-context.md` - AI assistant coding patterns and conventions
  - `.ai-modules.md` - Module quick reference
  - `CONTRIBUTING.md` - Contribution guidelines
  - `docs/RACING_CONCEPTS.md` - Racing domain knowledge

- **External Resources:**
  - [iRacing SDK Documentation](https://sajax.github.io/irsdkdocs/yaml)
  - [pyirsdk Library](https://github.com/kutu/pyirsdk)
  - [pyirsdk Examples](https://github.com/kutu/pyirsdk/tree/master/tutorials)

- **Testing:**
  - Run tests: `pytest`
  - With coverage: `pytest --cov`
  - Verbose: `pytest -v`
