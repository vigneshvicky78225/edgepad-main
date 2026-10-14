#!/usr/bin/env python3
"""Main launcher for Edgepad Qt 6 / QML Graphical Settings Interface.

Integrates with KDE Plasma on Wayland via org.kde.desktop style,
system tray icon, and background service management.
"""

from __future__ import annotations

import os
import signal
import sys
from pathlib import Path

# Enable Ctrl+C to terminate cleanly
signal.signal(signal.SIGINT, signal.SIG_DFL)

from PySide6.QtCore import QCoreApplication, QUrl
from PySide6.QtGui import QIcon, QPixmap
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
    app.setDesktopFileName("org.edgepad.Edgepad.desktop")

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

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
