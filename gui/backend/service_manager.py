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
        """Finds the most suitable edgepad binary path without hardcoded user directories."""
        # 1. Package-installed location (/usr/bin/edgepad)
        usr_bin = Path("/usr/bin/edgepad")
        if usr_bin.exists() and os.access(usr_bin, os.X_OK):
            return str(usr_bin)

        # 2. PATH lookup
        which = shutil.which("edgepad")
        if which:
            return which

        # 3. User-local location (~/.local/bin/edgepad)
        local_bin = Path.home() / ".local" / "bin" / "edgepad"
        if local_bin.exists() and os.access(local_bin, os.X_OK):
            return str(local_bin)

        # 4. Repo workspace target (release then debug)
        repo_root = Path(__file__).resolve().parent.parent.parent
        for sub in ["release", "debug"]:
            target_bin = repo_root / "target" / sub / "edgepad"
            if target_bin.exists() and os.access(target_bin, os.X_OK):
                return str(target_bin)

        return "edgepad"

    def is_unit_installed(self) -> bool:
        """Checks if edgepad.service unit file exists in system or user location."""
        if self.service_file_path.exists():
            return True
        sys_unit = Path("/usr/lib/systemd/user") / self.SERVICE_NAME
        return sys_unit.exists()

    def detect_legacy_unit(self) -> tuple[bool, str]:
        """Detects if a user-level override unit exists and whether it references invalid/legacy paths."""
        if not self.service_file_path.exists():
            return False, ""
        try:
            content = self.service_file_path.read_text(encoding="utf-8")
        except Exception as e:
            return False, f"Could not read user service: {e}"

        reasons = []
        if "/home/vicky" in content:
            reasons.append("References hardcoded developer path '/home/vicky'")
        if "%h/.local/bin/edgepad" in content:
            local_bin = Path.home() / ".local" / "bin" / "edgepad"
            if not local_bin.exists():
                reasons.append("References '%h/.local/bin/edgepad' which does not exist")

        for line in content.splitlines():
            line = line.strip()
            if line.startswith("ExecStart="):
                exec_cmd = line[len("ExecStart="):].strip()
                exec_bin = exec_cmd.split()[0] if exec_cmd else ""
                expanded_bin = exec_bin.replace("%h", str(Path.home()))
                if not Path(expanded_bin).exists() and not shutil.which(expanded_bin):
                    reasons.append(f"ExecStart binary '{exec_bin}' does not exist (causes status 203/EXEC)")
                break

        system_unit = Path("/usr/lib/systemd/user") / self.SERVICE_NAME
        if system_unit.exists() and reasons:
            return True, "; ".join(reasons)
        elif reasons:
            return True, "; ".join(reasons)

        return False, ""

    def repair_service(self) -> tuple[bool, str]:
        """Repairs or migrates legacy/broken user units to restore daemon operation."""
        is_legacy, reason = self.detect_legacy_unit()
        system_unit = Path("/usr/lib/systemd/user") / self.SERVICE_NAME

        if self.service_file_path.exists():
            if is_legacy or system_unit.exists():
                import time
                backup_path = self.service_file_path.with_suffix(f".service.bak.{int(time.time())}")
                try:
                    shutil.copy2(self.service_file_path, backup_path)
                    self.service_file_path.unlink()
                except Exception as e:
                    return False, f"Failed to migrate legacy unit file: {e}"

        if not system_unit.exists() and not self.service_file_path.exists():
            bin_path = self.find_edgepad_binary()
            if not Path(bin_path).exists() and not shutil.which(bin_path):
                return False, f"Cannot create service: executable '{bin_path}' not found"
            try:
                self.write_canonical_user_unit(bin_path)
            except Exception as e:
                return False, f"Failed to write service unit: {e}"

        # Clear failed state and reload
        self.run_systemctl(["reset-failed", self.SERVICE_NAME])
        self.run_systemctl(["daemon-reload"])

        return True, "Service definition repaired and reloaded"

    def write_canonical_user_unit(self, bin_path: str) -> None:
        """Writes canonical systemd user service pointing to a verified executable."""
        self.user_systemd_dir.mkdir(parents=True, exist_ok=True)
        if bin_path.startswith(str(Path.home())):
            bin_path = bin_path.replace(str(Path.home()), "%h", 1)
        service_content = f"""[Unit]
Description=edgepad touchpad edge gesture daemon
Documentation=https://github.com/assembledev/edgepad

[Service]
Type=notify
NotifyAccess=main
TimeoutStartSec=45s
ExecStart={bin_path} daemon
ExecReload=/usr/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=2s
Environment=PATH=/usr/local/bin:/usr/bin:/bin

[Install]
WantedBy=default.target
"""
        self.service_file_path.write_text(service_content, encoding="utf-8")

    def ensure_service_installed(self) -> tuple[bool, str]:
        """Installs user-level systemd service file if not present or repairs legacy unit."""
        is_legacy, _ = self.detect_legacy_unit()
        if is_legacy:
            return self.repair_service()

        if self.is_unit_installed():
            return True, "Service unit already installed"

        try:
            bin_path = self.find_edgepad_binary()
            self.write_canonical_user_unit(bin_path)
            self.run_systemctl(["daemon-reload"])
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
