import pytest
from core.detection.detector_common_types import DetectorState, DetectorEventTypes


def test_detector_state_initialization():
    """Test DetectorState initialization with required parameters."""
    state = DetectorState(
        current_time_since_start=300.5,  # 5 minutes and 0.5 seconds
        safety_car_event_counts={DetectorEventTypes.RANDOM: 2}
    )
    assert state.current_time_since_start == 300.5
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 2


def test_detector_state_empty_event_counts():
    """Test DetectorState with empty event counts."""
    state = DetectorState(
        current_time_since_start=100.0,
        safety_car_event_counts={}
    )
    assert state.current_time_since_start == 100.0
    assert state.safety_car_event_counts == {}


def test_increment_safety_car_event_new_type():
    """Test incrementing event count for a new event type."""
    state = DetectorState(
        current_time_since_start=300.0,
        safety_car_event_counts={}
    )
    
    state.increment_safety_car_event(DetectorEventTypes.RANDOM)
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 1


def test_increment_safety_car_event_existing_type():
    """Test incrementing event count for an existing event type."""
    state = DetectorState(
        current_time_since_start=300.0,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 3}
    )
    
    state.increment_safety_car_event(DetectorEventTypes.RANDOM)
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 4


def test_increment_safety_car_event_multiple_types():
    """Test incrementing event counts for multiple event types."""
    state = DetectorState(
        current_time_since_start=300.0,
        safety_car_event_counts={DetectorEventTypes.RANDOM: 1}
    )
    
    # Increment different types
    state.increment_safety_car_event(DetectorEventTypes.STOPPED)
    state.increment_safety_car_event(DetectorEventTypes.OFF_TRACK)
    state.increment_safety_car_event(DetectorEventTypes.RANDOM)
    
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 2
    assert state.safety_car_event_counts[DetectorEventTypes.STOPPED] == 1
    assert state.safety_car_event_counts[DetectorEventTypes.OFF_TRACK] == 1


def test_increment_safety_car_event_multiple_increments():
    """Test multiple increments of the same event type."""
    state = DetectorState(
        current_time_since_start=300.0,
        safety_car_event_counts={}
    )
    
    # Increment same type multiple times
    for i in range(5):
        state.increment_safety_car_event(DetectorEventTypes.STOPPED)
    
    assert state.safety_car_event_counts[DetectorEventTypes.STOPPED] == 5


def test_detector_state_immutable_like_behavior():
    """Test that DetectorState behaves predictably with dict operations."""
    original_counts = {DetectorEventTypes.RANDOM: 2, DetectorEventTypes.STOPPED: 1}
    state = DetectorState(
        current_time_since_start=300.0,
        safety_car_event_counts=original_counts.copy()  # Copy to avoid mutation
    )
    
    # Modify the state's counts
    state.increment_safety_car_event(DetectorEventTypes.RANDOM)
    
    # Original dict should be unchanged
    assert original_counts[DetectorEventTypes.RANDOM] == 2
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 3


def test_detector_state_with_all_event_types():
    """Test DetectorState with all possible event types."""
    state = DetectorState(
        current_time_since_start=600.0,
        safety_car_event_counts={
            DetectorEventTypes.RANDOM: 3,
            DetectorEventTypes.STOPPED: 5,
            DetectorEventTypes.OFF_TRACK: 2
        }
    )
    
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 3
    assert state.safety_car_event_counts[DetectorEventTypes.STOPPED] == 5
    assert state.safety_car_event_counts[DetectorEventTypes.OFF_TRACK] == 2
    
    # Increment each type
    state.increment_safety_car_event(DetectorEventTypes.RANDOM)
    state.increment_safety_car_event(DetectorEventTypes.STOPPED)
    state.increment_safety_car_event(DetectorEventTypes.OFF_TRACK)
    
    assert state.safety_car_event_counts[DetectorEventTypes.RANDOM] == 4
    assert state.safety_car_event_counts[DetectorEventTypes.STOPPED] == 6
    assert state.safety_car_event_counts[DetectorEventTypes.OFF_TRACK] == 3