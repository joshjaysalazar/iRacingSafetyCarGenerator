import pytest
import time
import math
from unittest.mock import MagicMock
from core.generator import Generator

@pytest.fixture
def generator():
    mock_arguments = MagicMock()
    mock_arguments.disable_window_interactions = True
    mock_master = MagicMock()
    mock_master.settings = {
        "settings": {
            "start_multi_val": "1.5",
            "start_multi_time": "300"
        }
    }
    gen = Generator(arguments=mock_arguments, master=mock_master)
    gen.start_time = 0  # Simulate the start time as 0 for testing
    return gen

def test_threshold_no_multiplier(generator):
    """Test when multiplier is 0."""
    generator.master.settings["settings"]["start_multi_val"] = "0"
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold

def test_threshold_no_adjustment(generator):
    """Test when adjustment time has passed."""
    generator.master.settings["settings"]["start_multi_time"] = "0"
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold

def test_threshold_with_multiplier(generator):
    """Test when multiplier is applied."""
    generator.start_time = time.time() - 295  # Simulate 295 seconds since start
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    expected = math.ceil(threshold * 1.5)  # Multiplier is 1.5
    assert result == expected

def test_threshold_no_adjustment_due_to_time(generator):
    """Test when adjustment time has passed."""
    generator.start_time = time.time() - 301  # Simulate 301 seconds since start
    threshold = 5
    result = generator._calc_dynamic_yellow_threshold(threshold)
    assert result == threshold