# Racing Concepts for Developers

This document explains racing terminology and concepts used throughout the iRacing Safety Car Generator codebase. It's intended for developers who may not be familiar with motorsports or racing rules.

## Table of Contents

- [Safety Car / Yellow Flag Basics](#safety-car--yellow-flag-basics)
- [Wave Arounds / Lucky Dog](#wave-arounds--lucky-dog)
- [Lap Counting and Position Calculation](#lap-counting-and-position-calculation)
- [Multi-Class Racing](#multi-class-racing)
- [Track Locations and Surfaces](#track-locations-and-surfaces)
- [iRacing-Specific Terminology](#iracing-specific-terminology)

## Safety Car / Yellow Flag Basics

### What is a Safety Car?

A **safety car** (also called **pace car** in oval racing) is a vehicle that enters the track during dangerous conditions to:
- Slow down the race
- Bunch up the field
- Allow track marshals to safely clear incidents or debris
- Neutralize racing competition temporarily

### Yellow Flag

When a safety car is deployed, **yellow flags** are shown to indicate:
- **No passing allowed** (with rare exceptions)
- **Slow down** to safety car speed
- **Caution period** is active

### Why Deploy a Safety Car?

Common reasons for safety car deployment:
1. **Stopped cars on track** - Vehicles that have crashed or broken down
2. **Cars off track** - Vehicles that have spun or left the racing surface
3. **Debris on track** - Parts, fluids, or other hazards
4. **Weather conditions** - Rain, fog, or other dangerous conditions
5. **Multiple incidents** - Several cars involved in crashes

### Safety Car Procedure

**Typical sequence:**
1. **Yellow flag thrown** - Racing neutralized, no passing
2. **Field bunches up** - Cars catch up to pace car
3. **Wave arounds** - Lapped cars allowed to regain a lap (see below)
4. **Pace laps** - Field circulates behind pace car for set number of laps
5. **Green flag** - Racing resumes

## Wave Arounds / Lucky Dog

### What is a Wave Around?

A **wave around** (also called **lucky dog** or **free pass**) is when lapped cars are allowed to pass the pace car and lead lap cars to **regain a lost lap**.

### Why Wave Arounds?

**Purpose:**
- Reduces likelihood of lapped cars interfering with lead lap battles
- Makes restarts safer by grouping similar-speed cars
- Rewards cars that were unlucky but still running

### When Are Wave Arounds Given?

**Timing:**
- After the field has bunched up behind the pace car
- Before the pace laps countdown begins
- Typically 1-2 laps into the yellow flag period

### Wave Around Strategies

This application implements **three strategies** for determining which cars get waved around:

#### 1. WAVE_LAPPED_CARS (Traditional Strategy)

**Who gets waved:**
- Cars that are **2 or more laps down** (clearly lapped)
- Cars that are **1 lap down AND behind their class leader**

**Logic:**
```
IF laps_behind >= 2:
    WAVE CAR
ELSE IF laps_behind == 1 AND position < class_leader_position:
    WAVE CAR
```

**Example:**
- Car #42 is 2 laps down → Gets waved
- Car #7 is 1 lap down but ahead of class leader → Does NOT get waved
- Car #99 is 1 lap down and behind class leader → Gets waved

#### 2. WAVE_AHEAD_OF_CLASS_LEAD (Road Course Strategy)

**Who gets waved:**
- Cars that are **ahead of their class leader** in running order
- But **behind the overall race leader**

**Logic:**
```
IF position_from_safety_car < class_leader_position_from_safety_car:
    WAVE CAR
```

**Purpose:** Handles situations in multi-class racing where faster class leaders may have lapped slower class cars.

#### 3. WAVE_COMBINED (Union Strategy)

**Who gets waved:**
- Any car that qualifies under **either Strategy 1 OR Strategy 2**

**Logic:**
```
IF qualifies_for_lapped_wave OR qualifies_for_ahead_of_class_wave:
    WAVE CAR
```

**Purpose:** Most comprehensive approach, ensures maximum fairness across all classes.

### Wave Around Command Execution

**Order matters:**
- Commands are sent in **running order behind the safety car**
- Closest car to pace car is waved first
- 0.5 second delay between commands to avoid rate limiting

**Why order matters:**
- Cars closer to pace car reach the wave-around point sooner
- Ensures smooth execution without traffic jams
- Mimics real-world race control procedures

## Lap Counting and Position Calculation

### Key Metrics

#### Laps Completed
- **Definition:** Number of full laps crossed at the start/finish line
- **Type:** Integer (0, 1, 2, ...)
- **SDK Field:** `CarIdxLap`

#### Laps Started
- **Definition:** The lap currently in progress
- **Type:** Integer
- **Relationship:** `laps_started = laps_completed + 1` (when on track)

#### Lap Distance
- **Definition:** Progress through the current lap
- **Type:** Float (0.0 to 1.0)
- **SDK Field:** `CarIdxLapDistPct`
- **Examples:**
  - `0.0` = At start/finish line
  - `0.5` = Halfway around the lap
  - `0.99` = Almost at start/finish line

#### Total Distance
- **Definition:** Complete measure of position accounting for fractional laps
- **Type:** Float
- **Calculation:** `total_distance = laps_completed + lap_distance`
- **Examples:**
  - `10.0` = Completed 10 laps, at start/finish
  - `10.5` = Completed 10 laps, halfway through lap 11
  - `10.75` = Completed 10 laps, 75% through lap 11

### Position Calculation

**Running order** is determined by `total_distance`:

```python
# Sort drivers by total_distance (descending)
sorted_drivers = sorted(drivers, key=lambda d: d["total_distance"], reverse=True)

# Driver with highest total_distance is in P1 (position 1)
# Driver with lowest total_distance is last
```

**Example:**
```
Car #1: total_distance = 15.8  → Position 1 (leader)
Car #2: total_distance = 15.6  → Position 2
Car #3: total_distance = 14.9  → Position 3 (1 lap down)
Car #4: total_distance = 13.2  → Position 4 (2 laps down)
```

### Lapped Cars

A car is **lapped** when its `laps_completed` is less than the leader's:

```python
laps_behind = leader_laps_completed - car_laps_completed

if laps_behind >= 1:
    # Car is lapped
```

**Note:** A car can be physically ahead of the leader on track but still be lapped (completed fewer full laps).

### Stopped Car Detection

A car is **stopped** if its `total_distance` hasn't changed between frames:

```python
# Previous frame
previous_total_distance = 10.5

# Current frame
current_total_distance = 10.5  # Same!

# Car hasn't moved → stopped
```

**Why this works:** Even at 1 mph, a car will show measurable `lap_distance` change over 1 second.

## Multi-Class Racing

### What is Multi-Class Racing?

**Definition:** Multiple vehicle classes compete in the same race simultaneously.

**Example classes in iRacing:**
- **GT3** - Fast, modern GT cars
- **GT4** - Slower, production-based GT cars
- **LMP2** - Fast prototype sports cars
- **GTE** - Professional-spec GT cars

**Key characteristic:** Different classes have different performance levels and race for separate class championships.

### Class Leaders

Each class has its own **class leader** (car with most laps completed in that class):

```python
# Find class leader for class_id=2
class_2_drivers = [d for d in drivers if d["car_class_id"] == 2]
class_leader = max(class_2_drivers, key=lambda d: d["total_distance"])
```

### Class Splitting

**What is Class Splitting?**

During a safety car period in multi-class racing, cars from different classes may be interleaved behind the pace car. **Class splitting** reorders the field so that all cars of the fastest class are at the front, followed by the next-fastest class, and so on.

**Why it matters:**
- Ensures clean restarts where classes don't interfere with each other
- Faster classes aren't stuck behind slower cars at the green flag
- Mirrors real-world race control procedures in series like IMSA and WEC

**How it works in the application:**
1. During a safety car period, the system checks if classes are out of order behind the pace car
2. Classes are sorted by `CarClassEstLapTime` (fastest first)
3. If any slower class car is found ahead of where it should be, `!eol` commands are sent for all drivers in that class and any slower classes
4. Commands are sent in position order within each class (closest to pace car first)

**Example:**
```
Before: SC → GT3(#1) → LMP2(#5) → GT3(#2) → LMP2(#6)
                        ↑ out of order!
After:  SC → LMP2(#5) → LMP2(#6) → GT3(#1) → GT3(#2)
```

### Why Multi-Class Matters for Wave Arounds

**Problem:** A fast class (e.g., LMP2) may lap a slower class (e.g., GT4) multiple times.

**Solution:** Wave around strategies consider **class-relative positions**:
- GT4 car 1 lap behind GT4 class leader → May get waved
- GT4 car 1 lap behind overall leader (LMP2) → Different rules apply

**Strategy 2 (WAVE_AHEAD_OF_CLASS_LEAD)** specifically handles this:
- GT4 car ahead of GT4 class leader but behind overall leader → Gets waved
- Prevents slower class leaders from being stuck behind their own lapped cars

## Track Locations and Surfaces

### TrkLoc (Track Location)

The iRacing SDK provides a `TrkLoc` enum indicating where a car is:

#### Primary Values

**TrkLoc.not_in_world** (`-1`)
- Car not loaded or not on track
- Filters out: spectators, disconnected drivers

**TrkLoc.off_track** (`0`)
- Car has left the racing surface
- Detection criteria for off-track incidents

**TrkLoc.in_pit_stall** (`1`)
- Car is stopped in their pit box
- Servicing (tires, fuel, repairs)

**TrkLoc.approaching_pits** (`2`)
- Car on pit entry road
- Heading to pit stall

**TrkLoc.on_track** (`3`)
- Car on the racing surface
- Normal racing conditions

### Why Track Location Matters

**Detection filtering:**
```python
# Don't count cars in pits as "stopped"
if driver["track_loc"] in [TrkLoc.in_pit_stall, TrkLoc.approaching_pits]:
    continue  # Skip this driver

# Don't count cars that aren't loaded
if driver["track_loc"] == TrkLoc.not_in_world:
    continue  # Skip this driver

# Only detect off-track cars
if driver["track_loc"] == TrkLoc.off_track:
    off_track_drivers.append(driver)
```

### on_pit_road Flag

Additional boolean flag indicating pit road status:

```python
if driver["on_pit_road"]:
    # Car is on pit entry or pit exit road
    # May still be in TrkLoc.on_track but should be filtered
```

**Combined checking:**
```python
# Comprehensive pit filtering
if driver["on_pit_road"] or driver["track_loc"] in [TrkLoc.in_pit_stall, TrkLoc.approaching_pits]:
    # Car is in pit complex, skip from detection
```

## iRacing-Specific Terminology

### Pace Car vs Safety Car

- **Pace Car:** iRacing's term for the AI-controlled safety car
- **Safety Car:** General racing term (same thing)
- **Code:** Often uses "pace car" to match iRacing terminology

### Chat Commands

iRacing accepts race control commands via the chat interface:

#### `!y <message>` - Throw Yellow Flag
```
!y Debris on track
!y Multiple cars involved
```
- Deploys full-course yellow
- Message appears to all drivers
- Pace car enters track

#### `!p <laps>` - Set Pace Laps
```
!p 2    # 2 more pace laps until green
!p 1    # 1 more pace lap until green
```
- Countdown displayed to drivers
- Pace car will exit after specified laps

#### `!w <car_number>` - Wave Around
```
!w 42   # Wave car #42
!w 7    # Wave car #7
```
- Allows specified car to pass pace car
- Car regains one lap

#### `!eol <car_number>` - End of Longest Line
```
!eol 42 Splitting classes   # Send car #42 to end of line
!eol 7 Splitting classes    # Send car #7 to end of line
```
- Sends specified car to the back of the field
- Used during class splitting to sort mixed-class grids by class speed
- Message after car number is displayed to all drivers

#### Command Timing
- **0.1s delay** after opening chat (UI update time)
- **0.5s delay** between commands (rate limiting)
- **Window focus required** (pywinauto limitation)

### Sessions

iRacing has different session types:

- **PRACTICE** - Non-competitive practice session
- **QUALIFY** - Qualifying for starting position
- **WARMUP** - Pre-race warm-up session
- **RACE** - Actual race session

**Application behavior:**
- Only monitors during **RACE** sessions
- Skips PRACTICE, QUALIFY, WARMUP
- Waits for green flag in RACE before monitoring

### SDK Data Structure

#### CarIdx (Car Index)
- **Definition:** Array index for a car (0-63)
- **Fixed:** Same car keeps same CarIdx throughout session
- **NOT position:** CarIdx=0 is not necessarily the leader
- **Not contiguous:** Only cars in the session appear in `DriverInfo.Drivers`, so CarIdx values can have gaps and the pace car can sit at a high index (e.g. CarIdx 62 with 16 cars at 0-15)

#### Array Access Pattern
```python
# All driver data is in parallel arrays indexed by CarIdx
laps = ir["CarIdxLap"]              # Array of laps per car
distances = ir["CarIdxLapDistPct"]  # Array of lap distances per car

# Access specific car's data
car_1_laps = laps[1]       # CarIdx=1's laps
car_1_distance = distances[1]  # CarIdx=1's lap distance
```

#### Driver Info Dictionary
```python
# Driver metadata (car number, class, etc.)
driver_info = ir["DriverInfo"]["Drivers"]  # List of driver dicts

# Find driver by CarIdx
for driver in driver_info:
    if driver["CarIdx"] == 5:
        car_number = driver["CarNumber"]
        is_pace_car = driver["CarIsPaceCar"]
```

### SDK Quirks

#### Negative Lap Distance
- **Issue:** SDK occasionally returns negative `CarIdxLapDistPct`
- **Cause:** Unknown (SDK glitch?)
- **Solution:** Filter out: `if lap_distance < 0: continue`

#### Lag Detection
- **Issue:** During SDK lag, all cars may appear stopped
- **Cause:** Data not updating during connection issues
- **Solution:** If >X cars stopped, assume lag and ignore

#### Pace Car in Arrays
- **Issue:** Pace car included in all driver arrays
- **Flag:** `CarIsPaceCar == 1` (true)
- **Solution:** Filter out: `if driver["is_pace_car"]: continue`

## Racing Rules Summary

For quick reference:

**Yellow Flag Rules:**
- No passing (except wave arounds)
- Slow to pace car speed
- Bunch up behind pace car

**Wave Around Rules:**
- Given to lapped cars during yellow
- Pass pace car to regain one lap
- Sent in running order (closest to pace car first)

**Lap Counting:**
- Laps completed = full laps crossed at S/F
- Lap distance = fraction of current lap (0.0-1.0)
- Total distance = laps_completed + lap_distance

**Multi-Class:**
- Multiple classes race simultaneously
- Each class has own leader
- Wave arounds consider class-relative positions

## Additional Resources

- [iRacing Sporting Code](https://www.iracing.com/iracingrules/) - Official rules
- [iRacing SDK Documentation](https://sajax.github.io/irsdkdocs/yaml) - SDK reference
- [Wikipedia: Safety Car](https://en.wikipedia.org/wiki/Safety_car) - General concept
- [Wikipedia: NASCAR Lucky Dog](https://en.wikipedia.org/wiki/NASCAR_rules_and_regulations#Lucky_Dog_Pass) - Wave around origins

---

For more technical details on how these concepts are implemented, see:
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [.ai-context.md](../.ai-context.md) - Implementation patterns
