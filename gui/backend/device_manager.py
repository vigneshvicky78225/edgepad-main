"""Device discovery and management for Edgepad GUI.

Discovers touchpads and input devices using the edgepad binary and udev symlinks.
Verifies read/write permissions and provides coordinate ranges for calibration.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any


class DeviceManager:
    """Discovers and inspects Linux input devices and touchpads."""

    def __init__(self, edgepad_bin: str | None = None) -> None:
        self.edgepad_bin = edgepad_bin or self._find_edgepad_bin()

    def _find_edgepad_bin(self) -> str:
        which = shutil.which("edgepad")
        if which:
            return which
        ws = Path("/home/vicky/Downloads/linux-projects/edgepad-main/target/debug/edgepad")
        if ws.exists():
            return str(ws)
        local_bin = Path.home() / ".local" / "bin" / "edgepad"
        if local_bin.exists():
            return str(local_bin)
        return "edgepad"

    def check_uinput_access(self) -> tuple[bool, str]:
        """Checks read and write access to /dev/uinput."""
        uinput = Path("/dev/uinput")
        if not uinput.exists():
            return False, "/dev/uinput device node does not exist"
        if not os.access(uinput, os.R_OK):
            return False, "Cannot read /dev/uinput (permission denied; check group 'input' or udev rules)"
        if not os.access(uinput, os.W_OK):
            return False, "Cannot write to /dev/uinput (permission denied; check group 'input' or udev rules)"
        return True, "Full access to /dev/uinput granted"

    def get_symlinks_for_device(self, dev_path: str) -> list[str]:
        """Finds persistent /dev/input/by-id or by-path symlinks pointing to this node."""
        symlinks = []
        real_dev = os.path.realpath(dev_path)
        for base in [Path("/dev/input/by-path"), Path("/dev/input/by-id")]:
            if base.exists():
                try:
                    for entry in base.iterdir():
                        if entry.is_symlink() and os.path.realpath(entry) == real_dev:
                            symlinks.append(str(entry))
                except Exception:
                    pass
        return symlinks

    def discover_devices(self, show_all: bool = False) -> list[dict[str, Any]]:
        """Discovers input devices using `edgepad devices`."""
        cmd = [self.edgepad_bin, "devices"]
        if show_all:
            cmd.append("--all")

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = res.stdout
        except Exception:
            output = ""

        devices = []
        # Parse lines like:
        # /dev/input/event4 kind=touchpad name="PIXA3848:01 093A:3848 Touchpad" id=093a:3848 slots=0..=4 x=0..=2905 y=0..=1766
        pattern = re.compile(
            r'^(?P<path>/dev/input/event\d+)\s+kind=(?P<kind>\w+)\s+name="(?P<name>[^"]*)"\s+id=(?P<id>[^\s]+)(?:\s+slots=(?P<slots>[^\s]+))?(?:\s+x=(?P<x>[^\s]+))?(?:\s+y=(?P<y>[^\s]+))?'
        )

        for line in output.splitlines():
            line = line.strip()
            match = pattern.match(line)
            if not match:
                continue

            path = match.group("path")
            kind = match.group("kind")
            name = match.group("name")
            dev_id = match.group("id")
            slots = match.group("slots") or "n/a"
            x_str = match.group("x") or "n/a"
            y_str = match.group("y") or "n/a"

            x_min, x_max = 0, 0
            if "..=" in x_str:
                parts = x_str.split("..=")
                try:
                    x_min, x_max = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

            y_min, y_max = 0, 0
            if "..=" in y_str:
                parts = y_str.split("..=")
                try:
                    y_min, y_max = int(parts[0]), int(parts[1])
                except ValueError:
                    pass

            readable = os.access(path, os.R_OK)
            writable = os.access(path, os.W_OK)
            symlinks = self.get_symlinks_for_device(path)
            persistent = symlinks[0] if symlinks else path

            devices.append({
                "path": path,
                "name": name,
                "kind": kind,
                "is_touchpad": (kind == "touchpad"),
                "id": dev_id,
                "slots": slots,
                "x_range": x_str,
                "y_range": y_str,
                "x_min": x_min,
                "x_max": x_max,
                "y_min": y_min,
                "y_max": y_max,
                "readable": readable,
                "writable": writable,
                "persistent_path": persistent,
                "symlinks": symlinks,
            })

        return devices

    def get_touchpads(self) -> list[dict[str, Any]]:
        """Returns only touchpad candidate devices."""
        return [d for d in self.discover_devices(show_all=False) if d.get("is_touchpad")]

    def get_selected_touchpad(self, configured_device: str) -> dict[str, Any] | None:
        """Finds details for the configured device ('auto' or specific path)."""
        touchpads = self.get_touchpads()
        if not touchpads:
            return None

        if configured_device == "auto" or not configured_device:
            return touchpads[0]

        real_target = os.path.realpath(configured_device)
        for t in touchpads:
            if t["path"] == configured_device or os.path.realpath(t["path"]) == real_target:
                return t
            if configured_device in t["symlinks"]:
                return t

        return touchpads[0]
