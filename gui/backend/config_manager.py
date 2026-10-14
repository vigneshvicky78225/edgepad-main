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


def get_default_config_path() -> Path:
    xdg_config_home = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config_home and xdg_config_home.strip():
        base = Path(xdg_config_home.strip())
    else:
        base = Path.home() / ".config"
    return base / "edgepad" / "edgepad.toml"


def get_backups_dir() -> Path:
    return get_default_config_path().parent / "backups"


def default_preset_config() -> dict[str, Any]:
    """Returns the default configuration preset with the requested 4 key mappings."""
    return {
        "device": "auto",
        "edge_width": 0.12,
        "engine": {
            "min_travel": 250,
            "max_drift": 120,
            "cooldown_ms": 250,
            "tap_max_duration_ms": 200,
            "tap_max_movement": 50,
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
    }


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
            self._current_config = default_preset_config()
            return copy.deepcopy(self._current_config), None

        try:
            with open(self.config_path, "rb") as f:
                data = tomllib.load(f)

            parsed = self._normalize_config(data)
            self._current_config = parsed
            return copy.deepcopy(parsed), None
        except Exception as e:
            return copy.deepcopy(self._current_config), f"Failed to load config: {e}"

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

        # Edge width
        if "edge_width" in raw:
            try:
                config["edge_width"] = float(raw["edge_width"])
            except (ValueError, TypeError):
                config["edge_width"] = 0.12

        # Engine options
        if "engine" in raw and isinstance(raw["engine"], dict):
            eng = raw["engine"]
            for k in ["min_travel", "max_drift", "cooldown_ms", "tap_max_duration_ms", "tap_max_movement"]:
                if k in eng:
                    try:
                        config["engine"][k] = int(eng[k])
                    except (ValueError, TypeError):
                        pass

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
        edge = str(item.get("edge", "left")).lower()
        direction = str(item.get("direction", "up")).lower()
        enabled = bool(item.get("enabled", True))
        name = item.get("name") or f"{edge.capitalize()} swipe {direction}"
        fingers = int(item.get("fingers", 1))

        # Action resolution
        action: dict[str, Any] = {"type": "log"}
        if "key" in item:
            action = {"type": "key", "key": str(item["key"]), "repeat": 1}
        elif "command" in item:
            cmd = item["command"]
            argv = cmd if isinstance(cmd, list) else [str(cmd)]
            action = {"type": "command", "argv": argv}
        elif "action" in item:
            act = item["action"]
            if isinstance(act, dict):
                if "key" in act:
                    action = {
                        "type": "key",
                        "key": str(act["key"]),
                        "repeat": int(act.get("repeat", 1)),
                    }
                elif "command" in act:
                    argv = act["command"] if isinstance(act["command"], list) else [str(act["command"])]
                    action = {"type": "command", "argv": argv}
                elif act.get("log") is True:
                    action = {"type": "log"}
            elif str(act).lower() == "log":
                action = {"type": "log"}

        return {
            "name": name,
            "enabled": enabled,
            "edge": edge,
            "direction": direction,
            "fingers": fingers,
            "action": action,
        }

    def _normalize_slider(self, item: dict[str, Any]) -> dict[str, Any] | None:
        edge = str(item.get("edge", "right")).lower()
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

        edge_width = config.get("edge_width", 0.12)
        if not (0.01 <= edge_width <= 0.45):
            errors.append(f"Edge width must be between 0.01 and 0.45 (got {edge_width})")

        engine = config.get("engine", {})
        min_travel = engine.get("min_travel", 250)
        if min_travel < 10:
            errors.append(f"Minimum travel distance must be at least 10 units (got {min_travel})")

        # Conflict check: no duplicate enabled gestures on same (edge, direction)
        seen_gestures: set[tuple[str, str]] = set()
        for idx, g in enumerate(config.get("gestures", [])):
            if not g.get("enabled", True):
                continue
            edge = str(g.get("edge", "")).lower()
            direction = str(g.get("direction", "")).lower()
            if edge not in ["left", "right", "top", "bottom"]:
                errors.append(f"Gesture #{idx+1}: invalid edge '{edge}'")
            if direction not in ["up", "down", "left", "right"]:
                errors.append(f"Gesture #{idx+1}: invalid direction '{direction}'")

            key = (edge, direction)
            if key in seen_gestures:
                errors.append(f"Conflicting enabled gestures found on {edge} edge, swipe {direction}")
            seen_gestures.add(key)

            action = g.get("action", {})
            act_type = action.get("type", "log")
            if act_type == "key":
                if not action.get("key"):
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': keyboard key cannot be empty")
            elif act_type == "command":
                argv = action.get("argv", [])
                if not argv or not argv[0].strip():
                    errors.append(f"Gesture #{idx+1} '{g.get('name')}': command cannot be empty")

        return len(errors) == 0, errors

    def to_toml_string(self, config: dict[str, Any]) -> str:
        """Serializes normalized config to clean TOML."""
        lines = [
            "# Edgepad Configuration File",
            f"# Generated by Edgepad GUI at {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f'device = "{config.get("device", "auto")}"',
            f'edge_width = {config.get("edge_width", 0.12):.4f}',
            "",
            "[engine]",
        ]

        engine = config.get("engine", {})
        for k in ["min_travel", "max_drift", "cooldown_ms", "tap_max_duration_ms", "tap_max_movement"]:
            if k in engine:
                lines.append(f"{k} = {engine[k]}")

        lines.append("")

        for g in config.get("gestures", []):
            lines.append("[[gestures]]")
            if g.get("name"):
                lines.append(f'name = "{g["name"]}"')
            lines.append(f'enabled = {str(g.get("enabled", True)).lower()}')
            lines.append(f'edge = "{g.get("edge", "left")}"')
            lines.append(f'direction = "{g.get("direction", "up")}"')
            if g.get("fingers", 1) != 1:
                lines.append(f'fingers = {g["fingers"]}')

            action = g.get("action", {"type": "log"})
            act_type = action.get("type", "log")
            if act_type == "key":
                key_name = action.get("key", "KEY_RESERVED")
                repeat = action.get("repeat", 1)
                if repeat > 1:
                    lines.append(f'action = {{ key = "{key_name}", repeat = {repeat} }}')
                else:
                    lines.append(f'key = "{key_name}"')
            elif act_type == "command":
                argv = action.get("argv", [])
                argv_str = ", ".join(f'"{arg}"' for arg in argv)
                lines.append(f"command = [{argv_str}]")
            else:
                lines.append('action = "log"')
            lines.append("")

        for s in config.get("sliders", []):
            lines.append("[[sliders]]")
            if s.get("name"):
                lines.append(f'name = "{s["name"]}"')
            lines.append(f'enabled = {str(s.get("enabled", True)).lower()}')
            lines.append(f'edge = "{s.get("edge", "right")}"')
            lines.append(f'direction = "{s.get("direction", "vertical")}"')
            lines.append(f'step_distance = {s.get("step_distance", 150)}')

            up = s.get("up", {})
            if up.get("type") == "key":
                lines.append(f'up_key = "{up.get("key", "KEY_VOLUMEUP")}"')
            elif up.get("type") == "command":
                argv_str = ", ".join(f'"{arg}"' for arg in up.get("argv", []))
                lines.append(f"up = {{ command = [{argv_str}] }}")

            down = s.get("down", {})
            if down.get("type") == "key":
                lines.append(f'down_key = "{down.get("key", "KEY_VOLUMEDOWN")}"')
            elif down.get("type") == "command":
                argv_str = ", ".join(f'"{arg}"' for arg in down.get("argv", []))
                lines.append(f"down = {{ command = [{argv_str}] }}")
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
