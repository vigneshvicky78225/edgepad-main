"""Central Qt Controller bridging backend services and the QML user interface.

Provides state management, atomic config updates, service control, device selection,
IPC event dispatching, and diagnostics reporting.
"""

from __future__ import annotations

import copy
import datetime
from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QObject, QTimer, Signal, Slot

from gui.backend.config_manager import ConfigManager, default_preset_config
from gui.backend.device_manager import DeviceManager
from gui.backend.diagnostics_manager import DiagnosticsManager
from gui.backend.ipc_client import IpcClient
from gui.backend.key_definitions import KNOWN_KEYS, search_keys
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
    sliderRulesChanged = Signal()
    edgeSettingsChanged = Signal()
    lastGestureChanged = Signal()
    lastErrorChanged = Signal(str)
    lastMessageChanged = Signal(str)
    testModeChanged = Signal(bool)
    connectedToIpcChanged = Signal(bool)
    doctorReportChanged = Signal()
    serviceLogsChanged = Signal()
    hasUnsavedChangesChanged = Signal(bool)
    notificationRequested = Signal(str, str)  # title, message

    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)

        # Backend subsystems
        self.config_manager = ConfigManager()
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
        self._slider_rules: list[dict[str, Any]] = []
        self._edge_settings: dict[str, Any] = {
            "edge_width": 0.12,
            "min_travel": 250,
            "max_drift": 120,
            "cooldown_ms": 250,
            "tap_max_duration_ms": 200,
            "tap_max_movement": 50,
        }
        self._last_gesture: dict[str, Any] = {}
        self._last_error = ""
        self._last_message = ""
        self._test_mode = False
        self._doctor_report: dict[str, Any] = {}
        self._service_logs = ""
        self._has_unsaved_changes = False

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
        self._gesture_rules = copy.deepcopy(cfg.get("gestures", []))
        self._slider_rules = copy.deepcopy(cfg.get("sliders", []))

        # Check if master is enabled (any gestures or sliders enabled)
        has_enabled = any(g.get("enabled", True) for g in self._gesture_rules) or any(
            s.get("enabled", True) for s in self._slider_rules
        )
        self._master_enabled = has_enabled

        engine = cfg.get("engine", {})
        self._edge_settings = {
            "edge_width": float(cfg.get("edge_width", 0.12)),
            "min_travel": int(engine.get("min_travel", 250)),
            "max_drift": int(engine.get("max_drift", 120)),
            "cooldown_ms": int(engine.get("cooldown_ms", 250)),
            "tap_max_duration_ms": int(engine.get("tap_max_duration_ms", 200)),
            "tap_max_movement": int(engine.get("tap_max_movement", 50)),
        }

        self._has_unsaved_changes = False
        self.selectedDeviceChanged.emit(self._selected_device)
        self.gestureRulesChanged.emit()
        self.sliderRulesChanged.emit()
        self.edgeSettingsChanged.emit()
        self.masterEnabledChanged.emit(self._master_enabled)
        self.hasUnsavedChangesChanged.emit(False)
        self._update_selected_device_details()

    def _update_selected_device_details(self) -> None:
        details = self.device_manager.get_selected_touchpad(self._selected_device)
        self._selected_device_details = details or {
            "name": "Auto (Default Touchpad)",
            "path": "/dev/input/event4",
            "id": "auto",
            "x_range": "0..=2905",
            "y_range": "0..=1766",
            "x_max": 2905,
            "y_max": 1766,
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

        new_enabled = self.service_manager.is_enabled()
        if new_enabled != self._start_at_login:
            self._start_at_login = new_enabled
            self.startAtLoginChanged.emit(self._start_at_login)

    def _set_error(self, message: str) -> None:
        self._last_error = message
        self.lastErrorChanged.emit(message)
        self.notificationRequested.emit("Error", message)

    def _set_message(self, message: str) -> None:
        self._last_message = message
        self.lastMessageChanged.emit(message)

    # --- Properties ---

    @Property(str, notify=daemonStatusChanged)
    def daemonStatus(self) -> str:
        return self._daemon_status

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

    @Property(list, notify=sliderRulesChanged)
    def sliderRules(self) -> list[dict[str, Any]]:
        return self._slider_rules

    @Property(dict, notify=edgeSettingsChanged)
    def edgeSettings(self) -> dict[str, Any]:
        return self._edge_settings

    @Property(dict, notify=lastGestureChanged)
    def lastGesture(self) -> dict[str, Any]:
        return self._last_gesture

    @Property(str, notify=lastErrorChanged)
    def lastError(self) -> str:
        return self._last_error

    @Property(str, notify=lastMessageChanged)
    def lastMessage(self) -> str:
        return self._last_message

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
            "edge_width": self._edge_settings.get("edge_width", 0.12),
            "engine": {
                "min_travel": self._edge_settings.get("min_travel", 250),
                "max_drift": self._edge_settings.get("max_drift", 120),
                "cooldown_ms": self._edge_settings.get("cooldown_ms", 250),
                "tap_max_duration_ms": self._edge_settings.get("tap_max_duration_ms", 200),
                "tap_max_movement": self._edge_settings.get("tap_max_movement", 50),
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
        self.hasUnsavedChangesChanged.emit(True)

    @Slot(int, "QVariantMap")
    def updateGestureRule(self, index: int, rule: dict[str, Any]) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules[index] = dict(rule)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int)
    def removeGestureRule(self, index: int) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules.pop(index)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int)
    def duplicateGestureRule(self, index: int) -> None:
        if 0 <= index < len(self._gesture_rules):
            dupe = copy.deepcopy(self._gesture_rules[index])
            dupe["name"] = f"{dupe.get('name', 'Rule')} (Copy)"
            self._gesture_rules.insert(index + 1, dupe)
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

    @Slot(int, bool)
    def toggleGestureRule(self, index: int, enabled: bool) -> None:
        if 0 <= index < len(self._gesture_rules):
            self._gesture_rules[index]["enabled"] = enabled
            self._has_unsaved_changes = True
            self.gestureRulesChanged.emit()
            self.hasUnsavedChangesChanged.emit(True)

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
        self._edge_settings = {
            "edge_width": edge_width,
            "min_travel": min_travel,
            "max_drift": max_drift,
            "cooldown_ms": cooldown_ms,
            "tap_max_duration_ms": tap_duration,
            "tap_max_movement": tap_movement,
        }
        self._has_unsaved_changes = True
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

    # --- Private Handlers ---

    def _on_ipc_event(self, event_data: dict[str, Any]) -> None:
        """Handles live gesture event sent by daemon IPC."""
        event_copy = dict(event_data)
        event_copy["time"] = datetime.datetime.now().strftime("%H:%M:%S")
        self._last_gesture = event_copy
        self.lastGestureChanged.emit()

    def _on_ipc_connection_changed(self, connected: bool) -> None:
        self.connectedToIpcChanged.emit(connected)
