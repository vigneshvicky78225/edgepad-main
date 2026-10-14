use edgepad::config::{EdgepadConfig, GestureActionConfig, SliderActionConfig};
use edgepad::core::{GestureDirection, Zone};
use edgepad::keyboard::{parse_key_code, key_code_to_name, VirtualKeyboard};

#[test]
fn default_preset_generates_valid_brightness_and_volume_mappings() {
    let preset = EdgepadConfig::default_preset();
    assert_eq!(preset.gestures.len(), 4);
    assert_eq!(preset.edge_width, 0.12);
    assert_eq!(preset.swipe_min_distance, 0.08);

    // Verify Left Edge Swipe Up -> KEY_BRIGHTNESSUP
    let left_up = preset.gestures.iter().find(|g| g.zone == Zone::Left && g.direction == GestureDirection::Up).unwrap();
    assert_eq!(left_up.action, GestureActionConfig::Key {
        key_code: 225,
        key_name: "KEY_BRIGHTNESSUP".to_string(),
        repeat: 1,
    });

    // Verify Left Edge Swipe Down -> KEY_BRIGHTNESSDOWN
    let left_down = preset.gestures.iter().find(|g| g.zone == Zone::Left && g.direction == GestureDirection::Down).unwrap();
    assert_eq!(left_down.action, GestureActionConfig::Key {
        key_code: 224,
        key_name: "KEY_BRIGHTNESSDOWN".to_string(),
        repeat: 1,
    });

    // Verify Right Edge Swipe Up -> KEY_VOLUMEUP
    let right_up = preset.gestures.iter().find(|g| g.zone == Zone::Right && g.direction == GestureDirection::Up).unwrap();
    assert_eq!(right_up.action, GestureActionConfig::Key {
        key_code: 115,
        key_name: "KEY_VOLUMEUP".to_string(),
        repeat: 1,
    });

    // Verify Right Edge Swipe Down -> KEY_VOLUMEDOWN
    let right_down = preset.gestures.iter().find(|g| g.zone == Zone::Right && g.direction == GestureDirection::Down).unwrap();
    assert_eq!(right_down.action, GestureActionConfig::Key {
        key_code: 114,
        key_name: "KEY_VOLUMEDOWN".to_string(),
        repeat: 1,
    });
}

#[test]
fn default_preset_toml_serialization_round_trip() {
    let preset = EdgepadConfig::default_preset();
    let toml_str = preset.to_toml().expect("default preset should serialize to TOML");
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

    assert_eq!(config.gestures[0].action, GestureActionConfig::Key {
        key_code: 225,
        key_name: "KEY_BRIGHTNESSUP".to_string(),
        repeat: 1,
    });

    assert_eq!(config.gestures[1].action, GestureActionConfig::Key {
        key_code: 224,
        key_name: "KEY_BRIGHTNESSDOWN".to_string(),
        repeat: 2,
    });

    assert_eq!(config.sliders[0].negative, SliderActionConfig::Key {
        key_code: 115,
        key_name: "KEY_VOLUMEUP".to_string(),
        repeat: 1,
    });
    assert_eq!(config.sliders[0].positive, SliderActionConfig::Key {
        key_code: 114,
        key_name: "KEY_VOLUMEDOWN".to_string(),
        repeat: 1,
    });
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
