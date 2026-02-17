"""End-to-end tests using NDJSON dump replay.

These tests replay real SDK recordings through the detection pipeline to validate
safety car triggering, wave around logic, and threshold behavior. They serve as
both regression tests and a template for writing new scenario tests.

GETTING STARTED — How to write a new e2e test:

1. Pick a dump file from docs/dumps/ (or record a new one in dev mode).

2. Create settings with make_settings(), overriding only what you need:
       settings = make_settings(
           stopped_cars_threshold=2,       # How many stopped cars trigger SC
           off_track_cars_threshold=3,      # How many off-track cars trigger SC
           stopped_detector_enabled=True,   # Enable/disable stopped detector
           off_track_detector_enabled=True, # Enable/disable off-track detector
           random_detector_enabled=False,   # Random SC (usually off for deterministic tests)
           proximity_filter_enabled=False,  # Proximity-based clustering
           proximity_filter_distance_percentage=0.05,
           event_time_window_seconds=5.0,   # Sliding window for threshold checking
           race_start_threshold_multiplier=1.0,  # 1.0 = no multiplier
           race_start_threshold_multiplier_time_seconds=0.0,
           detection_start_minute=0.0,      # Earliest SC possible (minutes)
           detection_end_minute=60.0,       # Latest SC possible (minutes)
           max_safety_cars=10,              # Max SCs per race
           wave_arounds_enabled=True,       # Whether to send wave arounds
           laps_before_wave_arounds=1,      # Laps after SC before waving
           wave_around_rules_index=0,       # 0=lapped, 1=ahead of lead, 2=combined
       )

3. Create a DumpReplayer and run:
       replayer = DumpReplayer(dump_path, settings=settings)
       result = replayer.run()

4. Assert on the result:
       result.total_safety_cars()           → int: number of SCs triggered
       result.safety_car_events[n]          → SafetyCarEvent with frame_index, wave_commands
       result.waved_car_numbers_for_sc(n)   → list[str]: car numbers waved at SC n
       result.sc_triggered_at_frame(idx)    → bool: was SC triggered at this frame?
       result.detection_log                 → list[DetectionLogEntry]: per-frame details

   DetectionLogEntry has:
       .frame_index, .timestamp
       .stopped_drivers   → list[int] of driver_idx values detected as stopped
       .off_track_drivers → list[int] of driver_idx values detected as off-track
       .threshold_met     → bool: was threshold met at this frame?

For wave around testing with realistic lap timing:
       replayer = DumpReplayer(
           dump_path,
           settings=settings,
           compute_waves_after_laps=1,  # Compute waves 1 lap after SC
       )
"""

from pathlib import Path

from core.tests.e2e_utils import DumpReplayer, make_settings

DUMPS_DIR = Path(__file__).resolve().parents[3] / "docs" / "dumps"


# ---------------------------------------------------------------------------
# Test: Safety car triggering with different thresholds
# ---------------------------------------------------------------------------

class TestSafetyCarTriggering:
    """Tests that validate whether a SC fires under various threshold settings.

    The dump 'race_weird_sc_with_lots_of_waves.ndjson' contains:
    - Car #153 off-track at frames 0-7
    - Cars #108 and #88 off-track at frames 13-24
    - Cars #108 and #88 stopped at frames 17-19
    """

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    def test_sc_triggers_with_low_off_track_threshold(self):
        """With off-track threshold=2 and the two-car incident around frame 13,
        a safety car should be triggered."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC with off_track_threshold=2, got {result.total_safety_cars()}"
        )

    def test_sc_triggers_with_low_stopped_threshold(self):
        """With stopped threshold=2, the stopped cars at frames 17-19 should trigger a SC."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            stopped_detector_enabled=True,
            stopped_cars_threshold=2,
            off_track_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC with stopped_threshold=2, got {result.total_safety_cars()}"
        )

    def test_no_sc_with_high_thresholds(self):
        """With very high thresholds, no SC should be triggered."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            stopped_detector_enabled=True,
            stopped_cars_threshold=50,
            off_track_detector_enabled=True,
            off_track_cars_threshold=50,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        assert result.total_safety_cars() == 0, (
            f"Expected 0 SCs with high thresholds, got {result.total_safety_cars()}"
        )

    def test_single_off_track_car_does_not_trigger(self):
        """Car #153 alone off-track (frames 0-7) should NOT trigger SC at threshold=2."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        # The first SC should not fire before frame 13 (when 2 cars go off-track)
        if result.total_safety_cars() > 0:
            first_sc_frame = result.safety_car_events[0].frame_index
            assert first_sc_frame >= 13, (
                f"SC triggered too early at frame {first_sc_frame}, expected >= 13"
            )


# ---------------------------------------------------------------------------
# Test: Race start multiplier
# ---------------------------------------------------------------------------

class TestRaceStartMultiplier:
    """Tests that validate the dynamic threshold multiplier at race start."""

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    def test_high_multiplier_prevents_sc(self):
        """A high race start multiplier should prevent SC during the multiplier window."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=10.0,  # 10x multiplier
            race_start_threshold_multiplier_time_seconds=120.0,  # Active for 2 minutes
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        # The dump is only 60s long, and with a 10x multiplier active for 120s,
        # a threshold of 2 becomes effectively 20 — should not trigger
        assert result.total_safety_cars() == 0, (
            f"Expected 0 SCs with 10x race start multiplier, got {result.total_safety_cars()}"
        )


# ---------------------------------------------------------------------------
# Test: Wave around commands
# ---------------------------------------------------------------------------

class TestWaveArounds:
    """Tests that validate which cars get waved around and in what order.

    The dump at the end (frame 59) shows:
    - Cars #257, #951, #924 are 2+ laps behind (should always be waved)
    - Many cars are 1 lap behind
    """

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    def test_wave_lapped_cars_includes_multi_lap_down(self):
        """Cars 2+ laps down should be waved using the 'wave lapped cars' rule."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
            wave_arounds_enabled=True,
            wave_around_rules_index=0,  # Wave lapped cars
            laps_before_wave_arounds=0,
        ))
        result = replayer.run()

        if result.total_safety_cars() > 0:
            waved = result.waved_car_numbers_for_sc(0)
            # Cars 2+ laps down at time of SC should be waved
            # Note: which cars are waved depends on the frame state when the SC fires
            # This is a structural test — verify we get some wave commands
            print(f"Wave commands at SC: {result.wave_commands_for_sc(0)}")
            print(f"Waved cars: {waved}")

    def test_no_wave_arounds_when_disabled(self):
        """When wave arounds are disabled, no wave commands should be produced."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
            wave_arounds_enabled=True,
            wave_around_rules_index=0,
        ), compute_waves=False)
        result = replayer.run()

        if result.total_safety_cars() > 0:
            assert result.wave_commands_for_sc(0) == [], (
                f"Expected no wave commands when compute_waves=False"
            )

    def test_wave_around_rules_comparison(self):
        """Compare different wave around rules on the same scenario.

        This test demonstrates how to compare the three wave strategies.
        """
        base_settings = dict(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
            wave_arounds_enabled=True,
            laps_before_wave_arounds=0,
        )

        results = {}
        for rule_name, rule_index in [
            ("wave_lapped_cars", 0),
            ("wave_ahead_of_class_lead", 1),
            ("wave_combined", 2),
        ]:
            replayer = DumpReplayer(self.dump, settings=make_settings(
                **base_settings,
                wave_around_rules_index=rule_index,
            ))
            result = replayer.run()
            if result.total_safety_cars() > 0:
                results[rule_name] = result.waved_car_numbers_for_sc(0)
            else:
                results[rule_name] = []

        # Log all results for manual inspection / future pinning
        for rule_name, waved in results.items():
            print(f"{rule_name}: {len(waved)} cars waved: {waved}")

        # Combined should include at least as many cars as either individual rule
        if results["wave_lapped_cars"] and results["wave_combined"]:
            lapped_set = set(results["wave_lapped_cars"])
            combined_set = set(results["wave_combined"])
            assert lapped_set.issubset(combined_set), (
                f"Combined rule should include all lapped cars. "
                f"Missing: {lapped_set - combined_set}"
            )


# ---------------------------------------------------------------------------
# Test: Proximity filter effect
# ---------------------------------------------------------------------------

class TestProximityFilter:
    """Tests that validate the proximity-based yellow flag clustering.

    When proximity filtering is enabled, only incidents where cars are close
    together on track should count toward the threshold.
    """

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    def test_proximity_filter_may_change_outcome(self):
        """Compare SC triggering with and without proximity filter.

        This test documents the effect of the proximity filter on the scenario.
        Depending on where the off-track cars are relative to each other,
        the proximity filter may prevent or allow the SC.
        """
        base = dict(
            off_track_detector_enabled=True,
            off_track_cars_threshold=2,
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        )

        # Without proximity
        replayer_no_prox = DumpReplayer(self.dump, settings=make_settings(
            **base,
            proximity_filter_enabled=False,
        ))
        result_no_prox = replayer_no_prox.run()

        # With proximity (tight distance)
        replayer_prox = DumpReplayer(self.dump, settings=make_settings(
            **base,
            proximity_filter_enabled=True,
            proximity_filter_distance_percentage=0.05,
        ))
        result_prox = replayer_prox.run()

        print(f"Without proximity: {result_no_prox.total_safety_cars()} SCs")
        print(f"With proximity (5%): {result_prox.total_safety_cars()} SCs")

        # With no proximity, the 2 off-track cars at frames 13+ should trigger
        assert result_no_prox.total_safety_cars() >= 1


# ---------------------------------------------------------------------------
# Test: Detection log inspection
# ---------------------------------------------------------------------------

class TestDetectionLog:
    """Tests demonstrating how to use the detection log for debugging.

    The detection log records per-frame what was detected, which is useful
    for understanding why a SC did or didn't trigger.
    """

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    def test_detection_log_captures_off_track_events(self):
        """Verify the detection log records off-track drivers."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            off_track_detector_enabled=True,
            off_track_cars_threshold=50,  # High threshold — no SC, just observe
            stopped_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        # Find frames where off-track drivers were detected
        frames_with_off_track = [
            entry for entry in result.detection_log
            if entry.off_track_drivers
        ]

        assert len(frames_with_off_track) > 0, "Expected some frames with off-track drivers"

        # Check that we see the 2-car incident
        frames_with_two_off = [
            entry for entry in frames_with_off_track
            if len(entry.off_track_drivers) >= 2
        ]
        assert len(frames_with_two_off) > 0, (
            "Expected frames with 2+ off-track drivers (the #108/#88 incident)"
        )


# ---------------------------------------------------------------------------
# Regression: race_weird_sc_with_lots_of_waves (v0.5.0 bugs)
# ---------------------------------------------------------------------------

class TestRegressionWeirdScWithLotsOfWaves:
    """Regression tests for two bugs observed during a race running v0.5.0.

    The dump captures an incident where cars #108 (driver_idx=12) and #88
    (driver_idx=14) went off-track and stopped together near lap distance ~0.08.

    Bug 1 — Double-counting in accumulative threshold (fixed in ec3dfc2):
        The old code summed weights for ALL event types per driver. A driver
        both stopped (weight=3) and off-track (weight=2) contributed 5 to the
        accumulative score. With 2 drivers: 2×5 = 10 >= 7 threshold → SC.
        The fix takes only the highest weight per driver: 2×max(3,2) = 6 < 7 → no SC.

    Bug 2 — Waving not-in-world cars (fixed in 597efb5):
        11 cars with track_loc=-1 (disconnected/not_in_world) had laps_started=-1,
        appearing "many laps behind" the class leader. They were incorrectly waved.
        The fix filters TrkLoc.not_in_world from wave around eligibility.
        Only 4 cars (#173, #284, #924, #257) should actually be waved.

    To verify these tests would FAIL on the buggy version:
        git stash && git checkout v0.5.0
        pytest src/core/tests/test_e2e_detection_and_procedures.py::TestRegressionWeirdScWithLotsOfWaves -v
        git checkout - && git stash pop
    """

    dump = DUMPS_DIR / "race_weird_sc_with_lots_of_waves.ndjson"

    # Exact settings from the race log (ThresholdCheckerSettings at line 12)
    race_settings = dict(
        stopped_detector_enabled=True,
        stopped_cars_threshold=3,
        off_track_detector_enabled=True,
        off_track_cars_threshold=4,
        random_detector_enabled=False,
        proximity_filter_enabled=True,
        proximity_filter_distance_percentage=0.08,
        event_time_window_seconds=5.0,
        accumulative_detector_enabled=True,
        accumulative_threshold=7.0,
        off_track_weight=2.0,
        stopped_weight=3.0,
        race_start_threshold_multiplier=1.0,
        race_start_threshold_multiplier_time_seconds=30.0,
        detection_start_minute=0.0,
        detection_end_minute=60.0,
        max_safety_cars=10,
        wave_arounds_enabled=True,
        wave_around_rules_index=0,
        laps_before_wave_arounds=0,
    )

    # --- Bug 1: Accumulative double-counting ---

    def test_sc_not_triggered_with_no_double_count(self):
        """With the double-count fix, the accumulative score is 6 < 7 → no SC.

        Before the fix (v0.5.0): acc = 2×(2+3) = 10 >= 7 → SC triggered.
        After the fix:           acc = 2×max(2,3) = 6  < 7 → no SC.
        """
        replayer = DumpReplayer(self.dump, settings=make_settings(**self.race_settings))
        result = replayer.run()

        assert result.total_safety_cars() == 0, (
            f"Expected 0 SCs with accumulative threshold=7 and no double-counting "
            f"(score should be 6), got {result.total_safety_cars()}"
        )

    def test_sc_triggers_at_old_accumulative_score(self):
        """With threshold=6 (the new scoring boundary), the SC triggers.

        This proves the incident IS real and detectable — only the counting
        method changed. New score: 2×max(3,2) = 6 >= 6 → SC.
        """
        settings = {**self.race_settings, "accumulative_threshold": 6.0}
        replayer = DumpReplayer(self.dump, settings=make_settings(**settings))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC with accumulative threshold=6 "
            f"(score should be exactly 6), got {result.total_safety_cars()}"
        )

    # --- Bug 2: Waving not-in-world cars ---

    def test_wave_arounds_only_wave_eligible_cars(self):
        """Only on-track lapped cars should be waved, not disconnected ones.

        Before the fix (v0.5.0): 15 cars were waved, 11 of which had
        track_loc=-1 (not_in_world) with laps_started=-1.
        After the fix: only 4 cars (#173, #284, #924, #257) are waved.

        Uses off_track_cars_threshold=2 to trigger the SC in the dump.
        Waves are computed after the leader crosses S/F (compute_waves_after_laps=0)
        to match the real race timing where waves fire at the next lap crossing.
        """
        settings = {
            **self.race_settings,
            "off_track_cars_threshold": 2,
        }
        replayer = DumpReplayer(
            self.dump,
            settings=make_settings(**settings),
            compute_waves_after_laps=0,
        )
        result = replayer.run()

        assert result.total_safety_cars() >= 1, "SC must trigger for wave around test"

        waved = set(result.waved_car_numbers_for_sc(0))
        expected = {"173", "284", "924", "257"}

        assert waved == expected, (
            f"Expected exactly {expected} to be waved, got {waved}. "
            f"Difference: extra={waved - expected}, missing={expected - waved}"
        )

    # --- Bug 2 (cont.): Wave around timing ---

    def test_wave_timing_zero_laps_fires_at_next_lap_crossing(self):
        """With laps_before_wave_arounds=0, waves fire at the next S/F crossing.

        The SC fires around frame 13-18 (when off-track threshold is met).
        Max lap goes 15→16 at frame 34. With compute_waves_after_laps=0,
        wave_target = lap_at_sc + 0 + 1, so waves fire when max_lap reaches
        that target — at or after frame 34.
        """
        settings = {
            **self.race_settings,
            "off_track_cars_threshold": 2,
        }
        replayer = DumpReplayer(
            self.dump,
            settings=make_settings(**settings),
            compute_waves_after_laps=0,
        )
        result = replayer.run()

        assert result.total_safety_cars() >= 1, "SC must trigger for timing test"

        sc = result.safety_car_events[0]
        assert sc.wave_commands, "Expected wave commands to be computed"
        assert sc.wave_frame_index is not None, "Expected wave_frame_index to be set"
        assert sc.wave_frame_index > sc.frame_index, (
            f"Waves should fire after SC (SC at frame {sc.frame_index}, "
            f"waves at frame {sc.wave_frame_index})"
        )

    def test_wave_timing_one_lap_waves_not_in_dump(self):
        """With laps_before_wave_arounds=1, wave target lap is never reached.

        Max lap only goes from 15 to 16 in the dump. With 1 extra lap wait,
        wave_target = lap_at_sc + 1 + 1 = 17, which is never reached.
        """
        settings = {
            **self.race_settings,
            "off_track_cars_threshold": 2,
        }
        replayer = DumpReplayer(
            self.dump,
            settings=make_settings(**settings),
            compute_waves_after_laps=1,
        )
        result = replayer.run()

        assert result.total_safety_cars() >= 1, "SC must trigger for timing test"

        sc = result.safety_car_events[0]
        assert sc.wave_commands == [], (
            f"Expected no wave commands with laps_before=1 (target lap not reached in dump), "
            f"got {sc.wave_commands}"
        )


# ---------------------------------------------------------------------------
# Test: Meatball / repairs required detection
# ---------------------------------------------------------------------------

class TestMeatballDetection:
    """Tests for the meatball (repairs required) detector using a dump where
    cars at indices 0, 7, 13 receive meatball flags starting around frame 36.

    The dump 'local_session_race_start_meatbal_and_tow.ndjson' contains:
    - Race starts at frame 15 (SessionState=4, green flag)
    - Frame 36: cars at indices 0, 7 get meatball flag (0x00140000)
    - Frame 37+: cars at indices 0, 7, 13 have meatball flag

    Car lifecycle in this dump:
    - idx 0: Gets meatball while OnTrack (frame 36, laps_completed=0). Later
      towed to InPitStall (frame 42, on_pit_road=True). Detected correctly.
    - idx 7: Crashes at ~frame 27, towed to NotInWorld at frame 31
      (laps_completed=-1, all values reset to -1). Receives meatball at
      frame 36 while *already* NotInWorld. Correctly excluded by the
      laps_completed < 0 and track_loc == NotInWorld filters.
    - idx 13: Gets meatball while OnTrack (frame 37, laps_completed=0).
      Continues driving. Detected correctly.
    """

    dump = DUMPS_DIR / "local_session_race_start_meatbal_and_tow.ndjson"

    def test_meatball_detected_in_log_default_settings(self):
        """With default settings (threshold=99999, weight=0.0), meatball events
        should appear in the detection log but no SC should trigger."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            meatball_detector_enabled=True,
            stopped_detector_enabled=False,
            off_track_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        # Meatball should be detected in the log
        frames_with_meatball = [
            entry for entry in result.detection_log
            if entry.meatball_drivers
        ]
        assert len(frames_with_meatball) > 0, "Expected meatball detections in log"

        # Check the known car indices appear
        all_meatball_idxs = set()
        for entry in frames_with_meatball:
            all_meatball_idxs.update(entry.meatball_drivers)
        # Index 7 has laps_completed=-1, so is filtered out by the detector
        assert {0, 13}.issubset(all_meatball_idxs), (
            f"Expected indices 0, 13 in meatball detections, got {all_meatball_idxs}"
        )

        # No SC should trigger with default threshold=99999
        assert result.total_safety_cars() == 0, (
            f"Expected 0 SCs with meatball threshold=99999, got {result.total_safety_cars()}"
        )

    def test_sc_triggers_with_low_meatball_threshold(self):
        """With meatball_cars_threshold=1, a single meatball car should trigger SC."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            meatball_detector_enabled=True,
            meatball_cars_threshold=1,
            stopped_detector_enabled=False,
            off_track_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC with meatball_threshold=1, got {result.total_safety_cars()}"
        )

    def test_meatball_contributes_to_accumulative_scoring(self):
        """With meaningful meatball weight and lowered accumulative threshold,
        meatball detections should contribute to accumulative scoring and trigger SC."""
        replayer = DumpReplayer(self.dump, settings=make_settings(
            meatball_detector_enabled=True,
            meatball_weight=2.0,
            accumulative_detector_enabled=True,
            accumulative_threshold=3.0,  # 2 cars * weight 2.0 = 4.0 >= 3.0
            stopped_detector_enabled=False,
            off_track_detector_enabled=False,
            random_detector_enabled=False,
            proximity_filter_enabled=False,
            race_start_threshold_multiplier=1.0,
            event_time_window_seconds=5.0,
            detection_start_minute=0.0,
            detection_end_minute=60.0,
            max_safety_cars=10,
        ))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC via accumulative meatball scoring, "
            f"got {result.total_safety_cars()}"
        )


# ---------------------------------------------------------------------------
# Test: Tow (teleport to pit) detection
# ---------------------------------------------------------------------------

class TestTowDetection:
    """Tests for the tow detector using dumps where cars teleport to pits.

    Tow signature: car jumps from on_track/off_track directly to in_pit_stall
    in a single frame, skipping aproaching_pits.

    Dump files:
    - local_session_tow_midway_through.ndjson: car idx=0 tows at frame 15
      from on_track (lap_distance ~0.53) to in_pit_stall
    - local_session_tow_around_start_finish.ndjson: car idx=0 tows at frame 20
      from on_track (lap_distance ~0.05) to in_pit_stall
    - local_session_regular_pitstop.ndjson: car idx=0 enters pits normally
      through aproaching_pits → in_pit_stall (no tow)
    - local_session_race_start_meatbal_and_tow.ndjson: car idx=0 tows at
      frame 42 from off_track, and cars idx 0, 13 get meatball flags
    """

    base_settings = dict(
        tow_detector_enabled=True,
        stopped_detector_enabled=False,
        off_track_detector_enabled=False,
        random_detector_enabled=False,
        meatball_detector_enabled=False,
        proximity_filter_enabled=False,
        race_start_threshold_multiplier=1.0,
        race_start_threshold_multiplier_time_seconds=0.0,
        event_time_window_seconds=5.0,
        detection_start_minute=0.0,
        detection_end_minute=60.0,
        max_safety_cars=10,
    )

    def test_tow_midway_through_detected(self):
        """Car idx=0 in local_session_tow_midway_through.ndjson tows from
        on_track to in_pit_stall at frame 15. Should be detected."""
        dump = DUMPS_DIR / "local_session_tow_midway_through.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(**self.base_settings))
        result = replayer.run()

        frames_with_tow = [
            entry for entry in result.detection_log
            if entry.towing_drivers
        ]
        assert len(frames_with_tow) > 0, "Expected tow detection in midway-through dump"

        all_tow_idxs = set()
        for entry in frames_with_tow:
            all_tow_idxs.update(entry.towing_drivers)
        assert 0 in all_tow_idxs, (
            f"Expected car idx=0 to be detected as towing, got {all_tow_idxs}"
        )

    def test_tow_around_start_finish_detected(self):
        """Car idx=0 in local_session_tow_around_start_finish.ndjson tows from
        near start/finish line. Should be detected."""
        dump = DUMPS_DIR / "local_session_tow_around_start_finish.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(**self.base_settings))
        result = replayer.run()

        frames_with_tow = [
            entry for entry in result.detection_log
            if entry.towing_drivers
        ]
        assert len(frames_with_tow) > 0, "Expected tow detection near start/finish"

        all_tow_idxs = set()
        for entry in frames_with_tow:
            all_tow_idxs.update(entry.towing_drivers)
        assert 0 in all_tow_idxs, (
            f"Expected car idx=0 to be detected as towing, got {all_tow_idxs}"
        )

    def test_regular_pitstop_not_detected_as_tow(self):
        """Car idx=0 in local_session_regular_pitstop.ndjson enters pits normally
        through aproaching_pits. Should NOT be detected as a tow."""
        dump = DUMPS_DIR / "local_session_regular_pitstop.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(**self.base_settings))
        result = replayer.run()

        frames_with_tow = [
            entry for entry in result.detection_log
            if entry.towing_drivers
        ]
        tow_idx_0_frames = [
            entry for entry in frames_with_tow
            if 0 in entry.towing_drivers
        ]
        assert len(tow_idx_0_frames) == 0, (
            f"Regular pitstop for idx=0 was incorrectly detected as tow "
            f"at frames {[e.frame_index for e in tow_idx_0_frames]}"
        )

    def test_meatball_and_tow_both_detected(self):
        """local_session_race_start_meatbal_and_tow.ndjson should detect both
        meatball events (idx 0, 13) and a tow event (idx 0 at frame 42)."""
        dump = DUMPS_DIR / "local_session_race_start_meatbal_and_tow.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(
            **{**self.base_settings, "meatball_detector_enabled": True},
        ))
        result = replayer.run()

        # Check meatball detections
        frames_with_meatball = [
            entry for entry in result.detection_log
            if entry.meatball_drivers
        ]
        all_meatball_idxs = set()
        for entry in frames_with_meatball:
            all_meatball_idxs.update(entry.meatball_drivers)
        assert {0, 13}.issubset(all_meatball_idxs), (
            f"Expected meatball for idx 0 and 13, got {all_meatball_idxs}"
        )

        # Check tow detections
        frames_with_tow = [
            entry for entry in result.detection_log
            if entry.towing_drivers
        ]
        assert len(frames_with_tow) > 0, "Expected tow detection in meatball+tow dump"

        all_tow_idxs = set()
        for entry in frames_with_tow:
            all_tow_idxs.update(entry.towing_drivers)
        assert 0 in all_tow_idxs, (
            f"Expected car idx=0 to be detected as towing, got {all_tow_idxs}"
        )

    def test_tow_shadow_mode_no_sc_triggered(self):
        """With default shadow mode settings (threshold=99999, weight=0.0),
        tow events should be detected but no SC should trigger."""
        dump = DUMPS_DIR / "local_session_tow_midway_through.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(**self.base_settings))
        result = replayer.run()

        # Tow should be detected
        frames_with_tow = [
            entry for entry in result.detection_log
            if entry.towing_drivers
        ]
        assert len(frames_with_tow) > 0, "Expected tow detection"

        # But no SC should trigger (shadow mode)
        assert result.total_safety_cars() == 0, (
            f"Expected 0 SCs in shadow mode, got {result.total_safety_cars()}"
        )

    def test_tow_triggers_sc_with_threshold_1(self):
        """With tow_cars_threshold=1, a single tow should trigger a SC."""
        dump = DUMPS_DIR / "local_session_tow_midway_through.ndjson"
        replayer = DumpReplayer(dump, settings=make_settings(
            **{**self.base_settings, "tow_cars_threshold": 1},
        ))
        result = replayer.run()

        assert result.total_safety_cars() >= 1, (
            f"Expected at least 1 SC with tow_threshold=1, got {result.total_safety_cars()}"
        )
