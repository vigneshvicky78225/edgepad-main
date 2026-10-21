"""Regression tests for independent Hitbox and Gesture calibration systems.

Proves that:
1. Hitbox geometry and gesture sensitivity are strictly independent in data structures,
   validation, TOML serialization, and controller state.
2. Updating hitbox settings never mutates gesture settings.
3. Updating gesture settings never mutates hitbox geometry.
4. UI views and components enforce independent controls.
"""

from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from gui.backend.config_manager import (
    DEFAULT_HITBOX_CONFIG,
    DEFAULT_GESTURE_CONFIG,
    ConfigManager,
    default_preset_config,
    validate_hitbox_config,
    validate_gesture_config,
)
from gui.backend.controller import EdgepadController


class TestCalibrationSeparation(unittest.TestCase):
    """Test suite ensuring strict decoupling between Hitbox and Gesture calibration."""

    def test_hitbox_validation_independent(self):
        """Validates physical hitbox geometry independently from gesture thresholds."""
        valid_hitbox = {
            "edge_width": 0.12,
            "left_edge_width": 0.15,
            "right_edge_width": 0.12,
            "top_edge_height": 0.10,
            "bottom_edge_height": 0.10,
            "corner_width": 0.18,
            "corner_height": 0.16,
        }
        ok, errors = validate_hitbox_config(valid_hitbox)
        self.assertTrue(ok, f"Expected valid hitbox config: {errors}")

        # Invalid left edge width (> 0.45)
        bad_hitbox = copy.deepcopy(valid_hitbox)
        bad_hitbox["left_edge_width"] = 0.60
        ok, errors = validate_hitbox_config(bad_hitbox)
        self.assertFalse(ok)
        self.assertTrue(any("left_edge_width" in e for e in errors))

        # Invalid corner height (< 0.05)
        bad_corner = copy.deepcopy(valid_hitbox)
        bad_corner["corner_height"] = 0.02
        ok, errors = validate_hitbox_config(bad_corner)
        self.assertFalse(ok)
        self.assertTrue(any("corner_height" in e for e in errors))

    def test_gesture_validation_independent(self):
        """Validates gesture recognition thresholds independently from physical hitboxes."""
        valid_gesture = {
            "swipe_min_distance": 0.08,
            "swipe_max_drift": 0.04,
            "tap_max_movement": 0.04,
            "tap_min_duration_ms": 40,
            "tap_max_duration_ms": 200,
            "double_tap_timeout_ms": 300,
            "double_tap_max_distance": 0.08,
            "cooldown_ms": 250,
        }
        ok, errors = validate_gesture_config(valid_gesture)
        self.assertTrue(ok, f"Expected valid gesture config: {errors}")

        # Invalid swipe drift (> 0.50)
        bad_gesture = copy.deepcopy(valid_gesture)
        bad_gesture["swipe_max_drift"] = 0.65
        ok, errors = validate_gesture_config(bad_gesture)
        self.assertFalse(ok)
        self.assertTrue(any("swipe_max_drift" in e for e in errors))

        # Inverted tap timings (min >= max)
        bad_timing = copy.deepcopy(valid_gesture)
        bad_timing["tap_min_duration_ms"] = 300
        bad_timing["tap_max_duration_ms"] = 200
        ok, errors = validate_gesture_config(bad_timing)
        self.assertFalse(ok)
        self.assertTrue(any("must be less than" in e for e in errors))

    def test_toml_independent_serialization_and_roundtrip(self):
        """TOML serializer preserves independent [hitbox] and [gesture] tables."""
        cm = ConfigManager()
        cfg = default_preset_config()
        cfg["hitbox"]["left_edge_width"] = 0.22
        cfg["hitbox"]["corner_width"] = 0.25
        cfg["hitbox"]["corner_height"] = 0.20

        cfg["gesture"]["swipe_min_distance"] = 0.12
        cfg["gesture"]["double_tap_timeout_ms"] = 450

        toml_str = cm.to_toml_string(cfg)
        self.assertIn("[hitbox]", toml_str)
        self.assertIn("[gesture]", toml_str)
        self.assertIn("left_edge_width = 0.2200", toml_str)
        self.assertIn("corner_width = 0.2500", toml_str)
        self.assertIn("corner_height = 0.2000", toml_str)
        self.assertIn("swipe_min_distance = 0.1200", toml_str)
        self.assertIn("double_tap_timeout_ms = 450", toml_str)

        # Roundtrip via file
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edgepad.toml"
            cm.config_path = path
            ok, msg = cm.save_config(cfg)
            self.assertTrue(ok, msg)

            loaded, err = cm.load_config()
            self.assertIsNone(err)
            self.assertAlmostEqual(loaded["hitbox"]["left_edge_width"], 0.22, places=4)
            self.assertAlmostEqual(loaded["hitbox"]["corner_width"], 0.25, places=4)
            self.assertAlmostEqual(loaded["hitbox"]["corner_height"], 0.20, places=4)
            self.assertAlmostEqual(loaded["gesture"]["swipe_min_distance"], 0.12, places=4)
            self.assertEqual(loaded["gesture"]["double_tap_timeout_ms"], 450)

    def test_controller_update_hitbox_preserves_gesture_settings(self):
        """Changing hitbox settings in controller never mutates gesture thresholds."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController(config_path=path)
            initial_gesture = copy.deepcopy(ctrl.gestureSettings)
            initial_encoder_step = ctrl.encoderStepSize

            # Update Hitbox settings: left=0.20, right=0.18, top=0.14, bottom=0.15, corner_w=0.22, corner_h=0.19
            ctrl.updateHitboxSettings(0.20, 0.18, 0.14, 0.15, 0.22, 0.19)

            # Hitbox settings should be updated
            hb = ctrl.hitboxSettings
            self.assertAlmostEqual(hb["left_edge_width"], 0.20, places=2)
            self.assertAlmostEqual(hb["right_edge_width"], 0.18, places=2)
            self.assertAlmostEqual(hb["top_edge_height"], 0.14, places=2)
            self.assertAlmostEqual(hb["bottom_edge_height"], 0.15, places=2)
            self.assertAlmostEqual(hb["corner_width"], 0.22, places=2)
            self.assertAlmostEqual(hb["corner_height"], 0.19, places=2)

            # Gesture settings and encoder must remain strictly identical
            self.assertEqual(ctrl.gestureSettings, initial_gesture)
            self.assertEqual(ctrl.encoderStepSize, initial_encoder_step)

    def test_controller_update_gesture_preserves_hitbox_settings(self):
        """Changing gesture settings in controller never mutates hitbox geometry."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController(config_path=path)
            initial_hitbox = copy.deepcopy(ctrl.hitboxSettings)
            initial_corner_hitbox = ctrl.cornerHitbox

            # Update Gesture settings
            ctrl.updateGestureSettings(
                0.14, # swipe_min_dist
                0.07, # swipe_max_drift
                0.03, # tap_max_mov
                35,   # tap_min_dur
                220,  # tap_max_dur
                350,  # dbl_tap_timeout
                0.09, # dbl_tap_max_dist
                240,  # cooldown_ms
            )

            # Gesture settings should be updated
            g = ctrl.gestureSettings
            self.assertAlmostEqual(g["swipe_min_distance"], 0.14, places=2)
            self.assertAlmostEqual(g["swipe_max_drift"], 0.07, places=2)
            self.assertAlmostEqual(g["tap_max_movement"], 0.03, places=2)
            self.assertEqual(g["tap_min_duration_ms"], 35)
            self.assertEqual(g["tap_max_duration_ms"], 220)
            self.assertEqual(g["double_tap_timeout_ms"], 350)

            # Hitbox settings must remain strictly identical
            self.assertEqual(ctrl.hitboxSettings, initial_hitbox)
            self.assertEqual(ctrl.cornerHitbox, initial_corner_hitbox)

    def test_controller_restore_hitbox_defaults(self):
        """Restoring hitbox defaults resets only hitbox geometry without touching gestures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController(config_path=path)

            # Change both
            ctrl.updateHitboxSettings(0.30, 0.30, 0.25, 0.25, 0.28, 0.28)
            ctrl.updateGestureSettings(0.18, 0.09, 0.05, 50, 250, 400, 0.10, 300)

            # Restore only Hitbox defaults
            ctrl.restoreHitboxDefaults()

            hb = ctrl.hitboxSettings
            self.assertAlmostEqual(hb["left_edge_width"], DEFAULT_HITBOX_CONFIG["left_edge_width"], places=2)
            self.assertAlmostEqual(hb["corner_width"], DEFAULT_HITBOX_CONFIG["corner_width"], places=2)

            # Gesture settings must retain the modified values
            self.assertAlmostEqual(ctrl.gestureSettings["swipe_min_distance"], 0.18, places=2)
            self.assertEqual(ctrl.gestureSettings["double_tap_timeout_ms"], 400)

    def test_controller_restore_gesture_defaults(self):
        """Restoring gesture defaults resets only gesture parameters without touching hitboxes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "edgepad.toml"
            ctrl = EdgepadController(config_path=path)

            # Change both
            ctrl.updateHitboxSettings(0.30, 0.30, 0.25, 0.25, 0.28, 0.28)
            ctrl.updateGestureSettings(0.18, 0.09, 0.05, 50, 250, 400, 0.10, 300)

            # Restore only Gesture defaults
            ctrl.restoreGestureDefaults()

            g = ctrl.gestureSettings
            self.assertAlmostEqual(g["swipe_min_distance"], DEFAULT_GESTURE_CONFIG["swipe_min_distance"], places=2)
            self.assertEqual(g["double_tap_timeout_ms"], DEFAULT_GESTURE_CONFIG["double_tap_timeout_ms"])

            # Hitbox settings must retain the modified values
            self.assertAlmostEqual(ctrl.hitboxSettings["left_edge_width"], 0.30, places=2)
            self.assertAlmostEqual(ctrl.hitboxSettings["corner_width"], 0.28, places=2)

    def test_qml_views_exist_and_isolated(self):
        """Checks that HitboxCalibrationView and GestureCalibrationView QML files exist and define independent controls."""
        views_dir = Path(__file__).resolve().parent.parent / "gui" / "qml" / "views"
        hitbox_view = views_dir / "HitboxCalibrationView.qml"
        gesture_view = views_dir / "GestureCalibrationView.qml"

        self.assertTrue(hitbox_view.exists(), "HitboxCalibrationView.qml must exist")
        self.assertTrue(gesture_view.exists(), "GestureCalibrationView.qml must exist")

        hitbox_content = hitbox_view.read_text()
        self.assertIn("updateHitboxSettings", hitbox_content)
        self.assertIn("restoreHitboxDefaults", hitbox_content)
        self.assertIn("applyHitboxCalibration", hitbox_content)
        self.assertIn("leftSlider", hitbox_content)
        self.assertIn("rightSlider", hitbox_content)
        self.assertIn("topSlider", hitbox_content)
        self.assertIn("bottomSlider", hitbox_content)
        self.assertIn("cornerWidthSlider", hitbox_content)
        self.assertIn("cornerHeightSlider", hitbox_content)
        self.assertNotIn("swipeMinSlider", hitbox_content)

        gesture_content = gesture_view.read_text()
        self.assertIn("updateGestureSettings", gesture_content)
        self.assertIn("restoreGestureDefaults", gesture_content)
        self.assertIn("applyGestureCalibration", gesture_content)
        self.assertIn("swipeMinSlider", gesture_content)
        self.assertIn("swipeDriftSlider", gesture_content)
        self.assertIn("tapMovementSlider", gesture_content)
        self.assertIn("doubleTapTimeoutSlider", gesture_content)
        self.assertIn("encoderStepSlider", gesture_content)
        self.assertNotIn("cornerWidthSlider", gesture_content)


if __name__ == "__main__":
    unittest.main()
