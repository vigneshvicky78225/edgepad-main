use edgepad::config::{EdgepadConfig, GestureConfig, HitboxConfig};
use edgepad::core::{AxisRange, Capabilities, EdgeWidths, Engine, EngineOptions, Zone, ZoneSet};
use std::time::Duration;

fn test_capabilities() -> Capabilities {
    Capabilities {
        slot_min: 0,
        slot_max: 4,
        x: AxisRange { min: 0, max: 2905 },
        y: AxisRange { min: 0, max: 1766 },
    }
}

#[test]
fn hitbox_changing_left_edge_changes_only_left_geometry() {
    let mut config = EdgepadConfig::default();
    let initial_right = config.hitbox.right_edge_width;
    let initial_top = config.hitbox.top_edge_height;
    let initial_bottom = config.hitbox.bottom_edge_height;
    let initial_corner_w = config.hitbox.corner_width;
    let initial_corner_h = config.hitbox.corner_height;

    config.hitbox.left_edge_width = Some(0.25);

    assert_eq!(config.hitbox.left_edge_width, Some(0.25));
    assert_eq!(config.hitbox.right_edge_width, initial_right);
    assert_eq!(config.hitbox.top_edge_height, initial_top);
    assert_eq!(config.hitbox.bottom_edge_height, initial_bottom);
    assert_eq!(config.hitbox.corner_width, initial_corner_w);
    assert_eq!(config.hitbox.corner_height, initial_corner_h);

    let resolved = config.hitbox.resolved_edge_widths();
    assert_eq!(resolved.left, 0.25);
    assert_eq!(resolved.right, config.hitbox.edge_width);

    let engine = Engine::new(test_capabilities(), resolved);
    // At x=0.20, y=0.50 (with 0.25 left edge width) it is in Left Edge
    assert_eq!(engine.zone_at_normalized(0.20, 0.50), Some(Zone::Left));
    // At x=0.80, y=0.50 (with 0.12 right edge width) it is in Center (None)
    assert_eq!(engine.zone_at_normalized(0.80, 0.50), None);
}

#[test]
fn hitbox_corner_dimensions_change_only_corner_geometry() {
    let mut config = EdgepadConfig::default();
    let initial_left = config.hitbox.left_edge_width;
    let initial_right = config.hitbox.right_edge_width;

    config.hitbox.corner_width = 0.25;
    config.hitbox.corner_height = 0.20;

    assert_eq!(config.hitbox.left_edge_width, initial_left);
    assert_eq!(config.hitbox.right_edge_width, initial_right);
    assert_eq!(config.hitbox.corner_width, 0.25);
    assert_eq!(config.hitbox.corner_height, 0.20);

    let engine = Engine::with_options(
        test_capabilities(),
        config.hitbox.resolved_edge_widths(),
        Vec::new(),
        EngineOptions {
            corner_width: 0.25,
            corner_height: 0.20,
            active_zones: ZoneSet::all_with_corners(),
            ..EngineOptions::default()
        },
    );

    // Point inside expanded top-left corner (x=0.20 < 0.25, y=0.15 < 0.20)
    assert_eq!(engine.zone_at_normalized(0.20, 0.15), Some(Zone::TopLeft));
    // Point outside corner height (y=0.25 > 0.20) but inside left edge width (x=0.05 < 0.12) -> Left Edge
    assert_eq!(engine.zone_at_normalized(0.05, 0.25), Some(Zone::Left));
}

#[test]
fn hitbox_overlapping_zones_follow_corner_precedence() {
    let engine = Engine::with_options(
        test_capabilities(),
        EdgeWidths {
            left: 0.20,
            right: 0.20,
            top: 0.20,
            bottom: 0.20,
        },
        Vec::new(),
        EngineOptions {
            corner_width: 0.15,
            corner_height: 0.15,
            active_zones: ZoneSet::all_with_corners(),
            ..EngineOptions::default()
        },
    );

    // Intersection region: x=0.10 (<0.15), y=0.10 (<0.15)
    // Corner double-tap detection takes deterministic precedence over left or top edge
    assert_eq!(engine.zone_at_normalized(0.10, 0.10), Some(Zone::TopLeft));

    // Outside corner and left edge (x=0.30 >= 0.20) but inside top edge (y=0.10 < 0.20) -> Top Edge
    assert_eq!(engine.zone_at_normalized(0.30, 0.10), Some(Zone::Top));

    // Outside corner and top edge (y=0.30 >= 0.20) but inside left edge (x=0.10 < 0.20) -> Left Edge
    assert_eq!(engine.zone_at_normalized(0.10, 0.30), Some(Zone::Left));

    // Outside all hitboxes -> Center Area (None)
    assert_eq!(engine.zone_at_normalized(0.50, 0.50), None);
}

#[test]
fn hitbox_raw_to_normalized_conversion_handles_nonzero_min() {
    // Touchpad device with non-zero minimum: X: 100..=3100 (range 3000), Y: 50..=2050 (range 2000)
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 2,
        x: AxisRange {
            min: 100,
            max: 3100,
        },
        y: AxisRange { min: 50, max: 2050 },
    };

    let engine = Engine::with_options(
        caps,
        EdgeWidths::all(0.10), // left edge raw x < 100 + 0.10 * 3000 = 400
        Vec::new(),
        EngineOptions {
            corner_width: 0.10,
            corner_height: 0.10,
            active_zones: ZoneSet::all_with_corners(),
            ..EngineOptions::default()
        },
    );

    // Raw point at X=250 (norm = 0.05), Y=1050 (norm = 0.50) -> Left Edge
    assert_eq!(engine.zone_at(250, 1050), Some(Zone::Left));

    // Raw point at X=1600 (norm = 0.50), Y=1050 (norm = 0.50) -> Center (None)
    assert_eq!(engine.zone_at(1600, 1050), None);
}

#[test]
fn gesture_changing_tap_tolerance_does_not_change_zone_boundaries() {
    let mut config = EdgepadConfig::default();
    let initial_hitbox = config.hitbox;

    // Adjust tap movement threshold from 0.04 to 0.12
    config.gesture.tap_max_movement = 0.12;

    assert_eq!(config.hitbox, initial_hitbox);
    let engine = Engine::new(test_capabilities(), config.hitbox.resolved_edge_widths());
    assert_eq!(engine.zone_at_normalized(0.05, 0.50), Some(Zone::Left));
    assert_eq!(engine.zone_at_normalized(0.50, 0.50), None);
}

#[test]
fn gesture_changing_double_tap_timeout_does_not_change_hitbox_dimensions() {
    let mut config = EdgepadConfig::default();
    let initial_corner_w = config.hitbox.corner_width;
    let initial_corner_h = config.hitbox.corner_height;

    config.gesture.double_tap_timeout_ms = 600;

    assert_eq!(config.hitbox.corner_width, initial_corner_w);
    assert_eq!(config.hitbox.corner_height, initial_corner_h);
}

#[test]
fn gesture_changing_swipe_thresholds_does_not_resize_hitboxes() {
    let mut config = EdgepadConfig::default();
    let initial_hitbox = config.hitbox;

    config.gesture.swipe_min_distance = 0.20;
    config.gesture.swipe_max_drift = 0.10;

    assert_eq!(config.hitbox, initial_hitbox);
    assert_eq!(
        config.hitbox.left_edge_width,
        initial_hitbox.left_edge_width
    );
    assert_eq!(
        config.hitbox.right_edge_width,
        initial_hitbox.right_edge_width
    );
}

#[test]
fn gesture_encoder_step_size_never_alters_hitbox_geometry() {
    let mut config = EdgepadConfig::default();
    let initial_hitbox = config.hitbox;

    config.encoder.step_size = 150.0;
    config.encoder.dead_zone = 25.0;
    config.encoder.repeat_interval = Duration::from_millis(40);

    assert_eq!(config.hitbox, initial_hitbox);
}

#[test]
fn cross_system_update_hitbox_preserves_gesture_thresholds() {
    let mut config = EdgepadConfig::default();
    config.gesture.swipe_min_distance = 0.15;
    config.gesture.swipe_max_drift = 0.07;
    config.gesture.tap_max_movement = 0.035;
    config.gesture.double_tap_timeout_ms = 350;

    let new_hitbox = HitboxConfig {
        edge_width: 0.18,
        left_edge_width: Some(0.20),
        right_edge_width: Some(0.22),
        top_edge_height: Some(0.15),
        bottom_edge_height: Some(0.16),
        corner_width: 0.18,
        corner_height: 0.14,
    };

    config.update_hitbox(new_hitbox);

    assert_eq!(config.hitbox, new_hitbox);
    assert_eq!(config.gesture.swipe_min_distance, 0.15);
    assert_eq!(config.gesture.swipe_max_drift, 0.07);
    assert_eq!(config.gesture.tap_max_movement, 0.035);
    assert_eq!(config.gesture.double_tap_timeout_ms, 350);
}

#[test]
fn cross_system_update_gesture_preserves_hitbox_geometry() {
    let mut config = EdgepadConfig::default();
    config.hitbox.left_edge_width = Some(0.21);
    config.hitbox.corner_width = 0.19;
    config.hitbox.corner_height = 0.17;

    let new_gesture = GestureConfig {
        swipe_min_distance: 0.14,
        swipe_max_drift: 0.06,
        tap_max_movement: 0.025,
        tap_min_duration_ms: 30,
        tap_max_duration_ms: 180,
        double_tap_timeout_ms: 280,
        double_tap_max_distance: 0.09,
        cooldown_ms: 220,
    };

    config.update_gesture(new_gesture);

    assert_eq!(config.gesture, new_gesture);
    assert_eq!(config.hitbox.left_edge_width, Some(0.21));
    assert_eq!(config.hitbox.corner_width, 0.19);
    assert_eq!(config.hitbox.corner_height, 0.17);
}

#[test]
fn toml_roundtrip_preserves_independent_hitbox_and_gesture_tables() {
    let toml_str = r#"
device = "auto"

[hitbox]
edge_width = 0.1400
left_edge_width = 0.1800
right_edge_width = 0.1600
top_edge_height = 0.1200
bottom_edge_height = 0.1300
corner_width = 0.2200
corner_height = 0.1900

[gesture]
swipe_min_distance = 0.0900
swipe_max_drift = 0.0450
tap_max_movement = 0.0300
tap_min_duration_ms = 35
tap_max_duration_ms = 190
double_tap_timeout_ms = 320
double_tap_max_distance = 0.0750
cooldown_ms = 240
"#;

    let config = EdgepadConfig::parse(toml_str).expect("Valid independent config should parse");

    assert_eq!(config.hitbox.left_edge_width, Some(0.18));
    assert_eq!(config.hitbox.right_edge_width, Some(0.16));
    assert_eq!(config.hitbox.top_edge_height, Some(0.12));
    assert_eq!(config.hitbox.bottom_edge_height, Some(0.13));
    assert_eq!(config.hitbox.corner_width, 0.22);
    assert_eq!(config.hitbox.corner_height, 0.19);

    assert_eq!(config.gesture.swipe_min_distance, 0.09);
    assert_eq!(config.gesture.swipe_max_drift, 0.045);
    assert_eq!(config.gesture.tap_max_movement, 0.03);
    assert_eq!(config.gesture.tap_min_duration_ms, 35);
    assert_eq!(config.gesture.tap_max_duration_ms, 190);
    assert_eq!(config.gesture.double_tap_timeout_ms, 320);
    assert_eq!(config.gesture.double_tap_max_distance, 0.075);
    assert_eq!(config.gesture.cooldown_ms, 240);
}
