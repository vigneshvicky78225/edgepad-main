"""Configuration manager for Edgepad GUI.

Provides atomic loading, validation, saving, backup, preset generation,
and export/import for ~/.config/edgepad/edgepad.toml.
"""

from __future__ import annotations

import copy
import datetime
import os
import shutil
import tempfile
import tomllib
from pathlib import Path
from typing import Any

from gui.backend.key_definitions import KNOWN_KEYS, get_key_code, get_key_name

VALID_EDGE_ZONES = ["left", "right", "top", "bottom"]
VALID_CORNER_ZONES = ["top-left", "top-right", "bottom-left", "bottom-right"]
VALID_ZONES = VALID_EDGE_ZONES + VALID_CORNER_ZONES
VALID_SWIPE_DIRECTIONS = ["up", "down", "left", "right"]
VALID_TAP_DIRECTIONS = ["tap", "double-tap"]
VALID_DIRECTIONS = VALID_SWIPE_DIRECTIONS + VALID_TAP_DIRECTIONS

MEDIA_ACTION_KEYS = {
    "play_pause": "KEY_PLAYPAUSE",
    "next": "KEY_NEXTSONG",
    "previous": "KEY_PREVIOUSSONG",
    "stop": "KEY_STOPCD",
    "mute": "KEY_MUTE",
}

MEDIA_ACTION_LABELS = {
    "play_pause": "Play / Pause",
    "next": "Next Track",
    "previous": "Previous Track",
    "stop": "Stop Playback",
    "mute": "Mute / Unmute",
}


def get_default_workspace_command(direction: str) -> list[str]:
    """Generates the best desktop command for switching workspaces on current DE."""
    qdbus_bin = shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus-qt5")
    if qdbus_bin:
        method = "nextDesktop" if direction == "next" else "previousDesktop"
        return [qdbus_bin, "org.kde.KWin", "/KWin", f"org.kde.KWin.{method}"]
    wmctrl_bin = shutil.which("wmctrl")
    if wmctrl_bin:
        return [wmctrl_bin, "-s", "next" if direction == "next" else "prev"]
    return ["notify-send", "Edgepad Workspace", f"Switch workspace: {direction}"]


def detect_workspace_support() -> dict[str, Any]:
    """Checks desktop environment capabilities for workspace switching."""
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    qdbus_bin = shutil.which("qdbus") or shutil.which("qdbus-qt6") or shutil.which("qdbus-qt5")
    wmctrl_bin = shutil.which("wmctrl")
    if "kde" in desktop or qdbus_bin:
        return {
            "supported": True,
            "method": "KDE Plasma KWin IPC (qdbus)",
            "next_cmd": [qdbus_bin or "qdbus", "org.kde.KWin", "/KWin", "org.kde.KWin.nextDesktop"],
            "prev_cmd": [qdbus_bin or "qdbus", "org.kde.KWin", "/KWin", "org.kde.KWin.previousDesktop"],
        }
    elif wmctrl_bin:
        return {
            "supported": True,
            "method": "X11 / EWMH (wmctrl)",
            "next_cmd": [wmctrl_bin, "-s", "next"],
            "prev_cmd": [wmctrl_bin, "-s", "prev"],
        }
    else:
        return {
            "supported": False,
            "method": f"{desktop.upper() or 'Desktop'} (install qdbus or wmctrl for workspace switching)",
            "next_cmd": ["notify-send", "Edgepad", "Next Workspace"],
            "prev_cmd": ["notify-send", "Edgepad", "Previous Workspace"],
        }


def default_tap_actions() -> list[dict[str, Any]]:
    """Returns recommended default tap actions for Left, Right, and Top zones."""
    return [
        {
            "name": "Mute Audio",
            "enabled": True,
            "edge": "left",
            "direction": "tap",
            "fingers": 1,
            "action": {
                "type": "key",
                "key": "KEY_MUTE",
                "repeat": 1,
            },
        },
        {
            "name": "Play / Pause",
            "enabled": True,
            "edge": "top",
            "direction": "tap",
            "fingers": 1,
            "action": {
                "type": "media",
                "media_action": "play_pause",
                "key": "KEY_PLAYPAUSE",
                "repeat": 1,
            },
        },
        {
            "name": "Stop Media",
            "enabled": True,
            "edge": "top",
            "direction": "double-tap",
            "fingers": 1,
            "action": {
                "type": "media",
                "media_action": "stop",
                "key": "KEY_STOPCD",
                "repeat": 1,
            },
        },
        {
            "name": "Display Toggle",
            "enabled": True,
            "edge": "right",
            "direction": "tap",
            "fingers": 1,
            "action": {
                "type": "key",
                "key": "KEY_DISPLAYTOGGLE",
                "repeat": 1,
            },
        },
    ]


def default_corner_tap_actions() -> list[dict[str, Any]]:
    """Returns recommended default corner double-tap actions."""
    return [
        {
            "name": "Mute Microphone",
            "enabled": True,
            "edge": "top-left",
            "direction": "double-tap",
            "keys": ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"],
            "action": {"type": "shortcut", "keys": ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"]},
        },
        {
            "name": "Close Window",
            "enabled": True,
            "edge": "top-right",
            "direction": "double-tap",
            "keys": ["KEY_LEFTALT", "KEY_F4"],
            "action": {"type": "shortcut", "keys": ["KEY_LEFTALT", "KEY_F4"]},
        },
        {
            "name": "Application Launcher",
            "enabled": True,
            "edge": "bottom-left",
            "direction": "double-tap",
            "keys": ["KEY_LEFTMETA"],
            "action": {"type": "shortcut", "keys": ["KEY_LEFTMETA"]},
        },
        {
            "name": "Open Terminal",
            "enabled": True,
            "edge": "bottom-right",
            "direction": "double-tap",
            "keys": ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"],
            "action": {"type": "shortcut", "keys": ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"]},
        },
    ]


def get_xdg_config_home() -> Path:
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config and xdg_config.strip():
        return Path(xdg_config.strip())
    return Path.home() / ".config"


def get_xdg_data_home() -> Path:
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data and xdg_data.strip():
        return Path(xdg_data.strip())
    return Path.home() / ".local" / "share"


def get_xdg_state_home() -> Path:
    xdg_state = os.environ.get("XDG_STATE_HOME")
    if xdg_state and xdg_state.strip():
        return Path(xdg_state.strip())
    return Path.home() / ".local" / "state"


def get_xdg_cache_home() -> Path:
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache and xdg_cache.strip():
        return Path(xdg_cache.strip())
    return Path.home() / ".cache"


def get_default_config_path() -> Path:
    return get_xdg_config_home() / "edgepad" / "edgepad.toml"


def get_backups_dir() -> Path:
    return get_default_config_path().parent / "backups"


DEFAULT_HITBOX_CONFIG: dict[str, Any] = {
    "edge_width": 0.12,
    "left_edge_width": 0.12,
    "right_edge_width": 0.12,
    "top_edge_height": 0.12,
    "bottom_edge_height": 0.12,
    "corner_width": 0.15,
    "corner_height": 0.15,
}

DEFAULT_GESTURE_CONFIG: dict[str, Any] = {
    "swipe_min_distance": 0.08,
    "swipe_max_drift": 0.04,
    "tap_max_movement": 0.04,
    "tap_min_duration_ms": 40,
    "tap_max_duration_ms": 200,
    "double_tap_timeout_ms": 300,
    "double_tap_max_distance": 0.08,
    "cooldown_ms": 250,
}


def default_preset_config() -> dict[str, Any]:
    """Returns the default configuration preset with the requested 4 key mappings."""
    return {
        "device": "auto",
        "hitbox": copy.deepcopy(DEFAULT_HITBOX_CONFIG),
        "gesture": copy.deepcopy(DEFAULT_GESTURE_CONFIG),
        "edge_width": 0.12,
        "corner_hitbox": 0.15,
        "swipe_min_distance": 0.08,
        "swipe_max_drift": 0.04,
        "tap_max_movement": 0.04,
        "tap_min_duration_ms": 40,
        "tap_max_duration_ms": 200,
        "double_tap_timeout_ms": 300,
        "double_tap_max_distance": 0.08,
        "engine": {
            "min_travel": 232,
            "max_drift": 116,
            "cooldown_ms": 250,
            "tap_max_duration_ms": 200,
            "tap_max_movement": 116,
        },
        "gestures": [
            {
                "name": "Brightness Up",
                "enabled": True,
                "edge": "left",
                "direction": "up",
                "fingers": 1,
                "action": {
                    "type": "key",
                    "key": "KEY_BRIGHTNESSUP",
                    "repeat": 1,
                },
            },
            {
                "name": "Brightness Down",
                "enabled": True,
                "edge": "left",
                "direction": "down",
                "fingers": 1,
                "action": {
                    "type": "key",
                    "key": "KEY_BRIGHTNESSDOWN",
                    "repeat": 1,
                },
            },
            {
                "name": "Volume Up",
                "enabled": True,
                "edge": "right",
                "direction": "up",
                "fingers": 1,
                "action": {
                    "type": "key",
                    "key": "KEY_VOLUMEUP",
                    "repeat": 1,
                },
            },
            {
                "name": "Volume Down",
                "enabled": True,
                "edge": "right",
                "direction": "down",
                "fingers": 1,
                "action": {
                    "type": "key",
                    "key": "KEY_VOLUMEDOWN",
                    "repeat": 1,
                },
            },
        ],
        "sliders": [],
        "encoder": {
            "enabled": True,
            "step_size": 50.0,
            "dead_zone": 10.0,
            "repeat_interval_ms": 20,
        },
    }


def validate_hitbox_config(hitbox: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validates physical hitbox calibration dimensions independently."""
    errors: list[str] = []
    edge_width = hitbox.get("edge_width", 0.12)
    if not (0.01 <= edge_width <= 0.45):
        errors.append(f"Hitbox edge_width must be between 0.01 and 0.45 (got {edge_width})")

    for side in ["left_edge_width", "right_edge_width", "top_edge_height", "bottom_edge_height"]:
        if side in hitbox:
            val = hitbox[side]
            if not (0.01 <= val <= 0.45):
                errors.append(f"Hitbox {side} must be between 0.01 and 0.45 (got {val})")

    for corner_dim in ["corner_width", "corner_height"]:
        val = hitbox.get(corner_dim, 0.15)
        if not (0.05 <= val <= 0.35):
            errors.append(f"Hitbox {corner_dim} must be between 0.05 and 0.35 (got {val})")

    return len(errors) == 0, errors


def validate_gesture_config(gesture: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validates gesture recognition thresholds and timings independently."""
    errors: list[str] = []

    swipe_min = gesture.get("swipe_min_distance", 0.08)
    if not (0.01 <= swipe_min <= 0.50):
        errors.append(f"Gesture swipe_min_distance must be between 0.01 and 0.50 (got {swipe_min})")

    max_drift = gesture.get("swipe_max_drift", 0.04)
    if not (0.005 <= max_drift <= 0.50):
        errors.append(f"Gesture swipe_max_drift must be between 0.005 and 0.50 (got {max_drift})")

    tap_mov = gesture.get("tap_max_movement", 0.04)
    if not (0.005 <= tap_mov <= 0.30):
        errors.append(f"Gesture tap_max_movement must be between 0.005 and 0.30 (got {tap_mov})")

    tap_min = gesture.get("tap_min_duration_ms", 40)
    tap_max = gesture.get("tap_max_duration_ms", 200)
    if tap_min < 0 or tap_min > 1000:
        errors.append(f"Gesture tap_min_duration_ms must be between 0 and 1000 ms (got {tap_min})")
    if tap_max < 10 or tap_max > 2000:
        errors.append(f"Gesture tap_max_duration_ms must be between 10 and 2000 ms (got {tap_max})")
    if tap_min >= tap_max:
        errors.append(f"Gesture tap_min_duration_ms ({tap_min}) must be less than tap_max_duration_ms ({tap_max})")

    dbl_timeout = gesture.get("double_tap_timeout_ms", 300)
    if not (50 <= dbl_timeout <= 2000):
        errors.append(f"Gesture double_tap_timeout_ms must be between 50 and 2000 ms (got {dbl_timeout})")

    dbl_dist = gesture.get("double_tap_max_distance", 0.08)
    if not (0.01 <= dbl_dist <= 0.50):
        errors.append(f"Gesture double_tap_max_distance must be between 0.01 and 0.50 (got {dbl_dist})")

    cooldown = gesture.get("cooldown_ms", 250)
    if not (0 <= cooldown <= 2000):
        errors.append(f"Gesture cooldown_ms must be between 0 and 2000 ms (got {cooldown})")

    return len(errors) == 0, errors


class ConfigManager:
    """Manages reading, validating, writing, and backing up Edgepad configuration."""

    def __init__(self, config_path: Path | None = None) -> None:
        self.config_path = config_path or get_default_config_path()
        self.backups_dir = get_backups_dir()
        self._current_config: dict[str, Any] = default_preset_config()

    @property
    def current_config(self) -> dict[str, Any]:
        return self._current_config

    def config_exists(self) -> bool:
        return self.config_path.exists() and self.config_path.is_file()

    def load_config(self) -> tuple[dict[str, Any], str | None]:
        """Loads configuration from disk or initializes default preset if missing."""
        if not self.config_exists():
            default_cfg = default_preset_config()
            try:
                self.config_path.parent.mkdir(parents=True, exist_ok=True)
                toml_text = self.to_toml_string(default_cfg)
                temp_file = self.config_path.with_suffix(".tmp")
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(toml_text)
                temp_file.replace(self.config_path)
            except Exception:
                pass
            self._current_config = default_cfg
            return copy.deepcopy(self._current_config), None

        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)

            parsed = self._normalize_config(data)
            self._current_config = parsed
            return copy.deepcopy(parsed), None
        except Exception as e:
            backup_path_str = None
            try:
                self.backups_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = self.backups_dir / f"edgepad.toml.bak.{timestamp}"
                shutil.copy2(self.config_path, backup_file)
                backup_path_str = str(backup_file)
            except Exception:
                pass

            msg = f"Failed to load config: {e}"
            if backup_path_str:
                msg += f". A safe backup of your malformed configuration was preserved at: {backup_path_str}"
            return copy.deepcopy(self._current_config), msg

    def _normalize_config(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Normalizes TOML structure into unified GUI representation."""
        config = default_preset_config()

        # Device
        if "device" in raw:
            dev = raw["device"]
            if isinstance(dev, str):
                config["device"] = dev
            elif isinstance(dev, dict) and "path" in dev:
                config["device"] = str(dev["path"])
            else:
                config["device"] = "auto"

        # 1. Hitbox Calibration
        hitbox = copy.deepcopy(DEFAULT_HITBOX_CONFIG)
        if "hitbox" in raw and isinstance(raw["hitbox"], dict):
            hb = raw["hitbox"]
            if "edge_width" in hb:
                try:
                    hitbox["edge_width"] = max(0.01, min(0.45, float(hb["edge_width"])))
                except (ValueError, TypeError):
                    pass
            for side in ["left_edge_width", "right_edge_width", "top_edge_height", "bottom_edge_height"]:
                if side in hb:
                    try:
                        hitbox[side] = max(0.01, min(0.45, float(hb[side])))
                    except (ValueError, TypeError):
                        pass
                else:
                    hitbox[side] = hitbox["edge_width"]
            if "corner_width" in hb or "corner_hitbox" in hb:
                try:
                    cw = float(hb.get("corner_width", hb.get("corner_hitbox", 0.15)))
                    hitbox["corner_width"] = max(0.05, min(0.35, cw))
                except (ValueError, TypeError):
                    pass
            if "corner_height" in hb or "corner_hitbox" in hb:
                try:
                    ch = float(hb.get("corner_height", hb.get("corner_hitbox", 0.15)))
                    hitbox["corner_height"] = max(0.05, min(0.35, ch))
                except (ValueError, TypeError):
                    pass
        else:
            # Fallback to legacy root hitbox keys
            if "edge_width" in raw:
                try:
                    hitbox["edge_width"] = max(0.01, min(0.45, float(raw["edge_width"])))
                except (ValueError, TypeError):
                    pass
            hitbox["left_edge_width"] = float(raw.get("left_edge_width", hitbox["edge_width"]))
            hitbox["right_edge_width"] = float(raw.get("right_edge_width", hitbox["edge_width"]))
            hitbox["top_edge_height"] = float(raw.get("top_edge_width", raw.get("top_edge_height", hitbox["edge_width"])))
            hitbox["bottom_edge_height"] = float(raw.get("bottom_edge_width", raw.get("bottom_edge_height", hitbox["edge_width"])))
            corner_val = float(raw.get("corner_hitbox", raw.get("corner_width", 0.15)))
            hitbox["corner_width"] = max(0.05, min(0.35, corner_val))
            hitbox["corner_height"] = max(0.05, min(0.35, float(raw.get("corner_height", corner_val))))

        config["hitbox"] = hitbox
        config["edge_width"] = hitbox["edge_width"]
        config["corner_hitbox"] = hitbox["corner_width"]

        # 2. Gesture Calibration
        gesture = copy.deepcopy(DEFAULT_GESTURE_CONFIG)
        if "gesture" in raw and isinstance(raw["gesture"], dict):
            g = raw["gesture"]
            if "swipe_min_distance" in g:
                try:
                    gesture["swipe_min_distance"] = max(0.01, min(0.50, float(g["swipe_min_distance"])))
                except (ValueError, TypeError):
                    pass
            if "swipe_max_drift" in g:
                try:
                    gesture["swipe_max_drift"] = max(0.005, min(0.50, float(g["swipe_max_drift"])))
                except (ValueError, TypeError):
                    pass
            if "tap_max_movement" in g:
                try:
                    gesture["tap_max_movement"] = max(0.005, min(0.30, float(g["tap_max_movement"])))
                except (ValueError, TypeError):
                    pass
            if "tap_min_duration_ms" in g:
                try:
                    gesture["tap_min_duration_ms"] = max(0, min(1000, int(g["tap_min_duration_ms"])))
                except (ValueError, TypeError):
                    pass
            if "tap_max_duration_ms" in g:
                try:
                    gesture["tap_max_duration_ms"] = max(10, min(2000, int(g["tap_max_duration_ms"])))
                except (ValueError, TypeError):
                    pass
            if "double_tap_timeout_ms" in g:
                try:
                    gesture["double_tap_timeout_ms"] = max(50, min(2000, int(g["double_tap_timeout_ms"])))
                except (ValueError, TypeError):
                    pass
            if "double_tap_max_distance" in g:
                try:
                    gesture["double_tap_max_distance"] = max(0.01, min(0.50, float(g["double_tap_max_distance"])))
                except (ValueError, TypeError):
                    pass
            if "cooldown_ms" in g:
                try:
                    gesture["cooldown_ms"] = max(0, min(2000, int(g["cooldown_ms"])))
                except (ValueError, TypeError):
                    pass
        else:
            # Fallback to root or [engine] keys
            if "swipe_min_distance" in raw:
                try:
                    gesture["swipe_min_distance"] = max(0.01, min(0.50, float(raw["swipe_min_distance"])))
                except (ValueError, TypeError):
                    pass
            elif "engine" in raw and isinstance(raw["engine"], dict) and "min_travel" in raw["engine"]:
                try:
                    mt = float(raw["engine"]["min_travel"])
                    gesture["swipe_min_distance"] = max(0.01, min(0.50, mt / 2905.0 if mt > 1.0 else mt))
                except (ValueError, TypeError):
                    pass

            if "swipe_max_drift" in raw:
                try:
                    gesture["swipe_max_drift"] = max(0.005, min(0.50, float(raw["swipe_max_drift"])))
                except (ValueError, TypeError):
                    pass
            elif "engine" in raw and isinstance(raw["engine"], dict) and "max_drift" in raw["engine"]:
                try:
                    md = float(raw["engine"]["max_drift"])
                    gesture["swipe_max_drift"] = max(0.005, min(0.50, md / 2905.0 if md > 1.0 else md))
                except (ValueError, TypeError):
                    pass

            if "tap_max_movement" in raw:
                try:
                    gesture["tap_max_movement"] = max(0.005, min(0.30, float(raw["tap_max_movement"])))
                except (ValueError, TypeError):
                    pass
            elif "engine" in raw and isinstance(raw["engine"], dict) and "tap_max_movement" in raw["engine"]:
                try:
                    tm = float(raw["engine"]["tap_max_movement"])
                    gesture["tap_max_movement"] = max(0.005, min(0.30, tm / 2905.0 if tm > 1.0 else tm))
                except (ValueError, TypeError):
                    pass

            if "tap_min_duration_ms" in raw:
                try:
                    gesture["tap_min_duration_ms"] = max(0, min(1000, int(raw["tap_min_duration_ms"])))
                except (ValueError, TypeError):
                    pass
            if "tap_max_duration_ms" in raw:
                try:
                    gesture["tap_max_duration_ms"] = max(10, min(2000, int(raw["tap_max_duration_ms"])))
                except (ValueError, TypeError):
                    pass
            elif "engine" in raw and isinstance(raw["engine"], dict) and "tap_max_duration_ms" in raw["engine"]:
                try:
                    gesture["tap_max_duration_ms"] = max(10, min(2000, int(raw["engine"]["tap_max_duration_ms"])))
                except (ValueError, TypeError):
                    pass

            if "double_tap_timeout_ms" in raw:
                try:
                    gesture["double_tap_timeout_ms"] = max(50, min(2000, int(raw["double_tap_timeout_ms"])))
                except (ValueError, TypeError):
                    pass
            if "double_tap_max_distance" in raw:
                try:
                    gesture["double_tap_max_distance"] = max(0.01, min(0.50, float(raw["double_tap_max_distance"])))
                except (ValueError, TypeError):
                    pass
            if "engine" in raw and isinstance(raw["engine"], dict) and "cooldown_ms" in raw["engine"]:
                try:
                    gesture["cooldown_ms"] = max(0, min(2000, int(raw["engine"]["cooldown_ms"])))
                except (ValueError, TypeError):
                    pass

        config["gesture"] = gesture
        config["swipe_min_distance"] = gesture["swipe_min_distance"]
        config["swipe_max_drift"] = gesture["swipe_max_drift"]
        config["tap_max_movement"] = gesture["tap_max_movement"]
        config["tap_min_duration_ms"] = gesture["tap_min_duration_ms"]
        config["tap_max_duration_ms"] = gesture["tap_max_duration_ms"]
        config["double_tap_timeout_ms"] = gesture["double_tap_timeout_ms"]
        config["double_tap_max_distance"] = gesture["double_tap_max_distance"]

        raw_engine = raw.get("engine", {}) if isinstance(raw.get("engine"), dict) else {}
        config["engine"]["min_travel"] = int(raw_engine.get("min_travel", gesture["swipe_min_distance"] * 2905.0))
        config["engine"]["max_drift"] = int(raw_engine.get("max_drift", gesture["swipe_max_drift"] * 2905.0))
        config["engine"]["cooldown_ms"] = int(raw_engine.get("cooldown_ms", gesture["cooldown_ms"]))
        config["engine"]["tap_max_duration_ms"] = int(raw_engine.get("tap_max_duration_ms", gesture["tap_max_duration_ms"]))
        config["engine"]["tap_max_movement"] = int(raw_engine.get("tap_max_movement", gesture["tap_max_movement"] * 2905.0))

        # Encoder options
        encoder = {
            "enabled": True,
            "step_size": 50.0,
            "dead_zone": 10.0,
            "repeat_interval_ms": 20,
        }
        if "encoder" in raw and isinstance(raw["encoder"], dict):
            raw_enc = raw["encoder"]
            if "enabled" in raw_enc:
                encoder["enabled"] = bool(raw_enc["enabled"])
            if "step_size" in raw_enc:
                try:
                    val = float(raw_enc["step_size"])
                    if 5.0 <= val <= 500.0:
                        encoder["step_size"] = val
                except (ValueError, TypeError):
                    pass
            if "dead_zone" in raw_enc:
                try:
                    val = float(raw_enc["dead_zone"])
                    if 0.0 <= val <= 100.0:
                        encoder["dead_zone"] = val
                except (ValueError, TypeError):
                    pass
            if "repeat_interval_ms" in raw_enc:
                try:
                    val = int(raw_enc["repeat_interval_ms"])
                    if 5 <= val <= 200:
                        encoder["repeat_interval_ms"] = val
                except (ValueError, TypeError):
                    pass
        config["encoder"] = encoder

        # Gestures
        gestures = []
        raw_gestures = raw.get("gestures", [])
        if isinstance(raw_gestures, list):
            for item in raw_gestures:
                if not isinstance(item, dict):
                    continue
                rule = self._normalize_gesture(item)
                if rule:
                    gestures.append(rule)
        config["gestures"] = gestures

        # Sliders
        sliders = []
        raw_sliders = raw.get("sliders", [])
        if isinstance(raw_sliders, list):
            for item in raw_sliders:
                if not isinstance(item, dict):
                    continue
                s = self._normalize_slider(item)
                if s:
                    sliders.append(s)
        config["sliders"] = sliders

        return config

    def _normalize_gesture(self, item: dict[str, Any]) -> dict[str, Any] | None:
        edge = str(item.get("zone") or item.get("edge") or "left").lower()
        direction = str(item.get("direction", "up")).lower()
        enabled = bool(item.get("enabled", True))
        fingers = int(item.get("fingers", 1))

        name = item.get("name")
        if not name:
            if direction == "tap":
                name = f"{edge.capitalize()} Single Tap"
            elif direction == "double-tap":
                name = f"{edge.capitalize()} Double Tap"
            else:
                name = f"{edge.capitalize()} swipe {direction}"

        # Action resolution
        action: dict[str, Any] = {"type": "log"}
        if "keys" in item and isinstance(item["keys"], list):
            keys = [str(k) for k in item["keys"]]
            action = {"type": "shortcut", "keys": keys}
        elif "key" in item:
            action = {"type": "key", "key": str(item["key"]), "repeat": 1}
        elif "command" in item:
            cmd = item["command"]
            argv = cmd if isinstance(cmd, list) else [str(cmd)]
            action = {"type": "command", "argv": argv}
        elif "action" in item:
            act = item["action"]
            if isinstance(act, dict):
                act_type = str(act.get("type", "")).lower()
                if "keys" in act or act_type == "shortcut":
                    keys = [str(k) for k in act.get("keys", [])]
                    action = {"type": "shortcut", "keys": keys}
                elif "media_action" in act or act_type == "media":
                    media_act = act.get("media_action", "play_pause")
                    key = act.get("key") or MEDIA_ACTION_KEYS.get(media_act, "KEY_PLAYPAUSE")
                    action = {
                        "type": "media",
                        "media_action": media_act,
                        "key": key,
                        "repeat": int(act.get("repeat", 1)),
                    }
                elif "workspace_action" in act or act_type == "workspace":
                    ws_act = act.get("workspace_action", "next")
                    action = {
                        "type": "workspace",
                        "workspace_action": ws_act,
                        "argv": act.get("argv", []),
                        "key": act.get("key"),
                    }
                elif act_type == "none" or act.get("none") is True:
                    action = {"type": "none"}
                    enabled = False
                elif "key" in act:
                    action = {
                        "type": "key",
                        "key": str(act["key"]),
                        "repeat": int(act.get("repeat", 1)),
                    }
                elif "command" in act:
                    argv = act["command"] if isinstance(act["command"], list) else [str(act["command"])]
                    action = {"type": "command", "argv": argv}
                elif act.get("log") is True or act_type == "log":
                    action = {"type": "log"}
            elif isinstance(act, list):
                action = {"type": "command", "argv": [str(x) for x in act]}
            elif str(act).lower() in ("none", "disabled"):
                action = {"type": "none"}
                enabled = False
            elif str(act).lower() == "log":
                action = {"type": "log"}

        if action.get("type") == "none":
            enabled = False

        res = {
            "name": name,
            "enabled": enabled,
            "edge": edge,
            "direction": direction,
            "fingers": fingers,
            "action": action,
        }
        if action.get("type") == "shortcut" or "keys" in action:
            res["keys"] = action.get("keys", [])
        return res

    def _normalize_slider(self, item: dict[str, Any]) -> dict[str, Any] | None:
        edge = str(item.get("zone") or item.get("edge") or "right").lower()
        direction = str(item.get("direction", "vertical")).lower()
        enabled = bool(item.get("enabled", True))
        step_distance = int(item.get("step_distance", 150))
        name = item.get("name") or f"{edge.capitalize()} {direction} slider"

        def parse_slot_action(key_prefix: str, sub_dict_name: str) -> dict[str, Any]:
            if f"{key_prefix}_key" in item:
                return {"type": "key", "key": str(item[f"{key_prefix}_key"]), "repeat": 1}
            if sub_dict_name in item and isinstance(item[sub_dict_name], dict):
                sub = item[sub_dict_name]
                if "key" in sub:
                    return {"type": "key", "key": str(sub["key"]), "repeat": int(sub.get("repeat", 1))}
                if "command" in sub:
                    argv = sub["command"] if isinstance(sub["command"], list) else [str(sub["command"])]
                    return {"type": "command", "argv": argv}
            return {"type": "log"}

        up_action = parse_slot_action("up", "up")
        down_action = parse_slot_action("down", "down")

        return {
            "name": name,
            "enabled": enabled,
            "edge": edge,
            "direction": direction,
            "step_distance": step_distance,
            "up": up_action,
            "down": down_action,
        }

    def validate_config(self, config: dict[str, Any]) -> tuple[bool, list[str]]:
        """Validates configuration for correctness and conflicts."""
        errors: list[str] = []

        if "hitbox" in config and isinstance(config["hitbox"], dict):
            _, hb_errors = validate_hitbox_config(config["hitbox"])
            errors.extend(hb_errors)
        if "edge_width" in config:
            edge_width = config["edge_width"]
            if not (0.01 <= edge_width <= 0.45):
                errors.append(f"Edge width must be between 0.01 and 0.45 (got {edge_width})")
        elif "hitbox" not in config:
            errors.append("Edge width must be between 0.01 and 0.45 (got None)")

        if "corner_hitbox" in config:
            corner_hitbox = config["corner_hitbox"]
            if not (0.05 <= corner_hitbox <= 0.35):
                errors.append(f"Corner hitbox must be between 0.05 and 0.35 (got {corner_hitbox})")

        if "gesture" in config and isinstance(config["gesture"], dict):
            _, g_errors = validate_gesture_config(config["gesture"])
            errors.extend(g_errors)
        if "engine" in config and isinstance(config["engine"], dict):
            engine = config["engine"]
            if "min_travel" in engine:
                min_travel = engine["min_travel"]
                if min_travel < 10:
                    errors.append(f"Minimum travel distance must be at least 10 units (got {min_travel})")
            if "max_drift" in engine:
                max_drift = engine["max_drift"]
                if not (10 <= max_drift <= 1000):
                    errors.append(f"Maximum horizontal drift must be between 10 and 1000 units (got {max_drift})")

        enabled_slider_zones = {
            str(s.get("zone") or s.get("edge") or "").lower()
            for s in config.get("sliders", [])
            if s.get("enabled", True)
        }

        # Conflict check: no duplicate enabled gestures on same (edge, direction)
        seen_gestures: set[tuple[str, str]] = set()
        for idx, g in enumerate(config.get("gestures", [])):
            if not g.get("enabled", True):
                continue
            edge = str(g.get("edge") or g.get("zone") or "").lower()
            direction = str(g.get("direction", "")).lower()
            if edge not in VALID_ZONES:
                errors.append(f"Gesture #{idx+1}: invalid edge '{edge}'")
            if direction not in VALID_DIRECTIONS:
                errors.append(f"Gesture #{idx+1}: invalid direction '{direction}'")

            key = (edge, direction)
            if key in seen_gestures:
                dir_label = "single tap" if direction == "tap" else ("double tap" if direction == "double-tap" else f"swipe {direction}")
                errors.append(f"Conflicting enabled gestures found on {edge} edge, {dir_label}")
            seen_gestures.add(key)

            # Sliders only conflict with directional swipe gestures; taps and double-taps are explicitly permitted
            if edge in enabled_slider_zones and direction in VALID_SWIPE_DIRECTIONS:
                errors.append(f"Gesture #{idx+1}: directional swipe on {edge} edge conflicts with active slider on {edge} edge (only taps are allowed on slider edges)")

            if edge in VALID_CORNER_ZONES and direction != "double-tap":
                errors.append(f"Gesture #{idx+1} '{g.get('name')}': Corner zones support double-tap only")

            action = g.get("action", {})
            act_type = action.get("type", "log")
            if act_type == "shortcut" or "keys" in g:
                keys_list = g.get("keys") or action.get("keys", [])
                if not keys_list:
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': keyboard shortcut combination cannot be empty")
                else:
                    for k in keys_list:
                        valid_code = get_key_code(k) is not None or (k.isdigit() and int(k) in _CODE_TO_NAME)
                        if not valid_code:
                            errors.append(f"Gesture #{idx+1} '{g.get('name')}': Unknown key '{k}' in shortcut combination")
            elif act_type == "key":
                k = str(action.get("key", "")).strip()
                if not k:
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': keyboard key cannot be empty")
                else:
                    valid_code = get_key_code(k) is not None or (k.isdigit() and int(k) in _CODE_TO_NAME)
                    if not valid_code:
                        errors.append(f"Gesture #{idx+1} '{g.get('name')}': Unknown key '{k}'")
            elif act_type == "command":
                argv = action.get("argv", [])
                if not argv or not argv[0].strip():
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': command cannot be empty")
                else:
                    prog = argv[0].strip()
                    if not shutil.which(prog) and not (os.path.isabs(prog) and os.path.exists(prog) and os.access(prog, os.X_OK)):
                        errors.append(f"Gesture #{idx+1} '{g.get('name')}': command executable '{prog}' not found in PATH or not executable")
            elif act_type == "media":
                media_act = action.get("media_action", "play_pause")
                if media_act not in MEDIA_ACTION_KEYS:
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': invalid media action '{media_act}'")
            elif act_type == "workspace":
                ws_act = action.get("workspace_action", "next")
                if ws_act not in ("next", "previous"):
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': invalid workspace action '{ws_act}'")

        return len(errors) == 0, errors

    def to_toml_string(self, config: dict[str, Any]) -> str:
        """Serializes normalized config to clean canonical Edgepad TOML with independent tables."""
        hitbox = copy.deepcopy(config.get("hitbox") or {})
        gesture = copy.deepcopy(config.get("gesture") or {})
        engine = copy.deepcopy(config.get("engine", {}))

        # Check if root legacy keys were explicitly set and differ from default
        if "edge_width" in config:
            ew_val = float(config["edge_width"])
            if ("edge_width" not in hitbox) or (hitbox.get("edge_width") == DEFAULT_HITBOX_CONFIG["edge_width"] and ew_val != DEFAULT_HITBOX_CONFIG["edge_width"]):
                hitbox["edge_width"] = ew_val
                if hitbox.get("left_edge_width") == DEFAULT_HITBOX_CONFIG["left_edge_width"]:
                    hitbox["left_edge_width"] = ew_val
                if hitbox.get("right_edge_width") == DEFAULT_HITBOX_CONFIG["right_edge_width"]:
                    hitbox["right_edge_width"] = ew_val
                if hitbox.get("top_edge_height") == DEFAULT_HITBOX_CONFIG["top_edge_height"]:
                    hitbox["top_edge_height"] = ew_val
                if hitbox.get("bottom_edge_height") == DEFAULT_HITBOX_CONFIG["bottom_edge_height"]:
                    hitbox["bottom_edge_height"] = ew_val

        if "corner_hitbox" in config:
            ch_val = float(config["corner_hitbox"])
            if ("corner_width" not in hitbox) or (hitbox.get("corner_width") == DEFAULT_HITBOX_CONFIG["corner_width"] and ch_val != DEFAULT_HITBOX_CONFIG["corner_width"]):
                hitbox["corner_width"] = ch_val
                hitbox["corner_height"] = ch_val

        edge_width = float(hitbox.get("edge_width", config.get("edge_width", 0.12)))
        left_edge_width = float(hitbox.get("left_edge_width", edge_width))
        right_edge_width = float(hitbox.get("right_edge_width", edge_width))
        top_edge_height = float(hitbox.get("top_edge_height", edge_width))
        bottom_edge_height = float(hitbox.get("bottom_edge_height", edge_width))
        corner_w = float(hitbox.get("corner_width", config.get("corner_hitbox", 0.15)))
        corner_h = float(hitbox.get("corner_height", config.get("corner_hitbox", 0.15)))

        swipe_min_distance = float(gesture.get("swipe_min_distance", config.get("swipe_min_distance", 0.08)))
        swipe_max_drift = float(gesture.get("swipe_max_drift", config.get("swipe_max_drift", 0.04)))
        tap_max_movement = float(gesture.get("tap_max_movement", config.get("tap_max_movement", 0.04)))
        tap_min_dur = int(gesture.get("tap_min_duration_ms", config.get("tap_min_duration_ms", 40)))
        tap_max_dur = int(gesture.get("tap_max_duration_ms", config.get("tap_max_duration_ms", engine.get("tap_max_duration_ms", 200))))
        double_tap_timeout = int(gesture.get("double_tap_timeout_ms", config.get("double_tap_timeout_ms", 300)))
        double_tap_max_dist = float(gesture.get("double_tap_max_distance", config.get("double_tap_max_distance", 0.08)))
        cooldown_ms = int(gesture.get("cooldown_ms", engine.get("cooldown_ms", 250)))

        min_travel = int(engine.get("min_travel", swipe_min_distance * 2905.0))
        max_drift = int(engine.get("max_drift", swipe_max_drift * 2905.0))
        tap_mov_raw = int(engine.get("tap_max_movement", tap_max_movement * 2905.0))

        lines = [
            "# Edgepad Configuration File",
            f"# Generated by Edgepad GUI at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f'device = "{config.get("device", "auto")}"',
            f'edge_width = {edge_width:.4f}',
            f'corner_hitbox = {corner_w:.2f}',
            f'tap_min_duration_ms = {tap_min_dur}',
            f'tap_max_duration_ms = {tap_max_dur}',
            f'double_tap_timeout_ms = {double_tap_timeout}',
            f'double_tap_max_distance = {double_tap_max_dist:.4f}',
            f'swipe_min_distance = {swipe_min_distance:.4f}',
            f'swipe_max_drift = {swipe_max_drift:.4f}',
            f'tap_max_movement = {tap_max_movement:.4f}',
            "",
            "[hitbox]",
            f'edge_width = {edge_width:.4f}',
            f'left_edge_width = {left_edge_width:.4f}',
            f'right_edge_width = {right_edge_width:.4f}',
            f'top_edge_height = {top_edge_height:.4f}',
            f'bottom_edge_height = {bottom_edge_height:.4f}',
            f'corner_width = {corner_w:.4f}',
            f'corner_height = {corner_h:.4f}',
            "",
            "[gesture]",
            f'swipe_min_distance = {swipe_min_distance:.4f}',
            f'swipe_max_drift = {swipe_max_drift:.4f}',
            f'tap_max_movement = {tap_max_movement:.4f}',
            f'tap_min_duration_ms = {tap_min_dur}',
            f'tap_max_duration_ms = {tap_max_dur}',
            f'double_tap_timeout_ms = {double_tap_timeout}',
            f'double_tap_max_distance = {double_tap_max_dist:.4f}',
            f'cooldown_ms = {cooldown_ms}',
            "",
            "[engine]",
            f"min_travel = {min_travel}",
            f"max_drift = {max_drift}",
            f'cooldown_ms = {cooldown_ms}',
            f'tap_max_duration_ms = {tap_max_dur}',
            f'tap_max_movement = {tap_mov_raw}',
            "",
            "[encoder]",
            f'enabled = {str(config.get("encoder", {}).get("enabled", True)).lower()}',
            f'step_size = {float(config.get("encoder", {}).get("step_size", 50.0)):.1f}',
            f'dead_zone = {float(config.get("encoder", {}).get("dead_zone", 10.0)):.1f}',
            f'repeat_interval_ms = {int(config.get("encoder", {}).get("repeat_interval_ms", 20))}',
            "",
        ]

        for g in config.get("gestures", []):
            lines.append("[[gestures]]")
            if g.get("name"):
                lines.append(f'name = "{g["name"]}"')
            lines.append(f'enabled = {str(g.get("enabled", True)).lower()}')
            zone = str(g.get("zone") or g.get("edge") or "left").lower()
            lines.append(f'zone = "{zone}"')
            lines.append(f'direction = "{g.get("direction", "up")}"')

            action = g.get("action", {"type": "log"})
            act_type = action.get("type", "log")
            if g.get("keys") or act_type == "shortcut":
                keys_list = g.get("keys") or action.get("keys", [])
                keys_str = ", ".join(f'"{k}"' for k in keys_list)
                lines.append(f"keys = [{keys_str}]")
            elif act_type == "key":
                key_name = action.get("key", "KEY_RESERVED")
                repeat = int(action.get("repeat", 1))
                if repeat > 1:
                    lines.append(f'action = {{ key = "{key_name}", repeat = {repeat} }}')
                else:
                    lines.append(f'key = "{key_name}"')
            elif act_type == "command":
                argv = action.get("argv", [])
                argv_str = ", ".join(f'"{arg}"' for arg in argv)
                lines.append(f"action = [{argv_str}]")
            elif act_type == "media":
                media_act = action.get("media_action", "play_pause")
                key_name = action.get("key") or MEDIA_ACTION_KEYS.get(media_act, "KEY_PLAYPAUSE")
                repeat = int(action.get("repeat", 1))
                if repeat > 1:
                    lines.append(f'action = {{ type = "media", media_action = "{media_act}", key = "{key_name}", repeat = {repeat} }}')
                else:
                    lines.append(f'action = {{ type = "media", media_action = "{media_act}", key = "{key_name}" }}')
            elif act_type == "workspace":
                argv = action.get("argv")
                if not argv:
                    ws_act = action.get("workspace_action", "next")
                    argv = get_default_workspace_command(ws_act)
                argv_str = ", ".join(f'"{arg}"' for arg in argv)
                lines.append(f"action = [{argv_str}]")
            elif act_type == "none":
                lines.append('action = "log"')
            else:
                lines.append('action = "log"')
            lines.append("")

        for s in config.get("sliders", []):
            lines.append("[[sliders]]")
            if s.get("name"):
                lines.append(f'name = "{s["name"]}"')
            lines.append(f'enabled = {str(s.get("enabled", True)).lower()}')
            zone = str(s.get("zone") or s.get("edge") or "right").lower()
            lines.append(f'zone = "{zone}"')
            lines.append("step = 0.04")

            up = s.get("up", {})
            if up.get("type") == "key":
                lines.append(f'up_key = "{up.get("key", "KEY_VOLUMEUP")}"')
            elif up.get("type") == "command":
                argv_str = ", ".join(f'"{arg}"' for arg in up.get("argv", []))
                lines.append(f"up = [{argv_str}]")

            down = s.get("down", {})
            if down.get("type") == "key":
                lines.append(f'down_key = "{down.get("key", "KEY_VOLUMEDOWN")}"')
            elif down.get("type") == "command":
                argv_str = ", ".join(f'"{arg}"' for arg in down.get("argv", []))
                lines.append(f"down = [{argv_str}]")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def create_backup(self) -> str | None:
        """Creates a timestamped backup of current config file."""
        if not self.config_exists():
            return None
        try:
            self.backups_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = self.backups_dir / f"edgepad_{timestamp}.toml"
            shutil.copy2(self.config_path, backup_path)
            return str(backup_path)
        except Exception:
            return None

    def save_config(self, config: dict[str, Any]) -> tuple[bool, str]:
        """Validates and atomically saves configuration to disk."""
        valid, errors = self.validate_config(config)
        if not valid:
            return False, "; ".join(errors)

        try:
            # Backup existing
            self.create_backup()

            # Prepare target dir
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            toml_content = self.to_toml_string(config)

            # Atomic write via temp file in same directory
            with tempfile.NamedTemporaryFile(
                "w",
                dir=self.config_path.parent,
                prefix="edgepad_cfg_",
                suffix=".tmp",
                delete=False,
                encoding="utf-8",
            ) as tmp_file:
                tmp_path = Path(tmp_file.name)
                tmp_file.write(toml_content)
                tmp_file.flush()
                os.fsync(tmp_file.fileno())

            # Atomic replace
            os.replace(tmp_path, self.config_path)

            self._current_config = copy.deepcopy(config)
            return True, "Configuration saved successfully"
        except Exception as e:
            return False, f"Failed to save configuration: {e}"

    def reset_to_defaults(self) -> tuple[bool, str]:
        """Resets configuration to the default 4-key preset."""
        preset = default_preset_config()
        return self.save_config(preset)

    def export_config(self, dest_path: str) -> tuple[bool, str]:
        """Exports current configuration to specified path."""
        try:
            dest = Path(dest_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            content = self.to_toml_string(self._current_config)
            dest.write_text(content, encoding="utf-8")
            return True, f"Exported successfully to {dest_path}"
        except Exception as e:
            return False, f"Failed to export configuration: {e}"

    def import_config(self, src_path: str) -> tuple[bool, str]:
        """Imports configuration from specified path and applies it."""
        try:
            src = Path(src_path)
            if not src.exists():
                return False, f"File not found: {src_path}"
            with open(src, "rb") as f:
                raw = tomllib.load(f)
            normalized = self._normalize_config(raw)
            return self.save_config(normalized)
        except Exception as e:
            return False, f"Failed to import configuration: {e}"

    def update_hitbox(self, hitbox_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Updates only physical hitbox calibration dimensions without altering gesture thresholds."""
        valid, errors = validate_hitbox_config(hitbox_data)
        if not valid:
            return False, "; ".join(errors)

        current = copy.deepcopy(self._current_config)
        if "hitbox" not in current or not isinstance(current["hitbox"], dict):
            current["hitbox"] = copy.deepcopy(DEFAULT_HITBOX_CONFIG)
        current["hitbox"].update(hitbox_data)
        current["edge_width"] = current["hitbox"].get("edge_width", 0.12)
        current["corner_hitbox"] = current["hitbox"].get("corner_width", 0.15)
        self._current_config = current
        return True, None

    def update_gesture(self, gesture_data: dict[str, Any]) -> tuple[bool, str | None]:
        """Updates only gesture recognition thresholds without altering physical hitbox dimensions."""
        valid, errors = validate_gesture_config(gesture_data)
        if not valid:
            return False, "; ".join(errors)

        current = copy.deepcopy(self._current_config)
        if "gesture" not in current or not isinstance(current["gesture"], dict):
            current["gesture"] = copy.deepcopy(DEFAULT_GESTURE_CONFIG)
        current["gesture"].update(gesture_data)
        g = current["gesture"]
        current["swipe_min_distance"] = g.get("swipe_min_distance", 0.08)
        current["swipe_max_drift"] = g.get("swipe_max_drift", 0.04)
        current["tap_max_movement"] = g.get("tap_max_movement", 0.04)
        current["tap_min_duration_ms"] = g.get("tap_min_duration_ms", 40)
        current["tap_max_duration_ms"] = g.get("tap_max_duration_ms", 200)
        current["double_tap_timeout_ms"] = g.get("double_tap_timeout_ms", 300)
        current["double_tap_max_distance"] = g.get("double_tap_max_distance", 0.08)
        if "engine" in current and isinstance(current["engine"], dict):
            current["engine"]["min_travel"] = int(current["swipe_min_distance"] * 2905.0)
            current["engine"]["max_drift"] = int(current["swipe_max_drift"] * 2905.0)
            current["engine"]["cooldown_ms"] = g.get("cooldown_ms", 250)
            current["engine"]["tap_max_duration_ms"] = current["tap_max_duration_ms"]
            current["engine"]["tap_max_movement"] = int(current["tap_max_movement"] * 2905.0)
        self._current_config = current
        return True, None

    def restore_hitbox_defaults(self) -> dict[str, Any]:
        """Restores hitbox calibration to factory defaults without affecting gestures."""
        self._current_config["hitbox"] = copy.deepcopy(DEFAULT_HITBOX_CONFIG)
        self._current_config["edge_width"] = DEFAULT_HITBOX_CONFIG["edge_width"]
        self._current_config["corner_hitbox"] = DEFAULT_HITBOX_CONFIG["corner_width"]
        return copy.deepcopy(self._current_config["hitbox"])

    def restore_gesture_defaults(self) -> dict[str, Any]:
        """Restores gesture calibration to factory defaults without affecting hitboxes."""
        self._current_config["gesture"] = copy.deepcopy(DEFAULT_GESTURE_CONFIG)
        g = self._current_config["gesture"]
        self._current_config["swipe_min_distance"] = g["swipe_min_distance"]
        self._current_config["swipe_max_drift"] = g["swipe_max_drift"]
        self._current_config["tap_max_movement"] = g["tap_max_movement"]
        self._current_config["tap_min_duration_ms"] = g["tap_min_duration_ms"]
        self._current_config["tap_max_duration_ms"] = g["tap_max_duration_ms"]
        self._current_config["double_tap_timeout_ms"] = g["double_tap_timeout_ms"]
        self._current_config["double_tap_max_distance"] = g["double_tap_max_distance"]
        if "engine" in self._current_config and isinstance(self._current_config["engine"], dict):
            self._current_config["engine"]["min_travel"] = int(g["swipe_min_distance"] * 2905.0)
            self._current_config["engine"]["max_drift"] = int(g["swipe_max_drift"] * 2905.0)
            self._current_config["engine"]["cooldown_ms"] = g.get("cooldown_ms", 250)
            self._current_config["engine"]["tap_max_duration_ms"] = g["tap_max_duration_ms"]
            self._current_config["engine"]["tap_max_movement"] = int(g["tap_max_movement"] * 2905.0)
        return copy.deepcopy(self._current_config["gesture"])

