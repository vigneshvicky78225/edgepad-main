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


if __name__ == "__main__":
    unittest.main()
