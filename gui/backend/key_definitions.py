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
]

_NAME_TO_CODE: dict[str, int] = {k["name"]: k["code"] for k in KNOWN_KEYS}
_CODE_TO_NAME: dict[int, str] = {k["code"]: k["name"] for k in KNOWN_KEYS}


def get_key_code(name: str) -> int | None:
    upper = name.strip().upper()
    if not upper.startswith("KEY_"):
        upper = f"KEY_{upper}"
    return _NAME_TO_CODE.get(upper)


def get_key_name(code: int) -> str | None:
    return _CODE_TO_NAME.get(code)


def search_keys(query: str) -> list[dict[str, Any]]:
    q = query.strip().lower()
    if not q:
        return KNOWN_KEYS
    return [
        k for k in KNOWN_KEYS
        if q in k["name"].lower() or q in k["friendly"].lower() or q in k["category"].lower() or q == str(k["code"])
    ]
