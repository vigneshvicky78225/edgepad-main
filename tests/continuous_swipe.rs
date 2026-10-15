//! Unit and integration tests for continuous ASUS VivoBook-style edge swipe behavior.
//!
//! Verifies:
//! - A single long swipe generates multiple key presses.
//! - Events are generated before the finger is lifted.
//! - Movement spread across many small input events accumulates correctly.
//! - Slow and fast swipes behave appropriately.
//! - Both vertical directions map to the correct keys.
//! - Direction reversal works without duplicate counting.
//! - Stationary touches do not trigger repeated adjustments.
//! - Jitter is filtered.
//! - Event-rate limits preserve pending movement.
//! - Every press is released.
//! - Normal pointer and scroll forwarding remain functional.

use std::time::Duration;

use edgepad::actions::ActionDispatcher;
use edgepad::core::{
    AxisRange, Capabilities, EdgeWidths, Engine, EngineOptions, Event, SliderDirection, Zone,
};
use edgepad::encoder::{EncoderAccumulator, EncoderConfig};
use edgepad::keyboard::VirtualKeyboard;

fn test_capabilities() -> Capabilities {
    Capabilities {
        slot_min: 0,
        slot_max: 4,
        x: AxisRange { min: 0, max: 2000 },
        y: AxisRange { min: 0, max: 1000 },
    }
}

fn test_engine(step_size: f32, dead_zone: f32) -> Engine {
    let mut options = EngineOptions::default();
    options.encoder.enabled = true;
    options.encoder.step_size = step_size;
    options.encoder.dead_zone = dead_zone;

    Engine::with_options(
        test_capabilities(),
        EdgeWidths::all(0.10),
        Vec::new(),
        options,
    )
}

#[test]
fn single_long_swipe_generates_multiple_key_presses() {
    let mut engine = test_engine(50.0, 0.0);
    let mut dispatcher = ActionDispatcher::new(Vec::new(), 64).unwrap();
    dispatcher.set_test_mode(true);

    // Initial touch on right edge (x=1950, y=900)
    let f1 = [
        Event::slot(0),
        Event::tracking_id(1),
        Event::x(1950),
        Event::y(900),
    ];
    let out1 = engine.process_frame(&f1).unwrap();
    assert_eq!(out1.slider_steps.len(), 0);

    // Continuous long swipe moving upward by 300 units (900 -> 600)
    let mut total_steps = 0;
    for y in (600..=850).rev().step_by(50) {
        let frame = [Event::slot(0), Event::y(y)];
        let out = engine.process_frame(&frame).unwrap();
        for step in out.slider_steps {
            assert_eq!(step.zone, Zone::Right);
            assert_eq!(step.direction, SliderDirection::Up);
            dispatcher.dispatch_slider_step(step);
            total_steps += 1;
        }
    }

    // 300 units traveled with step_size=50 must produce exactly 6 discrete adjustments
    assert_eq!(total_steps, 6);
    let stats = dispatcher.stats();
    assert_eq!(stats.matched_slider_steps, 6);
    assert_eq!(stats.queued_commands, 6);
}

#[test]
fn events_are_generated_before_finger_is_lifted() {
    let mut engine = test_engine(50.0, 0.0);

    // Touch down on right edge at y=800
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(2),
            Event::x(1950),
            Event::y(800),
        ])
        .unwrap();

    // Intermediate motion frame 1: move 50 units upward (y=750)
    let out_mid1 = engine
        .process_frame(&[Event::slot(0), Event::y(750)])
        .unwrap();
    // Must generate an event immediately in this frame, while finger is still down!
    assert_eq!(out_mid1.slider_steps.len(), 1);
    assert_eq!(out_mid1.slider_steps[0].direction, SliderDirection::Up);

    // Intermediate motion frame 2: move another 50 units upward (y=700)
    let out_mid2 = engine
        .process_frame(&[Event::slot(0), Event::y(700)])
        .unwrap();
    assert_eq!(out_mid2.slider_steps.len(), 1);

    // Only now lift the finger
    let out_lift = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    // Lift should clean up without duplicate swipe gestures
    assert_eq!(out_lift.slider_steps.len(), 0);
    assert_eq!(out_lift.gestures.len(), 0);
}

#[test]
fn movement_spread_across_many_small_input_events_accumulates_correctly() {
    let mut engine = test_engine(50.0, 0.0);

    // Finger down on left edge at y=200
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(3),
            Event::x(50),
            Event::y(200),
        ])
        .unwrap();

    // 10 small incremental frames of 5 units each (total 50 units)
    let mut emitted_ticks = Vec::new();
    for i in 1..=10 {
        let y = 200 + (i * 5); // moving down
        let out = engine
            .process_frame(&[Event::slot(0), Event::y(y)])
            .unwrap();
        emitted_ticks.push(out.slider_steps.len());
    }

    // Frames 1..9 (5 to 45 units): 0 ticks emitted
    for count in &emitted_ticks[0..9] {
        assert_eq!(*count, 0, "partial deltas must accumulate, not emit early");
    }

    // Frame 10 (reaches 50 units): exactly 1 tick emitted
    assert_eq!(emitted_ticks[9], 1, "accumulated 50 units must trigger 1 tick");
}

#[test]
fn slow_and_fast_swipes_behave_appropriately() {
    // 1. Slow swipe: 1 unit per frame across 100 frames
    let mut engine_slow = test_engine(50.0, 0.0);
    engine_slow
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(4),
            Event::x(1950),
            Event::y(500),
        ])
        .unwrap();

    let mut slow_steps = 0;
    for dy in 1..=100 {
        let out = engine_slow
            .process_frame(&[Event::slot(0), Event::y(500 + dy)])
            .unwrap();
        slow_steps += out.slider_steps.len();
    }
    assert_eq!(slow_steps, 2, "slow swipe of 100 units with step 50 must produce 2 steps");

    // 2. Fast swipe: 250 units in a single frame
    let mut engine_fast = test_engine(50.0, 0.0);
    engine_fast
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(5),
            Event::x(1950),
            Event::y(500),
        ])
        .unwrap();

    let out_fast = engine_fast
        .process_frame(&[Event::slot(0), Event::y(500 + 250)])
        .unwrap();
    assert_eq!(
        out_fast.slider_steps.len(),
        5,
        "fast swipe of 250 units in one frame must emit 5 steps immediately"
    );
}

#[test]
fn both_vertical_directions_map_to_the_correct_keys() {
    let mut dispatcher = ActionDispatcher::new(Vec::new(), 64).unwrap();
    dispatcher.set_test_mode(true);

    // Left edge Up -> KEY_BRIGHTNESSUP (225)
    dispatcher.dispatch_slider_step(edgepad::core::SliderStep {
        zone: Zone::Left,
        direction: SliderDirection::Up,
        slot: 0,
        tracking_id: 1,
    });

    // Left edge Down -> KEY_BRIGHTNESSDOWN (224)
    dispatcher.dispatch_slider_step(edgepad::core::SliderStep {
        zone: Zone::Left,
        direction: SliderDirection::Down,
        slot: 0,
        tracking_id: 1,
    });

    // Right edge Up -> KEY_VOLUMEUP (115)
    dispatcher.dispatch_slider_step(edgepad::core::SliderStep {
        zone: Zone::Right,
        direction: SliderDirection::Up,
        slot: 0,
        tracking_id: 1,
    });

    // Right edge Down -> KEY_VOLUMEDOWN (114)
    dispatcher.dispatch_slider_step(edgepad::core::SliderStep {
        zone: Zone::Right,
        direction: SliderDirection::Down,
        slot: 0,
        tracking_id: 1,
    });

    let stats = dispatcher.stats();
    assert_eq!(stats.matched_slider_steps, 4);
    assert_eq!(stats.unmatched_slider_steps, 0);
    assert_eq!(stats.queued_commands, 4);
}

#[test]
fn direction_reversal_works_without_duplicate_counting() {
    let range = AxisRange { min: 0, max: 1000 };
    let config = EncoderConfig {
        enabled: true,
        step_size: 50.0,
        dead_zone: 0.0,
        repeat_interval: Duration::from_millis(20),
    };
    let mut acc = EncoderAccumulator::new(config, range);
    acc.start_contact(Zone::Right, 0, 10, 500);

    // Move UP 75 units (500 -> 425): produces 1 UP tick, leaves +25 remainder
    let ticks1 = acc.update(425);
    assert_eq!(ticks1.len(), 1);
    assert_eq!(ticks1[0].direction, SliderDirection::Up);
    assert_eq!(acc.remainder(), 25.0);

    // Reverse: Move DOWN 30 units (425 -> 455): remainder changes from +25 to -5
    let ticks2 = acc.update(455);
    assert_eq!(ticks2.len(), 0);
    assert_eq!(acc.remainder(), -5.0);

    // Continue DOWN 45 units (455 -> 500): remainder reaches -50 -> produces 1 DOWN tick
    let ticks3 = acc.update(500);
    assert_eq!(ticks3.len(), 1);
    assert_eq!(ticks3[0].direction, SliderDirection::Down);
    assert_eq!(acc.remainder(), 0.0);
}

#[test]
fn stationary_touches_do_not_trigger_repeated_adjustments() {
    let mut engine = test_engine(50.0, 10.0);

    // Finger down at y=500
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(11),
            Event::x(1950),
            Event::y(500),
        ])
        .unwrap();

    // 20 subsequent frames with stationary position (same y=500)
    for _ in 0..20 {
        let out = engine
            .process_frame(&[Event::slot(0), Event::y(500)])
            .unwrap();
        assert_eq!(out.slider_steps.len(), 0, "stationary touches must never emit ticks");
    }
}

#[test]
fn jitter_is_filtered() {
    let mut engine = test_engine(50.0, 15.0); // 15 unit dead zone

    // Finger down at y=500
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(12),
            Event::x(1950),
            Event::y(500),
        ])
        .unwrap();

    // Sensor jitter oscillating +/- 5 units around y=500
    for jitter_y in [503, 497, 505, 495, 502, 498] {
        let out = engine
            .process_frame(&[Event::slot(0), Event::y(jitter_y)])
            .unwrap();
        assert_eq!(out.slider_steps.len(), 0, "dead zone must absorb sensor jitter");
    }
}

#[test]
fn event_rate_limits_preserve_pending_movement() {
    let mut dispatcher = ActionDispatcher::new(Vec::new(), 128).unwrap();
    dispatcher.set_repeat_interval_ms(15);
    assert_eq!(dispatcher.repeat_interval_ms(), 15);
    dispatcher.set_test_mode(true);

    // Rapid burst of 10 slider steps
    for _ in 0..10 {
        dispatcher.dispatch_slider_step(edgepad::core::SliderStep {
            zone: Zone::Right,
            direction: SliderDirection::Up,
            slot: 0,
            tracking_id: 1,
        });
    }

    // All 10 steps are preserved in queue without dropping
    let stats = dispatcher.stats();
    assert_eq!(stats.matched_slider_steps, 10);
    assert_eq!(stats.queued_commands, 10);
    assert_eq!(stats.dropped_commands, 0);
}

#[test]
fn every_press_is_released() {
    // Test VirtualKeyboard release semantics
    match VirtualKeyboard::new() {
        Ok(mut kb) => {
            assert!(!kb.has_held_keys());
            kb.press(115).unwrap();
            assert!(kb.has_held_keys());
            kb.release(115).unwrap();
            assert!(!kb.has_held_keys());

            // Tap helper: presses and releases
            kb.tap(115, Duration::from_millis(5)).unwrap();
            assert!(!kb.has_held_keys());

            // Release all helper
            kb.press(114).unwrap();
            kb.press(225).unwrap();
            assert!(kb.has_held_keys());
            kb.release_all().unwrap();
            assert!(!kb.has_held_keys());
        }
        Err(err) => {
            eprintln!("VirtualKeyboard creation requires /dev/uinput: {err}");
        }
    }
}

#[test]
fn normal_pointer_and_scroll_forwarding_remain_functional() {
    let mut engine = test_engine(50.0, 10.0);

    // 1. Single finger in center (x=1000, y=500)
    let f1 = [
        Event::slot(0),
        Event::tracking_id(20),
        Event::x(1000),
        Event::y(500),
    ];
    let out1 = engine.process_frame(&f1).unwrap();
    assert_eq!(out1.slider_steps.len(), 0);
    assert!(!out1.passthrough.is_empty(), "center pointer touch must pass through");

    // Center movement
    let f2 = [Event::slot(0), Event::x(1020), Event::y(530)];
    let out2 = engine.process_frame(&f2).unwrap();
    assert_eq!(out2.slider_steps.len(), 0);
    assert!(!out2.passthrough.is_empty(), "center pointer motion must pass through");

    // 2. Second finger down in center (e.g. for two-finger scroll)
    let f3 = [
        Event::slot(1),
        Event::tracking_id(21),
        Event::x(1100),
        Event::y(520),
    ];
    let out3 = engine.process_frame(&f3).unwrap();
    assert_eq!(out3.slider_steps.len(), 0);
    assert!(!out3.passthrough.is_empty(), "multitouch scroll finger must pass through");

    // Two finger scroll motion
    let f4 = [
        Event::slot(0),
        Event::y(560),
        Event::slot(1),
        Event::y(550),
    ];
    let out4 = engine.process_frame(&f4).unwrap();
    assert_eq!(out4.slider_steps.len(), 0);
    assert!(!out4.passthrough.is_empty(), "scroll motion must pass through");
}
