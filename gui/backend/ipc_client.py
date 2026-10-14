"""Unix domain socket IPC client for Edgepad GUI.

Streams real-time gesture and slider recognition events from the daemon
and controls Test Mode and configuration reloads.
"""

from __future__ import annotations

import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal


def get_default_ipc_socket_path() -> Path:
    runtime_dir = os.environ.get("XDG_RUNTIME_DIR")
    if runtime_dir and runtime_dir.strip():
        return Path(runtime_dir.strip()) / "edgepad" / "edgepad.sock"
    uid = os.getuid()
    return Path(f"/tmp/edgepad-{uid}") / "edgepad.sock"


class IpcClient(QObject):
    """Client for daemon IPC socket communicating with Qt main loop."""

    # Signals for Qt / QML
    event_received = Signal(dict)
    connection_changed = Signal(bool)

    def __init__(self, socket_path: Path | None = None) -> None:
        super().__init__()
        self.socket_path = socket_path or get_default_ipc_socket_path()
        self._socket: socket.socket | None = None
        self._connected = False
        self._stop_event = threading.Event()
        self._reader_thread: threading.Thread | None = None
        self._lock = threading.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        """Starts background reader thread that auto-connects to daemon."""
        self._stop_event.clear()
        if self._reader_thread is None or not self._reader_thread.is_alive():
            self._reader_thread = threading.Thread(target=self._connection_loop, daemon=True)
            self._reader_thread.start()

    def stop(self) -> None:
        """Stops background reader thread and closes socket."""
        self._stop_event.set()
        self._disconnect()
        if self._reader_thread and self._reader_thread.is_alive():
            self._reader_thread.join(timeout=1.0)

    def _disconnect(self) -> None:
        with self._lock:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
            if self._connected:
                self._connected = False
                self.connection_changed.emit(False)

    def _connection_loop(self) -> None:
        while not self._stop_event.is_set():
            if not self._connected:
                if self.socket_path.exists():
                    try:
                        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                        s.settimeout(2.0)
                        s.connect(str(self.socket_path))
                        with self._lock:
                            self._socket = s
                            self._connected = True
                        self.connection_changed.emit(True)
                        self._read_loop(s)
                    except Exception:
                        self._disconnect()
                time.sleep(1.0)
            else:
                time.sleep(0.5)

    def _read_loop(self, s: socket.socket) -> None:
        s.settimeout(1.0)
        buffer = ""
        while not self._stop_event.is_set() and self._connected:
            try:
                data = s.recv(4096)
                if not data:
                    break
                buffer += data.decode("utf-8", errors="replace")
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        parsed = json.loads(line)
                        self.event_received.emit(parsed)
                    except Exception:
                        pass
            except socket.timeout:
                continue
            except Exception:
                break
        self._disconnect()

    def send_command(self, cmd: str) -> bool:
        """Sends a command line to daemon socket."""
        with self._lock:
            if not self._socket or not self._connected:
                return False
            try:
                msg = cmd.strip() + "\n"
                self._socket.sendall(msg.encode("utf-8"))
                return True
            except Exception:
                self._disconnect()
                return False

    def set_test_mode(self, enabled: bool) -> bool:
        """Sets Test Mode on daemon (simulated action execution)."""
        val = "true" if enabled else "false"
        return self.send_command(f"test_mode:{val}")

    def request_reload(self) -> bool:
        """Requests SIGHUP-equivalent reload from daemon."""
        return self.send_command("reload")
