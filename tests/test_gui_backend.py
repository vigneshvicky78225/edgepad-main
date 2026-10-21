"""Automated unit and integration tests for Edgepad GUI backend and Qt integration.

Verifies:
- Configuration parsing, validation, atomic saving, and backup
- Gesture-rule creation, editing, duplication, and deletion
- 4 default brightness and volume key mappings
- Service state reporting and error handling
- Device discovery and coordinate translation
- Diagnostics doctor report parsing
- IPC event streaming and test mode simulation
"""

import copy
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication

from gui.backend.config_manager import ConfigManager, default_preset_config
from gui.backend.controller import EdgepadController
from gui.backend.device_manager import DeviceManager
from gui.backend.diagnostics_manager import DiagnosticsManager
from gui.backend.ipc_client import IpcClient
from gui.backend.key_definitions import KNOWN_KEYS, get_key_code, get_key_name, search_keys
from gui.backend.service_manager import ServiceManager


class TestEdgepadGuiBackend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app = QCoreApplication.instance()
        if app is None:
            cls.app = QApplication(["edgepad-test", "-platform", "offscreen"])
        else:
            cls.app = app

    def test_default_preset_mappings(self):
        """Verify the four mandatory preset mappings exist with exact keys and directions."""
        preset = default_preset_config()
        gestures = preset["gestures"]

        self.assertEqual(len(gestures), 4, "Expected exactly 4 default preset mappings")

        mappings = {(g["edge"], g["direction"]): g["action"]["key"] for g in gestures}

        self.assertEqual(mappings[("left", "up")], "KEY_BRIGHTNESSUP")
        self.assertEqual(mappings[("left", "down")], "KEY_BRIGHTNESSDOWN")
        self.assertEqual(mappings[("right", "up")], "KEY_VOLUMEUP")
        self.assertEqual(mappings[("right", "down")], "KEY_VOLUMEDOWN")

        for g in gestures:
            self.assertTrue(g["enabled"])
            self.assertEqual(g["action"]["type"], "key")
            self.assertEqual(g["action"]["repeat"], 1)

    def test_config_validation_and_conflicts(self):
        """Verify validation detects invalid widths, travel distance, and duplicate gestures."""
        cm = ConfigManager()

        # Valid config
        valid, errors = cm.validate_config(default_preset_config())
        self.assertTrue(valid, f"Default preset should be valid: {errors}")

        # Invalid edge width (< 0.01 or > 0.45)
        bad_cfg = copy.deepcopy(default_preset_config())
        bad_cfg["edge_width"] = 0.60
        valid, errors = cm.validate_config(bad_cfg)
        self.assertFalse(valid)
        self.assertTrue(any("Edge width" in e for e in errors))

        # Invalid minimum travel
        bad_cfg2 = copy.deepcopy(default_preset_config())
        bad_cfg2["engine"]["min_travel"] = 5
        valid, errors = cm.validate_config(bad_cfg2)
        self.assertFalse(valid)
        self.assertTrue(any("Minimum travel" in e for e in errors))

        # Invalid maximum drift (< 10 or > 1000)
        bad_cfg_drift = copy.deepcopy(default_preset_config())
        bad_cfg_drift["engine"]["max_drift"] = 5
        valid, errors = cm.validate_config(bad_cfg_drift)
        self.assertFalse(valid)
        self.assertTrue(any("Maximum horizontal drift" in e for e in errors))

        # Duplicate conflict: two enabled gestures on left edge swipe up
        bad_cfg3 = copy.deepcopy(default_preset_config())
        bad_cfg3["gestures"].append({
            "name": "Conflicting Brightness",
            "enabled": True,
            "edge": "left",
            "direction": "up",
            "fingers": 1,
            "action": {"type": "key", "key": "KEY_BRIGHTNESSUP", "repeat": 1},
        })
        valid, errors = cm.validate_config(bad_cfg3)
        self.assertFalse(valid)
        self.assertTrue(any("Conflicting enabled gestures" in e for e in errors))

    def test_config_atomic_save_and_backup(self):
        """Verify configuration is atomically saved, backed up, and round-tripped."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            cm = ConfigManager(config_path=cfg_path)

            preset = default_preset_config()
            ok, msg = cm.save_config(preset)
            self.assertTrue(ok, f"Save failed: {msg}")
            self.assertTrue(cfg_path.exists())

            # Modify and save again to verify backup creation
            preset["edge_width"] = 0.15
            preset["engine"]["max_drift"] = 180
            preset["gestures"][0]["name"] = "Modified Brightness Up"
            ok, msg = cm.save_config(preset)
            self.assertTrue(ok)

            # Check backup was created
            backups = list(cm.backups_dir.glob("edgepad_*.toml"))
            self.assertGreaterEqual(len(backups), 1, "Expected at least one backup file")

            # Load back
            loaded, err = cm.load_config()
            self.assertIsNone(err)
            self.assertEqual(loaded["edge_width"], 0.15)
            self.assertEqual(loaded["engine"]["max_drift"], 180)
            self.assertEqual(loaded["gestures"][0]["name"], "Modified Brightness Up")

    def test_controller_rule_lifecycle(self):
        """Verify adding, updating, duplicating, toggling, and removing gesture rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path
            ctrl.resetToDefaults()

            initial_count = len(ctrl.gestureRules)
            self.assertEqual(initial_count, 4)

            # Add rule
            new_rule = {
                "name": "Play / Pause",
                "enabled": True,
                "edge": "top",
                "direction": "down",
                "fingers": 1,
                "action": {"type": "key", "key": "KEY_PLAYPAUSE", "repeat": 1},
            }
            ctrl.addGestureRule(new_rule)
            self.assertEqual(len(ctrl.gestureRules), initial_count + 1)
            self.assertTrue(ctrl.hasUnsavedChanges)

            # Toggle rule
            ctrl.toggleGestureRule(0, False)
            self.assertFalse(ctrl.gestureRules[0]["enabled"])

            # Duplicate rule
            ctrl.duplicateGestureRule(0)
            self.assertEqual(len(ctrl.gestureRules), initial_count + 2)
            self.assertIn("Copy", ctrl.gestureRules[1]["name"])

            # Remove rule
            ctrl.removeGestureRule(1)
            self.assertEqual(len(ctrl.gestureRules), initial_count + 1)

            # Save and verify
            ctrl.saveConfiguration()
            self.assertFalse(ctrl.hasUnsavedChanges)

    def test_key_definitions_search(self):
        """Verify Linux key definition lookups and search."""
        self.assertEqual(get_key_code("KEY_BRIGHTNESSUP"), 225)
        self.assertEqual(get_key_code("KEY_BRIGHTNESSDOWN"), 224)
        self.assertEqual(get_key_code("KEY_VOLUMEUP"), 115)
        self.assertEqual(get_key_code("KEY_VOLUMEDOWN"), 114)

        self.assertEqual(get_key_name(225), "KEY_BRIGHTNESSUP")
        self.assertEqual(get_key_name(115), "KEY_VOLUMEUP")

        # Search
        results = search_keys("volume")
        self.assertGreaterEqual(len(results), 2)
        names = [r["name"] for r in results]
        self.assertIn("KEY_VOLUMEUP", names)
        self.assertIn("KEY_VOLUMEDOWN", names)

    def test_device_discovery_parsing(self):
        """Verify device manager correctly parses device attributes."""
        dm = DeviceManager()
        touchpads = dm.get_touchpads()

        if touchpads:
            pad = touchpads[0]
            self.assertTrue(pad["is_touchpad"])
            self.assertIn("Touchpad", pad["name"])
            self.assertTrue(pad["readable"])
            self.assertTrue(pad["writable"])
            self.assertGreater(pad["x_max"], 0)
            self.assertGreater(pad["y_max"], 0)

    def test_diagnostics_doctor_parsing(self):
        """Verify diagnostics manager parses edgepad doctor output into structured items."""
        diag = DiagnosticsManager()
        report = diag.run_doctor()

        self.assertIn("items", report)
        self.assertIn("summary", report)
        self.assertIsInstance(report["items"], list)
        self.assertGreaterEqual(report["summary"]["ok"], 1)


    def test_encoder_configuration_loading_and_saving(self):
        """Verify encoder settings persist correctly through TOML serialization."""
        preset = default_preset_config()
        self.assertIn("encoder", preset)
        self.assertTrue(preset["encoder"]["enabled"])
        self.assertEqual(preset["encoder"]["step_size"], 50.0)
        self.assertEqual(preset["encoder"]["dead_zone"], 10.0)
        self.assertEqual(preset["encoder"]["repeat_interval_ms"], 20)

        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "edgepad.toml"
            cm = ConfigManager(cfg_path)

            custom_cfg = copy.deepcopy(preset)
            custom_cfg["encoder"]["step_size"] = 75.0
            custom_cfg["encoder"]["dead_zone"] = 15.0
            custom_cfg["encoder"]["repeat_interval_ms"] = 35

            ok, err = cm.save_config(custom_cfg)
            self.assertTrue(ok, f"Save failed: {err}")

            with open(cfg_path, "r") as f:
                toml_text = f.read()
            self.assertIn("[encoder]", toml_text)
            self.assertIn("step_size = 75.0", toml_text)
            self.assertIn("dead_zone = 15.0", toml_text)
            self.assertIn("repeat_interval_ms = 35", toml_text)

            loaded, err = cm.load_config()
            self.assertIsNone(err)
            self.assertEqual(loaded["encoder"]["step_size"], 75.0)
            self.assertEqual(loaded["encoder"]["dead_zone"], 15.0)
            self.assertEqual(loaded["encoder"]["repeat_interval_ms"], 35)

    def test_encoder_controller_properties_and_diagnostics(self):
        """Verify EdgepadController exposes encoder properties, slots, and live diagnostics."""
        with tempfile.TemporaryDirectory() as tmp_dir:
            cfg_path = Path(tmp_dir) / "edgepad.toml"
            cm = ConfigManager(cfg_path)
            cm.save_config(default_preset_config())

            ctrl = EdgepadController()
            ctrl.config_manager = cm
            ctrl._load_initial_state()

            self.assertTrue(ctrl.encoderEnabled)
            self.assertEqual(ctrl.encoderStepSize, 50.0)
            self.assertEqual(ctrl.encoderDeadZone, 10.0)
            self.assertEqual(ctrl.encoderRepeatIntervalMs, 20)

            ctrl.setEncoderStepSize(60.0)
            ctrl.setEncoderDeadZone(12.0)
            ctrl.setEncoderRepeatIntervalMs(25)
            self.assertEqual(ctrl.encoderStepSize, 60.0)
            self.assertEqual(ctrl.encoderDeadZone, 12.0)
            self.assertEqual(ctrl.encoderRepeatIntervalMs, 25)

            # Test live event simulation
            ctrl._on_ipc_event({
                "event": "slider_step",
                "zone": "right",
                "direction": "up",
                "key": "KEY_VOLUMEUP",
                "key_code": 115,
            })
            self.assertEqual(ctrl.encoderLiveEdge, "Right")
            self.assertEqual(ctrl.encoderLiveDirection, "Up")
            self.assertEqual(ctrl.encoderLiveIncremental, 60.0)
            self.assertGreaterEqual(ctrl.encoderLiveTicks, 1)
            self.assertEqual(ctrl.encoderLiveKey, "KEY_VOLUMEUP")

            # Restore defaults
            ctrl.restoreEncoderDefaults()
            self.assertTrue(ctrl.encoderEnabled)
            self.assertEqual(ctrl.encoderStepSize, 50.0)
            self.assertEqual(ctrl.encoderDeadZone, 10.0)
            self.assertEqual(ctrl.encoderRepeatIntervalMs, 20)


    def test_default_tap_actions(self):
        """Verify default tap actions return recommended mappings with valid zones and gestures."""
        from gui.backend.config_manager import default_tap_actions, VALID_ZONES, VALID_TAP_DIRECTIONS

        taps = default_tap_actions()
        self.assertGreaterEqual(len(taps), 3)

        for rule in taps:
            self.assertIn(rule["edge"], VALID_ZONES)
            self.assertIn(rule["direction"], VALID_TAP_DIRECTIONS)
            self.assertTrue(rule["enabled"])
            self.assertIn(rule["action"]["type"], ["media", "command", "key"])

    def test_tap_and_swipe_rules_partitioning(self):
        """Verify tapRules and swipeRules correctly filter and maintain originalIndex."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path
            ctrl.resetToDefaults()

            # Initially, default preset has 4 swipe rules and 0 tap rules
            self.assertEqual(len(ctrl.swipeRules), 4)
            self.assertEqual(len(ctrl.tapRules), 0)

            # Add a tap rule
            ctrl.addTapRule({
                "name": "Left Tap Mute",
                "enabled": True,
                "edge": "left",
                "direction": "tap",
                "action": {"type": "media", "media_action": "mute", "key": "KEY_MUTE"},
            })

            self.assertEqual(len(ctrl.swipeRules), 4)
            self.assertEqual(len(ctrl.tapRules), 1)
            self.assertEqual(ctrl.tapRules[0]["originalIndex"], 4)
            self.assertEqual(ctrl.tapRules[0]["direction"], "tap")

    def test_tap_rule_controller_crud(self):
        """Verify adding, updating, toggling, duplicating, and removing tap rules."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path
            ctrl.resetToDefaults()

            # 1. Add Tap Rule
            ctrl.addTapRule({
                "name": "Top Play/Pause",
                "enabled": True,
                "edge": "top",
                "direction": "tap",
                "action": {"type": "media", "media_action": "play_pause", "key": "KEY_PLAYPAUSE"},
            })
            self.assertEqual(len(ctrl.tapRules), 1)
            self.assertTrue(ctrl.hasUnsavedChanges)

            # 2. Update Tap Rule
            ctrl.updateTapRule(0, {
                "name": "Top Stop",
                "enabled": True,
                "edge": "top",
                "direction": "double-tap",
                "action": {"type": "media", "media_action": "stop", "key": "KEY_STOPCD"},
            })
            self.assertEqual(len(ctrl.tapRules), 1)
            self.assertEqual(ctrl.tapRules[0]["name"], "Top Stop")
            self.assertEqual(ctrl.tapRules[0]["direction"], "double-tap")

            # 3. Toggle Tap Rule
            ctrl.toggleTapRule(0, False)
            self.assertFalse(ctrl.tapRules[0]["enabled"])

            # 4. Duplicate Tap Rule
            ctrl.duplicateTapRule(0)
            self.assertEqual(len(ctrl.tapRules), 2)
            self.assertIn("Copy", ctrl.tapRules[1]["name"])

            # 5. Remove Tap Rule
            ctrl.removeTapRule(1)
            self.assertEqual(len(ctrl.tapRules), 1)

            # 6. Save Configuration
            ctrl.saveConfiguration()
            self.assertFalse(ctrl.hasUnsavedChanges)

    def test_tap_action_types_normalization_and_serialization(self):
        """Verify round-trip TOML serialization for key, media, command, workspace, and none."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            cm = ConfigManager(cfg_path)

            cfg = {
                "edge_width": 0.12,
                "encoder": {"enabled": True, "step_size": 50.0, "dead_zone": 10.0, "repeat_interval_ms": 20},
                "gestures": [
                    {
                        "name": "Key Tap",
                        "enabled": True,
                        "edge": "left",
                        "direction": "tap",
                        "action": {"type": "key", "key": "KEY_MUTE", "repeat": 1},
                    },
                    {
                        "name": "Media Tap",
                        "enabled": True,
                        "edge": "top",
                        "direction": "tap",
                        "action": {"type": "media", "media_action": "play_pause", "key": "KEY_PLAYPAUSE"},
                    },
                    {
                        "name": "Command Tap",
                        "enabled": True,
                        "edge": "bottom",
                        "direction": "double-tap",
                        "action": {"type": "command", "argv": ["notify-send", "Edgepad", "Double tap"]},
                    },
                    {
                        "name": "Workspace Tap",
                        "enabled": True,
                        "edge": "right",
                        "direction": "tap",
                        "action": {"type": "workspace", "workspace_action": "next"},
                    },
                    {
                        "name": "Disabled Tap",
                        "enabled": False,
                        "edge": "right",
                        "direction": "double-tap",
                        "action": {"type": "none"},
                    },
                ],
            }

            ok, err = cm.save_config(cfg)
            self.assertTrue(ok, f"Save failed: {err}")

            # Verify TOML content on disk
            with open(cfg_path, "r") as f:
                toml_text = f.read()

            self.assertIn("[encoder]", toml_text)
            self.assertIn('direction = "tap"', toml_text)
            self.assertIn('direction = "double-tap"', toml_text)
            self.assertIn('action = ["notify-send", "Edgepad", "Double tap"]', toml_text)

            # Load back and verify normalization
            loaded, err = cm.load_config()
            self.assertIsNone(err)
            self.assertEqual(len(loaded["gestures"]), 5)

            # Check command action survived
            cmd_g = [g for g in loaded["gestures"] if g["name"] == "Command Tap"][0]
            self.assertEqual(cmd_g["action"]["type"], "command")
            self.assertEqual(cmd_g["action"]["argv"], ["notify-send", "Edgepad", "Double tap"])

            # Check media action survived
            media_g = [g for g in loaded["gestures"] if g["name"] == "Media Tap"][0]
            self.assertEqual(media_g["action"]["type"], "media")
            self.assertEqual(media_g["action"]["key"], "KEY_PLAYPAUSE")

    def test_validation_tap_vs_slider_conflicts(self):
        """Verify directional swipe conflicts with sliders, while tap gestures on sliders are allowed."""
        cm = ConfigManager()

        base_cfg = {
            "edge_width": 0.12,
            "sliders": [
                {
                    "name": "Right Edge Slider",
                    "zone": "right",
                    "enabled": True,
                    "direction": "vertical",
                }
            ],
            "gestures": [],
        }

        # 1. Directional swipe on slider edge -> CONFLICT
        bad_cfg = copy.deepcopy(base_cfg)
        bad_cfg["gestures"].append({
            "name": "Swipe on Slider",
            "enabled": True,
            "edge": "right",
            "direction": "up",
            "action": {"type": "key", "key": "KEY_VOLUMEUP"},
        })
        valid, errors = cm.validate_config(bad_cfg)
        self.assertFalse(valid)
        self.assertTrue(any("conflicts with active slider" in e for e in errors))

        # 2. Tap on slider edge -> ALLOWED (Rust engine explicitly allows taps on slider edges)
        good_cfg = copy.deepcopy(base_cfg)
        good_cfg["gestures"].append({
            "name": "Tap on Slider Edge",
            "enabled": True,
            "edge": "right",
            "direction": "tap",
            "action": {"type": "key", "key": "KEY_MUTE"},
        })
        valid, errors = cm.validate_config(good_cfg)
        self.assertTrue(valid, f"Tap on slider edge should be allowed: {errors}")

    def test_validation_invalid_keycodes_and_commands(self):
        """Verify validation of unknown keys and executable command availability."""
        cm = ConfigManager()
        ctrl = EdgepadController()

        # Unknown keycode validation in config
        bad_key_cfg = {
            "edge_width": 0.12,
            "gestures": [
                {
                    "name": "Bad Key",
                    "enabled": True,
                    "edge": "top",
                    "direction": "tap",
                    "action": {"type": "key", "key": "KEY_NONEXISTENT_XYZ"},
                }
            ],
        }
        valid, errors = cm.validate_config(bad_key_cfg)
        self.assertFalse(valid)
        self.assertTrue(any("Unknown key" in e for e in errors))

        # Command validation slot
        res_ok = ctrl.validateCommand(["sh", "-c", "echo hello"])
        self.assertTrue(res_ok["valid"])

        res_bad = ctrl.validateCommand(["nonexistent_binary_xyz_123"])
        self.assertFalse(res_bad["valid"])
        self.assertIn("not found", res_bad["error"])

        res_empty = ctrl.validateCommand([])
        self.assertFalse(res_empty["valid"])

    def test_reset_tap_actions_to_defaults(self):
        """Verify resetting tap actions populates recommended defaults while keeping swipes intact."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path
            ctrl.resetToDefaults()

            self.assertEqual(len(ctrl.swipeRules), 4)
            self.assertEqual(len(ctrl.tapRules), 0)

            ctrl.resetTapActionsToDefaults()
            self.assertEqual(len(ctrl.swipeRules), 4, "Swipe rules must remain intact")
            self.assertGreaterEqual(len(ctrl.tapRules), 3, "Recommended tap rules populated")

    def test_ipc_simulated_vs_hardware_events_and_debounce(self):
        """Verify live testing distinguishes simulated vs hardware events and debounces duplicates."""
        ctrl = EdgepadController()

        # Test simulation
        ctrl.testGestureAction("left", "tap", "media", "KEY_MUTE", "Left Tap (Mute)")
        last = ctrl.lastGesture
        self.assertTrue(last["is_simulated"])
        self.assertTrue(last["test_mode"])
        self.assertEqual(last["zone"], "left")
        self.assertEqual(last["direction"], "tap")

        # Hardware IPC event
        ctrl._on_ipc_event({
            "event": "gesture",
            "zone": "top",
            "direction": "tap",
            "action_type": "key",
            "key": "KEY_PLAYPAUSE",
            "success": True,
        })
        last_hw = ctrl.lastGesture
        self.assertFalse(last_hw["is_simulated"])
        self.assertEqual(last_hw["zone"], "top")
        self.assertEqual(last_hw["direction"], "tap")


    def test_tap_actions_full_crud_lifecycle_and_persistence(self):
        """Verify adding, editing, toggling, deleting, and saving tap actions preserves swipes and parses in Rust."""
        import subprocess

        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path
            ctrl.resetToDefaults()

            self.assertEqual(len(ctrl.swipeRules), 4)
            self.assertEqual(len(ctrl.tapRules), 0)

            # 1. Add single tap rule on Top edge
            new_tap = {
                "name": "Play/Pause Media",
                "enabled": True,
                "edge": "top",
                "direction": "tap",
                "action": {
                    "type": "media",
                    "media_action": "play_pause",
                    "key": "KEY_PLAYPAUSE",
                    "repeat": 1,
                },
            }
            ctrl.addTapRule(new_tap)
            self.assertEqual(len(ctrl.tapRules), 1)
            self.assertEqual(ctrl.tapRules[0]["name"], "Play/Pause Media")
            self.assertTrue(ctrl.hasUnsavedChanges)

            # 2. Add double tap rule on Top edge
            double_tap = {
                "name": "Stop Media",
                "enabled": True,
                "edge": "top",
                "direction": "double-tap",
                "action": {
                    "type": "media",
                    "media_action": "stop",
                    "key": "KEY_STOPCD",
                    "repeat": 1,
                },
            }
            ctrl.addTapRule(double_tap)
            self.assertEqual(len(ctrl.tapRules), 2)

            # 3. Update the tap rule
            updated_tap = dict(new_tap)
            updated_tap["name"] = "Toggle Music"
            ctrl.updateTapRule(0, updated_tap)
            self.assertEqual(ctrl.tapRules[0]["name"], "Toggle Music")

            # 4. Toggle enabled
            ctrl.toggleTapRule(0, False)
            self.assertFalse(ctrl.tapRules[0]["enabled"])
            ctrl.toggleTapRule(0, True)
            self.assertTrue(ctrl.tapRules[0]["enabled"])

            # 5. Save configuration
            ctrl.saveConfiguration()
            self.assertFalse(ctrl.hasUnsavedChanges)
            self.assertTrue(cfg_path.exists())

            # 6. Verify Rust binary parses the saved TOML without error (code 0 = running, code 2 = not running but valid)
            res = subprocess.run(
                ["cargo", "run", "--quiet", "--", "status", "--config", str(cfg_path)],
                capture_output=True,
                text=True,
            )
            self.assertIn(res.returncode, (0, 2), f"Rust status check failed with error: {res.stderr}\n{res.stdout}")
            self.assertNotIn("misconfigured", res.stdout.lower())
            self.assertIn("Zones", res.stdout)

            # 7. Reload into a fresh controller instance
            fresh_ctrl = EdgepadController()
            fresh_ctrl.config_manager.config_path = cfg_path
            fresh_ctrl._load_initial_state()

            self.assertEqual(len(fresh_ctrl.swipeRules), 4, "All 4 swipe rules must be preserved")
            self.assertEqual(len(fresh_ctrl.tapRules), 2, "Both tap rules must survive reload")
            self.assertEqual(fresh_ctrl.tapRules[0]["name"], "Toggle Music")
            self.assertEqual(fresh_ctrl.tapRules[0]["edge"], "top")
            self.assertEqual(fresh_ctrl.tapRules[0]["direction"], "tap")
            self.assertEqual(fresh_ctrl.tapRules[1]["name"], "Stop Media")
            self.assertEqual(fresh_ctrl.tapRules[1]["direction"], "double-tap")

            # 8. Delete a tap rule
            fresh_ctrl.removeTapRule(0)
            self.assertEqual(len(fresh_ctrl.tapRules), 1)
            fresh_ctrl.saveConfiguration()

            reloaded_again = EdgepadController()
            reloaded_again.config_manager.config_path = cfg_path
            reloaded_again._load_initial_state()
            self.assertEqual(len(reloaded_again.tapRules), 1)
            self.assertEqual(len(reloaded_again.swipeRules), 4)

    def test_separate_tap_actions_and_edge_gestures_navigation(self):
        """Verify QML navigation genuinely separates Tap Actions (Page 1) and Edge Gestures (Page 2)."""
        base_dir = Path(__file__).resolve().parent.parent
        main_qml = (base_dir / "gui" / "qml" / "Main.qml").read_text()
        gestures_view = (base_dir / "gui" / "qml" / "views" / "GesturesView.qml").read_text()
        tap_actions_view = (base_dir / "gui" / "qml" / "views" / "TapActionsView.qml").read_text()
        dashboard_view = (base_dir / "gui" / "qml" / "views" / "DashboardView.qml").read_text()

        # Main sidebar navigation: distinct page indices for Tap Actions and Edge Gestures
        self.assertIn('{ name: "Tap Actions", icon: "🎯", page: 1 }', main_qml)
        self.assertIn('{ name: "Edge Gestures", icon: "⚡", page: 2 }', main_qml)
        self.assertIn("TapActionsView { id: tapActionsViewItem }", main_qml)
        self.assertIn("GesturesView { id: gesturesViewItem }", main_qml)

        # GesturesView is strictly Edge Swipes and Rotary Encoder (no tap tabs or tap editor dialog)
        self.assertIn("⚡ Edge Swipes (", gestures_view)
        self.assertIn("🎛️ Rotary Encoder & Sliders", gestures_view)
        self.assertNotIn("tapEditorDialog", gestures_view)
        self.assertNotIn("tapListView", gestures_view)

        # TapActionsView is dedicated to the four corner double-taps
        self.assertIn("Touchpad Corner Double-Tap Actions", tap_actions_view)
        self.assertIn("top-left", tap_actions_view)
        self.assertIn("top-right", tap_actions_view)
        self.assertIn("bottom-left", tap_actions_view)
        self.assertIn("bottom-right", tap_actions_view)
        self.assertIn("shortcutRecordDialog", tap_actions_view)
        self.assertNotIn("swipeListView", tap_actions_view)
        self.assertNotIn("EncoderSettingsCard", tap_actions_view)

        # Dashboard navigation points to Page 1 for Tap Actions
        self.assertIn("Configure Tap Actions", dashboard_view)
        self.assertIn("navigateToPage(1)", dashboard_view)

    def test_corner_double_tap_exclusivity_and_validation(self):
        """Verify only double-tap is permitted for corner zones and single/triple tap are rejected."""
        cfg = ConfigManager()

        # Valid corner double-tap rule
        valid_config = {
            "device": "/dev/input/event0",
            "edge_width": 0.12,
            "engine": {"min_travel": 250, "max_drift": 120, "cooldown_ms": 250},
            "gestures": [
                {
                    "name": "Top-Left Double Tap",
                    "edge": "top-left",
                    "direction": "double-tap",
                    "keys": ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"],
                    "action": {"type": "shortcut", "keys": ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"]},
                }
            ],
        }
        ok, msg = cfg.validate_config(valid_config)
        self.assertTrue(ok, f"Expected valid config, got: {msg}")

        # Reject single-tap for corner zone
        invalid_tap = copy.deepcopy(valid_config)
        invalid_tap["gestures"][0]["direction"] = "tap"
        ok, msg = cfg.validate_config(invalid_tap)
        self.assertFalse(ok)
        self.assertTrue(any("Corner zones support double-tap only" in m for m in msg), f"Errors: {msg}")

        # Reject triple-tap or long-press for corner zone
        invalid_triple = copy.deepcopy(valid_config)
        invalid_triple["gestures"][0]["direction"] = "triple-tap"
        ok, msg = cfg.validate_config(invalid_triple)
        self.assertFalse(ok)
        self.assertTrue(any("Corner zones support double-tap only" in m for m in msg), f"Errors: {msg}")

    def test_shortcut_normalization_and_formatting(self):
        """Verify shortcut key normalization (Ctrl->Alt->Shift->Super->Key) and display formatting."""
        from gui.backend.key_definitions import format_shortcut, normalize_shortcut_keys, parse_qt_key_event

        # Normalization of modifier order: primary key at the end
        raw_keys = ["KEY_M", "KEY_LEFTSHIFT", "KEY_LEFTCTRL"]
        normalized = normalize_shortcut_keys(raw_keys)
        self.assertEqual(normalized, ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"])

        # Display formatting
        display = format_shortcut(normalized)
        self.assertEqual(display, "Ctrl + Shift + M")

        # Alt + F4
        alt_f4 = normalize_shortcut_keys(["KEY_F4", "KEY_LEFTALT"])
        self.assertEqual(alt_f4, ["KEY_LEFTALT", "KEY_F4"])
        self.assertEqual(format_shortcut(alt_f4), "Alt + F4")

        # Super + L
        super_l = normalize_shortcut_keys(["KEY_L", "KEY_LEFTMETA"])
        self.assertEqual(super_l, ["KEY_LEFTMETA", "KEY_L"])
        self.assertEqual(format_shortcut(super_l), "Super + L")

        # Parsing Qt key event: Ctrl + Shift + M
        # Qt.Key_M = 0x4D, Qt.ControlModifier = 0x04000000, Qt.ShiftModifier = 0x02000000
        qt_key_m = 0x4D
        qt_mods = 0x04000000 | 0x02000000
        parsed_keys, parsed_display = parse_qt_key_event(qt_key_m, qt_mods)
        self.assertEqual(parsed_keys, ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"])
        self.assertEqual(parsed_display, "Ctrl + Shift + M")

    def test_controller_corner_double_tap_crud_and_recording(self):
        """Verify controller slots for shortcut recording, activation-key filtering, and corner CRUD."""
        ctrl = EdgepadController()

        # Check 4 corner rules exist
        corner_rules = ctrl.cornerTapRules
        self.assertIn("top-left", corner_rules)
        self.assertIn("top-right", corner_rules)
        self.assertIn("bottom-left", corner_rules)
        self.assertIn("bottom-right", corner_rules)

        # Start shortcut recording for top-left
        ctrl.startShortcutRecording("top-left")
        self.assertTrue(ctrl.isRecording)
        self.assertEqual(ctrl.recordingCorner, "top-left")

        # Activation key filtering: Enter/Space pressed with no modifiers initially ignored
        ctrl.processRecordedKey(0x20, 0)  # Space
        self.assertEqual(ctrl.recordedKeys, [])

        # Process valid combination: Ctrl + Alt + T
        # Qt.Key_T = 0x54, Qt.ControlModifier = 0x04000000, Qt.AltModifier = 0x08000000
        res = ctrl.processRecordedKey(0x54, 0x04000000 | 0x08000000)
        self.assertTrue(res["valid"])
        self.assertEqual(ctrl.recordedKeys, ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"])
        self.assertEqual(ctrl.recordedShortcutDisplay, "Ctrl + Alt + T")

        # Confirm recorded shortcut
        ctrl.confirmRecordedShortcut()
        self.assertFalse(ctrl.isRecording)

        tl_rule = ctrl.getCornerRule("top-left")
        self.assertTrue(tl_rule.get("configured"))
        self.assertEqual(tl_rule.get("shortcutDisplay"), "Ctrl + Alt + T")
        self.assertEqual(tl_rule.get("keys"), ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"])

        # Toggle corner rule
        ctrl.toggleCornerRule("top-left", False)
        self.assertFalse(ctrl.getCornerRule("top-left").get("enabled"))
        ctrl.toggleCornerRule("top-left", True)
        self.assertTrue(ctrl.getCornerRule("top-left").get("enabled"))

        # Clear corner shortcut
        ctrl.clearCornerShortcut("top-left")
        cleared_rule = ctrl.getCornerRule("top-left")
        self.assertFalse(cleared_rule.get("configured"))

        # Reset corner rules to defaults
        ctrl.resetCornerRulesToDefaults()
        default_tl = ctrl.getCornerRule("top-left")
        self.assertTrue(default_tl.get("configured"))
        self.assertEqual(default_tl.get("keys"), ["KEY_LEFTCTRL", "KEY_LEFTSHIFT", "KEY_M"])

        # Cancel recording mode safely
        ctrl.startShortcutRecording("bottom-right")
        self.assertTrue(ctrl.isRecording)
        ctrl.cancelShortcutRecording()
        self.assertFalse(ctrl.isRecording)

    def test_corner_double_tap_serialization_and_persistence(self):
        """Verify saving corner double-tap actions to TOML with keys = [...] and reloading."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"

            ctrl = EdgepadController()
            ctrl.config_manager.config_path = cfg_path

            # Assign shortcuts
            ctrl.setCornerShortcut("top-left", ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"], "Terminal")
            ctrl.setCornerShortcut("top-right", ["KEY_LEFTMETA", "KEY_L"], "Lock Screen")

            # Save configuration
            ctrl.saveConfiguration()
            self.assertTrue(cfg_path.exists())

            content = cfg_path.read_text()
            self.assertIn('zone = "top-left"', content)
            self.assertIn('direction = "double-tap"', content)
            self.assertIn('keys = ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"]', content)
            self.assertIn('zone = "top-right"', content)
            self.assertIn('keys = ["KEY_LEFTMETA", "KEY_L"]', content)

            # Reload into a new controller instance
            reloaded = EdgepadController()
            reloaded.config_manager.config_path = cfg_path
            reloaded._load_initial_state()

            tl = reloaded.getCornerRule("top-left")
            self.assertTrue(tl.get("configured"))
            self.assertEqual(tl.get("keys"), ["KEY_LEFTCTRL", "KEY_LEFTALT", "KEY_T"])
            self.assertEqual(tl.get("shortcutDisplay"), "Ctrl + Alt + T")

            tr = reloaded.getCornerRule("top-right")
            self.assertTrue(tr.get("configured"))
            self.assertEqual(tr.get("keys"), ["KEY_LEFTMETA", "KEY_L"])
            self.assertEqual(tr.get("shortcutDisplay"), "Super + L")

    def test_corner_hitbox_configuration_and_persistence(self):
        """Verify corner hitbox getter, setter, clamping (0.05 to 0.35), validation, and TOML persistence."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cfg_path = Path(tmpdir) / "edgepad.toml"

            ctrl = EdgepadController(config_path=cfg_path)

            # Default hitbox should be 0.15 (15%)
            self.assertAlmostEqual(ctrl.cornerHitbox, 0.15, places=2)

            # Set to 22%
            ctrl.setCornerHitbox(0.22)
            self.assertAlmostEqual(ctrl.cornerHitbox, 0.22, places=2)
            self.assertTrue(ctrl.hasUnsavedChanges)

            # Clamping lower bound (5%)
            ctrl.setCornerHitbox(0.02)
            self.assertAlmostEqual(ctrl.cornerHitbox, 0.05, places=2)

            # Clamping upper bound (35%)
            ctrl.setCornerHitbox(0.48)
            self.assertAlmostEqual(ctrl.cornerHitbox, 0.35, places=2)

            # Validation check
            valid, errors = ctrl.config_manager.validate_config({"edge_width": 0.12, "corner_hitbox": 0.40})
            self.assertFalse(valid)
            self.assertTrue(any("Corner hitbox" in e for e in errors))

            # Set to 20% and save
            ctrl.setCornerHitbox(0.20)
            ctrl.saveConfiguration()
            self.assertTrue(cfg_path.exists())

            content = cfg_path.read_text()
            self.assertIn("corner_hitbox = 0.20", content)

            # Reload into fresh controller
            reloaded = EdgepadController(config_path=cfg_path)
            self.assertAlmostEqual(reloaded.cornerHitbox, 0.20, places=2)

    def test_service_manager_detect_legacy_unit(self):
        """Verify detect_legacy_unit identifies developer paths and broken ExecStart binaries."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = ServiceManager()
            service_path = Path(tmpdir) / "edgepad.service"
            sm.service_file_path = service_path

            # Non-existent unit
            self.assertFalse(sm.detect_legacy_unit()[0])

            # Legacy unit with /home/vicky
            service_path.write_text("[Service]\nExecStart=/home/vicky/.local/bin/edgepad daemon\n")
            is_legacy, reason = sm.detect_legacy_unit()
            self.assertTrue(is_legacy)
            self.assertIn("/home/vicky", reason)

            # Legacy unit with missing %h/.local/bin/edgepad
            service_path.write_text("[Service]\nExecStart=%h/.local/bin/edgepad daemon\n")
            is_legacy, reason = sm.detect_legacy_unit()
            if not (Path.home() / ".local" / "bin" / "edgepad").exists():
                self.assertTrue(is_legacy)
                self.assertIn("causes status 203/EXEC", reason)

            # Valid unit pointing to /usr/bin/edgepad or system binary
            service_path.write_text("[Service]\nExecStart=/usr/bin/edgepad daemon\n")
            # If /usr/bin/edgepad exists, should not report missing binary
            if Path("/usr/bin/edgepad").exists():
                self.assertFalse(sm.detect_legacy_unit()[0])

    def test_service_manager_repair_service(self):
        """Verify repair_service safely backs up legacy unit and unlinks or replaces it."""
        with tempfile.TemporaryDirectory() as tmpdir:
            sm = ServiceManager()
            user_dir = Path(tmpdir) / "user"
            user_dir.mkdir(parents=True, exist_ok=True)
            sm.user_systemd_dir = user_dir
            sm.service_file_path = user_dir / "edgepad.service"

            # Create broken legacy unit
            sm.service_file_path.write_text("[Service]\nExecStart=/home/vicky/.local/bin/edgepad daemon\n")

            ok, msg = sm.repair_service()
            self.assertTrue(ok)

            # Verify backup was created
            backups = list(user_dir.glob("edgepad.service.bak.*"))
            self.assertGreaterEqual(len(backups), 1, "Backup file should be created")

    def test_controller_repair_service_slot(self):
        """Verify controller exposes legacyServiceDetected and repairService without error."""
        ctrl = EdgepadController()
        # legacyServiceDetected returns bool
        self.assertIsInstance(ctrl.legacyServiceDetected, bool)
        # repairService executes without unhandled exception
        ctrl.repairService()

    def test_notification_dismissal_clears_error_and_message(self):
        """Verify dismissCurrentNotification clears lastError and lastMessage and emits change signals."""
        ctrl = EdgepadController()
        error_emissions = []
        message_emissions = []
        ctrl.lastErrorChanged.connect(lambda e: error_emissions.append(e))
        ctrl.lastMessageChanged.connect(lambda m: message_emissions.append(m))

        ctrl._set_error("Test failure message")
        ctrl._set_message("Test success status")
        self.assertEqual(ctrl.lastError, "Test failure message")
        self.assertEqual(ctrl.lastMessage, "Test success status")

        ctrl.dismissCurrentNotification()
        self.assertEqual(ctrl.lastError, "")
        self.assertEqual(ctrl.lastMessage, "")
        self.assertIn("", error_emissions)
        self.assertIn("", message_emissions)

    def test_notification_dismissal_prevents_immediate_reappearance_on_poll(self):
        """Verify the same unchanged service error does not immediately reappear on the next status poll."""
        ctrl = EdgepadController()
        # Mock service manager status to "error"
        ctrl.service_manager.get_status = lambda: "error"

        ctrl._poll_status()
        self.assertTrue(bool(ctrl.lastError), "Service error should be populated on poll")
        initial_error = ctrl.lastError

        # Dismiss notification
        ctrl.dismissCurrentNotification()
        self.assertEqual(ctrl.lastError, "")

        # Poll again - unchanged error must NOT reappear
        ctrl._poll_status()
        self.assertEqual(ctrl.lastError, "", "Dismissed unchanged error must remain suppressed on next poll")

    def test_notification_new_error_displays_after_dismissal(self):
        """Verify genuinely new or user-action errors display normally after a previous error was dismissed."""
        ctrl = EdgepadController()
        ctrl._set_error("First error")
        ctrl.dismissCurrentNotification()
        self.assertEqual(ctrl.lastError, "")

        # A new, different error should appear normally
        ctrl._set_error("Second error: operation failed")
        self.assertEqual(ctrl.lastError, "Second error: operation failed")

        ctrl.dismissCurrentNotification()
        self.assertEqual(ctrl.lastError, "")

    def test_notification_dismissal_does_not_mutate_daemon_state(self):
        """Verify dismissing a notification does not stop, restart, or alter daemon service state."""
        ctrl = EdgepadController()
        ctrl._daemon_status = "running"
        ctrl._set_error("Unrelated runtime note")
        ctrl.dismissCurrentNotification()
        self.assertEqual(ctrl.daemonStatus, "running", "Daemon status must remain completely unaffected")

    def test_notification_property_setters(self):
        """Verify setting lastError or lastMessage directly updates state or dismisses cleanly."""
        ctrl = EdgepadController()
        ctrl.lastError = "Custom error"
        self.assertEqual(ctrl.lastError, "Custom error")

        ctrl.lastError = ""
        self.assertEqual(ctrl.lastError, "")

        ctrl.lastMessage = "Custom success"
        self.assertEqual(ctrl.lastMessage, "Custom success")

        ctrl.lastMessage = ""
        self.assertEqual(ctrl.lastMessage, "")


if __name__ == "__main__":
    unittest.main()



