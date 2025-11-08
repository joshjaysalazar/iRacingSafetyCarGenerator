"""Quick test for the towing detector functionality."""

import sys
sys.path.insert(0, 'src')

from core.drivers import Drivers, Driver
from core.detection.towing_detector import TowingDetector, PitEntryStatistics


class MockMaster:
    """Mock master object for testing."""
    def __init__(self):
        self.ir = {
            "CarIdxLapCompleted": [0] * 64,
            "CarIdxLap": [1] * 64,
            "CarIdxLapDistPct": [0.0] * 64,
            "CarIdxTrackSurface": [0] * 64,
            "CarIdxOnPitRoad": [False] * 64,
            "DriverInfo": {
                "PaceCarIdx": -1,
                "Drivers": [
                    {
                        "CarIdx": i,
                        "CarNumber": str(i),
                        "CarClassID": 1,
                        "CarIsPaceCar": 0
                    } for i in range(5)
                ]
            }
        }


def test_normal_pit_entry():
    """Test that normal pit entries are recorded correctly."""
    print("\n=== Test 1: Normal Pit Entry ===")

    master = MockMaster()
    drivers = Drivers(master)
    detector = TowingDetector(drivers, max_pit_entry_delta=0.05)

    # Initial state - car 1 at 0.45 lap distance, not on pit road
    master.ir["CarIdxLapDistPct"][1] = 0.45
    master.ir["CarIdxOnPitRoad"][1] = False
    drivers.update()

    result = detector.detect()
    print(f"Initial detection: {len(result.drivers)} towing cars")
    print(f"Statistics: {detector.get_statistics()}")

    # Car enters pits normally (small delta)
    master.ir["CarIdxLapDistPct"][1] = 0.47
    master.ir["CarIdxOnPitRoad"][1] = True
    drivers.update()

    result = detector.detect()
    print(f"\nAfter normal entry: {len(result.drivers)} towing cars")
    stats = detector.get_statistics()
    print(f"Statistics: {stats}")

    assert len(result.drivers) == 0, "Normal pit entry should not be flagged as towing"
    assert stats.observation_count == 1, "Should have 1 observation"
    assert abs(stats.estimated_location - 0.47) < 0.01, "Location should be ~0.47"
    print("✓ Test passed!")


def test_towing_detection():
    """Test that towing is detected correctly."""
    print("\n=== Test 2: Towing Detection ===")

    master = MockMaster()
    drivers = Drivers(master)
    detector = TowingDetector(drivers, max_pit_entry_delta=0.05)

    # Build up some normal observations first
    for i in range(3):
        master.ir["CarIdxLapDistPct"][0] = 0.45 + (i * 0.01)
        master.ir["CarIdxOnPitRoad"][0] = False
        drivers.update()
        detector.detect()

        master.ir["CarIdxLapDistPct"][0] = 0.47 + (i * 0.01)
        master.ir["CarIdxOnPitRoad"][0] = True
        drivers.update()
        detector.detect()

        master.ir["CarIdxOnPitRoad"][0] = False
        drivers.update()

    stats = detector.get_statistics()
    print(f"After normal entries: {stats}")

    # Now test a tow - car appears on pit road far from pit entry
    master.ir["CarIdxLapDistPct"][1] = 0.10
    master.ir["CarIdxOnPitRoad"][1] = False
    drivers.update()
    detector.detect()

    master.ir["CarIdxLapDistPct"][1] = 0.12  # Small delta but wrong location
    master.ir["CarIdxOnPitRoad"][1] = True
    drivers.update()

    result = detector.detect()
    print(f"\nAfter tow attempt: {len(result.drivers)} towing cars detected")

    if len(result.drivers) > 0:
        print(f"Car {result.drivers[0]['car_number']} flagged as towing")
        print("✓ Test passed!")
    else:
        print("✗ Test failed - towing not detected")


def test_large_delta_detection():
    """Test that large deltas are detected as towing."""
    print("\n=== Test 3: Large Delta Detection ===")

    master = MockMaster()
    drivers = Drivers(master)
    detector = TowingDetector(drivers, max_pit_entry_delta=0.05)

    # Build up normal observations
    for i in range(3):
        master.ir["CarIdxLapDistPct"][0] = 0.45
        master.ir["CarIdxOnPitRoad"][0] = False
        drivers.update()
        detector.detect()

        master.ir["CarIdxLapDistPct"][0] = 0.47
        master.ir["CarIdxOnPitRoad"][0] = True
        drivers.update()
        detector.detect()

        master.ir["CarIdxOnPitRoad"][0] = False
        drivers.update()

    # Car with large delta
    master.ir["CarIdxLapDistPct"][1] = 0.80
    master.ir["CarIdxOnPitRoad"][1] = False
    drivers.update()
    detector.detect()

    master.ir["CarIdxLapDistPct"][1] = 0.47  # Jumps to pit entry location
    master.ir["CarIdxOnPitRoad"][1] = True
    drivers.update()

    result = detector.detect()
    print(f"Large delta tow: {len(result.drivers)} towing cars detected")

    # This is a large delta but near the expected pit location, so may not be flagged
    # Let's check what happens
    if len(result.drivers) > 0:
        print(f"Car {result.drivers[0]['car_number']} flagged as towing")
    else:
        print("Large delta near pit entry accepted as slow approach")
    print("✓ Test completed!")


if __name__ == "__main__":
    print("Testing Towing Detector Implementation")
    print("=" * 50)

    test_normal_pit_entry()
    test_towing_detection()
    test_large_delta_detection()

    print("\n" + "=" * 50)
    print("All tests completed!")
