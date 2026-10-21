use edgepad::config::{EdgepadConfig, GestureActionConfig, SliderActionConfig};
use edgepad::core::{
    AxisRange, Capabilities, EdgeWidths, Engine, EngineOptions, Event, GestureDirection, Zone,
    ZoneSet,
};
use edgepad::keyboard::{key_code_to_name, parse_key_code, VirtualKeyboard};
use std::time::Duration;

#[test]
fn default_preset_generates_valid_brightness_and_volume_mappings() {
    let preset = EdgepadConfig::default_preset();
    assert_eq!(preset.gestures.len(), 4);
    assert_eq!(preset.edge_width, 0.12);
    assert_eq!(preset.swipe_min_distance, 0.08);

    // Verify Left Edge Swipe Up -> KEY_BRIGHTNESSUP
    let left_up = preset
        .gestures
        .iter()
        .find(|g| g.zone == Zone::Left && g.direction == GestureDirection::Up)
        .unwrap();
    assert_eq!(
        left_up.action,
        GestureActionConfig::Key {
            key_code: 225,
            key_name: "KEY_BRIGHTNESSUP".to_string(),
            repeat: 1,
        }
    );

    // Verify Left Edge Swipe Down -> KEY_BRIGHTNESSDOWN
    let left_down = preset
        .gestures
        .iter()
        .find(|g| g.zone == Zone::Left && g.direction == GestureDirection::Down)
        .unwrap();
    assert_eq!(
        left_down.action,
        GestureActionConfig::Key {
            key_code: 224,
            key_name: "KEY_BRIGHTNESSDOWN".to_string(),
            repeat: 1,
        }
    );

    // Verify Right Edge Swipe Up -> KEY_VOLUMEUP
    let right_up = preset
        .gestures
        .iter()
        .find(|g| g.zone == Zone::Right && g.direction == GestureDirection::Up)
        .unwrap();
    assert_eq!(
        right_up.action,
        GestureActionConfig::Key {
            key_code: 115,
            key_name: "KEY_VOLUMEUP".to_string(),
            repeat: 1,
        }
    );

    // Verify Right Edge Swipe Down -> KEY_VOLUMEDOWN
    let right_down = preset
        .gestures
        .iter()
        .find(|g| g.zone == Zone::Right && g.direction == GestureDirection::Down)
        .unwrap();
    assert_eq!(
        right_down.action,
        GestureActionConfig::Key {
            key_code: 114,
            key_name: "KEY_VOLUMEDOWN".to_string(),
            repeat: 1,
        }
    );
}

#[test]
fn default_preset_toml_serialization_round_trip() {
    let preset = EdgepadConfig::default_preset();
    let toml_str = preset
        .to_toml()
        .expect("default preset should serialize to TOML");
    let parsed = EdgepadConfig::parse(&toml_str).expect("serialized default preset should parse");

    assert_eq!(preset.edge_width, parsed.edge_width);
    assert_eq!(preset.swipe_min_distance, parsed.swipe_min_distance);
    assert_eq!(preset.gestures.len(), parsed.gestures.len());
    for (orig, p) in preset.gestures.iter().zip(parsed.gestures.iter()) {
        assert_eq!(orig.zone, p.zone);
        assert_eq!(orig.direction, p.direction);
        assert_eq!(orig.action, p.action);
        assert_eq!(orig.enabled, p.enabled);
    }
}

#[test]
fn parse_key_bindings_from_toml() {
    let toml = r#"
        device = "auto"
        edge_width = 0.12

        [[gestures]]
        zone = "left"
        direction = "up"
        key = "KEY_BRIGHTNESSUP"

        [[gestures]]
        zone = "left"
        direction = "down"
        action = { key = "KEY_BRIGHTNESSDOWN", repeat = 2 }

        [[sliders]]
        zone = "right"
        up_key = "KEY_VOLUMEUP"
        down_key = "KEY_VOLUMEDOWN"
    "#;

    let config = EdgepadConfig::parse(toml).expect("config with keys should parse");
    assert_eq!(config.gestures.len(), 2);
    assert_eq!(config.sliders.len(), 1);

    assert_eq!(
        config.gestures[0].action,
        GestureActionConfig::Key {
            key_code: 225,
            key_name: "KEY_BRIGHTNESSUP".to_string(),
            repeat: 1,
        }
    );

    assert_eq!(
        config.gestures[1].action,
        GestureActionConfig::Key {
            key_code: 224,
            key_name: "KEY_BRIGHTNESSDOWN".to_string(),
            repeat: 2,
        }
    );

    assert_eq!(
        config.sliders[0].negative,
        SliderActionConfig::Key {
            key_code: 115,
            key_name: "KEY_VOLUMEUP".to_string(),
            repeat: 1,
        }
    );
    assert_eq!(
        config.sliders[0].positive,
        SliderActionConfig::Key {
            key_code: 114,
            key_name: "KEY_VOLUMEDOWN".to_string(),
            repeat: 1,
        }
    );
}

#[test]
fn key_code_parsing_and_names() {
    assert_eq!(parse_key_code("KEY_BRIGHTNESSUP").unwrap(), 225);
    assert_eq!(parse_key_code("brightnessdown").unwrap(), 224);
    assert_eq!(parse_key_code("KEY_VOLUMEUP").unwrap(), 115);
    assert_eq!(parse_key_code("volumedown").unwrap(), 114);
    assert_eq!(parse_key_code("KEY_MUTE").unwrap(), 113);
    assert_eq!(parse_key_code("115").unwrap(), 115);

    assert_eq!(key_code_to_name(225), "KEY_BRIGHTNESSUP");
    assert_eq!(key_code_to_name(115), "KEY_VOLUMEUP");
}

#[test]
fn virtual_keyboard_creation_and_release() {
    // Attempt creating virtual keyboard
    match VirtualKeyboard::new() {
        Ok(mut kb) => {
            assert!(!kb.has_held_keys());
            let _ = kb.press(115);
            assert!(kb.has_held_keys());
            let _ = kb.release_all();
            assert!(!kb.has_held_keys());
        }
        Err(err) => {
            eprintln!("VirtualKeyboard requires /dev/uinput access: {err}");
        }
    }
}

#[test]
fn tap_and_double_tap_gestures_parsing_and_zones() {
    let toml = r#"
        device = "auto"
        edge_width = 0.12

        [[gestures]]
        zone = "left"
        direction = "tap"
        key = "KEY_MUTE"

        [[gestures]]
        zone = "top"
        direction = "tap"
        action = ["playerctl", "play-pause"]

        [[gestures]]
        zone = "top"
        direction = "double-tap"
        action = { key = "KEY_STOPCD", repeat = 1 }

        [[gestures]]
        zone = "right"
        direction = "tap"
        command = ["notify-send", "Edgepad", "Right Tap"]
    "#;

    let config = EdgepadConfig::parse(toml).expect("config with tap gestures should parse");
    assert_eq!(config.gestures.len(), 4);

    assert_eq!(config.gestures[0].zone, Zone::Left);
    assert_eq!(config.gestures[0].direction, GestureDirection::Tap);
    assert_eq!(
        config.gestures[0].action,
        GestureActionConfig::Key {
            key_code: 113,
            key_name: "KEY_MUTE".to_string(),
            repeat: 1,
        }
    );

    assert_eq!(config.gestures[1].zone, Zone::Top);
    assert_eq!(config.gestures[1].direction, GestureDirection::Tap);
    assert_eq!(
        config.gestures[1].action,
        GestureActionConfig::Command {
            argv: vec!["playerctl".to_string(), "play-pause".to_string()],
        }
    );

    assert_eq!(config.gestures[2].zone, Zone::Top);
    assert_eq!(config.gestures[2].direction, GestureDirection::DoubleTap);
    assert_eq!(
        config.gestures[2].action,
        GestureActionConfig::Key {
            key_code: 166,
            key_name: "KEY_STOPCD".to_string(),
            repeat: 1,
        }
    );

    assert_eq!(config.gestures[3].zone, Zone::Right);
    assert_eq!(config.gestures[3].direction, GestureDirection::Tap);
    assert_eq!(
        config.gestures[3].action,
        GestureActionConfig::Command {
            argv: vec![
                "notify-send".to_string(),
                "Edgepad".to_string(),
                "Right Tap".to_string()
            ],
        }
    );

    let engine_opts = config.engine_options();
    assert!(engine_opts.single_tap_zones.contains(Zone::Left));
    assert!(engine_opts.single_tap_zones.contains(Zone::Top));
    assert!(engine_opts.single_tap_zones.contains(Zone::Right));
    assert!(!engine_opts.single_tap_zones.contains(Zone::Bottom));

    assert!(engine_opts.double_tap_zones.contains(Zone::Top));
    assert!(!engine_opts.double_tap_zones.contains(Zone::Left));
    assert!(!engine_opts.double_tap_zones.contains(Zone::Right));
    assert!(!engine_opts.double_tap_zones.contains(Zone::Bottom));
}

#[test]
fn parse_tap_actions_with_media_table_and_log_string() {
    let toml = r#"
        device = "auto"
        edge_width = 0.12

        [[gestures]]
        zone = "top"
        direction = "tap"
        action = { type = "media", media_action = "play_pause", key = "KEY_PLAYPAUSE" }

        [[gestures]]
        zone = "top"
        direction = "double-tap"
        action = { type = "media", media_action = "stop" }

        [[gestures]]
        zone = "left"
        direction = "tap"
        action = "log"
    "#;

    let config =
        EdgepadConfig::parse(toml).expect("config with media actions and string log should parse");
    assert_eq!(config.gestures.len(), 3);

    // Top tap -> KEY_PLAYPAUSE (164)
    assert_eq!(
        config.gestures[0].action,
        GestureActionConfig::Key {
            key_code: 164,
            key_name: "KEY_PLAYPAUSE".to_string(),
            repeat: 1,
        }
    );

    // Top double-tap -> KEY_STOPCD (166)
    assert_eq!(
        config.gestures[1].action,
        GestureActionConfig::Key {
            key_code: 166,
            key_name: "KEY_STOPCD".to_string(),
            repeat: 1,
        }
    );

    // Left tap -> Log
    assert_eq!(config.gestures[2].action, GestureActionConfig::Log);
}

#[test]
fn active_edge_widths_enables_zones_for_tap_actions() {
    let toml = r#"
        device = "auto"
        edge_width = 0.15

        [[gestures]]
        zone = "top"
        direction = "tap"
        key = "KEY_PLAYPAUSE"

        [[gestures]]
        zone = "left"
        direction = "up"
        key = "KEY_BRIGHTNESSUP"
    "#;

    let config = EdgepadConfig::parse(toml).unwrap();
    let widths = config.active_edge_widths();

    // Left has swipe -> active
    assert_eq!(widths.left, 0.15);
    // Top has tap -> active
    assert_eq!(widths.top, 0.15);
    // Right and Bottom have no bindings -> 0.0
    assert_eq!(widths.right, 0.0);
    assert_eq!(widths.bottom, 0.0);
}

#[test]
fn invalid_action_fails_visibly_instead_of_silently_becoming_log() {
    let toml = r#"
        device = "auto"
        edge_width = 0.12

        [[gestures]]
        zone = "top"
        direction = "tap"
        key = "NONEXISTENT_KEY_FOR_TESTING"
    "#;

    let result = EdgepadConfig::parse(toml);
    assert!(
        result.is_err(),
        "Invalid key name must fail parsing with an error"
    );
    let err_msg = result.unwrap_err();
    assert!(
        err_msg.contains("unknown key name"),
        "Error message must mention unknown key: {err_msg}"
    );
}

#[test]
fn corner_zones_parse_and_serialize_shortcuts() {
    let toml = r#"
        device = "auto"
        edge_width = 0.10

        [[gestures]]
        zone = "top-left"
        direction = "double-tap"
        keys = ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"]
        name = "Mute Mic"

        [[gestures]]
        zone = "top-right"
        direction = "double-tap"
        keys = ["KEY_LEFTALT", "KEY_F4"]
        name = "Close Window"

        [[gestures]]
        zone = "bottom-left"
        direction = "double-tap"
        keys = ["KEY_LEFTMETA"]
        name = "Launcher"

        [[gestures]]
        zone = "bottom-right"
        direction = "double-tap"
        action = { type = "shortcut", keys = ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"] }
        name = "Terminal"
    "#;

    let config = EdgepadConfig::parse(toml).expect("config with corner shortcuts should parse");
    assert_eq!(config.gestures.len(), 4);

    assert_eq!(config.gestures[0].zone, Zone::TopLeft);
    assert_eq!(config.gestures[0].direction, GestureDirection::DoubleTap);
    assert_eq!(
        config.gestures[0].action,
        GestureActionConfig::KeyCombo {
            key_codes: vec![29, 42, 50],
            key_names: vec![
                "KEY_LEFTCTRL".to_string(),
                "KEY_LEFTSHIFT".to_string(),
                "KEY_M".to_string()
            ],
        }
    );

    assert_eq!(config.gestures[1].zone, Zone::TopRight);
    assert_eq!(config.gestures[1].direction, GestureDirection::DoubleTap);
    assert_eq!(
        config.gestures[1].action,
        GestureActionConfig::KeyCombo {
            key_codes: vec![56, 62],
            key_names: vec!["KEY_LEFTALT".to_string(), "KEY_F4".to_string()],
        }
    );

    assert_eq!(config.gestures[2].zone, Zone::BottomLeft);
    assert_eq!(config.gestures[2].direction, GestureDirection::DoubleTap);

    assert_eq!(config.gestures[3].zone, Zone::BottomRight);
    assert_eq!(config.gestures[3].direction, GestureDirection::DoubleTap);
    assert_eq!(
        config.gestures[3].action,
        GestureActionConfig::KeyCombo {
            key_codes: vec![29, 56, 20],
            key_names: vec![
                "KEY_LEFTCTRL".to_string(),
                "KEY_LEFTALT".to_string(),
                "KEY_T".to_string()
            ],
        }
    );

    // active_edge_widths should enable all 4 edges since all 4 corners are used
    let widths = config.active_edge_widths();
    assert_eq!(widths.left, 0.10);
    assert_eq!(widths.right, 0.10);
    assert_eq!(widths.top, 0.10);
    assert_eq!(widths.bottom, 0.10);

    let engine_opts = config.engine_options();
    assert!(engine_opts.double_tap_zones.contains(Zone::TopLeft));
    assert!(engine_opts.double_tap_zones.contains(Zone::TopRight));
    assert!(engine_opts.double_tap_zones.contains(Zone::BottomLeft));
    assert!(engine_opts.double_tap_zones.contains(Zone::BottomRight));

    // Corner zones must NEVER be in single_tap_zones
    assert!(!engine_opts.single_tap_zones.contains(Zone::TopLeft));
    assert!(!engine_opts.single_tap_zones.contains(Zone::TopRight));
    assert!(!engine_opts.single_tap_zones.contains(Zone::BottomLeft));
    assert!(!engine_opts.single_tap_zones.contains(Zone::BottomRight));

    // Verify roundtrip serialization
    let raw = config.to_raw();
    assert_eq!(raw.gestures.len(), 4);
    assert_eq!(raw.gestures[0].zone, "top-left");
    assert_eq!(raw.gestures[0].direction, "double-tap");
    assert_eq!(
        raw.gestures[0].keys,
        Some(vec![
            "KEY_LEFTCTRL".to_string(),
            "KEY_LEFTSHIFT".to_string(),
            "KEY_M".to_string()
        ])
    );
}

#[test]
fn corner_zones_reject_single_tap_or_swipes() {
    let toml = r#"
        device = "auto"
        edge_width = 0.10

        [[gestures]]
        zone = "top-left"
        direction = "tap"
        key = "KEY_M"
    "#;

    let result = EdgepadConfig::parse(toml);
    assert!(
        result.is_err(),
        "Single tap on corner zone must be rejected"
    );
    let err_msg = result.unwrap_err();
    assert!(
        err_msg.contains("corner zones support double-tap only"),
        "Error message should mention corner double-tap only: {err_msg}"
    );
}

#[test]
fn engine_recognizes_double_tap_in_four_corners() {
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 9,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    };
    let edges = EdgeWidths::all(0.15); // edges 0..150 and 850..1000

    let options = EngineOptions {
        double_tap_zones: ZoneSet::from_zones([
            Zone::TopLeft,
            Zone::TopRight,
            Zone::BottomLeft,
            Zone::BottomRight,
        ]),
        single_tap_zones: ZoneSet::default(),
        active_zones: ZoneSet::from_zones([
            Zone::TopLeft,
            Zone::TopRight,
            Zone::BottomLeft,
            Zone::BottomRight,
        ]),
        double_tap_timeout: Duration::from_millis(300),
        tap_max_duration: Duration::from_millis(200),
        ..Default::default()
    };

    let corners = [
        (Zone::TopLeft, 50, 50),
        (Zone::TopRight, 950, 50),
        (Zone::BottomLeft, 50, 950),
        (Zone::BottomRight, 950, 950),
    ];

    for (corner_zone, cx, cy) in corners {
        let mut engine = Engine::with_options(caps, edges, Vec::new(), options);
        let mut now = Duration::from_millis(1000);

        // --- First Tap Down ---
        let f1 = vec![
            Event::slot(0),
            Event::tracking_id(1),
            Event::x(cx),
            Event::y(cy),
        ];
        let out1 = engine.process_frame_at(&f1, now).unwrap();
        assert_eq!(out1.gestures.len(), 0);

        // Hold for 40ms
        now += Duration::from_millis(40);
        // First Tap Release
        let f2 = vec![Event::slot(0), Event::tracking_id(-1)];
        let out2 = engine.process_frame_at(&f2, now).unwrap();
        // First tap MUST NOT emit an action!
        assert_eq!(
            out2.gestures.len(),
            0,
            "First tap must not trigger an action in {:?}",
            corner_zone
        );

        // Gap of 80ms
        now += Duration::from_millis(80);

        // --- Second Tap Down in same corner ---
        let f3 = vec![
            Event::slot(0),
            Event::tracking_id(2),
            Event::x(cx + 2),
            Event::y(cy + 2),
        ];
        let out3 = engine.process_frame_at(&f3, now).unwrap();
        assert_eq!(out3.gestures.len(), 0);

        // Hold for 40ms
        now += Duration::from_millis(40);
        // Second Tap Release
        let f4 = vec![Event::slot(0), Event::tracking_id(-1)];
        let out4 = engine.process_frame_at(&f4, now).unwrap();

        // Exactly ONE double-tap recognized!
        assert_eq!(
            out4.gestures.len(),
            1,
            "Second tap in {:?} must recognize double tap",
            corner_zone
        );
        assert_eq!(out4.gestures[0].direction, GestureDirection::DoubleTap);
        assert_eq!(out4.gestures[0].zone, corner_zone);
    }
}

#[test]
fn engine_single_tap_in_corner_times_out_without_action() {
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 9,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    };
    let edges = EdgeWidths::all(0.15);

    let options = EngineOptions {
        double_tap_zones: ZoneSet::from_zones([Zone::TopLeft]),
        single_tap_zones: ZoneSet::default(), // No single tap
        active_zones: ZoneSet::from_zones([Zone::TopLeft]),
        double_tap_timeout: Duration::from_millis(250),
        ..Default::default()
    };

    let mut engine = Engine::with_options(caps, edges, Vec::new(), options);
    let mut now = Duration::from_millis(1000);

    // Tap Down
    let f1 = vec![
        Event::slot(0),
        Event::tracking_id(1),
        Event::x(50),
        Event::y(50),
    ];
    engine.process_frame_at(&f1, now).unwrap();

    // Tap Up
    now += Duration::from_millis(50);
    let f2 = vec![Event::slot(0), Event::tracking_id(-1)];
    let out = engine.process_frame_at(&f2, now).unwrap();
    assert_eq!(out.gestures.len(), 0);

    // Advance time past timeout
    now += Duration::from_millis(300);
    let timeout_out = engine.advance_time(now);
    // MUST NOT emit any gesture!
    assert_eq!(
        timeout_out.gestures.len(),
        0,
        "Single tap in corner must silently expire without triggering action"
    );
}

#[test]
fn engine_rejects_tap_outside_corner_or_cross_corner_tap() {
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 9,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    };
    let edges = EdgeWidths::all(0.15);

    let options = EngineOptions {
        double_tap_zones: ZoneSet::from_zones([Zone::TopLeft, Zone::TopRight]),
        single_tap_zones: ZoneSet::default(),
        active_zones: ZoneSet::from_zones([Zone::TopLeft, Zone::TopRight]),
        double_tap_timeout: Duration::from_millis(250),
        ..Default::default()
    };

    let mut engine = Engine::with_options(caps, edges, Vec::new(), options);
    let mut now = Duration::from_millis(1000);

    // 1. First tap in TopLeft
    let f1 = vec![
        Event::slot(0),
        Event::tracking_id(1),
        Event::x(50),
        Event::y(50),
    ];
    engine.process_frame_at(&f1, now).unwrap();
    now += Duration::from_millis(40);
    engine
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();

    // 2. Second tap in TopRight (different corner!)
    now += Duration::from_millis(50);
    let f3 = vec![
        Event::slot(0),
        Event::tracking_id(2),
        Event::x(950),
        Event::y(50),
    ];
    engine.process_frame_at(&f3, now).unwrap();
    now += Duration::from_millis(40);
    let out = engine
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();

    // Must NOT recognize a double tap across different corners!
    assert_eq!(
        out.gestures.len(),
        0,
        "Taps across different corners must not trigger double tap"
    );

    // 3. Movement beyond threshold cancels tap candidate
    now += Duration::from_millis(500);
    let f_move_1 = vec![
        Event::slot(0),
        Event::tracking_id(3),
        Event::x(50),
        Event::y(50),
    ];
    engine.process_frame_at(&f_move_1, now).unwrap();
    // Drag finger significantly
    now += Duration::from_millis(50);
    let f_move_2 = vec![Event::slot(0), Event::x(50), Event::y(250)];
    engine.process_frame_at(&f_move_2, now).unwrap();
    now += Duration::from_millis(50);
    let out_move = engine
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    for g in out_move.gestures {
        assert_ne!(
            g.direction,
            GestureDirection::DoubleTap,
            "Dragging must not produce a double tap"
        );
    }
}

#[test]
fn engine_honors_custom_corner_hitbox_bounds() {
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 9,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    };
    let edges = EdgeWidths::all(0.02);

    // 1. Test 5% tiny corner hitbox
    let options_tiny = EngineOptions {
        double_tap_zones: ZoneSet::from_zones([Zone::TopLeft]),
        single_tap_zones: ZoneSet::default(),
        active_zones: ZoneSet::from_zones([Zone::TopLeft]),
        corner_hitbox: 0.05,
        ..Default::default()
    };
    let mut engine_tiny = Engine::with_options(caps, edges, Vec::new(), options_tiny);
    let mut now = Duration::from_millis(1000);

    // First tap at (x=40, y=40) -> 0.04 is within 0.05
    engine_tiny
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(1),
                Event::x(40),
                Event::y(40),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    engine_tiny
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();

    // Second tap at (x=40, y=40)
    now += Duration::from_millis(50);
    engine_tiny
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(2),
                Event::x(40),
                Event::y(40),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    let out = engine_tiny
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    assert_eq!(out.gestures.len(), 1);
    assert_eq!(out.gestures[0].zone, Zone::TopLeft);
    assert_eq!(out.gestures[0].direction, GestureDirection::DoubleTap);

    // Taps at (x=80, y=40) -> 0.08 is outside 0.05 hitbox
    now += Duration::from_millis(500);
    engine_tiny
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(3),
                Event::x(80),
                Event::y(40),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    engine_tiny
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    now += Duration::from_millis(50);
    engine_tiny
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(4),
                Event::x(80),
                Event::y(40),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    let out_outside = engine_tiny
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    assert_eq!(
        out_outside.gestures.len(),
        0,
        "Touch at 8% must not trigger 5% corner hitbox"
    );

    // 2. Test 35% large corner hitbox
    let options_large = EngineOptions {
        double_tap_zones: ZoneSet::from_zones([Zone::TopLeft]),
        single_tap_zones: ZoneSet::default(),
        active_zones: ZoneSet::from_zones([Zone::TopLeft]),
        corner_hitbox: 0.35,
        ..Default::default()
    };
    let mut engine_large = Engine::with_options(caps, edges, Vec::new(), options_large);
    now += Duration::from_millis(500);

    // Double tap at (x=300, y=300) -> 0.30 is within 0.35 hitbox
    engine_large
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(5),
                Event::x(300),
                Event::y(300),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    engine_large
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    now += Duration::from_millis(50);
    engine_large
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(6),
                Event::x(300),
                Event::y(300),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    let out_large = engine_large
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    assert_eq!(out_large.gestures.len(), 1);
    assert_eq!(out_large.gestures[0].zone, Zone::TopLeft);
    assert_eq!(out_large.gestures[0].direction, GestureDirection::DoubleTap);
}

#[test]
fn swipe_max_drift_calibration_filters_excessive_drift() {
    let caps = Capabilities {
        slot_min: 0,
        slot_max: 9,
        x: AxisRange { min: 0, max: 1000 },
        y: AxisRange { min: 0, max: 1000 },
    };
    let edges = EdgeWidths::all(0.15); // edge zone: 0..150

    // Calibrated with max drift threshold of 0.05 (50 units on 1000-wide touchpad)
    let options = EngineOptions {
        swipe_min_distance: 0.08, // 80 units
        swipe_max_drift: 0.05,    // 50 units
        active_zones: ZoneSet::from_zones([Zone::Left]),
        ..Default::default()
    };

    // 1. Swipe Up with drift WITHIN threshold (dx = 30 units = 0.03 <= 0.05, dy = -120 units)
    let mut engine = Engine::with_options(caps, edges, Vec::new(), options);
    let mut now = Duration::from_millis(1000);
    engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(1),
                Event::x(50),
                Event::y(600),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    // Finger moves to x=80 (+30 units drift), y=480 (-120 units vertical)
    engine
        .process_frame_at(&[Event::slot(0), Event::x(80), Event::y(480)], now)
        .unwrap();
    now += Duration::from_millis(50);
    let out_valid = engine
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    assert_eq!(
        out_valid.gestures.len(),
        1,
        "Swipe with drift within threshold must be recognized"
    );
    assert_eq!(out_valid.gestures[0].direction, GestureDirection::Up);
    assert_eq!(out_valid.gestures[0].zone, Zone::Left);

    // 2. Swipe Up with excessive horizontal drift (dx = 80 units = 0.08 > 0.05, dy = -120 units)
    now += Duration::from_millis(500);
    engine
        .process_frame_at(
            &[
                Event::slot(0),
                Event::tracking_id(2),
                Event::x(50),
                Event::y(600),
            ],
            now,
        )
        .unwrap();
    now += Duration::from_millis(50);
    // Finger drifts inward to x=130 (+80 units horizontal drift > 0.05 threshold)
    engine
        .process_frame_at(&[Event::slot(0), Event::x(130), Event::y(480)], now)
        .unwrap();
    now += Duration::from_millis(50);
    let out_drift_rejected = engine
        .process_frame_at(&[Event::slot(0), Event::tracking_id(-1)], now)
        .unwrap();
    assert_eq!(
        out_drift_rejected.gestures.len(),
        0,
        "Swipe with drift exceeding max drift calibration threshold must be rejected"
    );
}

#[test]
fn toml_parses_swipe_max_drift_and_engine_table() {
    let toml_toplevel = r#"
        device = "auto"
        edge_width = 0.12
        swipe_max_drift = 0.0413
        swipe_min_distance = 0.08

        [[gestures]]
        zone = "left"
        direction = "up"
        key = "KEY_BRIGHTNESSUP"
    "#;
    let cfg = EdgepadConfig::parse(toml_toplevel).expect("valid toml with swipe_max_drift");
    assert!((cfg.swipe_max_drift - 0.0413).abs() < 1e-4);

    let toml_engine = r#"
        device = "auto"
        edge_width = 0.12
        
        [engine]
        min_travel = 250
        max_drift = 120

        [[gestures]]
        zone = "left"
        direction = "up"
        key = "KEY_BRIGHTNESSUP"
    "#;
    let cfg_engine = EdgepadConfig::parse(toml_engine).expect("valid toml with [engine] table");
    // 120 / 2905 ≈ 0.0413
    assert!((cfg_engine.swipe_max_drift - (120.0 / 2905.0)).abs() < 1e-4);
}
