"""End-to-end integration tests for the complete detection pipeline.

Tests the full workflow from individual detectors through the unified Detector system
to ThresholdChecker and final safety car decision. Focuses on realistic racing scenarios
with multiple detectors, proximity clustering, and complex threshold interactions.
"""

import pytest
import time

from irsdk import TrkLoc
from core.detection.detector import Detector, DetectorSettings
from core.detection.threshold_checker import ThresholdChecker, ThresholdCheckerSettings, DetectorEventTypes
from core.tests.test_utils import make_driver, MockDrivers, dict_to_config


@pytest.fixture
def racing_drivers():
    """Create realistic racing grid with 20 drivers spread around track."""
    current = []
    previous = []
    
    # Create 20 drivers with realistic lap distances (spread around track)
    for i in range(20):
        lap_distance = (i * 0.05) % 1.0  # Spread around track: 0.0, 0.05, 0.10, ..., 0.95
        current.append(make_driver(
            track_loc=TrkLoc.on_track,
            driver_idx=i,
            lap_distance=lap_distance,
            laps_completed=5
        ))
        # Previous positions slightly behind current for movement detection
        # Handle wraparound at start/finish line properly
        prev_distance = lap_distance - 0.02
        if prev_distance < 0:
            prev_distance = prev_distance + 1.0  # Wrap around track
            prev_laps = 4  # One less lap completed
        else:
            prev_laps = 5
            
        previous.append(make_driver(
            track_loc=TrkLoc.on_track,
            driver_idx=i, 
            lap_distance=prev_distance,
            laps_completed=prev_laps
        ))
    
    return MockDrivers(current, previous)


@pytest.fixture
def full_detection_system(racing_drivers):
    """Create complete detection system with all detectors enabled."""
    # Settings that enable all detector types
    settings_dict = {
        "settings": {
            # Detector enables
            "random": "1",
            "stopped": "1", 
            "off": "1",
            # Random detector settings
            "random_prob": "0.1",
            "start_minute": "0",
            "end_minute": "30", 
            "random_max_occ": "5",
            # Threshold settings
            "off_min": "3",
            "stopped_min": "2", 
            # Dynamic threshold settings
            "start_multi_val": "0.5",  # Half threshold at start
            "start_multi_time": "300",  # For 5 minutes
            # Proximity settings
            "proximity_yellows": "1",
            "proximity_yellows_distance": "0.1",  # 10% of track
        }
    }
    
    settings = dict_to_config(settings_dict)
    
    # Create detector system
    detector_settings = DetectorSettings.from_settings(settings)
    detector = Detector.build_detector(detector_settings, racing_drivers)
    
    # Create threshold checker with controlled session start time for testing
    threshold_settings = ThresholdCheckerSettings.from_settings(settings, session_start_time=1000.0)
    threshold_checker = ThresholdChecker(threshold_settings)
    
    return detector, threshold_checker, racing_drivers


class TestEndToEndDetectionPipeline:
    """Test complete detection workflow from individual detectors to safety car decision."""
    
    def test_single_detector_end_to_end_workflow(self, full_detection_system, mocker):
        """Test complete workflow with single detector type triggering threshold."""
        detector, threshold_checker, drivers = full_detection_system
        mocker.patch("time.time", return_value=1000.0)
        
        # Create scenario: 3 off-track cars in proximity (should trigger threshold)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track  
        drivers.current_drivers[2]["track_loc"] = TrkLoc.off_track
        # Cars 0, 1, 2 are at positions 0.0, 0.05, 0.10 - all within 0.1 proximity
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Step 1: Run detection
        detector_results = detector.detect()
        
        # Step 2: Register results with threshold checker
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Step 3: Check if threshold is met
        assert threshold_checker.threshold_met() == True
        
        # Verify the detection pipeline worked correctly
        off_track_result = detector_results.get_events(DetectorEventTypes.OFF_TRACK)
        assert off_track_result is not None
        assert len(off_track_result.drivers) == 3
        
    def test_multiple_detectors_mixed_events_proximity_clustering(self, full_detection_system, mocker):
        """Test multiple detector types triggering with proximity clustering."""
        detector, threshold_checker, drivers = full_detection_system
        mocker.patch("time.time", return_value=1000.0)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Create mixed scenario: stopped + off-track cars in same proximity cluster
        # Cluster 1: Cars 0-2 (positions 0.0, 0.05, 0.10)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        drivers.current_drivers[1] = make_driver(track_loc=TrkLoc.on_track, driver_idx=1, lap_distance=0.05, laps_completed=5)  # Stopped
        drivers.previous_drivers[1] = make_driver(track_loc=TrkLoc.on_track, driver_idx=1, lap_distance=0.05, laps_completed=5)  # Same position = stopped
        drivers.current_drivers[2]["track_loc"] = TrkLoc.off_track
        
        # Cluster 2: Cars 10-11 (positions 0.50, 0.55) - not enough for individual thresholds
        drivers.current_drivers[10]["track_loc"] = TrkLoc.off_track
        
        # Run complete detection pipeline
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Should meet threshold due to mixed events in proximity cluster 1
        assert threshold_checker.threshold_met() == True
        
        # Verify both detector types detected events
        off_track_result = detector_results.get_events(DetectorEventTypes.OFF_TRACK)
        stopped_result = detector_results.get_events(DetectorEventTypes.STOPPED)
        
        assert off_track_result is not None
        assert stopped_result is not None
        assert len(off_track_result.drivers) >= 2  # Cars 0, 2, 10
        assert len(stopped_result.drivers) >= 1   # Car 1
        
    def test_proximity_clustering_prevents_false_positives(self, full_detection_system, mocker):
        """Test that proximity clustering prevents false positives from spread out incidents."""
        detector, threshold_checker, drivers = full_detection_system
        mocker.patch("time.time", return_value=1000.0)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Create scenario: enough incidents individually but spread out (no proximity)
        # 4 off-track cars spread around track (threshold is 3, but they're not in proximity)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track   # Position 0.0
        drivers.current_drivers[5]["track_loc"] = TrkLoc.off_track   # Position 0.25  
        drivers.current_drivers[10]["track_loc"] = TrkLoc.off_track  # Position 0.50
        drivers.current_drivers[15]["track_loc"] = TrkLoc.off_track  # Position 0.75
        # All separated by > 0.1 track distance (proximity threshold)
        
        # Run detection pipeline
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events() 
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Should NOT meet threshold due to proximity filtering
        assert threshold_checker.threshold_met() == False
        
        # Verify events were detected but proximity prevented threshold
        off_track_result = detector_results.get_events(DetectorEventTypes.OFF_TRACK)
        assert off_track_result is not None
        assert len(off_track_result.drivers) == 4  # All 4 detected
        
    def test_accumulative_threshold_cross_event_types(self, full_detection_system, mocker):
        """Test accumulative threshold calculation across different event types."""
        detector, threshold_checker, drivers = full_detection_system
        mocker.patch("time.time", return_value=1000.0)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Create scenario that meets accumulative but not individual thresholds
        # 1 stopped (weight 2.0) + 2 off-track (weight 1.0 each) = 4.0 total
        # Individual thresholds: OFF_TRACK=3, STOPPED=2 (not met individually)
        # Accumulative threshold: 10.0 (not met with standard weights)
        # But with dynamic threshold (0.5 multiplier): 5.0 (should be met: 4.0 < 5.0)
        
        # Create tight cluster of mixed events
        drivers.current_drivers[0] = make_driver(track_loc=TrkLoc.on_track, driver_idx=0, lap_distance=0.05, laps_completed=5)  # Stopped
        drivers.previous_drivers[0] = make_driver(track_loc=TrkLoc.on_track, driver_idx=0, lap_distance=0.05, laps_completed=5)  # Same = stopped
        
        # Update drivers 1 and 2 to be off-track but still moving
        drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track  # Off track
        drivers.current_drivers[1]["lap_distance"] = 0.06
        drivers.previous_drivers[1]["lap_distance"] = 0.05  # Was at 0.05, now at 0.06 (moving)
        
        drivers.current_drivers[2]["track_loc"] = TrkLoc.off_track  # Off track  
        drivers.current_drivers[2]["lap_distance"] = 0.07
        drivers.previous_drivers[2]["lap_distance"] = 0.06  # Was at 0.06, now at 0.07 (moving)
        
        # Run detection pipeline
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Should meet threshold due to accumulative weight calculation with dynamic scaling
        # Note: This depends on your exact accumulative threshold settings
        assert threshold_checker.threshold_met() == True
        
        # Verify mixed event types were detected
        off_track_result = detector_results.get_events(DetectorEventTypes.OFF_TRACK)
        stopped_result = detector_results.get_events(DetectorEventTypes.STOPPED)
        
        assert off_track_result is not None
        assert stopped_result is not None
        assert len(stopped_result.drivers) == 1
        assert len(off_track_result.drivers) == 2
        
    def test_dynamic_threshold_scaling_integration(self, racing_drivers, mocker):
        """Test dynamic threshold scaling in complete detection pipeline."""
        mocker.patch("time.time", return_value=1000.0)
        
        # Settings with dynamic threshold enabled
        settings = dict_to_config({
            "settings": {
                "random": "0", "stopped": "1", "off": "1",
                # Random detector settings (even though disabled, still needed)
                "random_prob": "0.1", "start_minute": "0", "end_minute": "30", "random_max_occ": "1",
                "off_min": "4", "stopped_min": "4",  # High thresholds
                "start_multi_val": "0.5",  # Half threshold at start
                "start_multi_time": "300",  # For 5 minutes
                "proximity_yellows": "1",
                "proximity_yellows_distance": "0.1",
            }
        })
        
        detector_settings = DetectorSettings.from_settings(settings)
        detector = Detector.build_detector(detector_settings, racing_drivers)
        
        # Session just started - should get dynamic scaling
        threshold_settings = ThresholdCheckerSettings.from_settings(settings, session_start_time=1000.0)
        threshold_checker = ThresholdChecker(threshold_settings)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Create 2 off-track cars in proximity (normally not enough: 2 < 4)
        # But with 0.5 multiplier: effective threshold becomes 2
        racing_drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        racing_drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track
        racing_drivers.current_drivers[1]["lap_distance"] = 0.05  # Within proximity
        
        # Run detection pipeline
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Should meet threshold due to dynamic scaling
        assert threshold_checker.threshold_met() == True
        
    def test_random_detector_integration_workflow(self, mocker):
        """Test random detector integration with threshold system."""
        mocker.patch("time.time", return_value=1000.0)
        
        # Create minimal driver setup for random detector
        racing_drivers = MockDrivers([make_driver(track_loc=TrkLoc.on_track, driver_idx=0)], [make_driver(track_loc=TrkLoc.on_track, driver_idx=0)])
        
        settings = dict_to_config({
            "settings": {
                "random": "1", "stopped": "0", "off": "0",
                "random_prob": "1.0",  # 100% chance for testing
                "start_minute": "0", "end_minute": "30", "random_max_occ": "1",
                "off_min": "999", "stopped_min": "999",  # High thresholds for other types
                "start_multi_val": "1.0", "start_multi_time": "300",
                "proximity_yellows": "0",
                "proximity_yellows_distance": "0.05",
            }
        })
        
        detector_settings = DetectorSettings.from_settings(settings)  
        detector = Detector.build_detector(detector_settings, racing_drivers)
        
        threshold_settings = ThresholdCheckerSettings.from_settings(settings)
        threshold_checker = ThresholdChecker(threshold_settings)
        
        # Simulate race started to enable random detector
        detector.race_started(1000.0)
        
        # Force random detector to return True
        mocker.patch("random.random", return_value=0.0)  # Always < any positive chance
        
        # Run detection pipeline
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        # Random events have threshold of 1.0, so any detection should trigger
        assert threshold_checker.threshold_met() == True
        
        # Verify random detection occurred
        random_result = detector_results.get_events(DetectorEventTypes.RANDOM)
        assert random_result is not None
        assert random_result.detected_flag == True
        
    def test_large_grid_performance_end_to_end(self, mocker):
        """Test complete pipeline with large racing grid (40 cars)."""
        mocker.patch("time.time", return_value=1000.0)
        
        # Create 40-car grid with proper movement patterns
        current = []
        previous = []
        for i in range(40):
            lap_distance = (i * 0.025) % 1.0  # Spread around track
            current.append(make_driver(track_loc=TrkLoc.on_track, driver_idx=i, lap_distance=lap_distance, laps_completed=10))
            
            # Previous position behind current (same logic as racing_drivers fixture)
            prev_distance = lap_distance - 0.02
            if prev_distance < 0:
                prev_distance = prev_distance + 1.0
                prev_laps = 9  # One less lap completed
            else:
                prev_laps = 10
            previous.append(make_driver(track_loc=TrkLoc.on_track, driver_idx=i, lap_distance=prev_distance, laps_completed=prev_laps))
        
        large_grid = MockDrivers(current, previous)
        
        settings = dict_to_config({
            "settings": {
                "random": "0", "stopped": "1", "off": "1",
                # Random detector settings (even though disabled, still needed)
                "random_prob": "0.1", "start_minute": "0", "end_minute": "30", "random_max_occ": "1",
                "off_min": "5", "stopped_min": "3",
                "start_multi_val": "1.0", "start_multi_time": "300",
                "proximity_yellows": "1", "proximity_yellows_distance": "0.1",
            }
        })
        
        detector_settings = DetectorSettings.from_settings(settings)
        detector = Detector.build_detector(detector_settings, large_grid)
        
        threshold_settings = ThresholdCheckerSettings.from_settings(settings)
        threshold_checker = ThresholdChecker(threshold_settings)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Create incident affecting 8 cars in tight formation (positions 0.0-0.175)
        for i in range(8):
            if i % 2 == 0:
                large_grid.current_drivers[i]["track_loc"] = TrkLoc.off_track
            else:
                # Stopped cars - same position as previous
                large_grid.current_drivers[i]["lap_distance"] = large_grid.previous_drivers[i]["lap_distance"]
        
        # Run detection pipeline
        start_time = time.time()
        detector_results = detector.detect()
        
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        threshold_met = threshold_checker.threshold_met()
        end_time = time.time()
        
        # Verify performance (should complete quickly even with 40 cars)
        processing_time = end_time - start_time
        assert processing_time < 0.1  # Should complete in < 100ms
        
        # Verify correct detection with large grid
        assert threshold_met == True
        
        off_track_result = detector_results.get_events(DetectorEventTypes.OFF_TRACK)
        stopped_result = detector_results.get_events(DetectorEventTypes.STOPPED)
        
        assert off_track_result is not None
        assert stopped_result is not None
        assert len(off_track_result.drivers) == 4  # Cars 0, 2, 4, 6
        assert len(stopped_result.drivers) == 4   # Cars 1, 3, 5, 7
        
    def test_sequential_event_registration_consistency(self, full_detection_system, mocker):
        """Test that multiple detection cycles maintain consistent state."""
        detector, threshold_checker, drivers = full_detection_system
        mocker.patch("time.time", return_value=1000.0)
        
        # Initialize detector (simulate race start)
        detector.race_started(1000.0)
        
        # Cycle 0: Single incident - should not meet threshold
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        
        # Run first detection cycle
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        cycle0_threshold_met = threshold_checker.threshold_met()
        
        # Cycle 1: Two incidents in proximity - should meet threshold (2 >= 1.5 with dynamic scaling)
        drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        cycle1_threshold_met = threshold_checker.threshold_met()
        
        # Cycle 2: Add more incidents (simulate time progression)
        mocker.patch("time.time", return_value=1001.0)
        drivers.current_drivers[2]["track_loc"] = TrkLoc.off_track  # Another off track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        cycle2_threshold_met = threshold_checker.threshold_met()
        
        # Cycle 3: Incidents clear (cars return to track)
        mocker.patch("time.time", return_value=1002.0)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.on_track  # Back on track
        drivers.current_drivers[1]["track_loc"] = TrkLoc.on_track  # Back on track  
        drivers.current_drivers[2]["track_loc"] = TrkLoc.on_track  # Back on track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        cycle3_threshold_met = threshold_checker.threshold_met()
        
        # Verify state consistency across cycles
        # With dynamic threshold scaling (0.5x), OFF_TRACK threshold becomes 1.5
        assert cycle0_threshold_met == False  # 1 car doesn't meet threshold (1 < 1.5)
        assert cycle1_threshold_met == True   # 2 cars in proximity meet threshold (2 >= 1.5)
        assert cycle2_threshold_met == True   # 3 cars definitely meet threshold
        assert cycle3_threshold_met == True   # Events still in time window
        
        # Cycle 4: Wait for event cleanup (simulate time passing beyond time_range)
        mocker.patch("time.time", return_value=1020.0)  # 20 seconds later
        threshold_checker.clean_up_events()
        cycle4_threshold_met = threshold_checker.threshold_met()
        
        assert cycle4_threshold_met == False  # Events should be cleaned up
        
    def test_dynamic_threshold_time_boundary_transition(self, full_detection_system, mocker):
        """Test that dynamic thresholds stop applying after start_multi_time expires."""
        detector, threshold_checker, drivers = full_detection_system
        
        # Initialize detector (simulate race start at time 1000.0)
        detector.race_started(1000.0)
        
        # Phase 1: Early in race (within start_multi_time=300s) - dynamic scaling active
        mocker.patch("time.time", return_value=1100.0)  # 100 seconds into race
        
        # Create scenario: 2 off-track cars (normally threshold=3, but with 0.5x = 1.5)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        phase1_threshold_met = threshold_checker.threshold_met()
        
        # Reset cars to on-track
        drivers.current_drivers[0]["track_loc"] = TrkLoc.on_track  
        drivers.current_drivers[1]["track_loc"] = TrkLoc.on_track
        
        # Phase 2: Late in race (after start_multi_time=300s) - no dynamic scaling
        mocker.patch("time.time", return_value=1400.0)  # 400 seconds into race (> 300s)
        
        # Wait for event cleanup
        threshold_checker.clean_up_events()
        
        # Create same scenario: 2 off-track cars (now full threshold=3.0 applies)
        drivers.current_drivers[0]["track_loc"] = TrkLoc.off_track
        drivers.current_drivers[1]["track_loc"] = TrkLoc.off_track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events() 
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        phase2_threshold_met = threshold_checker.threshold_met()
        
        # Phase 3: Add third car to meet full threshold
        drivers.current_drivers[2]["track_loc"] = TrkLoc.off_track
        
        detector_results = detector.detect()
        threshold_checker.clean_up_events()
        for event_type in DetectorEventTypes:
            detection_result = detector_results.get_events(event_type)
            if detection_result:
                threshold_checker.register_detection_result(detection_result)
        
        phase3_threshold_met = threshold_checker.threshold_met()
        
        # Verify dynamic threshold behavior
        assert phase1_threshold_met == True   # 2 cars meet reduced threshold (1.5) 
        assert phase2_threshold_met == False  # 2 cars don't meet full threshold (3.0)
        assert phase3_threshold_met == True   # 3 cars meet full threshold (3.0)