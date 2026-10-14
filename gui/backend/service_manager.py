"""Service manager for Edgepad GUI.

Controls the user-level systemd service (edgepad.service) via systemctl.
Handles starting, stopping, restarting, reloading, enabling, disabling,
and installing the unit file if missing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any


class ServiceManager:
    """Manages edgepad.service state and start-at-login integration."""

    SERVICE_NAME = "edgepad.service"

    def __init__(self) -> None:
        self.user_systemd_dir = Path.home() / ".config" / "systemd" / "user"
        self.service_file_path = self.user_systemd_dir / self.SERVICE_NAME

    def find_edgepad_binary(self) -> str:
        """Finds the most suitable edgepad binary path."""
        # 1. PATH lookup
        which = shutil.which("edgepad")
        if which:
            return which

        # 2. ~/.local/bin/edgepad
        local_bin = Path.home() / ".local" / "bin" / "edgepad"
        if local_bin.exists():
            return str(local_bin)

        # 3. /usr/bin/edgepad
        usr_bin = Path("/usr/bin/edgepad")
        if usr_bin.exists():
            return str(usr_bin)

        # 4. Workspace build target
        workspace_target = Path("/home/vicky/Downloads/linux-projects/edgepad-main/target/debug/edgepad")
        if workspace_target.exists():
            return str(workspace_target)

        return "edgepad"

    def is_unit_installed(self) -> bool:
        """Checks if edgepad.service unit file exists."""
        if self.service_file_path.exists():
            return True
        sys_unit = Path("/usr/lib/systemd/user") / self.SERVICE_NAME
        return sys_unit.exists()

    def ensure_service_installed(self) -> tuple[bool, str]:
        """Installs user-level systemd service file if not present."""
        if self.is_unit_installed():
            return True, "Service unit already installed"

        try:
            self.user_systemd_dir.mkdir(parents=True, exist_ok=True)
            bin_path = self.find_edgepad_binary()
            service_content = f"""[Unit]
Description=edgepad touchpad edge gesture daemon
Documentation=https://github.com/assembledev/edgepad

[Service]
Type=notify
NotifyAccess=main
TimeoutStartSec=45s
ExecStart={bin_path} daemon --config %h/.config/edgepad/edgepad.toml
ExecReload=kill -HUP $MAINPID
Restart=on-failure
RestartSec=1s
Environment=PATH=%h/.local/bin:/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
"""
            self.service_file_path.write_text(service_content, encoding="utf-8")
            subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, check=False)
            return True, "Service unit installed successfully"
        except Exception as e:
            return False, f"Failed to install service unit: {e}"

    def run_systemctl(self, args: list[str]) -> tuple[int, str, str]:
        """Runs a systemctl command and returns (exit_code, stdout, stderr)."""
        cmd = ["systemctl", "--user"] + args
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except Exception as e:
            return 1, "", str(e)

    def get_status(self) -> str:
        """Returns normalized status: 'running', 'stopped', 'starting', 'error', or 'not_installed'."""
        if not self.is_unit_installed():
            return "not_installed"

        code, out, _ = self.run_systemctl(["is-active", self.SERVICE_NAME])
        if out == "active":
            return "running"
        elif out == "activating":
            return "starting"
        elif out == "failed":
            return "error"
        elif out in ["inactive", "unknown"]:
            return "stopped"

        # Check substate if needed
        return "stopped" if code != 0 else "running"

    def is_enabled(self) -> bool:
        """Returns True if service is enabled to start on login."""
        if not self.is_unit_installed():
            return False
        code, out, _ = self.run_systemctl(["is-enabled", self.SERVICE_NAME])
        return out == "enabled"

    def start(self) -> tuple[bool, str]:
        self.ensure_service_installed()
        code, out, err = self.run_systemctl(["start", self.SERVICE_NAME])
        if code == 0:
            return True, "Gesture service started"
        return False, f"Failed to start service: {err or out or f'exit code {code}'}"

    def stop(self) -> tuple[bool, str]:
        code, out, err = self.run_systemctl(["stop", self.SERVICE_NAME])
        if code == 0:
            return True, "Gesture service stopped"
        return False, f"Failed to stop service: {err or out or f'exit code {code}'}"

    def restart(self) -> tuple[bool, str]:
        self.ensure_service_installed()
        code, out, err = self.run_systemctl(["restart", self.SERVICE_NAME])
        if code == 0:
            return True, "Gesture service restarted"
        return False, f"Failed to restart service: {err or out or f'exit code {code}'}"

    def reload(self) -> tuple[bool, str]:
        """Triggers SIGHUP reload on the active daemon."""
        status = self.get_status()
        if status != "running":
            # If not running, starting it applies the latest config
            return self.restart()

        code, out, err = self.run_systemctl(["reload", self.SERVICE_NAME])
        if code == 0:
            return True, "Configuration reloaded"
        return False, f"Failed to reload service: {err or out or f'exit code {code}'}"

    def set_start_at_login(self, enable: bool) -> tuple[bool, str]:
        """Enables or disables service start on login."""
        self.ensure_service_installed()
        action = "enable" if enable else "disable"
        code, out, err = self.run_systemctl([action, self.SERVICE_NAME])
        if code == 0:
            return True, f"Start at login {'enabled' if enable else 'disabled'}"
        return False, f"Failed to {action} service: {err or out or f'exit code {code}'}"

    def get_recent_logs(self, lines: int = 40) -> str:
        """Fetches recent journald logs for the service."""
        cmd = ["journalctl", "--user", "-u", self.SERVICE_NAME, "-n", str(lines), "--no-pager"]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            return res.stdout.strip()
        except Exception as e:
            return f"Failed to retrieve logs: {e}"
