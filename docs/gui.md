# Edgepad GUI — Architecture and User Guide

The Edgepad GUI is a native Linux desktop application built with **Qt 6 and QML** designed specifically for **Fedora KDE Plasma on Wayland** (and other systemd-based Linux desktop environments). It wraps the high-performance Edgepad Rust daemon in a polished graphical settings manager, eliminating the need to manually edit configuration files or run terminal commands for routine operations.

---

## 1. Architectural Overview

```
 ┌───────────────────────────────────────────────────────────────┐
 │                   Edgepad Qt 6 / QML GUI                      │
 │    Dashboard • Gestures • Edge Zones • Touchpad • Diagnostics │
 └───────────────────────▲──────────────────────▲────────────────┘
                         │ Qt Signals/Slots     │ QLocalSocket IPC
                         ▼                      ▼
 ┌───────────────────────────────┐      ┌────────────────────────┐
 │   Python / PySide6 Backend    │      │   Unix Socket Server   │
 │ • ConfigManager (Atomic TOML) │      │   $XDG_RUNTIME_DIR/    │
 │ • ServiceManager (systemd)    │      │   edgepad/edgepad.sock │
 │ • DeviceManager (evdev / sys) │      └───────────▲────────────┘
 │ • DiagnosticsManager (doctor) │                  │ Broadcast JSON
 └───────────────▲───────────────┘                  │ Events
                 │ CLI / Subprocess                 │
                 ▼                                  ▼
 ┌───────────────────────────────────────────────────────────────┐
 │                     Edgepad Rust Daemon                       │
 │  Multi-touch Proxy  •  Gesture Engine  •  Action Dispatcher   │
 └───────────────▲──────────────────────────────────┬────────────┘
                 │ /dev/input/event*                │ /dev/uinput
                 ▼                                  ▼
 ┌───────────────────────────────┐      ┌────────────────────────┐
 │       Physical Touchpad       │      │ Virtual Input Keyboard │
 │      (PIXA3848:01 Touchpad)   │      │ (Physical Keys Emitted)│
 └───────────────────────────────┘      └────────────────────────┘
```

The application is cleanly divided into separate responsibilities:

1. **GUI Application (`gui/`)**:
   - `gui/qml/Main.qml`: Main window with KDE Breeze styling, sidebar navigation, system tray icon, and global notifications.
   - `gui/qml/views/`: 7 modular views (Dashboard, Gestures, Edge Zones, Touchpad Devices, Live Tester, Diagnostics, About).
   - `gui/qml/components/`: Reusable components (`StatusBadge`, `TouchpadCanvas`, `KeySelectorDialog`).
   - `gui/backend/controller.py`: Reactive `EdgepadController` QObject managing memory state and IPC synchronization.
2. **Gesture Engine (`src/`)**:
   - High-throughput multi-touch recognizer that detects swipe gestures on the calibrated outer zones of the trackpad.
   - Passive passthrough ensures that center pointer movement, physical clicks, and two-finger scrolling continue without interruption.
3. **Virtual Keyboard Backend (`src/keyboard.rs`)**:
   - Native `/dev/uinput` virtual device (`edgepad virtual keyboard`).
   - Translates gesture actions into real Linux kernel keycodes (`KEY_BRIGHTNESSUP`, `KEY_BRIGHTNESSDOWN`, `KEY_VOLUMEUP`, `KEY_VOLUMEDOWN`).
   - Auto-releases any pressed keys on contact release, error, or shutdown to prevent stuck keys.
4. **Daemon IPC Server (`src/ipc.rs` & `gui/backend/ipc_client.py`)**:
   - Non-blocking Unix domain socket at `$XDG_RUNTIME_DIR/edgepad/edgepad.sock`.
   - Streams live JSON events to the GUI's Live Tester in real time.
   - Allows toggling Test Mode (simulated action execution) without modifying configuration files.
5. **Configuration Manager (`gui/backend/config_manager.py`)**:
   - Reads, validates, and atomically writes `~/.config/edgepad/edgepad.toml`.
   - Creates timestamped backups in `~/.config/edgepad/backups/`.
   - Manages preset restoration and configuration import/export.
6. **Service Manager (`gui/backend/service_manager.py`)**:
   - Controls the user-level systemd service `edgepad.service` via `systemctl --user`.
   - Manages start-at-login integration and captures journald service logs.

---

## 2. Default Hardware Presets

The application comes pre-configured with the four mandatory hardware control mappings:

| Touchpad Gesture | Physical Keycode | Emitted Linux Key | Hardware Action |
|---|---|---|---|
| **Left Edge, Swipe Up** | `225` | `KEY_BRIGHTNESSUP` | Increase screen brightness |
| **Left Edge, Swipe Down** | `224` | `KEY_BRIGHTNESSDOWN` | Decrease screen brightness |
| **Right Edge, Swipe Up** | `115` | `KEY_VOLUMEUP` | Increase audio volume |
| **Right Edge, Swipe Down** | `114` | `KEY_VOLUMEDOWN` | Decrease audio volume |

These mappings generate genuine keyboard-like input events rather than calling shell utilities like `brightnessctl` or `pactl`, allowing the desktop environment (KDE Plasma, GNOME, etc.) to handle the action natively with on-screen display (OSD) feedback.

---

## 3. Touchpad Hardware Calibration

Initial calibration values for the testing touchpad (`PIXA3848:01 093A:3848 Touchpad`):
- **Input Node**: `/dev/input/event4`
- **X Coordinate Range**: `0..2905`
- **Y Coordinate Range**: `0..1766`
- **Edge Zone Width**: `12%` (~348 units on left and right)
- **Minimum Swipe Distance**: `250 units` (~14% of touchpad height)
- **Max Permitted Drift**: `120 units`
- **Gesture Cooldown**: `250 ms`

---

## 4. Running and Installing

### Launching the GUI
You can launch the GUI using the Edgepad CLI or directly via Python:
```bash
# Using the edgepad binary
edgepad gui

# Or directly via the Python entry point
python3 gui/main.py
```

### Building the RPM Package (Fedora)
The RPM specification file is located at `packaging/edgepad.spec`.
To build an RPM:
```bash
rpmbuild -ba packaging/edgepad.spec
```

### Running Automated Tests
```bash
# Run Rust engine and keyboard tests
cargo test

# Run GUI backend and integration tests
python3 -m unittest tests/test_gui_backend.py -v
```
