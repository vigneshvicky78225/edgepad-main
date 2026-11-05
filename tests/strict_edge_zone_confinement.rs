use std::time::Duration;

use edgepad::actions::{
    ActionCommandRunner, ActionCommandStatus, ActionDispatcher, ActionShutdownToken,
};
use edgepad::core::{
    AxisRange, Capabilities, EdgeWidths, Engine, EngineOptions, Event, GestureDirection,
    SliderDirection, Zone, ZoneSet,
};

fn test_capabilities() -> Capabilities {
    Capabilities {
        slot_min: 0,
        slot_max: 4,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    }
}

fn test_engine(left: f32, right: f32, top: f32, bottom: f32, encoder_step: f32) -> Engine {
    let mut options = EngineOptions::default();
    options.encoder.enabled = true;
    options.encoder.step_size = encoder_step;
    options.encoder.dead_zone = 0.0;
    options.active_zones = ZoneSet::all_with_corners();
    options.single_tap_zones = ZoneSet::all();
    options.double_tap_zones = ZoneSet::all_with_corners();

    Engine::with_options(
        test_capabilities(),
        EdgeWidths {
            left,
            right,
            top,
            bottom,
        },
        Vec::new(),
        options,
    )
}

#[derive(Default)]
struct MockRunner;

impl ActionCommandRunner for MockRunner {
    fn run(
        &mut self,
        _argv: &[String],
        _shutdown: &ActionShutdownToken,
    ) -> Result<ActionCommandStatus, String> {
        Ok(ActionCommandStatus::success())
    }
}

#[test]
fn left_edge_exit_into_center_cancels_gesture() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Initial contact on left edge (x=50 < 100, y=500)
    let out_down = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(1),
            Event::x(50),
            Event::y(500),
        ])
        .unwrap();
    assert!(out_down.passthrough.is_empty());
    assert!(out_down.cancellations.is_empty());

    // Move vertically within left edge (x=70 < 100, y=550)
    let out_move1 = engine
        .process_frame(&[Event::slot(0), Event::x(70), Event::y(550)])
        .unwrap();
    assert!(out_move1.cancellations.is_empty());

    // Move horizontally into center (x=300 >= 100, y=550) -> must cancel immediately!
    let out_move2 = engine
        .process_frame(&[Event::slot(0), Event::x(300), Event::y(550)])
        .unwrap();
    assert_eq!(out_move2.cancellations.len(), 1);
    assert_eq!(out_move2.cancellations[0].zone, Zone::Left);
    assert_eq!(out_move2.cancellations[0].slot, 0);
    assert_eq!(out_move2.cancellations[0].tracking_id, 1);
    assert!(out_move2.slider_steps.is_empty());
    assert!(out_move2.gestures.is_empty());

    // Finger releases in center: must emit zero gestures
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up.gestures.is_empty());
    assert!(out_up.slider_steps.is_empty());
}

#[test]
fn right_edge_exit_into_center_cancels_gesture() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Initial contact on right edge (x=950 > 900, y=500)
    let out_down = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(2),
            Event::x(950),
            Event::y(500),
        ])
        .unwrap();
    assert!(out_down.passthrough.is_empty());
    assert!(out_down.cancellations.is_empty());

    // Move vertically within right edge (x=930 > 900, y=550)
    let out_move1 = engine
        .process_frame(&[Event::slot(0), Event::x(930), Event::y(550)])
        .unwrap();
    assert!(out_move1.cancellations.is_empty());

    // Move horizontally into center (x=700 <= 900, y=550) -> must cancel immediately!
    let out_move2 = engine
        .process_frame(&[Event::slot(0), Event::x(700), Event::y(550)])
        .unwrap();
    assert_eq!(out_move2.cancellations.len(), 1);
    assert_eq!(out_move2.cancellations[0].zone, Zone::Right);
    assert_eq!(out_move2.cancellations[0].slot, 0);
    assert_eq!(out_move2.cancellations[0].tracking_id, 2);
    assert!(out_move2.slider_steps.is_empty());
    assert!(out_move2.gestures.is_empty());

    // Release in center: zero gestures
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up.gestures.is_empty());
    assert!(out_up.slider_steps.is_empty());
}

#[test]
fn top_and_bottom_edges_exit_into_center_cancels_gesture() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // 1. Top edge (y < 100)
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(10),
            Event::x(500),
            Event::y(50),
        ])
        .unwrap();
    // Move into center (y=300 >= 100)
    let out_top = engine
        .process_frame(&[Event::slot(0), Event::x(500), Event::y(300)])
        .unwrap();
    assert_eq!(out_top.cancellations.len(), 1);
    assert_eq!(out_top.cancellations[0].zone, Zone::Top);
    let out_up_top = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up_top.gestures.is_empty());

    // 2. Bottom edge (y > 900)
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(11),
            Event::x(500),
            Event::y(950),
        ])
        .unwrap();
    // Move into center (y=700 <= 900)
    let out_bottom = engine
        .process_frame(&[Event::slot(0), Event::x(500), Event::y(700)])
        .unwrap();
    assert_eq!(out_bottom.cancellations.len(), 1);
    assert_eq!(out_bottom.cancellations[0].zone, Zone::Bottom);
    let out_up_bottom = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up_bottom.gestures.is_empty());
}

#[test]
fn no_keyboard_events_or_slider_steps_emitted_after_leaving_hitbox() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);
    let mut dispatcher = ActionDispatcher::with_runner(Vec::new(), 64, MockRunner).unwrap();
    dispatcher.set_test_mode(true);

    // Start inside right edge at y=800
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(20),
            Event::x(950),
            Event::y(800),
        ])
        .unwrap();

    // Move up by 50 units inside right edge (y=750): generates 1 slider step
    let out1 = engine
        .process_frame(&[Event::slot(0), Event::y(750)])
        .unwrap();
    assert_eq!(out1.slider_steps.len(), 1);
    dispatcher.dispatch_slider_step(out1.slider_steps[0]);
    assert_eq!(dispatcher.stats().matched_slider_steps, 1);

    // Finger moves into center (x=500): must cancel immediately
    let out2 = engine
        .process_frame(&[Event::slot(0), Event::x(500)])
        .unwrap();
    assert_eq!(out2.cancellations.len(), 1);
    dispatcher.cancel_gesture(out2.cancellations[0]);

    // Finger continues moving through center by 200 units (750 -> 550)
    for y in [700, 650, 600, 550] {
        let out_center = engine
            .process_frame(&[Event::slot(0), Event::y(y)])
            .unwrap();
        assert!(
            out_center.slider_steps.is_empty(),
            "Must NOT emit slider steps while in center"
        );
        for step in out_center.slider_steps {
            dispatcher.dispatch_slider_step(step);
        }
    }

    // No further commands were queued or matched
    assert_eq!(dispatcher.stats().matched_slider_steps, 1);

    // Lift finger in center
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up.gestures.is_empty());
    assert!(out_up.slider_steps.is_empty());
}

#[test]
fn reentering_edge_without_lifting_does_not_reactivate_gesture() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // 1. Finger starts inside right edge (x=950, y=800)
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(30),
            Event::x(950),
            Event::y(800),
        ])
        .unwrap();

    // 2. Finger moves into center (x=500, y=750): cancelled!
    let out_center = engine
        .process_frame(&[Event::slot(0), Event::x(500), Event::y(750)])
        .unwrap();
    assert_eq!(out_center.cancellations.len(), 1);

    // 3. Finger moves back to right edge without lifting (x=950, y=700)
    let out_reenter = engine
        .process_frame(&[Event::slot(0), Event::x(950), Event::y(700)])
        .unwrap();
    assert!(
        out_reenter.slider_steps.is_empty(),
        "Re-entry must NOT reactivate the gesture or emit slider steps"
    );

    // 4. Finger moves further along right edge (x=950, y=600)
    let out_more_motion = engine
        .process_frame(&[Event::slot(0), Event::y(600)])
        .unwrap();
    assert!(
        out_more_motion.slider_steps.is_empty(),
        "Movement after re-entry must NOT emit events without lifting"
    );

    // 5. Finger lifts: no gesture emitted
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up.gestures.is_empty());
    assert!(out_up.slider_steps.is_empty());
}

#[test]
fn lifting_and_starting_new_contact_inside_edge_allows_new_gesture() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // First contact exits and cancels
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(40),
            Event::x(950),
            Event::y(800),
        ])
        .unwrap();
    engine
        .process_frame(&[Event::slot(0), Event::x(500), Event::y(750)])
        .unwrap();
    engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();

    // New contact begins after lifting: touches down inside right edge
    let out_down2 = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(41),
            Event::x(950),
            Event::y(800),
        ])
        .unwrap();
    assert!(out_down2.cancellations.is_empty());

    // New contact moves within right edge by 50 units (y=750): must produce slider step!
    let out_move2 = engine
        .process_frame(&[Event::slot(0), Event::y(750)])
        .unwrap();
    assert_eq!(out_move2.slider_steps.len(), 1);
    assert_eq!(out_move2.slider_steps[0].zone, Zone::Right);
    assert_eq!(out_move2.slider_steps[0].direction, SliderDirection::Up);
}

#[test]
fn encoder_movement_accumulated_before_cancellation_is_not_emitted_afterward() {
    // Step size 100 units
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 100.0);

    // Start on right edge at y=800
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(50),
            Event::x(950),
            Event::y(800),
        ])
        .unwrap();

    // Move up by 60 units (y=740): below 100 step size -> 0 ticks emitted
    let out1 = engine
        .process_frame(&[Event::slot(0), Event::y(740)])
        .unwrap();
    assert_eq!(out1.slider_steps.len(), 0);

    // Move into center (x=500): exits hitbox and is cancelled!
    let out2 = engine
        .process_frame(&[Event::slot(0), Event::x(500)])
        .unwrap();
    assert_eq!(out2.cancellations.len(), 1);

    // Move up by another 60 units in center (y=680):
    // Total displacement from start is 120 units, but since gesture was cancelled,
    // pending movement was cleared and NO tick is emitted!
    let out3 = engine
        .process_frame(&[Event::slot(0), Event::y(680)])
        .unwrap();
    assert_eq!(out3.slider_steps.len(), 0);

    // Release: no ticks or gestures emitted
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert_eq!(out_up.slider_steps.len(), 0);
    assert_eq!(out_up.gestures.len(), 0);
}

#[test]
fn independent_hitbox_calibration_values_are_respected() {
    // Narrow left edge: 5% (50 px), wide right edge: 20% (200 px)
    let mut engine = test_engine(0.05, 0.20, 0.10, 0.10, 50.0);

    // Touch down at x=70:
    // Left edge boundary is 50 px. 70 > 50, so this is NOT in left edge hitbox!
    // It should become passthrough, not an edge gesture.
    let out1 = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(60),
            Event::x(70),
            Event::y(500),
        ])
        .unwrap();
    assert_eq!(out1.passthrough.len(), 4); // slot, tracking_id, x, y passed through!

    // Touch down on right edge at x=850 (1000 - 850 = 150 < 200 px):
    // Inside the 20% right edge hitbox!
    engine
        .process_frame(&[
            Event::slot(1),
            Event::tracking_id(61),
            Event::x(850),
            Event::y(500),
        ])
        .unwrap();

    // Move within the wide 20% right edge hitbox (x=820 -> 180 < 200): still in zone!
    let out2 = engine
        .process_frame(&[Event::slot(1), Event::x(820), Event::y(550)])
        .unwrap();
    assert!(out2.cancellations.is_empty());

    // Move outside the 20% right edge hitbox (x=780 -> 220 > 200): exits and cancels!
    let out3 = engine
        .process_frame(&[Event::slot(1), Event::x(780), Event::y(550)])
        .unwrap();
    assert_eq!(out3.cancellations.len(), 1);
    assert_eq!(out3.cancellations[0].zone, Zone::Right);
}

#[test]
fn corner_double_tap_recognition_does_not_trigger_from_taps_outside_corner() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Corner dimensions default: width 0.15 (150 px), height 0.15 (150 px)
    // First tap: inside TopLeft corner (x=50, y=50)
    engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(70),
                Event::x(50),
                Event::y(50),
            ],
            Duration::from_millis(1000),
        )
        .unwrap();
    engine
        .process_frame_at(
            &[Event::slot(0), Event::tracking_id(-1)],
            Duration::from_millis(1050),
        )
        .unwrap();

    // Second tap: OUTSIDE corner region at x=200 (> 150 px), y=50
    let out_down2 = engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(71),
                Event::x(200),
                Event::y(50),
            ],
            Duration::from_millis(1150),
        )
        .unwrap();
    // The second tap is not in TopLeft corner, so sequence is broken and tap is not recognized as double tap
    let out_up2 = engine
        .process_frame_at(
            &[Event::slot(0), Event::tracking_id(-1)],
            Duration::from_millis(1200),
        )
        .unwrap();

    // Must NOT recognize double tap
    let double_taps: Vec<_> = out_down2
        .gestures
        .into_iter()
        .chain(out_up2.gestures)
        .filter(|g| g.direction == GestureDirection::DoubleTap)
        .collect();
    assert!(
        double_taps.is_empty(),
        "Double-tap must NOT trigger from tap outside configured corner region"
    );
}

#[test]
fn corner_tap_moving_outside_corner_cancels_and_rejects_double_tap() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // First tap: inside TopLeft corner (x=50, y=50), then moves to (200, 200) before lifting
    engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(80),
                Event::x(50),
                Event::y(50),
            ],
            Duration::from_millis(1000),
        )
        .unwrap();

    // Move out of corner before lifting:
    let out_exit = engine
        .process_frame_at(
            &[Event::slot(0), Event::x(200), Event::y(200)],
            Duration::from_millis(1020),
        )
        .unwrap();
    assert_eq!(out_exit.cancellations.len(), 1);

    // Release first tap
    engine
        .process_frame_at(
            &[Event::slot(0), Event::tracking_id(-1)],
            Duration::from_millis(1050),
        )
        .unwrap();

    // Attempt second tap inside TopLeft corner (x=50, y=50)
    engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(81),
                Event::x(50),
                Event::y(50),
            ],
            Duration::from_millis(1150),
        )
        .unwrap();
    let out_up2 = engine
        .process_frame_at(
            &[Event::slot(0), Event::tracking_id(-1)],
            Duration::from_millis(1200),
        )
        .unwrap();

    let double_taps: Vec<_> = out_up2
        .gestures
        .into_iter()
        .filter(|g| g.direction == GestureDirection::DoubleTap)
        .collect();
    assert!(
        double_taps.is_empty(),
        "Double tap must NOT trigger when first tap exited corner hitbox"
    );
}

#[test]
fn normal_pointer_movement_and_scrolling_in_center_remain_functional() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Finger 1 touches down in center: (x=500, y=500)
    let out1 = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(90),
            Event::x(500),
            Event::y(500),
        ])
        .unwrap();
    assert_eq!(out1.passthrough.len(), 4);
    assert!(out1.gestures.is_empty());
    assert!(out1.cancellations.is_empty());

    // Finger 1 moves in center: (x=520, y=530)
    let out2 = engine
        .process_frame(&[Event::slot(0), Event::x(520), Event::y(530)])
        .unwrap();
    assert_eq!(out2.passthrough.len(), 3);
    assert_eq!(out2.passthrough[0], Event::slot(0));
    assert_eq!(out2.passthrough[1], Event::x(520));
    assert_eq!(out2.passthrough[2], Event::y(530));

    // Finger 2 touches down in center for two-finger scroll: (x=600, y=500)
    let out3 = engine
        .process_frame(&[
            Event::slot(1),
            Event::tracking_id(91),
            Event::x(600),
            Event::y(500),
        ])
        .unwrap();
    assert_eq!(out3.passthrough.len(), 4);

    // Both fingers move vertically (scroll)
    let out4 = engine
        .process_frame(&[Event::slot(0), Event::y(560), Event::slot(1), Event::y(530)])
        .unwrap();
    assert_eq!(out4.passthrough.len(), 4);
    assert!(out4.gestures.is_empty());
    assert!(out4.slider_steps.is_empty());
    assert!(out4.cancellations.is_empty());
}

#[test]
fn corner_downward_swipe_transitions_to_left_edge_slider() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Initial contact inside TopLeft corner hitbox: (x=50 < 150, y=50 < 150)
    let out_down = engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(101),
            Event::x(50),
            Event::y(50),
        ])
        .unwrap();
    assert!(out_down.cancellations.is_empty());
    assert!(out_down.passthrough.is_empty());

    // Continuous downward motion along the left edge (x=50 < 100 left edge width)
    let mut total_steps = 0;
    for y in [100, 150, 200, 250, 300, 350] {
        let out = engine
            .process_frame(&[Event::slot(0), Event::y(y)])
            .unwrap();
        assert!(
            out.cancellations.is_empty(),
            "Downward swipe along left edge must not be cancelled near corner boundary"
        );
        for step in out.slider_steps {
            assert_eq!(step.zone, Zone::Left);
            assert_eq!(step.direction, SliderDirection::Down);
            total_steps += 1;
        }
    }

    assert!(
        total_steps >= 5,
        "Expected at least 5 slider steps for 300 units traveled (got {total_steps})"
    );

    // Lift finger
    let out_up = engine
        .process_frame(&[Event::slot(0), Event::tracking_id(-1)])
        .unwrap();
    assert!(out_up.gestures.is_empty());
    assert!(out_up.cancellations.is_empty());
}

#[test]
fn corner_downward_swipe_exiting_into_center_cancels() {
    let mut engine = test_engine(0.10, 0.10, 0.10, 0.10, 50.0);

    // Initial contact inside TopLeft corner hitbox: (x=50, y=50)
    engine
        .process_frame(&[
            Event::slot(0),
            Event::tracking_id(102),
            Event::x(50),
            Event::y(50),
        ])
        .unwrap();

    // Move downward along left edge (x=50, y=150)
    let out1 = engine
        .process_frame(&[Event::slot(0), Event::y(150)])
        .unwrap();
    assert!(out1.cancellations.is_empty());

    // Move horizontally into center of touchpad (x=300 >= 100): must cancel!
    let out_center = engine
        .process_frame(&[Event::slot(0), Event::x(300)])
        .unwrap();
    assert_eq!(
        out_center.cancellations.len(),
        1,
        "Exiting left edge into center must trigger gesture cancellation"
    );
    assert_eq!(out_center.cancellations[0].zone, Zone::Left);
}

