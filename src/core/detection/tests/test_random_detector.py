import pytest
from core.detection.random_detector import RandomDetector

def test_random_detector_initialization():
    detector = RandomDetector(chance=0.5, start_minute=10, end_minute=20)
    assert detector.chance == 0.5
    assert detector.len_of_window == 600  # (20-10)*60

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
    assert detector.detect() is False

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
        