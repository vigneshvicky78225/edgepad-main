# Edgepad 🖐️🎛️

[![License: MIT OR Apache-2.0](https://img.shields.io/badge/License-MIT%20OR%20Apache--2.0-blue.svg)](LICENSE-MIT)
[![Rust 2021](https://img.shields.io/badge/Rust-2021%20Edition-orange.svg)](https://www.rust-lang.org/)
[![GUI: Qt 6 / QML](https://img.shields.io/badge/GUI-Qt%206%20%2F%20PySide6-green.svg)](https://www.qt.io/)
[![Platform: Linux / Wayland](https://img.shields.io/badge/Platform-Linux%20%2F%20Wayland-purple.svg)](https://wayland.freedesktop.org/)
[![Packaging: Fedora RPM & Nix](https://img.shields.io/badge/Packaging-Fedora%20RPM%20%2F%20Nix-informational.svg)](packaging/)

**Touchpad edge gestures and hardware rotary-encoder controls for Linux & Wayland.**

Edgepad transforms the unused physical borders of your laptop touchpad into customizable swipe zones for hardware control—such as adjusting display brightness, controlling system audio volume, or managing media and workspaces. The center of your touchpad remains **100% unaffected** for normal pointer movement, physical clicks, tap-to-click, and two-finger scrolling.

Edgepad includes a **high-performance Rust core daemon** and a **native Qt 6 / QML Graphical Settings Interface** designed for modern desktop environments like Fedora KDE Plasma and GNOME on Wayland.

---

## ✨ Features

- 🖥️ **Native Qt 6 / QML Graphical Interface (`edgepad gui`)**
  - Modern dark-themed interface integrated with KDE Plasma and Wayland.
  - System tray icon with quick controls (toggle gestures, reload config, restart service, test mode).
  - 7 specialized views: Dashboard, Gestures, Edge Zones, Touchpad Selection, Live Tester, Diagnostics, and About.
- 🎛️ **Distance-Based Rotary Encoder Emulation**
  - Continuous vertical edge swipes act like a hardware rotary knob or dial.
  - Movement distance determines the number of emitted discrete key ticks.
  - Highly tunable: configure `step_size` (movement per tick), `dead_zone` (jitter filter), and `repeat_interval_ms`.
- ⌨️ **Real Linux Virtual Keyboard (`/dev/uinput`)**
  - Emits native kernel keycodes (`KEY_BRIGHTNESSUP`, `KEY_BRIGHTNESSDOWN`, `KEY_VOLUMEUP`, `KEY_VOLUMEDOWN`).
  - Triggers native desktop on-screen display (OSD) popups directly without sluggish external shell commands (`brightnessctl`, `pactl`, etc.).
  - Guaranteed zero stuck keys: all virtual keys are automatically released on contact lift, cancellation, or shutdown.
- 🛡️ **Non-Intrusive Multi-Touch Proxy**
  - Only touches starting in calibrated outer edge margins are claimed for gestures.
  - Center touches, multi-finger gestures, and physical button presses pass through to the desktop completely untouched.
- 🎯 **Real-Time Live Gesture Tester & IPC**
  - Non-blocking Unix domain socket IPC streaming live touch events, zone recognition, and emitted keys.
  - Built-in safe **Test Mode** to test gestures visually without changing actual system volume or brightness.
- ⚙️ **Robust Configuration & Automatic Backups**
  - Human-readable TOML configuration (`~/.config/edgepad/edgepad.toml`).
  - Automatic timestamped backups on every save (`~/.config/edgepad/backups/`).
  - One-click configuration export, import, and factory reset in the GUI.
- 🩺 **Built-in Diagnostics (`edgepad doctor`)**
  - Verifies device permissions, udev rules, `/dev/uinput` access, systemd service health, and active touchpad configuration.

---

## 🏛️ Architecture

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
 │  Multi-touch Proxy  •  Rotary Encoder  •  Action Dispatcher   │
 └───────────────▲──────────────────────────────────┬────────────┘
                 │ /dev/input/event*                │ /dev/uinput
                 ▼                                  ▼
 ┌───────────────────────────────┐      ┌────────────────────────┐
 │       Physical Touchpad       │      │ Virtual Input Keyboard │
 │      (Kernel Evdev Node)      │      │ (Physical Keys Emitted)│
 └───────────────────────────────┘      └────────────────────────┘
```

---

## 🚀 Default Hardware Mappings

Edgepad comes ready out-of-the-box with standard hardware control mappings:

| Zone / Gesture | Emitted Linux Keycode | Kernel Key Constant | Desktop Action |
|---|---|---|---|
| **Left Edge — Swipe Up** | `225` | `KEY_BRIGHTNESSUP` | Increase screen brightness |
| **Left Edge — Swipe Down** | `224` | `KEY_BRIGHTNESSDOWN` | Decrease screen brightness |
| **Right Edge — Swipe Up** | `115` | `KEY_VOLUMEUP` | Increase audio volume |
| **Right Edge — Swipe Down** | `114` | `KEY_VOLUMEDOWN` | Decrease audio volume |
| **Top Edge — Tap** | Custom / Command | `KEY_PLAYPAUSE` or custom | Play / Pause media |
| **Bottom Edge — Swipe Left / Right** | Custom / Command | Workspace switch or custom | Switch virtual workspaces |

---

## 📦 Installation

### Option 1: Fedora / RHEL RPM Package (Recommended for Fedora KDE)

Build and install a native RPM package using the provided packaging scripts:

```bash
# 1. Install build requirements
sudo dnf install -y cargo rust python3-devel systemd-rpm-macros rpm-build python3-pyside6 libevdev

# 2. Build the RPM package
./packaging/build-rpm.sh

# 3. Install the generated RPM
sudo dnf install -y rpmbuild/RPMS/x86_64/edgepad-*.rpm
```

The RPM automatically registers:
- `/usr/bin/edgepad` and `/usr/share/edgepad/gui/`
- Desktop entry: `org.edgepad.Edgepad.desktop` (searchable in application launcher)
- Systemd user service: `edgepad.service`
- Udev rules: `/usr/lib/udev/rules.d/70-edgepad.rules`

### Option 2: Quick Installer Script

For an automatic user installation on x86_64 Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/vigneshvicky78225/edgepad-main/main/install.sh | sh
```

The installer installs `edgepad` to `~/.local/bin`, sets up udev device permissions, creates the default configuration, and starts the systemd user service.

To preview changes beforehand without modifying files:
```bash
curl -fsSL https://raw.githubusercontent.com/vigneshvicky78225/edgepad-main/main/install.sh | sh -s -- --dry-run
```

### Option 3: Building from Source

Ensure you have Rust (>= 1.70), Python 3, and PySide6 installed:

```bash
# Clone the repository
git clone https://github.com/vigneshvicky78225/edgepad-main.git
cd edgepad-main

# Build the Rust daemon
cargo build --release

# Run tests
cargo test
python3 -m unittest tests/test_gui_backend.py

# Install udev rules for device and /dev/uinput access
sudo cp packaging/70-edgepad.rules /etc/udev/rules.d/
sudo udevadm control --reload-rules && sudo udevadm trigger
```

### Option 4: Nix / NixOS

Follow the [Nix setup guide](docs/nix.md). You can run Edgepad via flakes:
```bash
nix run github:vigneshvicky78225/edgepad-main#edgepad -- gui
```

---

## 🖥️ Using the GUI

Launch the Graphical Settings Interface from your desktop application launcher or run:

```bash
edgepad gui
```

### GUI Views Overview

1. **Dashboard**
   - Check real-time service status (Active, Stopped, Error).
   - Master gesture toggle switch to enable/disable gesture interception instantly.
   - Quick overview of active touchpad device, edge margins, and hardware bindings.
2. **Gestures & Rotary Encoder**
   - Configure edge gesture bindings (swipes, sliders, taps, double-taps).
   - Distance-Based Rotary Encoder Card: toggle discrete continuous ticks, set step size, dead zone, and repeat intervals.
   - Built-in Key Selector Dialog with instant search over standard Linux input keys.
3. **Edge Zones**
   - Interactive touchpad canvas (`TouchpadCanvas`) showing live edge margin boundaries.
   - Adjust global or per-edge zone widths (Left, Right, Top, Bottom) from 1% to 45%.
4. **Touchpad Selection**
   - Automatically detect all connected touchpad hardware.
   - Inspect device coordinates, capabilities, and event nodes (`/dev/input/eventX`).
5. **Live Gesture Tester**
   - Test touches and swipes with real-time visual feedback.
   - Streams live coordinates, active edge zone, cumulative travel distance, encoder ticks, and emitted keycodes.
   - Supports safe **Test Mode** without affecting real system volume or brightness.
6. **Diagnostics**
   - One-click `edgepad doctor` execution.
   - Inspect journald systemd logs for `edgepad.service`.
   - Verify udev permissions and virtual device creation.
7. **About & Backups**
   - One-click configuration export and import.
   - Restore factory default preset with one click.

---

## ⌨️ CLI Usage & Background Service

Edgepad can be fully managed from the terminal:

```bash
# Show summary of daemon, active config, and touchpad device
edgepad status

# Run health diagnostics (checks uinput, udev rules, permissions, systemd)
edgepad doctor

# List available input devices and touchpad candidates
edgepad devices

# Run the live daemon manually in foreground
edgepad daemon

# Launch the Qt 6 / QML settings manager
edgepad gui
```

### Systemd User Service

Edgepad runs as a standard systemd user service:

```bash
# Start or restart the background service
systemctl --user start edgepad.service
systemctl --user restart edgepad.service

# Reload configuration after manual file edits
systemctl --user reload edgepad.service

# Check service status and logs
systemctl --user status edgepad.service
journalctl --user -u edgepad.service -f
```

---

## ⚙️ Configuration (`edgepad.toml`)

The configuration file is located at `~/.config/edgepad/edgepad.toml`. You can edit it directly or modify it through the GUI:

```toml
# Touchpad selection ("auto" or specific event path e.g. "/dev/input/event4")
device = "auto"

# Outer edge border width (fraction of touchpad width/height: 0.12 = 12%)
edge_width = 0.12

# Optional per-edge margin overrides:
# left_edge_width = 0.10
# right_edge_width = 0.12
# top_edge_width = 0.08
# bottom_edge_width = 0.08

# Rotary encoder behavior for vertical edge swipes:
# Finger movement produces discrete key events proportional to travel distance
[encoder]
enabled = true
step_size = 50.0          # Coordinate units per tick (or fraction if < 1.0)
dead_zone = 10.0          # Initial jitter filter before ticks start accumulating
repeat_interval_ms = 20   # Cadence between generated virtual key events (5-200 ms)

# Left edge: Volume slider
[[sliders]]
zone = "left"
step = 0.04
up = ["notify-send", "edgepad", "volume-up"]
down = ["notify-send", "edgepad", "volume-down"]

# Left edge: Tap to toggle mute
[[gestures]]
zone = "left"
direction = "tap"
action = ["notify-send", "edgepad", "volume-mute"]

# Right edge: Brightness slider
[[sliders]]
zone = "right"
step = 0.04
up = ["notify-send", "edgepad", "brightness-up"]
down = ["notify-send", "edgepad", "brightness-down"]

# Top edge: Media controls
[[gestures]]
zone = "top"
direction = "tap"
action = ["playerctl", "play-pause"]

[[gestures]]
zone = "top"
direction = "right"
action = ["playerctl", "next"]

[[gestures]]
zone = "top"
direction = "left"
action = ["playerctl", "previous"]
```

> **Note:** When using the default hardware preset in the GUI or when no custom command is defined for edge sliders, Edgepad automatically emits native `/dev/uinput` physical keys (`KEY_BRIGHTNESSUP`, `KEY_BRIGHTNESSDOWN`, `KEY_VOLUMEUP`, `KEY_VOLUMEDOWN`), requiring no external commands or shell processes.

---

## 🩺 Troubleshooting & Diagnostics

If edgepad does not respond or gestures behave unexpectedly:

1. **Run Edgepad Doctor:**
   ```bash
   edgepad doctor
   ```
   This validates whether `/dev/uinput` exists, whether your user has read/write permissions to input devices, whether `70-edgepad.rules` is active, and whether the systemd service is running.

2. **Check Device Permissions & Udev:**
   Ensure your user is authorized to read touchpad events and write to `/dev/uinput`. The udev rule `/etc/udev/rules.d/70-edgepad.rules` should contain:
   ```udev
   KERNEL=="uinput", SUBSYSTEM=="misc", TAG+="uaccess", OPTIONS+="static_node=uinput"
   SUBSYSTEM=="input", ENV{ID_INPUT_TOUCHPAD}=="1", TAG+="uaccess"
   ```
   After modifying, reload udev:
   ```bash
   sudo udevadm control --reload-rules && sudo udevadm trigger
   ```

3. **Multiple Touchpads:**
   If multiple touchpads are detected, run `edgepad devices`, copy the desired `/dev/input/eventX` path, set `device = "/dev/input/eventX"` in `edgepad.toml`, and restart the service.

4. **Temporary Emergency Release:**
   If pointer movement ever behaves unexpectedly, stop edgepad to release control of the physical touchpad back to the default driver:
   ```bash
   systemctl --user stop edgepad.service
   ```

---

## 🧪 Development & Testing

```bash
# Check code formatting & lints
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings

# Run the complete Rust test suite (recognizer, uinput, encoder, CLI)
cargo test

# Run the Python GUI backend unit test suite
python3 -m unittest discover tests -p "test_*.py"
```

For advanced gesture capture and replay diagnostics, see:
- [Event Capture Guide](docs/dump-capture.md) — record raw evdev events for regression testing.
- [GUI Architecture Guide](docs/gui.md) — in-depth details on Qt / QML structure and IPC design.
- [Input Forwarding & Uinput](docs/passthrough-uinput.md) — low-level input proxy implementation.
- [Double-Tap Recognition](docs/double-tap.md) — multi-tap state machine specifications.

---

## 📄 License

Dual-licensed under either of:

- [Apache License, Version 2.0](LICENSE-APACHE)
- [MIT License](LICENSE-MIT)

at your option.
