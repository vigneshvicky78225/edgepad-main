"""Central Qt Controller bridging backend services and the QML user interface.

Provides state management, atomic config updates, service control, device selection,
IPC event dispatching, and diagnostics reporting.
"""

from __future__ import annotations

import copy
import datetime
import os
import shlex
import shutil
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from gui.backend.config_manager import (
    DEFAULT_GESTURE_CONFIG,
    DEFAULT_HITBOX_CONFIG,
    MEDIA_ACTION_KEYS,
    MEDIA_ACTION_LABELS,
    VALID_CORNER_ZONES,
    VALID_DIRECTIONS,
    VALID_EDGE_ZONES,
    VALID_SWIPE_DIRECTIONS,
    VALID_TAP_DIRECTIONS,
    VALID_ZONES,
    ConfigManager,
    default_corner_tap_actions,
    default_preset_config,
    default_tap_actions,
    detect_workspace_support,
    get_default_workspace_command,
)
from gui.backend.device_manager import DeviceManager
from gui.backend.diagnostics_manager import DiagnosticsManager
from gui.backend.ipc_client import IpcClient
from gui.backend.key_definitions import (
    KNOWN_KEYS,
    format_shortcut,
    get_key_code,
    get_key_name,
    normalize_shortcut_keys,
    parse_qt_key_event,
    search_keys,
)
from gui.backend.service_manager import ServiceManager


class EdgepadController(QObject):
    """Main QObject exposed to QML providing complete reactive state and controls."""

    # Notification & status signals
    daemonStatusChanged = Signal(str)
    masterEnabledChanged = Signal(bool)
    startAtLoginChanged = Signal(bool)
    touchpadsChanged = Signal()
    selectedDeviceChanged = Signal(str)
    selectedDeviceDetailsChanged = Signal()
    gestureRulesChanged = Signal()
    tapRulesChanged = Signal()
    cornerTapRulesChanged = Signal()
    cornerHitboxChanged = Signal(float)
    shortcutRecordingStateChanged = Signal()
    swipeRulesChanged = Signal()
    sliderRulesChanged = Signal()
    edgeSettingsChanged = Signal()
    hitboxSettingsChanged = Signal()
    gestureSettingsChanged = Signal()
    lastGestureChanged = Signal()
    lastErrorChanged = Signal(str)
    lastMessageChanged = Signal(str)
    testModeChanged = Signal(bool)
    connectedToIpcChanged = Signal(bool)
    doctorReportChanged = Signal()
    serviceLogsChanged = Signal()
    hasUnsavedChangesChanged = Signal(bool)
    notificationRequested = Signal(str, str)  # title, message
    encoderSettingsChanged = Signal()
    encoderDiagnosticsChanged = Signal()
    workspaceSupportChanged = Signal()
    recordingActiveChanged = Signal(bool)
    swipeShortcutRecorded = Signal(list, str)

    def __init__(self, parent: QObject | None = None, config_path: Path | None = None) -> None:
        super().__init__(parent)

        # Backend subsystems
        self.config_manager = ConfigManager(config_path=config_path)
        self.service_manager = ServiceManager()
        self.device_manager = DeviceManager()
        self.diagnostics_manager = DiagnosticsManager()
        self.ipc_client = IpcClient()

        # State fields
        self._daemon_status = "stopped"
        self._master_enabled = True
        self._start_at_login = False
        self._touchpads: list[dict[str, Any]] = []
        self._selected_device = "auto"
        self._selected_device_details: dict[str, Any] = {}
        self._gesture_rules: list[dict[str, Any]] = []
        self._corner_hitbox: float = 0.15
        self._slider_rules: list[dict[str, Any]] = []
        self._hitbox_settings: dict[str, Any] = copy.deepcopy(DEFAULT_HITBOX_CONFIG)
        self._gesture_settings: dict[str, Any] = copy.deepcopy(DEFAULT_GESTURE_CONFIG)
        self._edge_settings: dict[str, Any] = {
            "edge_width": 0.12,
            "min_travel": 232,
            "max_drift": 116,
            "cooldown_ms": 250,
            "tap_max_duration_ms": 200,
            "tap_max_movement": 116,
        }
        self._last_gesture: dict[str, Any] = {}
        self._last_error = ""
        self._last_message = ""
        self._dismissed_error = ""
        self._dismissed_message = ""
        self._test_mode = False
        self._doctor_report: dict[str, Any] = {}
        self._service_logs = ""
        self._has_unsaved_changes = False

        # Encoder settings & live diagnostics
        self._encoder_enabled = True
        self._encoder_step_size = 50.0
        self._encoder_dead_zone = 10.0
        self._encoder_repeat_interval_ms = 20
        self._encoder_live_edge = "None"
        self._encoder_live_direction = "None"
        self._encoder_live_incremental = 0.0
        self._encoder_live_distance = 0.0
        self._encoder_live_ticks = 0
        self._encoder_live_key = ""

        self._encoder_diag_timer = QTimer(self)
        self._encoder_diag_timer.setSingleShot(True)
        self._encoder_diag_timer.setInterval(2500)
        self._encoder_diag_timer.timeout.connect(self._on_encoder_diag_timeout)

        # Shortcut recording state
        self._recording_corner = ""
        self._recording_keys: list[str] = []
        self._recording_display = "None"
        self._is_recording = False
        self._ignoring_initial_key = False
        self._prev_test_mode = False

        self._recording_timer = QTimer(self)
        self._recording_timer.setSingleShot(True)
        self._recording_timer.setInterval(15000)
        self._recording_timer.timeout.connect(self._on_recording_timeout)

        # Hook IPC client
        self.ipc_client.event_received.connect(self._on_ipc_event)
        self.ipc_client.connection_changed.connect(self._on_ipc_connection_changed)
        self.ipc_client.start()

        # Load initial data
        self._load_initial_state()

        # Poller timer for systemd status & log updates (2 seconds)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(2000)
        self._poll_timer.timeout.connect(self._poll_status)
        self._poll_timer.start()

    def _load_initial_state(self) -> None:
        """Loads configuration, discovers devices, and checks initial service state."""
        cfg, err = self.config_manager.load_config()
        if err:
            self._set_error(err)

        self._apply_config_to_state(cfg)
        self.refreshDevices()
        self._poll_status()
        self.refreshDoctor()

    def _apply_config_to_state(self, cfg: dict[str, Any]) -> None:
        self._selected_device = cfg.get("device", "auto")
        self._corner_hitbox = float(cfg.get("corner_hitbox", 0.15))
        self._gesture_rules = copy.deepcopy(cfg.get("gestures", []))
        self._slider_rules = copy.deepcopy(cfg.get("sliders", []))

        # Check if master is enabled (any gestures or sliders enabled)
        has_enabled = any(g.get("enabled", True) for g in self._gesture_rules) or any(
            s.get("enabled", True) for s in self._slider_rules
        )
        self._master_enabled = has_enabled

        self._hitbox_settings = copy.deepcopy(cfg.get("hitbox", DEFAULT_HITBOX_CONFIG))
        self._gesture_settings = copy.deepcopy(cfg.get("gesture", DEFAULT_GESTURE_CONFIG))

        self._edge_settings = {
            "edge_width": float(self._hitbox_settings.get("edge_width", cfg.get("edge_width", 0.12))),
            "min_travel": int(self._gesture_settings.get("swipe_min_distance", 0.08) * 2905.0),
            "max_drift": int(self._gesture_settings.get("swipe_max_drift", 0.04) * 2905.0),
            "cooldown_ms": int(self._gesture_settings.get("cooldown_ms", 250)),
            "tap_max_duration_ms": int(self._gesture_settings.get("tap_max_duration_ms", 200)),
            "tap_max_movement": int(self._gesture_settings.get("tap_max_movement", 0.04) * 2905.0),
        }

        encoder = cfg.get("encoder", {})
        self._encoder_enabled = bool(encoder.get("enabled", True))
        self._encoder_step_size = float(encoder.get("step_size", 50.0))
        self._encoder_dead_zone = float(encoder.get("dead_zone", 10.0))
        self._encoder_repeat_interval_ms = int(encoder.get("repeat_interval_ms", 20))

        self._has_unsaved_changes = False
        self.selectedDeviceChanged.emit(self._selected_device)
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.cornerHitboxChanged.emit(self._corner_hitbox)
        self.swipeRulesChanged.emit()
        self.sliderRulesChanged.emit()
        self.hitboxSettingsChanged.emit()
        self.gestureSettingsChanged.emit()
        self.edgeSettingsChanged.emit()
        self.encoderSettingsChanged.emit()
        self.masterEnabledChanged.emit(self._master_enabled)
        self.workspaceSupportChanged.emit()
        self.hasUnsavedChangesChanged.emit(False)
        self._update_selected_device_details()

    def _update_selected_device_details(self) -> None:
        details = self.device_manager.get_selected_touchpad(self._selected_device)
        self._selected_device_details = details or {
            "name": "Auto (Default Touchpad)",
            "path": "/dev/input/event4",
            "id": "auto",
            "x_min": 0,
            "x_max": 2905,
            "y_min": 0,
            "y_max": 1766,
            "x_range": "0..=2905",
            "y_range": "0..=1766",
            "slots": "0..=4",
            "readable": True,
            "writable": True,
        }
        self.selectedDeviceDetailsChanged.emit()

    def _poll_status(self) -> None:
        """Periodic status update."""
        new_status = self.service_manager.get_status()
        if new_status != self._daemon_status:
            self._daemon_status = new_status
            self.daemonStatusChanged.emit(self._daemon_status)
            if self._daemon_status in ("running", "stopped"):
                self._dismissed_error = ""

        new_enabled = self.service_manager.is_enabled()
        if new_enabled != self._start_at_login:
            self._start_at_login = new_enabled
            self.startAtLoginChanged.emit(self._start_at_login)

        if self._daemon_status == "error":
            service_err = "The background gesture daemon is in an error or failed state."
            if service_err != self._dismissed_error and not self._last_error:
                self._set_error(service_err, is_poll=True)

    def _set_error(self, message: str, is_poll: bool = False) -> None:
        if not message:
            return
        if is_poll and message == self._dismissed_error:
            return
        self._last_error = message
        if message != self._dismissed_error:
            self._dismissed_error = ""
        self.lastErrorChanged.emit(self._last_error)
        self.notificationRequested.emit("Error", message)

    def _set_message(self, message: str, is_poll: bool = False) -> None:
        if not message:
            return
        if is_poll and message == self._dismissed_message:
            return
        self._last_message = message
        if message != self._dismissed_message:
            self._dismissed_message = ""
        self.lastMessageChanged.emit(self._last_message)

    # --- Properties ---

    @Property(str, notify=daemonStatusChanged)
    def daemonStatus(self) -> str:
        return self._daemon_status

    @Property(bool, notify=daemonStatusChanged)
    def legacyServiceDetected(self) -> bool:
        is_legacy, _ = self.service_manager.detect_legacy_unit()
        return is_legacy

    @Property(bool, notify=masterEnabledChanged)
    def masterEnabled(self) -> bool:
        return self._master_enabled

    @Property(bool, notify=startAtLoginChanged)
    def startAtLogin(self) -> bool:
        return self._start_at_login

    @Property(list, notify=touchpadsChanged)
    def touchpads(self) -> list[dict[str, Any]]:
        return self._touchpads

    @Property(str, notify=selectedDeviceChanged)
    def selectedDevice(self) -> str:
        return self._selected_device

    @Property(dict, notify=selectedDeviceDetailsChanged)
    def selectedDeviceDetails(self) -> dict[str, Any]:
        return self._selected_device_details

    @Property(list, notify=gestureRulesChanged)
    def gestureRules(self) -> list[dict[str, Any]]:
        return self._gesture_rules

    @Property(list, notify=tapRulesChanged)
    def tapRules(self) -> list[dict[str, Any]]:
        return [
            dict(g, originalIndex=idx)
            for idx, g in enumerate(self._gesture_rules)
            if g.get("direction") in ("tap", "double-tap")
        ]

    @Property("QVariantMap", notify=cornerTapRulesChanged)
    def cornerTapRules(self) -> dict[str, Any]:
        """Returns the dictionary of the 4 corner double-tap configuration rules."""
        result: dict[str, Any] = {}
        corners = [
            ("top-left", "Top-Left Corner"),
            ("top-right", "Top-Right Corner"),
            ("bottom-left", "Bottom-Left Corner"),
            ("bottom-right", "Bottom-Right Corner"),
        ]
        for corner_id, default_name in corners:
            matching = None
            for idx, g in enumerate(self._gesture_rules):
                edge = str(g.get("edge") or g.get("zone") or "").lower()
                if edge == corner_id and g.get("direction") == "double-tap":
                    matching = (idx, g)
                    break

            if matching is not None:
                idx, rule = matching
                keys = list(rule.get("keys") or rule.get("action", {}).get("keys", []))
                display = format_shortcut(keys) if keys else "None"
                result[corner_id] = {
                    "zone": corner_id,
                    "direction": "double-tap",
                    "name": rule.get("name") or default_name,
                    "enabled": bool(rule.get("enabled", True)),
                    "keys": keys,
                    "shortcutDisplay": display,
                    "configured": len(keys) > 0,
                    "originalIndex": idx,
                }
            else:
                result[corner_id] = {
                    "zone": corner_id,
                    "direction": "double-tap",
                    "name": default_name,
                    "enabled": False,
                    "keys": [],
                    "shortcutDisplay": "None",
                    "configured": False,
                    "originalIndex": -1,
                }
        return result

    @Property(float, notify=cornerHitboxChanged)
    def cornerHitbox(self) -> float:
        """Returns the configured corner double-tap hitbox ratio (0.05 to 0.35)."""
        return self._corner_hitbox

    @Property(str, notify=shortcutRecordingStateChanged)
    def recordingCorner(self) -> str:
        return self._recording_corner

    @Property(bool, notify=shortcutRecordingStateChanged)
    def isRecording(self) -> bool:
        return self._is_recording

    @Property(str, notify=shortcutRecordingStateChanged)
    def recordedShortcutDisplay(self) -> str:
        return self._recording_display

    @Property(list, notify=shortcutRecordingStateChanged)
    def recordedKeys(self) -> list[str]:
        return self._recording_keys

    @Property(list, notify=swipeRulesChanged)
    def swipeRules(self) -> list[dict[str, Any]]:
        return [
            dict(g, originalIndex=idx)
            for idx, g in enumerate(self._gesture_rules)
            if g.get("direction") not in ("tap", "double-tap")
        ]

    @Property(dict, notify=workspaceSupportChanged)
    def workspaceSupport(self) -> dict[str, Any]:
        return detect_workspace_support()

    @Property(list, notify=sliderRulesChanged)
    def sliderRules(self) -> list[dict[str, Any]]:
        return self._slider_rules

    @Property(dict, notify=hitboxSettingsChanged)
    def hitboxSettings(self) -> dict[str, Any]:
        return self._hitbox_settings

    @Property(float, notify=hitboxSettingsChanged)
    def edgeSwipeWidth(self) -> float:
        """Returns the configured edge swipe margin ratio (0.04 to 0.30)."""
        return float(self._hitbox_settings.get("left_edge_width", self._hitbox_settings.get("edge_width", 0.12)))

    @Property(dict, notify=gestureSettingsChanged)
    def gestureSettings(self) -> dict[str, Any]:
        return self._gesture_settings

    @Property(dict, notify=edgeSettingsChanged)
    def edgeSettings(self) -> dict[str, Any]:
        return {
            "edge_width": self._hitbox_settings.get("edge_width", 0.12),
            "min_travel": int(self._gesture_settings.get("swipe_min_distance", 0.08) * 2905.0),
            "max_drift": int(self._gesture_settings.get("swipe_max_drift", 0.04) * 2905.0),
            "cooldown_ms": int(self._gesture_settings.get("cooldown_ms", 250)),
            "tap_max_duration_ms": int(self._gesture_settings.get("tap_max_duration_ms", 200)),
            "tap_max_movement": int(self._gesture_settings.get("tap_max_movement", 0.04) * 2905.0),
        }

    @Property(dict, notify=lastGestureChanged)
    def lastGesture(self) -> dict[str, Any]:
        return self._last_gesture

    @Property(str, notify=lastErrorChanged)
    def lastError(self) -> str:
        return self._last_error

    @lastError.setter
    def lastError(self, value: str) -> None:
        if not value:
            self.dismissCurrentNotification()
        else:
            self._set_error(value)

    @Property(str, notify=lastMessageChanged)
    def lastMessage(self) -> str:
        return self._last_message

    @lastMessage.setter
    def lastMessage(self, value: str) -> None:
        if not value:
            self.dismissCurrentNotification()
        else:
            self._set_message(value)

    # --- Slots: Notification Management ---

    @Slot()
    def dismissCurrentNotification(self) -> None:
        """Dismisses the current error or status notification immediately without mutating daemon."""
        if self._last_error:
            self._dismissed_error = self._last_error
            self._last_error = ""
            self.lastErrorChanged.emit("")
        if self._last_message:
            self._dismissed_message = self._last_message
            self._last_message = ""
            self.lastMessageChanged.emit("")

    @Slot()
    def dismissNotification(self) -> None:
        """Alias for dismissCurrentNotification."""
        self.dismissCurrentNotification()

    @Slot()
    def clearNotification(self) -> None:
        """Alias for dismissCurrentNotification."""
        self.dismissCurrentNotification()

    @Property(bool, notify=testModeChanged)
    def testMode(self) -> bool:
        return self._test_mode

    @Property(bool, notify=connectedToIpcChanged)
    def connectedToIpc(self) -> bool:
        return self.ipc_client.is_connected

    @Property(dict, notify=doctorReportChanged)
    def doctorReport(self) -> dict[str, Any]:
        return self._doctor_report

    @Property(str, notify=serviceLogsChanged)
    def serviceLogs(self) -> str:
        return self._service_logs

    @Property(bool, notify=hasUnsavedChangesChanged)
    def hasUnsavedChanges(self) -> bool:
        return self._has_unsaved_changes

    # --- Encoder Properties ---
    @Property(bool, notify=encoderSettingsChanged)
    def encoderEnabled(self) -> bool:
        return self._encoder_enabled

    @Property(float, notify=encoderSettingsChanged)
    def encoderStepSize(self) -> float:
        return self._encoder_step_size

    @Property(float, notify=encoderSettingsChanged)
    def encoderDeadZone(self) -> float:
        return self._encoder_dead_zone

    @Property(int, notify=encoderSettingsChanged)
    def encoderRepeatIntervalMs(self) -> int:
        return self._encoder_repeat_interval_ms

    @Property(str, notify=encoderDiagnosticsChanged)
    def encoderLiveEdge(self) -> str:
        return self._encoder_live_edge

    @Property(str, notify=encoderDiagnosticsChanged)
    def encoderLiveDirection(self) -> str:
        return self._encoder_live_direction

    @Property(float, notify=encoderDiagnosticsChanged)
    def encoderLiveIncremental(self) -> float:
        return self._encoder_live_incremental

    @Property(float, notify=encoderDiagnosticsChanged)
    def encoderLiveDistance(self) -> float:
        return self._encoder_live_distance

    @Property(int, notify=encoderDiagnosticsChanged)
    def encoderLiveTicks(self) -> int:
        return self._encoder_live_ticks

    @Property(str, notify=encoderDiagnosticsChanged)
    def encoderLiveKey(self) -> str:
        return self._encoder_live_key

    @Property(list, constant=True)
    def knownKeys(self) -> list[dict[str, Any]]:
        return KNOWN_KEYS

    # --- Slots: Service Controls ---

    @Slot()
    def startService(self) -> None:
        ok, msg = self.service_manager.start()
        if ok:
            self._set_message(msg)
        else:
            self._set_error(msg)
        self._poll_status()

    @Slot()
    def stopService(self) -> None:
        ok, msg = self.service_manager.stop()
        if ok:
            self._set_message(msg)
        else:
            self._set_error(msg)
        self._poll_status()

    @Slot()
    def restartService(self) -> None:
        ok, msg = self.service_manager.restart()
        if ok:
            self._set_message(msg)
        else:
            self._set_error(msg)
        self._poll_status()

    @Slot()
    def repairService(self) -> None:
        """Repairs broken or legacy service units and restarts the daemon."""
        ok, msg = self.service_manager.repair_service()
        if ok:
            start_ok, start_msg = self.service_manager.restart()
            if start_ok:
                self._set_message(f"{msg}. Service restarted successfully.")
            else:
                self._set_message(f"{msg}. Restart output: {start_msg}")
        else:
            self._set_error(msg)
        self._poll_status()

    @Slot()
    def reloadConfig(self) -> None:
        """Applies latest configuration via SIGHUP or IPC."""
        if self.ipc_client.is_connected:
            self.ipc_client.request_reload()
        ok, msg = self.service_manager.reload()
        if ok:
            self._set_message(msg)
        else:
            self._set_error(msg)
        self._poll_status()

    @Slot(bool)
    def setMasterEnabled(self, enabled: bool) -> None:
        self._master_enabled = enabled
        for g in self._gesture_rules:
            g["enabled"] = enabled
        for s in self._slider_rules:
            s["enabled"] = enabled
        self._has_unsaved_changes = True
        self.masterEnabledChanged.emit(enabled)
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.swipeRulesChanged.emit()
        self.sliderRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    @Slot(bool)
    def setStartAtLogin(self, enabled: bool) -> None:
        ok, msg = self.service_manager.set_start_at_login(enabled)
        if ok:
            self._start_at_login = enabled
            self.startAtLoginChanged.emit(enabled)
            self._set_message(msg)
        else:
            self._set_error(msg)

    @Slot(str)
    def selectDevice(self, device_path: str) -> None:
        if self._selected_device != device_path:
            self._selected_device = device_path
            self._has_unsaved_changes = True
            self.selectedDeviceChanged.emit(device_path)
            self.hasUnsavedChangesChanged.emit(True)
            self._update_selected_device_details()

    @Slot(bool)
    def setTestMode(self, enabled: bool) -> None:
        self._test_mode = enabled
        self.ipc_client.set_test_mode(enabled)
        self.testModeChanged.emit(enabled)
        self._set_message(f"Test Mode {'enabled' if enabled else 'disabled'}")

    # --- Slots: Configuration Management ---

    @Slot()
    def saveConfiguration(self) -> None:
        """Saves current memory configuration to disk and reloads service."""
        config_dict = {
            "device": self._selected_device,
            "hitbox": copy.deepcopy(self._hitbox_settings),
            "gesture": copy.deepcopy(self._gesture_settings),
            "edge_width": self._hitbox_settings.get("edge_width", 0.12),
            "corner_hitbox": self._hitbox_settings.get("corner_width", 0.15),
            "swipe_min_distance": self._gesture_settings.get("swipe_min_distance", 0.08),
            "swipe_max_drift": self._gesture_settings.get("swipe_max_drift", 0.04),
            "tap_max_movement": self._gesture_settings.get("tap_max_movement", 0.04),
            "tap_min_duration_ms": self._gesture_settings.get("tap_min_duration_ms", 40),
            "tap_max_duration_ms": self._gesture_settings.get("tap_max_duration_ms", 200),
            "double_tap_timeout_ms": self._gesture_settings.get("double_tap_timeout_ms", 300),
            "double_tap_max_distance": self._gesture_settings.get("double_tap_max_distance", 0.08),
            "engine": {
                "min_travel": int(self._gesture_settings.get("swipe_min_distance", 0.08) * 2905.0),
                "max_drift": int(self._gesture_settings.get("swipe_max_drift", 0.04) * 2905.0),
                "cooldown_ms": self._gesture_settings.get("cooldown_ms", 250),
                "tap_max_duration_ms": self._gesture_settings.get("tap_max_duration_ms", 200),
                "tap_max_movement": int(self._gesture_settings.get("tap_max_movement", 0.04) * 2905.0),
            },
            "encoder": {
                "enabled": self._encoder_enabled,
                "step_size": self._encoder_step_size,
                "dead_zone": self._encoder_dead_zone,
                "repeat_interval_ms": self._encoder_repeat_interval_ms,
            },
            "gestures": self._gesture_rules,
            "sliders": self._slider_rules,
        }

        ok, msg = self.config_manager.save_config(config_dict)
        if not ok:
            self._set_error(msg)
            return

        self._has_unsaved_changes = False
        self.hasUnsavedChangesChanged.emit(False)
        self._set_message("Settings saved. Applying to gesture engine...")

        # Reload or restart daemon if running
        if self._daemon_status == "running":
            self.reloadConfig()
        else:
            self._set_message("Settings saved successfully")

    @Slot()
    def resetToDefaults(self) -> None:
        """Resets to default preset with brightness and volume keys."""
        preset = default_preset_config()
        self._apply_config_to_state(preset)
        self.saveConfiguration()
        self._set_message("Configuration reset to default preset")

    @Slot()
    def applyDefaultPreset(self) -> None:
        """Restores the four brightness/volume key gestures."""
        preset = default_preset_config()
        self._gesture_rules = copy.deepcopy(preset["gestures"])
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.swipeRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message("Default 4-key preset applied (Save to activate)")

    # --- Slots: Rule List Editing ---

    @Slot("QVariantMap")
    def addGestureRule(self, rule: dict[str, Any]) -> None:
        rule_copy = dict(rule)
        if "enabled" not in rule_copy:
            rule_copy["enabled"] = True
        self._gesture_rules.append(rule_copy)
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.swipeRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    @Slot(int, "QVariantMap")
    def updateGestureRule(self, index: int, rule: dict[str, Any]) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules[index] = dict(rule)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int)
    def removeGestureRule(self, index: int) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules.pop(index)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int)
    def duplicateGestureRule(self, index: int) -> None:
        if 0 <= index < len(self._gesture_rules):
            dupe = copy.deepcopy(self._gesture_rules[index])
            dupe["name"] = f"{dupe.get('name', 'Rule')} (Copy)"
            self._gesture_rules.insert(index + 1, dupe)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int, bool)
    def toggleGestureRule(self, index: int, enabled: bool) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules[index]["enabled"] = enabled
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    # --- Slots: Dedicated Tap Actions Management ---

    @Slot("QVariantMap")
    def addTapRule(self, rule: dict[str, Any]) -> None:
        """Adds a tap or double-tap action rule."""
        rule_copy = dict(rule)
        if "enabled" not in rule_copy:
            rule_copy["enabled"] = True
        self._gesture_rules.append(rule_copy)
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.swipeRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message(f"Added tap action '{rule_copy.get('name', 'New Tap Action')}' (Save Changes to activate)")

    def _resolve_tap_index(self, index: int) -> int:
        """Resolves index to the index within _gesture_rules, whether passed as global or tap-filtered index."""
        if 0 <= index < len(self._gesture_rules) and self._gesture_rules[index].get("direction") in ("tap", "double-tap"):
            return index
        taps = self.tapRules
        if 0 <= index < len(taps):
            return int(taps[index]["originalIndex"])
        return -1

    @Slot(int, "QVariantMap")
    def updateTapRule(self, index: int, rule: dict[str, Any]) -> None:
        """Updates the tap rule at the specified underlying gesture index."""
        idx = self._resolve_tap_index(index)
        if 0 <= idx < len(self._gesture_rules):
            self._gesture_rules[idx] = dict(rule)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)
            self._set_message(f"Updated tap action '{rule.get('name', 'Tap Action')}' (Save Changes to activate)")

    @Slot(int)
    def removeTapRule(self, index: int) -> None:
        """Removes the tap rule at the specified underlying gesture index."""
        idx = self._resolve_tap_index(index)
        if 0 <= idx < len(self._gesture_rules):
            popped = self._gesture_rules.pop(idx)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)
            self._set_message(f"Removed tap action '{popped.get('name', 'Tap Action')}' (Save Changes to activate)")

    @Slot(int, bool)
    def toggleTapRule(self, index: int, enabled: bool) -> None:
        """Toggles the enabled status of a tap rule."""
        idx = self._resolve_tap_index(index)
        if 0 <= idx < len(self._gesture_rules):
            self._gesture_rules[idx]["enabled"] = enabled
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int)
    def duplicateTapRule(self, index: int) -> None:
        """Duplicates a tap rule."""
        idx = self._resolve_tap_index(index)
        if 0 <= idx < len(self._gesture_rules):
            dupe = copy.deepcopy(self._gesture_rules[idx])
            dupe["name"] = f"{dupe.get('name', 'Tap Action')} (Copy)"
            self._gesture_rules.insert(idx + 1, dupe)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.tapRulesChanged.emit()
            self.swipeRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)
            self._set_message("Tap action duplicated (Save Changes to activate)")

    @Slot()
    def resetTapActionsToDefaults(self) -> None:
        """Restores the recommended default tap actions for Left, Right, and Top zones."""
        swipes = [g for g in self._gesture_rules if g.get("direction") not in ("tap", "double-tap")]
        taps = default_tap_actions()
        self._gesture_rules = swipes + taps
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.swipeRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message("Default tap actions restored (Save Changes to activate)")

    # --- Slots: Dedicated Corner Double-Tap Actions Management ---

    @Slot(str, result="QVariantMap")
    def getCornerRule(self, corner_zone: str) -> dict[str, Any]:
        rules = self.cornerTapRules
        return rules.get(corner_zone.lower(), {})

    @Slot(str, "QVariantList")
    @Slot(str, "QVariantList", str)
    def setCornerShortcut(self, corner_zone: str, keys: list[str], name: str = "") -> None:
        """Sets or updates the double-tap shortcut for a specific touchpad corner."""
        zone = corner_zone.strip().lower()
        if zone not in VALID_CORNER_ZONES:
            self._set_error(f"Invalid corner zone '{zone}'")
            return

        normalized_keys = normalize_shortcut_keys([str(k) for k in keys])
        if not normalized_keys:
            self._set_error("Shortcut combination cannot be empty")
            return

        corner_labels = {
            "top-left": "Top-Left Corner",
            "top-right": "Top-Right Corner",
            "bottom-left": "Bottom-Left Corner",
            "bottom-right": "Bottom-Right Corner",
        }
        rule_name = name.strip() or f"{corner_labels.get(zone, zone.capitalize())} Double Tap"

        existing_idx = None
        for idx, g in enumerate(self._gesture_rules):
            edge = str(g.get("edge") or g.get("zone") or "").lower()
            if edge == zone and g.get("direction") == "double-tap":
                existing_idx = idx
                break

        rule_data = {
            "name": rule_name,
            "enabled": True,
            "edge": zone,
            "direction": "double-tap",
            "keys": normalized_keys,
            "action": {"type": "shortcut", "keys": normalized_keys},
        }

        if existing_idx is not None:
            self._gesture_rules[existing_idx] = rule_data
        else:
            self._gesture_rules.append(rule_data)

        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        display = format_shortcut(normalized_keys)
        self._set_message(f"Assigned '{display}' to {corner_labels.get(zone, zone)} (Save Changes to activate)")

    @Slot(str)
    def clearCornerShortcut(self, corner_zone: str) -> None:
        """Clears/removes the shortcut for a corner zone."""
        zone = corner_zone.strip().lower()
        self._gesture_rules = [
            g for g in self._gesture_rules
            if not (str(g.get("edge") or g.get("zone") or "").lower() == zone and g.get("direction") == "double-tap")
        ]
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message(f"Cleared shortcut for {zone} (Save Changes to activate)")

    @Slot(str, bool)
    def toggleCornerRule(self, corner_zone: str, enabled: bool) -> None:
        """Toggles enabled state of a corner double-tap rule."""
        zone = corner_zone.strip().lower()
        for g in self._gesture_rules:
            edge = str(g.get("edge") or g.get("zone") or "").lower()
            if edge == zone and g.get("direction") == "double-tap":
                g["enabled"] = enabled
                break
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.tapRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    @Slot()
    def resetCornerRulesToDefaults(self) -> None:
        """Restores default corner double-tap actions."""
        non_corners = [
            g for g in self._gesture_rules
            if not (str(g.get("edge") or g.get("zone") or "").lower() in VALID_CORNER_ZONES and g.get("direction") == "double-tap")
        ]
        defaults = default_corner_tap_actions()
        self._gesture_rules = non_corners + defaults
        self._corner_hitbox = 0.15
        self._hitbox_settings["corner_width"] = 0.15
        self._hitbox_settings["corner_height"] = 0.15
        self.hitboxSettingsChanged.emit()
        self._has_unsaved_changes = True
        self.gestureRulesChanged.emit()
        self.cornerTapRulesChanged.emit()
        self.cornerHitboxChanged.emit(self._corner_hitbox)
        self.tapRulesChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message("Default corner double-tap actions restored (Save Changes to activate)")

    @Slot(float)
    def setCornerHitbox(self, val: float) -> None:
        """Updates the corner double-tap hitbox size (clamped 0.05 to 0.35)."""
        clamped = max(0.05, min(0.35, round(float(val), 2)))
        if abs(self._corner_hitbox - clamped) > 0.001:
            self._corner_hitbox = clamped
            self._hitbox_settings["corner_width"] = clamped
            self._hitbox_settings["corner_height"] = clamped
            self.hitboxSettingsChanged.emit()
            self.cornerHitboxChanged.emit(self._corner_hitbox)
            self._has_unsaved_changes = True
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(float)
    def setEdgeSwipeWidth(self, val: float) -> None:
        """Updates the edge swipe zone thickness (clamped 0.04 to 0.30)."""
        clamped = max(0.04, min(0.30, round(float(val), 2)))
        self._hitbox_settings["edge_width"] = clamped
        self._hitbox_settings["left_edge_width"] = clamped
        self._hitbox_settings["right_edge_width"] = clamped
        self._hitbox_settings["top_edge_height"] = clamped
        self._hitbox_settings["bottom_edge_height"] = clamped
        self.hitboxSettingsChanged.emit()
        self._has_unsaved_changes = True
        self.hasUnsavedChangesChanged.emit(True)

    # --- Slots: Keyboard Shortcut Recorder ---

    def _on_recording_timeout(self) -> None:
        if self._is_recording:
            self._is_recording = False
            self.shortcutRecordingStateChanged.emit()
            self._set_message("Shortcut recording timed out safely")

    @Slot(str)
    def startShortcutRecording(self, target: str) -> None:
        """Puts the GUI into explicit shortcut recording mode for a corner or swipe gesture."""
        self._recording_corner = target.strip().lower()
        self._recording_keys = []
        self._recording_display = "Press key combination..."
        self._is_recording = True
        self._ignoring_initial_key = True
        self._prev_test_mode = self.testMode
        # Temporary test mode so touch interactions don't trigger real system actions while recording keys
        self.ipc_client.set_test_mode(True)
        self._recording_timer.start()
        self.shortcutRecordingStateChanged.emit()
        self.recordingActiveChanged.emit(True)

    @Slot(int, int, str, result="QVariantMap")
    @Slot(int, int, result="QVariantMap")
    def processRecordedKey(self, qt_key: int, qt_modifiers: int, key_text: str = "") -> dict[str, Any]:
        """Processes a keyboard event during recording mode, updating captured keys."""
        if not self._is_recording:
            return {"keys": [], "display": "None", "valid": False}

        # Safely ignore activation key (Space or Return) if just entered recording mode via keyboard
        if self._ignoring_initial_key:
            if qt_key in (0x20, 0x01000004, 0x01000005) and (qt_modifiers == 0):
                self._ignoring_initial_key = False
                return {"keys": self._recording_keys, "display": self._recording_display, "valid": len(self._recording_keys) > 0}
            self._ignoring_initial_key = False

        normalized, display = parse_qt_key_event(qt_key, qt_modifiers)
        if normalized:
            self._recording_keys = normalized
            self._recording_display = display
            self._recording_timer.start()
            self.shortcutRecordingStateChanged.emit()

        return {
            "keys": self._recording_keys,
            "display": self._recording_display,
            "valid": len(self._recording_keys) > 0,
        }

    @Slot()
    def confirmRecordedShortcut(self) -> None:
        """Confirms and saves the currently recorded combination to corner or swipe."""
        if not self._is_recording:
            return
        target = self._recording_corner
        keys = list(self._recording_keys)
        display = self._recording_display
        self.cancelShortcutRecording()
        if target == "swipe":
            self.swipeShortcutRecorded.emit(keys, display)
            self._set_message(f"Recorded swipe shortcut: {display}")
        elif target in ("top-left", "top-right", "bottom-left", "bottom-right") and keys:
            self.setCornerShortcut(target, keys)
            self._set_message(f"Updated {target} shortcut: {display}")

    @Slot()
    def cancelShortcutRecording(self) -> None:
        """Safely exits shortcut recording mode, restoring prior daemon test mode state."""
        if not self._is_recording:
            return
        self._recording_timer.stop()
        self._is_recording = False
        self._recording_corner = ""
        self._recording_keys = []
        self._recording_display = "None"
        self._ignoring_initial_key = False
        self.ipc_client.set_test_mode(self._prev_test_mode)
        self.shortcutRecordingStateChanged.emit()
        self.recordingActiveChanged.emit(False)

    @Slot()
    def clearRecordedShortcut(self) -> None:
        """Clears the currently recorded keys in recording mode."""
        self._recording_keys = []
        self._recording_display = "Press key combination..."
        self.shortcutRecordingStateChanged.emit()

    @Slot("QVariantList")
    def setRecordedShortcut(self, keys: list[str]) -> None:
        """Sets the recorded shortcut keys directly from preset or manual action."""
        normalized = normalize_shortcut_keys([str(k) for k in keys])
        if normalized:
            self._recording_keys = normalized
            self._recording_display = format_shortcut(normalized)
            self._recording_timer.start()
            self.shortcutRecordingStateChanged.emit()

    @Slot(str, result=bool)
    def hasRecordedKey(self, key_name: str) -> bool:
        """Checks if a key or modifier is currently in the recorded combination."""
        upper = key_name.strip().upper()
        if upper in ("CTRL", "KEY_LEFTCTRL", "KEY_RIGHTCTRL"):
            return "KEY_LEFTCTRL" in self._recording_keys or "KEY_RIGHTCTRL" in self._recording_keys
        if upper in ("ALT", "KEY_LEFTALT", "KEY_RIGHTALT"):
            return "KEY_LEFTALT" in self._recording_keys or "KEY_RIGHTALT" in self._recording_keys
        if upper in ("SHIFT", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
            return "KEY_LEFTSHIFT" in self._recording_keys or "KEY_RIGHTSHIFT" in self._recording_keys
        if upper in ("SUPER", "META", "KEY_LEFTMETA", "KEY_RIGHTMETA"):
            return "KEY_LEFTMETA" in self._recording_keys or "KEY_RIGHTMETA" in self._recording_keys
        canonical = upper if upper.startswith("KEY_") else f"KEY_{upper}"
        return canonical in self._recording_keys

    @Slot(str)
    def toggleRecordedModifier(self, mod_name: str) -> None:
        """Toggles a modifier key (Ctrl, Alt, Shift, Meta) in the recorded combination."""
        upper = mod_name.strip().upper()
        target = "KEY_LEFTCTRL"
        alt_target = "KEY_RIGHTCTRL"
        if upper in ("ALT", "KEY_LEFTALT", "KEY_RIGHTALT"):
            target, alt_target = "KEY_LEFTALT", "KEY_RIGHTALT"
        elif upper in ("SHIFT", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"):
            target, alt_target = "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT"
        elif upper in ("SUPER", "META", "KEY_LEFTMETA", "KEY_RIGHTMETA"):
            target, alt_target = "KEY_LEFTMETA", "KEY_RIGHTMETA"

        current = list(self._recording_keys)
        if target in current or alt_target in current:
            current = [k for k in current if k not in (target, alt_target)]
        else:
            current.append(target)
        normalized = normalize_shortcut_keys(current)
        self._recording_keys = normalized
        self._recording_display = format_shortcut(normalized) if normalized else "Press key combination..."
        self._recording_timer.start()
        self.shortcutRecordingStateChanged.emit()

    @Slot(str)
    def setRecordedPrimaryKey(self, key_name: str) -> None:
        """Sets or replaces the primary non-modifier key in the recorded combination."""
        upper = key_name.strip().upper()
        canonical = upper if upper.startswith("KEY_") else f"KEY_{upper}"
        code = get_key_code(canonical)
        if code is None:
            code = get_key_code(key_name)
        if code is not None:
            key_item = next((k for k in KNOWN_KEYS if k["code"] == code), None)
            if key_item:
                canonical = key_item["name"]

        mods = [
            k for k in self._recording_keys
            if k in ("KEY_LEFTCTRL", "KEY_RIGHTCTRL", "KEY_LEFTALT", "KEY_RIGHTALT", "KEY_LEFTSHIFT", "KEY_RIGHTSHIFT", "KEY_LEFTMETA", "KEY_RIGHTMETA")
        ]
        if canonical and canonical not in mods:
            mods.append(canonical)
        normalized = normalize_shortcut_keys(mods)
        self._recording_keys = normalized
        self._recording_display = format_shortcut(normalized)
        self._recording_timer.start()
        self.shortcutRecordingStateChanged.emit()

    @Slot("QVariantList", result=str)
    @Slot(str, result=str)
    def formatShortcut(self, keys: Any) -> str:
        """Formats a list of key names into a user-friendly combination string."""
        if isinstance(keys, list):
            return format_shortcut([str(k) for k in keys])
        if isinstance(keys, str):
            return format_shortcut([keys]) if keys else "None"
        return "None"

    # --- Slots: Command Validation & Workspace Helpers ---

    @Slot(str, str, result="QVariantMap")
    @Slot("QVariantList", result="QVariantMap")
    def validateCommand(self, executable: Any, args_str: str = "") -> dict[str, Any]:
        """Validates command syntax, checks executable presence in PATH, and splits arguments safely."""
        if isinstance(executable, list):
            if not executable:
                return {"valid": False, "error": "Executable path cannot be empty", "argv": [], "resolved": ""}
            prog = str(executable[0]).strip()
            args = [str(x) for x in executable[1:]]
        else:
            prog = str(executable).strip()
            if not prog:
                return {"valid": False, "error": "Executable path cannot be empty", "argv": [], "resolved": ""}
            try:
                args = shlex.split(args_str.strip()) if args_str.strip() else []
            except Exception as e:
                return {"valid": False, "error": f"Invalid arguments format: {e}", "argv": [], "resolved": ""}

        argv = [prog] + args
        resolved = shutil.which(prog)
        if resolved:
            return {"valid": True, "error": "", "argv": argv, "resolved": resolved}
        if os.path.isabs(prog) and os.path.exists(prog) and os.access(prog, os.X_OK):
            return {"valid": True, "error": "", "argv": argv, "resolved": prog}
        return {
            "valid": False,
            "error": f"Executable '{prog}' not found in PATH or not executable",
            "argv": argv,
            "resolved": "",
        }

    @Slot("QVariantMap", int, result="QVariantMap")
    def validateGestureRule(self, rule: dict[str, Any], edit_index: int = -1) -> dict[str, Any]:
        """Performs comprehensive pre-save validation for a single gesture rule."""
        edge = str(rule.get("edge", "")).lower()
        direction = str(rule.get("direction", "")).lower()
        if edge not in VALID_ZONES:
            return {"valid": False, "error": f"Invalid edge zone '{edge}'"}
        if direction not in VALID_DIRECTIONS:
            return {"valid": False, "error": f"Invalid gesture direction '{direction}'"}

        # Conflict check with existing enabled rules
        for idx, existing in enumerate(self._gesture_rules):
            if idx == edit_index or not existing.get("enabled", True):
                continue
            ex_edge = str(existing.get("edge", "")).lower()
            ex_dir = str(existing.get("direction", "")).lower()
            if ex_edge == edge and ex_dir == direction:
                dir_label = "Single Tap" if direction == "tap" else ("Double Tap" if direction == "double-tap" else f"Swipe {direction.capitalize()}")
                return {"valid": False, "error": f"Conflicting gesture already enabled on {edge.capitalize()} edge ({dir_label})"}

        # Slider conflict check: swipes conflict, taps are allowed
        enabled_slider_zones = {
            str(s.get("zone") or s.get("edge") or "").lower()
            for s in self._slider_rules
            if s.get("enabled", True)
        }
        if edge in enabled_slider_zones and direction in VALID_SWIPE_DIRECTIONS:
            return {"valid": False, "error": f"Directional swipe on {edge.capitalize()} edge conflicts with active slider"}

        # Action validation
        act = rule.get("action", {})
        act_type = act.get("type", "key")
        if act_type == "key":
            k = str(act.get("key", "")).strip()
            if not k:
                return {"valid": False, "error": "Keyboard key cannot be empty"}
        elif act_type == "command":
            argv = act.get("argv", [])
            if not argv or not argv[0].strip():
                return {"valid": False, "error": "Command executable cannot be empty"}
            cmd_check = self.validateCommand(argv[0], " ".join(argv[1:]))
            if not cmd_check["valid"]:
                return cmd_check
        elif act_type == "media":
            media_act = act.get("media_action", "play_pause")
            if media_act not in MEDIA_ACTION_KEYS:
                return {"valid": False, "error": f"Unsupported media action '{media_act}'"}
        elif act_type == "workspace":
            ws_act = act.get("workspace_action", "next")
            if ws_act not in ("next", "previous"):
                return {"valid": False, "error": f"Unsupported workspace direction '{ws_act}'"}

        return {"valid": True, "error": ""}

    @Slot(str, result="QVariantMap")
    def getMediaAction(self, media_type: str) -> dict[str, Any]:
        """Returns standard media key definition dictionary."""
        key = MEDIA_ACTION_KEYS.get(media_type, "KEY_PLAYPAUSE")
        return {
            "type": "media",
            "media_action": media_type,
            "key": key,
            "repeat": 1,
        }

    @Slot(str, result="QVariantMap")
    def getWorkspaceAction(self, direction: str) -> dict[str, Any]:
        """Returns standard workspace action dictionary."""
        cmd = get_default_workspace_command(direction)
        return {
            "type": "workspace",
            "workspace_action": direction,
            "argv": cmd,
            "key": "",
        }

    @Slot("QVariantMap")
    @Slot(str, str, str, str, str)
    def testGestureAction(
        self,
        rule_or_edge: Any,
        direction: str = "",
        act_type: str = "key",
        key_val: str = "",
        name: str = "",
    ) -> None:
        """Safely simulates or tests triggering the given action in Test Mode."""
        if isinstance(rule_or_edge, dict):
            rule = rule_or_edge
            edge = str(rule.get("edge", "top")).lower()
            direction = str(rule.get("direction", "tap")).lower()
            action = rule.get("action", {})
            name = rule.get("name") or f"{edge.capitalize()} {direction}"
        else:
            edge = str(rule_or_edge).lower()
            direction = str(direction).lower()
            action = {"type": act_type}
            if act_type == "media":
                action["media_action"] = "mute" if "MUTE" in key_val else "play_pause"
                action["key"] = key_val
            elif act_type == "key":
                action["key"] = key_val
            elif act_type == "command":
                action["argv"] = [key_val]
            rule = {"edge": edge, "direction": direction, "action": action, "name": name}

        # Debounce: prevent duplicate test execution within 250ms
        import time as _time
        now_ts = _time.time()
        if hasattr(self, "_last_test_trigger_time") and (now_ts - self._last_test_trigger_time) < 0.25:
            if getattr(self, "_last_test_trigger_key", "") == f"{edge}:{direction}":
                return
        self._last_test_trigger_time = now_ts
        self._last_test_trigger_key = f"{edge}:{direction}"

        act_type = action.get("type", "key")
        name = rule.get("name") or f"{edge.capitalize()} {direction}"

        key_name = ""
        action_str = ""
        if act_type == "key":
            key_name = action.get("key", "KEY_RESERVED")
            action_str = f"Key: {key_name}"
        elif act_type == "media":
            media_key = action.get("key") or MEDIA_ACTION_KEYS.get(action.get("media_action", "play_pause"), "KEY_PLAYPAUSE")
            key_name = media_key
            label = MEDIA_ACTION_LABELS.get(action.get("media_action", "play_pause"), "Play / Pause")
            action_str = f"Media: {label} ({media_key})"
        elif act_type == "command":
            argv = action.get("argv", [])
            action_str = f"Command: {' '.join(argv)}"
        elif act_type == "shortcut" or "keys" in action or ("keys" in rule and rule["keys"]):
            keys = action.get("keys") or rule.get("keys", [])
            display = format_shortcut(keys)
            action_str = f"Shortcut: {display}"
        elif act_type == "workspace":
            ws_act = action.get("workspace_action", "next")
            action_str = f"Workspace: {'Next Desktop' if ws_act == 'next' else 'Previous Desktop'}"
        elif act_type == "none":
            action_str = "No Action (Disabled)"
        else:
            action_str = "Log Event"

        self._last_gesture = {
            "event": "gesture",
            "zone": edge,
            "direction": direction,
            "action_type": act_type,
            "action": action_str,
            "key": key_name,
            "success": True,
            "test_mode": True,
            "is_simulated": True,
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        self.lastGestureChanged.emit()
        self._set_message(f"Simulated {name} -> {action_str} (Safe Test Mode)")

    @Slot(float, float, float, float, float, float)
    def updateHitboxSettings(
        self,
        left: float,
        right: float,
        top: float,
        bottom: float,
        corner_w: float,
        corner_h: float,
    ) -> None:
        """Updates only physical hitbox detection geometry without altering gesture sensitivity."""
        self._hitbox_settings = {
            "edge_width": (left + right + top + bottom) / 4.0,
            "left_edge_width": left,
            "right_edge_width": right,
            "top_edge_height": top,
            "bottom_edge_height": bottom,
            "corner_width": corner_w,
            "corner_height": corner_h,
        }
        self._corner_hitbox = corner_w
        self._has_unsaved_changes = True
        self.hitboxSettingsChanged.emit()
        self.cornerHitboxChanged.emit(self._corner_hitbox)
        self.edgeSettingsChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    @Slot()
    def applyHitboxCalibration(self) -> None:
        """Applies and saves hitbox calibration to running daemon without touching gestures."""
        self.saveConfiguration()
        self._set_message("Hitbox calibration applied successfully")

    @Slot()
    def restoreHitboxDefaults(self) -> None:
        """Restores hitbox calibration to defaults without modifying gesture sensitivity."""
        self._hitbox_settings = copy.deepcopy(DEFAULT_HITBOX_CONFIG)
        self._corner_hitbox = DEFAULT_HITBOX_CONFIG["corner_width"]
        self._has_unsaved_changes = True
        self.hitboxSettingsChanged.emit()
        self.cornerHitboxChanged.emit(self._corner_hitbox)
        self.edgeSettingsChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message("Hitbox calibration restored to defaults (unsaved)")

    @Slot(float, float, float, int, int, int, float, int)
    def updateGestureSettings(
        self,
        swipe_min_dist: float,
        swipe_max_drift: float,
        tap_max_mov: float,
        tap_min_dur: int,
        tap_max_dur: int,
        dbl_tap_timeout: int,
        dbl_tap_max_dist: float,
        cooldown_ms: int,
    ) -> None:
        """Updates only gesture recognition thresholds without altering hitbox detection geometry."""
        self._gesture_settings = {
            "swipe_min_distance": swipe_min_dist,
            "swipe_max_drift": swipe_max_drift,
            "tap_max_movement": tap_max_mov,
            "tap_min_duration_ms": tap_min_dur,
            "tap_max_duration_ms": tap_max_dur,
            "double_tap_timeout_ms": dbl_tap_timeout,
            "double_tap_max_distance": dbl_tap_max_dist,
            "cooldown_ms": cooldown_ms,
        }
        self._has_unsaved_changes = True
        self.gestureSettingsChanged.emit()
        self.edgeSettingsChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    @Slot()
    def applyGestureCalibration(self) -> None:
        """Applies and saves gesture calibration to running daemon without touching hitboxes."""
        self.saveConfiguration()
        self._set_message("Gesture calibration applied successfully")

    @Slot()
    def restoreGestureDefaults(self) -> None:
        """Restores gesture calibration to defaults without modifying hitbox geometry."""
        self._gesture_settings = copy.deepcopy(DEFAULT_GESTURE_CONFIG)
        self._has_unsaved_changes = True
        self.gestureSettingsChanged.emit()
        self.edgeSettingsChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)
        self._set_message("Gesture calibration restored to defaults (unsaved)")

    @Slot(float, int, int, int, int, int)
    def updateEdgeSettings(
        self,
        edge_width: float,
        min_travel: int,
        max_drift: int,
        cooldown_ms: int,
        tap_duration: int,
        tap_movement: int,
    ) -> None:
        # Legacy compatibility slot
        self._hitbox_settings["edge_width"] = edge_width
        self._hitbox_settings["left_edge_width"] = edge_width
        self._hitbox_settings["right_edge_width"] = edge_width
        self._hitbox_settings["top_edge_height"] = edge_width
        self._hitbox_settings["bottom_edge_height"] = edge_width

        self._gesture_settings["swipe_min_distance"] = min_travel / 2905.0 if min_travel > 1.0 else min_travel
        self._gesture_settings["swipe_max_drift"] = max_drift / 2905.0 if max_drift > 1.0 else max_drift
        self._gesture_settings["cooldown_ms"] = cooldown_ms
        self._gesture_settings["tap_max_duration_ms"] = tap_duration
        self._gesture_settings["tap_max_movement"] = tap_movement / 2905.0 if tap_movement > 1.0 else tap_movement

        self._edge_settings = {
            "edge_width": edge_width,
            "min_travel": min_travel,
            "max_drift": max_drift,
            "cooldown_ms": cooldown_ms,
            "tap_max_duration_ms": tap_duration,
            "tap_max_movement": tap_movement,
        }
        self._has_unsaved_changes = True
        self.hitboxSettingsChanged.emit()
        self.gestureSettingsChanged.emit()
        self.edgeSettingsChanged.emit()
        self.hasUnsavedChangesChanged.emit(True)

    # --- Slots: Testing & Diagnostics ---

    @Slot(str)
    def testKeyAction(self, key_name: str) -> None:
        """Safely simulates or tests emitting a key action."""
        # Simulated gesture event on the test screen
        self._last_gesture = {
            "event": "gesture",
            "zone": "manual_test",
            "direction": "press",
            "action_type": "key",
            "key": key_name,
            "success": True,
            "test_mode": True,
            "time": datetime.datetime.now().strftime("%H:%M:%S"),
        }
        self.lastGestureChanged.emit()
        self._set_message(f"Key test triggered for {key_name}")

    @Slot()
    def refreshDevices(self) -> None:
        self._touchpads = self.device_manager.get_touchpads()
        self.touchpadsChanged.emit()
        self._update_selected_device_details()

    @Slot()
    def refreshDoctor(self) -> None:
        self._doctor_report = self.diagnostics_manager.run_doctor()
        self.doctorReportChanged.emit()

    @Slot()
    def refreshLogs(self) -> None:
        self._service_logs = self.service_manager.get_recent_logs(50)
        self.serviceLogsChanged.emit()

    @Slot()
    def refreshAll(self) -> None:
        self.refreshDevices()
        self._poll_status()
        self.refreshDoctor()
        self.refreshLogs()
        self._set_message("Status and diagnostics refreshed")

    @Slot(str)
    def exportDiagnostics(self, file_path: str) -> None:
        report_text = self.diagnostics_manager.generate_full_report(
            config_dict=self.config_manager.current_config,
            service_status=self._daemon_status,
            service_logs=self.service_logs,
            selected_device=self._selected_device_details,
        )
        try:
            clean_path = file_path.replace("file://", "")
            Path(clean_path).write_text(report_text, encoding="utf-8")
            self._set_message(f"Report exported to {clean_path}")
        except Exception as e:
            self._set_error(f"Failed to export report: {e}")

    @Slot(str)
    def exportConfig(self, file_path: str) -> None:
        clean_path = file_path.replace("file://", "")
        ok, msg = self.config_manager.export_config(clean_path)
        if ok:
            self._set_message(msg)
        else:
            self._set_error(msg)

    @Slot(str)
    def importConfig(self, file_path: str) -> None:
        clean_path = file_path.replace("file://", "")
        ok, msg = self.config_manager.import_config(clean_path)
        if ok:
            cfg, _ = self.config_manager.load_config()
            self._apply_config_to_state(cfg)
            self._set_message(msg)
            if self._daemon_status == "running":
                self.reloadConfig()
        else:
            self._set_error(msg)

    @Slot(str, result=list)
    def filterKeys(self, query: str) -> list[dict[str, Any]]:
        return search_keys(query)

    # --- Encoder Slots ---

    @Slot(bool)
    def setEncoderEnabled(self, enabled: bool) -> None:
        if self._encoder_enabled != enabled:
            self._encoder_enabled = enabled
            self._has_unsaved_changes = True
            self.hasUnsavedChangesChanged.emit(True)
            self.encoderSettingsChanged.emit()

    @Slot(float)
    def setEncoderStepSize(self, step_size: float) -> None:
        step_size = max(5.0, min(500.0, float(step_size)))
        if abs(self._encoder_step_size - step_size) > 0.01:
            self._encoder_step_size = step_size
            self._has_unsaved_changes = True
            self.hasUnsavedChangesChanged.emit(True)
            self.encoderSettingsChanged.emit()

    @Slot(float)
    def setEncoderDeadZone(self, dead_zone: float) -> None:
        dead_zone = max(0.0, min(100.0, float(dead_zone)))
        if abs(self._encoder_dead_zone - dead_zone) > 0.01:
            self._encoder_dead_zone = dead_zone
            self._has_unsaved_changes = True
            self.hasUnsavedChangesChanged.emit(True)
            self.encoderSettingsChanged.emit()

    @Slot(int)
    def setEncoderRepeatIntervalMs(self, interval_ms: int) -> None:
        interval_ms = max(5, min(200, int(interval_ms)))
        if self._encoder_repeat_interval_ms != interval_ms:
            self._encoder_repeat_interval_ms = interval_ms
            self._has_unsaved_changes = True
            self.hasUnsavedChangesChanged.emit(True)
            self.encoderSettingsChanged.emit()

    @Slot()
    def restoreEncoderDefaults(self) -> None:
        self._encoder_enabled = True
        self._encoder_step_size = 50.0
        self._encoder_dead_zone = 10.0
        self._encoder_repeat_interval_ms = 20
        self._has_unsaved_changes = True
        self.hasUnsavedChangesChanged.emit(True)
        self.encoderSettingsChanged.emit()

    @Slot()
    def resetEncoderDiagnostics(self) -> None:
        self._encoder_live_edge = "None"
        self._encoder_live_direction = "None"
        self._encoder_live_incremental = 0.0
        self._encoder_live_distance = 0.0
        self._encoder_live_ticks = 0
        self._encoder_live_key = ""
        self.encoderDiagnosticsChanged.emit()

    # --- Private Handlers ---

    def _on_ipc_event(self, event_data: dict[str, Any]) -> None:
        """Handles live gesture event sent by daemon IPC."""
        # Prevent duplicate input event spam within 100ms
        import time as _time
        now_ts = _time.time()
        event_sig = (
            event_data.get("event"),
            event_data.get("zone"),
            event_data.get("direction"),
            event_data.get("action"),
            event_data.get("key"),
        )
        if (
            hasattr(self, "_last_ipc_event_time")
            and (now_ts - self._last_ipc_event_time) < 0.1
            and getattr(self, "_last_ipc_event_sig", None) == event_sig
        ):
            return
        self._last_ipc_event_time = now_ts
        self._last_ipc_event_sig = event_sig

        event_copy = dict(event_data)
        event_copy["is_simulated"] = False
        event_copy["time"] = datetime.datetime.now().strftime("%H:%M:%S")
        self._last_gesture = event_copy
        self.lastGestureChanged.emit()

        evt_type = event_data.get("event")
        if evt_type in ("slider_step", "encoder_tick"):
            zone_str = str(event_data.get("zone", "")).capitalize()
            dir_str = str(event_data.get("direction", "")).capitalize()
            self._encoder_live_edge = zone_str if zone_str else "Edge"
            self._encoder_live_direction = dir_str
            self._encoder_live_incremental = self._encoder_step_size
            self._encoder_live_ticks += 1
            self._encoder_live_distance = round(self._encoder_live_ticks * self._encoder_step_size, 1)
            self._encoder_live_key = str(event_data.get("key", ""))
            self.encoderDiagnosticsChanged.emit()
            if self._encoder_diag_timer:
                self._encoder_diag_timer.start()

    def _on_encoder_diag_timeout(self) -> None:
        # Keep direction and final tick count visible but mark inactive
        self.encoderDiagnosticsChanged.emit()

    def _on_ipc_connection_changed(self, connected: bool) -> None:
        self.connectedToIpcChanged.emit(connected)
