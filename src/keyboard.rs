//! Linux uinput keyboard backend for emitting keyboard events safely.
//!
//! Emits key press and release events via /dev/uinput.
//! Guarantees that held keys are released on shutdown or drop.

use evdev::{
    uinput::VirtualDevice, AttributeSet, EventType, InputEvent, KeyCode,
};
use std::collections::HashSet;
use std::io;
use std::thread;
use std::time::Duration;

pub const DEFAULT_KEY_HOLD_DURATION: Duration = Duration::from_millis(18);

/// A virtual keyboard device backed by /dev/uinput.
#[derive(Debug)]
pub struct VirtualKeyboard {
    device: VirtualDevice,
    held_keys: HashSet<u16>,
}

impl VirtualKeyboard {
    /// Create a new virtual keyboard capable of emitting standard and media key events.
    pub fn new() -> io::Result<Self> {
        Self::with_name("edgepad virtual keyboard")
    }

    /// Create a new virtual keyboard with a custom device name.
    pub fn with_name(name: &str) -> io::Result<Self> {
        let mut keys = AttributeSet::<KeyCode>::new();
        // Register key codes up to 0x2ff (767) covering all standard and multimedia keys
        for code in 1..=0x2ff {
            keys.insert(KeyCode(code));
        }

        let device = VirtualDevice::builder()?
            .name(name)
            .with_keys(&keys)?
            .build()?;

        Ok(Self {
            device,
            held_keys: HashSet::new(),
        })
    }

    /// Press a key down.
    pub fn press(&mut self, key_code: u16) -> io::Result<()> {
        let ev = InputEvent::new(EventType::KEY.0, key_code, 1);
        let syn = InputEvent::new(EventType::SYNCHRONIZATION.0, 0, 0);
        self.device.emit(&[ev, syn])?;
        self.held_keys.insert(key_code);
        Ok(())
    }

    /// Release a key up.
    pub fn release(&mut self, key_code: u16) -> io::Result<()> {
        let ev = InputEvent::new(EventType::KEY.0, key_code, 0);
        let syn = InputEvent::new(EventType::SYNCHRONIZATION.0, 0, 0);
        self.device.emit(&[ev, syn])?;
        self.held_keys.remove(&key_code);
        Ok(())
    }

    /// Tap a key: press down, hold briefly, then release up.
    pub fn tap(&mut self, key_code: u16, hold_duration: Duration) -> io::Result<()> {
        self.press(key_code)?;
        if !hold_duration.is_zero() {
            thread::sleep(hold_duration);
        }
        self.release(key_code)?;
        Ok(())
    }

    /// Release all currently held keys.
    pub fn release_all(&mut self) -> io::Result<()> {
        let keys_to_release: Vec<u16> = self.held_keys.drain().collect();
        for key_code in keys_to_release {
            let ev = InputEvent::new(EventType::KEY.0, key_code, 0);
            let syn = InputEvent::new(EventType::SYNCHRONIZATION.0, 0, 0);
            let _ = self.device.emit(&[ev, syn]);
        }
        Ok(())
    }

    /// Check if any keys are currently logically held down.
    pub fn has_held_keys(&self) -> bool {
        !self.held_keys.is_empty()
    }
}

impl Drop for VirtualKeyboard {
    fn drop(&mut self) {
        let _ = self.release_all();
    }
}

/// Parse a key identifier (such as "KEY_VOLUMEUP", "volumeup", or "115") into an evdev key code.
pub fn parse_key_code(raw: &str) -> Result<u16, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Err("key code cannot be empty".to_string());
    }

    // Try parsing as integer
    if let Ok(code) = trimmed.parse::<u16>() {
        if code > 0 && code <= 0x2ff {
            return Ok(code);
        }
        return Err(format!("numeric key code {code} out of valid range (1..=767)"));
    }

    let upper = trimmed.to_ascii_uppercase();
    let normalized = if upper.starts_with("KEY_") {
        upper
    } else {
        format!("KEY_{upper}")
    };

    match lookup_key_code(&normalized) {
        Some(code) => Ok(code),
        None => Err(format!(
            "unknown key name '{trimmed}'; see supported keys such as KEY_BRIGHTNESSUP, KEY_VOLUMEUP, KEY_MUTE"
        )),
    }
}

/// Convert an evdev key code to its canonical string representation.
pub fn key_code_to_name(code: u16) -> String {
    for &(name, c, _) in KNOWN_KEYS {
        if c == code {
            return name.to_string();
        }
    }
    format!("KEY_{code}")
}

fn lookup_key_code(name: &str) -> Option<u16> {
    for &(kname, code, _) in KNOWN_KEYS {
        if kname == name {
            return Some(code);
        }
    }
    None
}

/// Table of common Linux key codes: (Name, Code, Human Description).
pub const KNOWN_KEYS: &[(&str, u16, &str)] = &[
    // Brightness & Display
    ("KEY_BRIGHTNESSUP", 225, "Brightness Up"),
    ("KEY_BRIGHTNESSDOWN", 224, "Brightness Down"),
    ("KEY_KBDILLUMUP", 230, "Keyboard Backlight Up"),
    ("KEY_KBDILLUMDOWN", 229, "Keyboard Backlight Down"),
    ("KEY_KBDILLUMTOGGLE", 228, "Keyboard Backlight Toggle"),
    ("KEY_DISPLAYTOGGLE", 175, "Display Toggle"),

    // Audio & Media
    ("KEY_VOLUMEUP", 115, "Volume Up"),
    ("KEY_VOLUMEDOWN", 114, "Volume Down"),
    ("KEY_MUTE", 113, "Mute Audio"),
    ("KEY_MICMUTE", 248, "Mute Microphone"),
    ("KEY_PLAYPAUSE", 164, "Play / Pause Media"),
    ("KEY_PLAY", 207, "Play Media"),
    ("KEY_PAUSE", 119, "Pause Media"),
    ("KEY_STOPCD", 166, "Stop Media"),
    ("KEY_NEXTSONG", 163, "Next Track"),
    ("KEY_PREVIOUSSONG", 165, "Previous Track"),
    ("KEY_FASTFORWARD", 208, "Fast Forward"),
    ("KEY_REWIND", 168, "Rewind"),

    // System & Power
    ("KEY_POWER", 116, "Power Button"),
    ("KEY_SLEEP", 142, "Sleep / Suspend"),
    ("KEY_WAKEUP", 143, "Wakeup"),
    ("KEY_RESTART", 0x198, "Restart"),

    // Navigation & Common Controls
    ("KEY_ESC", 1, "Escape"),
    ("KEY_ENTER", 28, "Enter / Return"),
    ("KEY_TAB", 15, "Tab"),
    ("KEY_BACKSPACE", 14, "Backspace"),
    ("KEY_SPACE", 57, "Space"),
    ("KEY_INSERT", 110, "Insert"),
    ("KEY_DELETE", 111, "Delete"),
    ("KEY_HOME", 102, "Home"),
    ("KEY_END", 107, "End"),
    ("KEY_PAGEUP", 104, "Page Up"),
    ("KEY_PAGEDOWN", 109, "Page Down"),
    ("KEY_UP", 103, "Up Arrow"),
    ("KEY_DOWN", 108, "Down Arrow"),
    ("KEY_LEFT", 105, "Left Arrow"),
    ("KEY_RIGHT", 106, "Right Arrow"),

    // Modifiers & Meta
    ("KEY_LEFTCTRL", 29, "Left Control"),
    ("KEY_RIGHTCTRL", 97, "Right Control"),
    ("KEY_LEFTSHIFT", 42, "Left Shift"),
    ("KEY_RIGHTSHIFT", 54, "Right Shift"),
    ("KEY_LEFTALT", 56, "Left Alt"),
    ("KEY_RIGHTALT", 100, "Right Alt"),
    ("KEY_LEFTMETA", 125, "Super / Meta / Windows"),
    ("KEY_RIGHTMETA", 126, "Right Meta"),
    ("KEY_CAPSLOCK", 58, "Caps Lock"),
    ("KEY_PRINT", 210, "Print Screen"),

    // Function Keys
    ("KEY_F1", 59, "F1"),
    ("KEY_F2", 60, "F2"),
    ("KEY_F3", 61, "F3"),
    ("KEY_F4", 62, "F4"),
    ("KEY_F5", 63, "F5"),
    ("KEY_F6", 64, "F6"),
    ("KEY_F7", 65, "F7"),
    ("KEY_F8", 66, "F8"),
    ("KEY_F9", 67, "F9"),
    ("KEY_F10", 68, "F10"),
    ("KEY_F11", 87, "F11"),
    ("KEY_F12", 88, "F12"),

    // Alphabet
    ("KEY_A", 30, "A"),
    ("KEY_B", 48, "B"),
    ("KEY_C", 46, "C"),
    ("KEY_D", 32, "D"),
    ("KEY_E", 18, "E"),
    ("KEY_F", 33, "F"),
    ("KEY_G", 34, "G"),
    ("KEY_H", 35, "H"),
    ("KEY_I", 23, "I"),
    ("KEY_J", 36, "J"),
    ("KEY_K", 37, "K"),
    ("KEY_L", 38, "L"),
    ("KEY_M", 50, "M"),
    ("KEY_N", 49, "N"),
    ("KEY_O", 24, "O"),
    ("KEY_P", 25, "P"),
    ("KEY_Q", 16, "Q"),
    ("KEY_R", 19, "R"),
    ("KEY_S", 31, "S"),
    ("KEY_T", 20, "T"),
    ("KEY_U", 22, "U"),
    ("KEY_V", 47, "V"),
    ("KEY_W", 17, "W"),
    ("KEY_X", 45, "X"),
    ("KEY_Y", 21, "Y"),
    ("KEY_Z", 44, "Z"),

    // Numbers
    ("KEY_1", 2, "1"),
    ("KEY_2", 3, "2"),
    ("KEY_3", 4, "3"),
    ("KEY_4", 5, "4"),
    ("KEY_5", 6, "5"),
    ("KEY_6", 7, "6"),
    ("KEY_7", 8, "7"),
    ("KEY_8", 9, "8"),
    ("KEY_9", 10, "9"),
    ("KEY_0", 11, "0"),
];

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn parse_standard_key_names() {
        assert_eq!(parse_key_code("KEY_BRIGHTNESSUP").unwrap(), 225);
        assert_eq!(parse_key_code("KEY_BRIGHTNESSDOWN").unwrap(), 224);
        assert_eq!(parse_key_code("KEY_VOLUMEUP").unwrap(), 115);
        assert_eq!(parse_key_code("KEY_VOLUMEDOWN").unwrap(), 114);
        assert_eq!(parse_key_code("volumeup").unwrap(), 115);
        assert_eq!(parse_key_code("115").unwrap(), 115);
    }

    #[test]
    fn key_code_to_name_mapping() {
        assert_eq!(key_code_to_name(225), "KEY_BRIGHTNESSUP");
        assert_eq!(key_code_to_name(115), "KEY_VOLUMEUP");
        assert_eq!(key_code_to_name(999), "KEY_999");
    }

    #[test]
    fn parse_invalid_key_fails() {
        assert!(parse_key_code("KEY_NOT_EXISTING_XYZ").is_err());
        assert!(parse_key_code("").is_err());
        assert!(parse_key_code("0").is_err());
    }
}
