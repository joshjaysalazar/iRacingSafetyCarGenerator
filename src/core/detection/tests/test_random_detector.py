import pytest
from core.detection.random_detector import RandomDetector
from core.detection.detector_common_types import DetectorState, DetectorEventTypes

def test_random_detector_initialization():
    detector = RandomDetector(chance=0.5, start_minute=10, end_minute=20)
    assert detector.chance == 0.5
    assert detector.len_of_window == 600  # (20-10)*60
    assert detector.max_occurrences == float('inf')  # Default value

def test_random_detector_initialization_with_max_occurrences():
    detector = RandomDetector(chance=0.5, start_minute=10, end_minute=20, max_occurrences=3)
    assert detector.chance == 0.5
    assert detector.max_occurrences == 3

def test_random_detector_detect_probability(monkeypatch):
    # Set up a detector with a known window
    detector = RandomDetector(chance=0.5, start_minute=0, end_minute=1)
    # Calculate expected chance
    expected_chance = 1 - ((1 - 0.5) ** (1 / 60))
    # Patch random.random to return a value below expected_chance
    monkeypatch.setattr("random.random", lambda: expected_chance - 0.01)
    result = detector.detect()
    assert result.has_detected_flag()
    assert result.detected_flag is True
    # Patch random.random to return a value above expected_chance
    monkeypatch.setattr("random.random", lambda: expected_chance + 0.01)
    result = detector.detect()
    assert result.has_detected_flag()
    assert result.detected_flag is False

def test_random_detector_zero_window():
    # If start_minute == end_minute, window is zero, always return False
    detector = RandomDetector(chance=0.5, start_minute=10, end_minute=10)
    result = detector.detect()
    assert result.has_detected_flag()
    assert result.detected_flag is False

@pytest.mark.skip(reason="This test is to check random distribution and will be flaky.")
def test_random_distribution():
    # Test the distribution of random events over multiple checks
    chance = 0.1
    detector = RandomDetector(chance, start_minute=0, end_minute=60)
    nr_repeats = 10000
    nr_checks = 60 * 60  # 1 check per second for 60 minutes
    triggered_count = 0
    ran_all_checks_count = 0
    for _ in range (nr_repeats):
        checks_count = 0
        for _ in range(nr_checks):
            result = detector.detect()
            if result.has_detected_flag() and result.detected_flag:
                triggered_count += 1
                break
            else:
                checks_count += 1

        if checks_count == nr_checks:
            ran_all_checks_count += 1

    # Expect around 10% true events across all repeats, allow some variance due to randomness
    assert (nr_repeats * (chance-0.01)) < triggered_count < (nr_repeats * (chance+0.01))
    assert ran_all_checks_count + triggered_count == nr_repeats


# Tests for should_run() method
def test_should_run_within_time_bounds():
    """Test should_run returns True when within time bounds."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=10 * 60,  # 10 minutes since start
        safety_car_event_counts={DetectorEventTypes.RANDOM: 1}
    )
    assert detector.should_run(state) is True

def test_should_run_before_start_time():
    """Test should_run returns False when before start time."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=3 * 60,  # 3 minutes since start (before start_minute=5)
        safety_car_event_counts={DetectorEventTypes.RANDOM: 0}
    )
    assert detector.should_run(state) is False

def test_should_run_after_end_time():
    """Test should_run returns False when after end time."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=20 * 60,  # 20 minutes since start (after end_minute=15)
        safety_car_event_counts={DetectorEventTypes.RANDOM: 1}
    )
    assert detector.should_run(state) is False

def test_should_run_at_boundary_times():
    """Test should_run behavior at exact boundary times."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    
    # Exactly at start time
    state = DetectorState(
        current_time_since_start=5 * 60,  # Exactly 5 minutes
        safety_car_event_counts={DetectorEventTypes.RANDOM: 0}
    )
    assert detector.should_run(state) is True
    
    # Exactly at end time
    state = DetectorState(
        current_time_since_start=15 * 60,  # Exactly 15 minutes
        safety_car_event_counts={DetectorEventTypes.RANDOM: 0}
    )
    assert detector.should_run(state) is True

def test_should_run_max_occurrences_not_reached():
    """Test should_run returns True when max occurrences not reached."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 2}  # Below max of 3
    )
    assert detector.should_run(state) is True

def test_should_run_max_occurrences_reached():
    """Test should_run returns False when max occurrences reached."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 3}  # Reached max of 3
    )
    assert detector.should_run(state) is False

def test_should_run_max_occurrences_exceeded():
    """Test should_run returns False when max occurrences exceeded."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 5}  # Exceeded max of 3
    )
    assert detector.should_run(state) is False

def test_should_run_no_event_counts():
    """Test should_run works when event type is not in counts dict."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=3)
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={}  # Empty dict - no RANDOM events recorded
    )
    assert detector.should_run(state) is True

def test_should_run_infinite_max_occurrences():
    """Test should_run with infinite max occurrences (default behavior)."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15)  # No max_occurrences specified
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 100}  # Large number
    )
    assert detector.should_run(state) is True

def test_should_run_combined_constraints():
    """Test should_run with multiple constraints - time bounds and max occurrences."""
    detector = RandomDetector(chance=0.5, start_minute=5, end_minute=15, max_occurrences=2)
    
    # Before time, under max - should be False (time constraint fails)
    state = DetectorState(
        current_time_since_start=3 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 1}
    )
    assert detector.should_run(state) is False
    
    # Within time, at max - should be False (occurrence constraint fails)
    state = DetectorState(
        current_time_since_start=10 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 2}
    )
    assert detector.should_run(state) is False
    
    # After time, under max - should be False (time constraint fails)
    state = DetectorState(
        current_time_since_start=20 * 60,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 1}
    )
    assert detector.should_run(state) is False
        