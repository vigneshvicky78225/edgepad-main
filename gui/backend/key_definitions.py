"""Linux evdev key definitions and metadata for Edgepad GUI.

Provides searchable key mappings with Linux key codes, canonical names,
human-readable descriptions, and categories.
"""

from __future__ import annotations

from typing import Any


KNOWN_KEYS: list[dict[str, Any]] = [
    # Brightness & Display
    {"code": 225, "name": "KEY_BRIGHTNESSUP", "friendly": "Brightness Up", "category": "Display"},
    {"code": 224, "name": "KEY_BRIGHTNESSDOWN", "friendly": "Brightness Down", "category": "Display"},
    {"code": 230, "name": "KEY_KBDILLUMUP", "friendly": "Keyboard Backlight Up", "category": "Display"},
    {"code": 229, "name": "KEY_KBDILLUMDOWN", "friendly": "Keyboard Backlight Down", "category": "Display"},
    {"code": 228, "name": "KEY_KBDILLUMTOGGLE", "friendly": "Keyboard Backlight Toggle", "category": "Display"},
    {"code": 175, "name": "KEY_DISPLAYTOGGLE", "friendly": "Display Toggle", "category": "Display"},

    # Audio & Media
    {"code": 115, "name": "KEY_VOLUMEUP", "friendly": "Volume Up", "category": "Audio"},
    {"code": 114, "name": "KEY_VOLUMEDOWN", "friendly": "Volume Down", "category": "Audio"},
    {"code": 113, "name": "KEY_MUTE", "friendly": "Mute Audio", "category": "Audio"},
    {"code": 248, "name": "KEY_MICMUTE", "friendly": "Mute Microphone", "category": "Audio"},
    {"code": 164, "name": "KEY_PLAYPAUSE", "friendly": "Play / Pause Media", "category": "Media"},
    {"code": 207, "name": "KEY_PLAY", "friendly": "Play Media", "category": "Media"},
    {"code": 119, "name": "KEY_PAUSE", "friendly": "Pause Media", "category": "Media"},
    {"code": 166, "name": "KEY_STOPCD", "friendly": "Stop Media", "category": "Media"},
    {"code": 163, "name": "KEY_NEXTSONG", "friendly": "Next Track", "category": "Media"},
    {"code": 165, "name": "KEY_PREVIOUSSONG", "friendly": "Previous Track", "category": "Media"},
    {"code": 208, "name": "KEY_FASTFORWARD", "friendly": "Fast Forward", "category": "Media"},
    {"code": 168, "name": "KEY_REWIND", "friendly": "Rewind", "category": "Media"},

    # Navigation & System Controls
    {"code": 1, "name": "KEY_ESC", "friendly": "Escape", "category": "Navigation"},
    {"code": 28, "name": "KEY_ENTER", "friendly": "Enter / Return", "category": "Navigation"},
    {"code": 15, "name": "KEY_TAB", "friendly": "Tab", "category": "Navigation"},
    {"code": 14, "name": "KEY_BACKSPACE", "friendly": "Backspace", "category": "Navigation"},
    {"code": 57, "name": "KEY_SPACE", "friendly": "Space", "category": "Navigation"},
    {"code": 110, "name": "KEY_INSERT", "friendly": "Insert", "category": "Navigation"},
    {"code": 111, "name": "KEY_DELETE", "friendly": "Delete", "category": "Navigation"},
    {"code": 102, "name": "KEY_HOME", "friendly": "Home", "category": "Navigation"},
    {"code": 107, "name": "KEY_END", "friendly": "End", "category": "Navigation"},
    {"code": 104, "name": "KEY_PAGEUP", "friendly": "Page Up", "category": "Navigation"},
    {"code": 109, "name": "KEY_PAGEDOWN", "friendly": "Page Down", "category": "Navigation"},
    {"code": 103, "name": "KEY_UP", "friendly": "Up Arrow", "category": "Navigation"},
    {"code": 108, "name": "KEY_DOWN", "friendly": "Down Arrow", "category": "Navigation"},
    {"code": 105, "name": "KEY_LEFT", "friendly": "Left Arrow", "category": "Navigation"},
    {"code": 106, "name": "KEY_RIGHT", "friendly": "Right Arrow", "category": "Navigation"},

    # Modifiers & System
    {"code": 125, "name": "KEY_LEFTMETA", "friendly": "Super / Meta / Windows", "category": "Modifier"},
    {"code": 126, "name": "KEY_RIGHTMETA", "friendly": "Right Meta", "category": "Modifier"},
    {"code": 29, "name": "KEY_LEFTCTRL", "friendly": "Left Control", "category": "Modifier"},
    {"code": 97, "name": "KEY_RIGHTCTRL", "friendly": "Right Control", "category": "Modifier"},
    {"code": 42, "name": "KEY_LEFTSHIFT", "friendly": "Left Shift", "category": "Modifier"},
    {"code": 54, "name": "KEY_RIGHTSHIFT", "friendly": "Right Shift", "category": "Modifier"},
    {"code": 56, "name": "KEY_LEFTALT", "friendly": "Left Alt", "category": "Modifier"},
    {"code": 100, "name": "KEY_RIGHTALT", "friendly": "Right Alt", "category": "Modifier"},
    {"code": 58, "name": "KEY_CAPSLOCK", "friendly": "Caps Lock", "category": "Modifier"},
    {"code": 210, "name": "KEY_PRINT", "friendly": "Print Screen", "category": "System"},
    {"code": 116, "name": "KEY_POWER", "friendly": "Power Button", "category": "System"},
    {"code": 142, "name": "KEY_SLEEP", "friendly": "Sleep / Suspend", "category": "System"},
    {"code": 143, "name": "KEY_WAKEUP", "friendly": "Wakeup", "category": "System"},

    # Function Keys
    {"code": 59, "name": "KEY_F1", "friendly": "F1", "category": "Function"},
    {"code": 60, "name": "KEY_F2", "friendly": "F2", "category": "Function"},
    {"code": 61, "name": "KEY_F3", "friendly": "F3", "category": "Function"},
    {"code": 62, "name": "KEY_F4", "friendly": "F4", "category": "Function"},
    {"code": 63, "name": "KEY_F5", "friendly": "F5", "category": "Function"},
    {"code": 64, "name": "KEY_F6", "friendly": "F6", "category": "Function"},
    {"code": 65, "name": "KEY_F7", "friendly": "F7", "category": "Function"},
    {"code": 66, "name": "KEY_F8", "friendly": "F8", "category": "Function"},
    {"code": 67, "name": "KEY_F9", "friendly": "F9", "category": "Function"},
    {"code": 68, "name": "KEY_F10", "friendly": "F10", "category": "Function"},
    {"code": 87, "name": "KEY_F11", "friendly": "F11", "category": "Function"},
    {"code": 88, "name": "KEY_F12", "friendly": "F12", "category": "Function"},

    # Alphabet
    {"code": 30, "name": "KEY_A", "friendly": "A", "category": "Alphabet"},
    {"code": 48, "name": "KEY_B", "friendly": "B", "category": "Alphabet"},
    {"code": 46, "name": "KEY_C", "friendly": "C", "category": "Alphabet"},
    {"code": 32, "name": "KEY_D", "friendly": "D", "category": "Alphabet"},
    {"code": 18, "name": "KEY_E", "friendly": "E", "category": "Alphabet"},
    {"code": 33, "name": "KEY_F", "friendly": "F", "category": "Alphabet"},
    {"code": 34, "name": "KEY_G", "friendly": "G", "category": "Alphabet"},
    {"code": 35, "name": "KEY_H", "friendly": "H", "category": "Alphabet"},
    {"code": 23, "name": "KEY_I", "friendly": "I", "category": "Alphabet"},
    {"code": 36, "name": "KEY_J", "friendly": "J", "category": "Alphabet"},
    {"code": 37, "name": "KEY_K", "friendly": "K", "category": "Alphabet"},
    {"code": 38, "name": "KEY_L", "friendly": "L", "category": "Alphabet"},
    {"code": 50, "name": "KEY_M", "friendly": "M", "category": "Alphabet"},
    {"code": 49, "name": "KEY_N", "friendly": "N", "category": "Alphabet"},
    {"code": 24, "name": "KEY_O", "friendly": "O", "category": "Alphabet"},
    {"code": 25, "name": "KEY_P", "friendly": "P", "category": "Alphabet"},
    {"code": 16, "name": "KEY_Q", "friendly": "Q", "category": "Alphabet"},
    {"code": 19, "name": "KEY_R", "friendly": "R", "category": "Alphabet"},
    {"code": 31, "name": "KEY_S", "friendly": "S", "category": "Alphabet"},
    {"code": 20, "name": "KEY_T", "friendly": "T", "category": "Alphabet"},
    {"code": 22, "name": "KEY_U", "friendly": "U", "category": "Alphabet"},
    {"code": 47, "name": "KEY_V", "friendly": "V", "category": "Alphabet"},
    {"code": 17, "name": "KEY_W", "friendly": "W", "category": "Alphabet"},
    {"code": 45, "name": "KEY_X", "friendly": "X", "category": "Alphabet"},
    {"code": 21, "name": "KEY_Y", "friendly": "Y", "category": "Alphabet"},
    {"code": 44, "name": "KEY_Z", "friendly": "Z", "category": "Alphabet"},

    # Numbers
    {"code": 11, "name": "KEY_0", "friendly": "0", "category": "Number"},
    {"code": 2, "name": "KEY_1", "friendly": "1", "category": "Number"},
    {"code": 3, "name": "KEY_2", "friendly": "2", "category": "Number"},
    {"code": 4, "name": "KEY_3", "friendly": "3", "category": "Number"},
    {"code": 5, "name": "KEY_4", "friendly": "4", "category": "Number"},
    {"code": 6, "name": "KEY_5", "friendly": "5", "category": "Number"},
    {"code": 7, "name": "KEY_6", "friendly": "6", "category": "Number"},
    {"code": 8, "name": "KEY_7", "friendly": "7", "category": "Number"},
    {"code": 9, "name": "KEY_8", "friendly": "8", "category": "Number"},
    {"code": 10, "name": "KEY_9", "friendly": "9", "category": "Number"},
]

_NAME_TO_CODE: dict[str, int] = {k["name"]: k["code"] for k in KNOWN_KEYS}
_CODE_TO_NAME: dict[int, str] = {k["code"]: k["name"] for k in KNOWN_KEYS}
_FRIENDLY_NAMES: dict[str, str] = {k["name"]: k["friendly"] for k in KNOWN_KEYS}

# Canonical modifier ordering (Linux / KDE desktop standard)
MODIFIER_ORDER = [
    "KEY_LEFTCTRL",
    "KEY_RIGHTCTRL",
    "KEY_LEFTALT",
    "KEY_RIGHTALT",
    "KEY_LEFTSHIFT",
    "KEY_RIGHTSHIFT",
    "KEY_LEFTMETA",
    "KEY_RIGHTMETA",
]

MODIFIER_DISPLAY = {
    "KEY_LEFTCTRL": "Ctrl",
    "KEY_RIGHTCTRL": "Ctrl",
    "KEY_LEFTALT": "Alt",
    "KEY_RIGHTALT": "Alt",
    "KEY_LEFTSHIFT": "Shift",
    "KEY_RIGHTSHIFT": "Shift",
    "KEY_LEFTMETA": "Super",
    "KEY_RIGHTMETA": "Super",
}


def get_key_code(name: str) -> int | None:
    upper = name.strip().upper()
    if not upper.startswith("KEY_"):
        upper = f"KEY_{upper}"
    return _NAME_TO_CODE.get(upper)


def get_key_name(code: int) -> str | None:
    return _CODE_TO_NAME.get(code)


def format_key_name(key_name: str) -> str:
    """Returns human-friendly label for a Linux key identifier."""
    if key_name in MODIFIER_DISPLAY:
        return MODIFIER_DISPLAY[key_name]
    if key_name in _FRIENDLY_NAMES:
        return _FRIENDLY_NAMES[key_name]
    if key_name.startswith("KEY_"):
        suffix = key_name[4:]
        if len(suffix) == 1:
            return suffix
        return suffix.capitalize()
    return key_name


def normalize_shortcut_keys(keys: list[str]) -> list[str]:
    """Sorts modifiers into canonical order (Ctrl -> Alt -> Shift -> Super) followed by primary keys."""
    modifiers: list[str] = []
    primary: list[str] = []

    seen = set()
    for k in keys:
        canonical = k.strip().upper()
        if not canonical.startswith("KEY_"):
            canonical = f"KEY_{canonical}"
        if canonical in seen:
            continue
        seen.add(canonical)
        if canonical in MODIFIER_ORDER:
            modifiers.append(canonical)
        else:
            primary.append(canonical)

    # Sort modifiers by canonical index
    modifiers.sort(key=lambda m: MODIFIER_ORDER.index(m) if m in MODIFIER_ORDER else 99)
    return modifiers + primary


def format_shortcut(keys: list[str]) -> str:
    """Formats a list of Linux key identifiers into a readable combination string (e.g. 'Ctrl + Shift + M')."""
    if not keys:
        return "None"
    normalized = normalize_shortcut_keys(keys)
    labels = [format_key_name(k) for k in normalized]
    return " + ".join(labels)


# Common Qt.Key (integer values) to evdev KEY_* mappings
QT_KEY_MAP: dict[int, str] = {
    # Qt.Key_Escape .. Qt.Key_Backtab
    0x01000000: "KEY_ESC",
    0x01000001: "KEY_TAB",
    0x01000002: "KEY_TAB",
    0x01000003: "KEY_BACKSPACE",
    0x01000004: "KEY_ENTER",
    0x01000005: "KEY_ENTER",
    0x01000006: "KEY_INSERT",
    0x01000007: "KEY_DELETE",
    0x01000008: "KEY_PAUSE",
    0x01000009: "KEY_PRINT",
    0x01000010: "KEY_HOME",
    0x01000011: "KEY_END",
    0x01000012: "KEY_LEFT",
    0x01000013: "KEY_UP",
    0x01000014: "KEY_RIGHT",
    0x01000015: "KEY_DOWN",
    0x01000016: "KEY_PAGEUP",
    0x01000017: "KEY_PAGEDOWN",
    0x01000020: "KEY_LEFTSHIFT",
    0x01000021: "KEY_LEFTCTRL",
    0x01000022: "KEY_LEFTMETA",
    0x01000023: "KEY_LEFTALT",
    0x01000024: "KEY_CAPSLOCK",
    0x01000025: "KEY_NUMLOCK",
    0x01000026: "KEY_SCROLLLOCK",
    # Function Keys F1-F12
    0x01000030: "KEY_F1",
    0x01000031: "KEY_F2",
    0x01000032: "KEY_F3",
    0x01000033: "KEY_F4",
    0x01000034: "KEY_F5",
    0x01000035: "KEY_F6",
    0x01000036: "KEY_F7",
    0x01000037: "KEY_F8",
    0x01000038: "KEY_F9",
    0x01000039: "KEY_F10",
    0x0100003A: "KEY_F11",
    0x0100003B: "KEY_F12",
    # Space and Symbols
    0x20: "KEY_SPACE",
    0x2D: "KEY_MINUS",
    0x3D: "KEY_EQUAL",
    0x5B: "KEY_LEFTBRACE",
    0x5D: "KEY_RIGHTBRACE",
    0x3B: "KEY_SEMICOLON",
    0x27: "KEY_APOSTROPHE",
    0x60: "KEY_GRAVE",
    0x5C: "KEY_BACKSLASH",
    0x2C: "KEY_COMMA",
    0x2E: "KEY_DOT",
    0x2F: "KEY_SLASH",
}

# Add ASCII alphabet (A-Z: 0x41..0x5A)
for _ord in range(ord("A"), ord("Z") + 1):
    QT_KEY_MAP[_ord] = f"KEY_{chr(_ord)}"

# Add ASCII numbers (0-9: 0x30..0x39)
for _ord in range(ord("0"), ord("9") + 1):
    QT_KEY_MAP[_ord] = f"KEY_{chr(_ord)}"


def parse_qt_key_event(qt_key: int, qt_modifiers: int) -> tuple[list[str], str]:
    """Converts a Qt key and modifier bitmask into canonical Linux key names and display string."""
    modifiers: list[str] = []
    # Qt.KeyboardModifier bitmasks:
    # ShiftModifier   = 0x02000000
    # ControlModifier = 0x04000000
    # AltModifier     = 0x08000000
    # MetaModifier    = 0x10000000
    if qt_modifiers & 0x04000000:
        modifiers.append("KEY_LEFTCTRL")
    if qt_modifiers & 0x08000000:
        modifiers.append("KEY_LEFTALT")
    if qt_modifiers & 0x02000000:
        modifiers.append("KEY_LEFTSHIFT")
    if qt_modifiers & 0x10000000:
        modifiers.append("KEY_LEFTMETA")

    # Resolve primary key
    primary_key = QT_KEY_MAP.get(qt_key)
    if primary_key is None and 0 < qt_key < 256:
        ch = chr(qt_key).upper()
        if "A" <= ch <= "Z" or "0" <= ch <= "9":
            primary_key = f"KEY_{ch}"

    # If the pressed key was itself a modifier, ensure it is recorded
    if qt_key == 0x01000021 and "KEY_LEFTCTRL" not in modifiers:
        modifiers.append("KEY_LEFTCTRL")
        primary_key = None
    elif qt_key == 0x01000023 and "KEY_LEFTALT" not in modifiers:
        modifiers.append("KEY_LEFTALT")
        primary_key = None
    elif qt_key == 0x01000020 and "KEY_LEFTSHIFT" not in modifiers:
        modifiers.append("KEY_LEFTSHIFT")
        primary_key = None
    elif qt_key == 0x01000022 and "KEY_LEFTMETA" not in modifiers:
        modifiers.append("KEY_LEFTMETA")
        primary_key = None

    all_keys = list(modifiers)
    if primary_key and primary_key not in all_keys:
        all_keys.append(primary_key)

    normalized = normalize_shortcut_keys(all_keys)
    display = format_shortcut(normalized)
    return normalized, display


def search_keys(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return KNOWN_KEYS
    return [
        k for k in KNOWN_KEYS
        if q in k["name"].lower() or q in k["friendly"].lower() or q in k["category"].lower() or q == str(k["code"])
    ]

