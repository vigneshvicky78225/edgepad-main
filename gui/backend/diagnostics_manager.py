"""Diagnostics and troubleshooting manager for Edgepad GUI.

Runs and parses `edgepad doctor`, inspects permissions, gathers service logs,
and exports comprehensive diagnostic reports.
"""

from __future__ import annotations

import datetime
import os
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Any


class DiagnosticsManager:
    """Manages diagnostics checks and report generation."""

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

    def run_doctor(self, config_path: str | None = None) -> dict[str, Any]:
        """Runs `edgepad doctor` and parses results into structured report."""
        cmd = [self.edgepad_bin, "doctor"]
        if config_path and Path(config_path).exists():
            cmd.extend(["--config", config_path])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            raw_text = (res.stdout + "\n" + res.stderr).strip()
            exit_code = res.returncode
        except Exception as e:
            raw_text = f"Failed to run edgepad doctor: {e}"
            exit_code = 1

        items = []
        summary = {"ok": 0, "warn": 0, "fail": 0, "result": "unknown"}

        current_section = "General"
        for line in raw_text.splitlines():
            line_str = line.strip()
            if not line_str or line_str == "edgepad doctor":
                continue

            # Section headers like "Config", "Device", "Access", "Session", "Service", "Summary"
            if not line.startswith(" ") and not line.startswith("\t"):
                current_section = line_str
                continue

            # Summary lines
            if "ok=" in line_str and "warn=" in line_str:
                for part in line_str.split():
                    if "=" in part:
                        k, v = part.split("=", 1)
                        try:
                            summary[k] = int(v)
                        except ValueError:
                            pass
                continue
            if line_str.startswith("result:"):
                summary["result"] = line_str.replace("result:", "").strip()
                continue

            # Check lines like: "ok    touchpad   /dev/input/event4..." or "warn  udev tags  ..."
            parts = line_str.split(None, 2)
            if len(parts) >= 2 and parts[0] in ["ok", "warn", "fail"]:
                level = parts[0]
                name = parts[1]
                details = parts[2] if len(parts) > 2 else ""
                items.append({
                    "section": current_section,
                    "level": level,
                    "name": name,
                    "details": details,
                })

        return {
            "exit_code": exit_code,
            "raw_text": raw_text,
            "items": items,
            "summary": summary,
        }

    def generate_full_report(
        self,
        config_dict: dict[str, Any] | None = None,
        service_status: str = "unknown",
        service_logs: str = "",
        selected_device: dict[str, Any] | None = None,
    ) -> str:
        """Generates a complete diagnostic Markdown report."""
        doctor_info = self.run_doctor()

        lines = [
            "# Edgepad Diagnostics Report",
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## 1. Environment & System",
            f"- **OS:** {platform.platform()}",
            f"- **Linux Kernel:** {platform.release()}",
            f"- **Desktop Session:** {os.environ.get('XDG_CURRENT_DESKTOP', 'Unknown')} ({os.environ.get('XDG_SESSION_TYPE', 'Unknown')})",
            f"- **Wayland Display:** {os.environ.get('WAYLAND_DISPLAY', 'None')}",
            f"- **User:** {os.environ.get('USER', 'Unknown')} (UID: {os.getuid()})",
            "",
            "## 2. Touchpad Device Information",
        ]

        if selected_device:
            lines.extend([
                f"- **Device Name:** `{selected_device.get('name')}`",
                f"- **Node Path:** `{selected_device.get('path')}`",
                f"- **Hardware ID:** `{selected_device.get('id')}`",
                f"- **Axis Range:** X: `{selected_device.get('x_range')}`, Y: `{selected_device.get('y_range')}`",
                f"- **Slots:** `{selected_device.get('slots')}`",
                f"- **Readable:** {'Yes' if selected_device.get('readable') else 'No'}",
                f"- **Writable:** {'Yes' if selected_device.get('writable') else 'No'}",
            ])
        else:
            lines.append("No active touchpad selected or detected.")

        lines.extend([
            "",
            "## 3. Daemon & Service Status",
            f"- **Service State:** `{service_status}`",
            "",
            "## 4. Edgepad Doctor Checks",
            "| Section | Status | Check | Details |",
            "|---|---|---|---|",
        ])

        for item in doctor_info.get("items", []):
            badge = "✅ OK" if item["level"] == "ok" else ("⚠️ Warning" if item["level"] == "warn" else "❌ Failed")
            lines.append(f"| {item['section']} | {badge} | {item['name']} | {item['details']} |")

        lines.extend([
            "",
            "## 5. Active Configuration Summary",
        ])

        if config_dict:
            lines.extend([
                f"- **Configured Device:** `{config_dict.get('device', 'auto')}`",
                f"- **Edge Width:** `{config_dict.get('edge_width', 0.12):.2%}`",
                f"- **Min Travel:** `{config_dict.get('engine', {}).get('min_travel', 250)}` units",
                f"- **Gestures Count:** `{len(config_dict.get('gestures', []))}`",
                f"- **Sliders Count:** `{len(config_dict.get('sliders', []))}`",
            ])
        else:
            lines.append("No configuration loaded.")

        if service_logs:
            lines.extend([
                "",
                "## 6. Recent Service Logs (journalctl)",
                "```text",
                service_logs.strip(),
                "```",
            ])

        return "\n".join(lines) + "\n"
