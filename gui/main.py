#!/usr/bin/env python3
"""Main launcher for Edgepad Qt 6 / QML Graphical Settings Interface.

Integrates with KDE Plasma on Wayland via org.kde.desktop style,
system tray icon, and background service management.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
from pathlib import Path

# Disable stale QML disk bytecode caching across builds and updates
os.environ["QML_DISABLE_DISK_CACHE"] = "1"

# Invalidate any lingering legacy on-disk QML bytecode caches
for _cache_name in ("Edgepad", "edgepad", "PySideApp"):
    _cache_dir = Path.home() / ".cache" / _cache_name / "qmlcache"
    if _cache_dir.is_dir():
        try:
            shutil.rmtree(_cache_dir, ignore_errors=True)
        except Exception:
            pass

# Enable Ctrl+C to terminate cleanly
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PySide6.QtCore import QCoreApplication, QEvent, QObject, QUrl
from PySide6.QtGui import QIcon, QKeyEvent, QPixmap
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

# Add repo root to sys.path so imports work whether run from repo or system install
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from gui.backend.controller import EdgepadController


def create_tray_icon(app: QApplication, window, controller: EdgepadController) -> QSystemTrayIcon | None:
    """Creates desktop system tray icon with KDE Plasma-native context menu."""
    if not QSystemTrayIcon.isSystemTrayAvailable():
        return None

    # Load icon from packaging if available, or create fallback pixmap
    icon_candidates = [
        REPO_ROOT / "packaging" / "icons" / "org.edgepad.Edgepad.svg",
        REPO_ROOT / "packaging" / "org.edgepad.Edgepad.svg",
        Path("/usr/share/icons/hicolor/scalable/apps/org.edgepad.Edgepad.svg"),
    ]

    icon = None
    for cand in icon_candidates:
        if cand.exists():
            icon = QIcon(str(cand))
            break

    if icon is None or icon.isNull():
        # Fallback colored pixmap
        pm = QPixmap(32, 32)
        pm.fill(0)
        icon = QIcon.fromTheme("input-touchpad", QIcon(pm))

    tray = QSystemTrayIcon(icon, app)
    tray.setToolTip("Edgepad Touchpad Gesture Manager")

    menu = QMenu()

    action_open = menu.addAction("Open Settings")
    action_open.triggered.connect(lambda: (window.show(), window.raise_(), window.requestActivate()))

    menu.addSeparator()

    action_toggle = menu.addAction("Enable Gestures")
    action_toggle.setCheckable(True)
    action_toggle.setChecked(controller.masterEnabled)
    action_toggle.toggled.connect(controller.setMasterEnabled)

    controller.masterEnabledChanged.connect(lambda enabled: action_toggle.setChecked(enabled))

    action_reload = menu.addAction("Reload Configuration")
    action_reload.triggered.connect(controller.reloadConfig)

    action_restart = menu.addAction("Restart Service")
    action_restart.triggered.connect(controller.restartService)

    menu.addSeparator()

    action_test_mode = menu.addAction("Test Mode (Safe)")
    action_test_mode.setCheckable(True)
    action_test_mode.setChecked(controller.testMode)
    action_test_mode.toggled.connect(controller.setTestMode)

    menu.addSeparator()

    action_quit = menu.addAction("Quit Edgepad GUI")
    action_quit.triggered.connect(app.quit)

    tray.setContextMenu(menu)

    def on_tray_activated(reason: QSystemTrayIcon.ActivationReason):
        if reason in [QSystemTrayIcon.Trigger, QSystemTrayIcon.DoubleClick]:
            if window.isVisible():
                window.hide()
            else:
                window.show()
                window.raise_()
                window.requestActivate()

    tray.activated.connect(on_tray_activated)

    # Tray notifications
    controller.notificationRequested.connect(
        lambda title, msg: tray.showMessage(title, msg, QSystemTrayIcon.Information, 4000)
    )

    tray.show()
    return tray


def main() -> int:
    # Set desktop application metadata
    QCoreApplication.setOrganizationName("Edgepad")
    QCoreApplication.setApplicationName("Edgepad")
    QCoreApplication.setApplicationVersion("0.1.0")

    # Use KDE desktop native controls style
    QQuickStyle.setStyle("org.kde.desktop")

    app = QApplication(sys.argv)
    app.setDesktopFileName("org.edgepad.Edgepad")

    # Controller instance
    controller = EdgepadController()

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(SCRIPT_DIR / "qml"))
    engine.rootContext().setContextProperty("edgepadController", controller)

    qml_file = SCRIPT_DIR / "qml" / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(qml_file)))

    if not engine.rootObjects():
        print(f"Error: Failed to load QML interface from {qml_file}", file=sys.stderr)
        return 1

    main_window = engine.rootObjects()[0]
    tray = create_tray_icon(app, main_window, controller)
    if tray is not None:
        app.setQuitOnLastWindowClosed(False)

    main_window.show()
    main_window.raise_()
    main_window.requestActivate()

    def set_kwin_global_shortcuts_blocked(blocked: bool) -> None:
        """Asks KDE Plasma KGlobalAccel to temporarily block global shortcuts (like Alt+Tab) during recording."""
        try:
            val = "true" if blocked else "false"
            # qdbus-qt6 handles KWin global shortcut inhibition safely without Shiboken binding teardown issues
            subprocess.run(
                ["qdbus-qt6", "org.kde.kglobalaccel", "/kglobalaccel", "org.kde.KGlobalAccel.blockGlobalShortcuts", val],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=1.0,
            )
        except Exception:
            pass

    def on_recording_state_changed(active: bool) -> None:
        try:
            main_window.setKeyboardGrabEnabled(active)
        except Exception:
            pass
        set_kwin_global_shortcuts_blocked(active)

    controller.recordingActiveChanged.connect(on_recording_state_changed)

    try:
        ret = app.exec()
    finally:
        set_kwin_global_shortcuts_blocked(False)
        try:
            controller.ipc_client.stop()
        except Exception:
            pass
    return ret


if __name__ == "__main__":
    os._exit(main())
