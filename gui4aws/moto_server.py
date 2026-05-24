"""Moto server manager: launch/stop moto in HTTP server mode.

moto[server] exposes a real HTTP endpoint so that boto3 clients can point at it via
endpoint_url — identical to the workflow against real AWS. This module manages the
subprocess lifecycle and credential injection.

Port selection: we bind to an ephemeral port chosen by the OS (via socket.bind("", 0))
so we never collide with whatever else is running on the machine.
"""

from __future__ import annotations

import logging
import os
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any

__all__ = ["MotoServerManager"]

logger = logging.getLogger(__name__)

MOTO_HOST = "127.0.0.1"

# Fake credentials injected when moto server is running so boto3 is satisfied.
_FAKE_KEY_ID = "testing"
_FAKE_SECRET = "testing"
_FAKE_TOKEN = "testing"
_FAKE_REGION = "us-east-1"

_ENV_VARS = {
    "AWS_ACCESS_KEY_ID": _FAKE_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": _FAKE_SECRET,
    "AWS_SESSION_TOKEN": _FAKE_TOKEN,
    "AWS_DEFAULT_REGION": _FAKE_REGION,
    # Prevent boto3 from reading ~/.aws/credentials which would override our fakes.
    "AWS_CONFIG_FILE": "",
    "AWS_SHARED_CREDENTIALS_FILE": "",
}


def find_free_port() -> int:
    """Ask the OS for an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return int(s.getsockname()[1])


class MotoServerManager:
    """Start and stop a moto HTTP server subprocess.

    Usage::

        mgr = MotoServerManager()
        mgr.start()   # launches subprocess, injects env vars
        mgr.stop()    # kills subprocess, restores env vars
        mgr.running   # True when the server is up
        mgr.endpoint_url  # e.g. "http://127.0.0.1:54321"
    """

    def __init__(self) -> None:
        self.process: subprocess.Popen[str] | None = None
        self.saved_env: dict[str, str | None] = {}
        self.port: int = 0
        self.output_lock = threading.RLock()
        self.output_lines: deque[str] = deque(maxlen=2000)
        self.reader_thread: threading.Thread | None = None

    @property
    def running(self) -> bool:
        """True when the moto server subprocess is alive."""
        return self.process is not None and self.process.poll() is None

    @property
    def endpoint_url(self) -> str:
        """The HTTP URL the moto server listens on."""
        return f"http://{MOTO_HOST}:{self.port}"

    @property
    def dashboard_url(self) -> str:
        """Moto dashboard URL."""
        return f"{self.endpoint_url}/moto-api/"

    def start(self, timeout: float = 10.0) -> None:
        """Launch the moto server subprocess and block until it is ready.

        Raises RuntimeError if moto is not installed or the server doesn't come up in time.
        """
        if self.running:
            return

        try:
            import moto  # pylint: disable=unused-import  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("moto is not installed; add it to dev deps") from exc

        self.port = find_free_port()
        cmd = [sys.executable, "-m", "moto.server", "-H", MOTO_HOST, "-p", str(self.port)]
        logger.info("starting moto server: %s", " ".join(cmd))
        self.clear_output()
        self.append_output(f"=== starting moto on {self.endpoint_url} ===")

        # pylint: disable=consider-using-with
        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        if self.process.stdout is not None:
            self.reader_thread = threading.Thread(target=self.capture_output, name="moto-output", daemon=True)
            self.reader_thread.start()

        self.inject_credentials()

        try:
            self.wait_ready(timeout)
        except RuntimeError as exc:
            stderr_output = self.output_text(max_lines=80)
            self.stop()
            raise RuntimeError(
                f"moto server did not come up within {timeout}s on port {self.port}.\n"
                f"Server output:\n{stderr_output or '(none)'}"
            ) from exc

        logger.info("moto server ready at %s", self.endpoint_url)

    def stop(self) -> None:
        """Terminate the moto server subprocess and restore environment."""
        if self.process is not None:
            logger.info("stopping moto server")
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
            self.process = None
        self.append_output("=== moto stopped ===")
        self.restore_credentials()

    def restart(self, timeout: float = 10.0) -> None:
        """Restart Moto, preserving the fake credential wiring."""
        self.stop()
        self.start(timeout=timeout)

    def reset_state(self) -> None:
        """POST /moto-api/reset to wipe all moto state without restarting the server.

        Raises RuntimeError if moto is not running or the request fails.
        """
        if not self.running:
            raise RuntimeError("Moto server is not running")
        url = f"{self.endpoint_url}/moto-api/reset"
        req = urllib.request.Request(url, method="POST", data=b"")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310

                body = resp.read()
                self.append_output(f"=== moto state reset: {resp.status} {body!r} ===")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Moto reset failed: HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError(f"Moto reset failed: {exc}") from exc

    def output_text(self, *, max_lines: int | None = None) -> str:
        """Return collected Moto stdout/stderr."""
        with self.output_lock:
            lines = list(self.output_lines)
        if max_lines is not None:
            lines = lines[-max_lines:]
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        """Return process state and output summary for diagnostics."""
        with self.output_lock:
            lines = list(self.output_lines)
        return {
            "running": self.running,
            "port": self.port,
            "endpoint_url": self.endpoint_url if self.port else None,
            "output_line_count": len(lines),
            "recent_output": lines[-50:],
        }

    def inject_credentials(self) -> None:
        """Inject fake AWS credentials into the environment for the current process."""
        for key, value in _ENV_VARS.items():
            self.saved_env[key] = os.environ.get(key)
            os.environ[key] = value

    def restore_credentials(self) -> None:
        """Restore original AWS credentials to the environment."""
        for key, saved in self.saved_env.items():
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved
        self.saved_env.clear()

    def wait_ready(self, timeout: float) -> None:
        """Poll the moto endpoint until it responds or the timeout is reached."""
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Fail fast if the process already exited.
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"moto server process exited with code {self.process.returncode}")
            try:
                with urllib.request.urlopen(self.endpoint_url, timeout=1):  # nosec B310
                    return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)
        raise RuntimeError(f"moto server did not respond within {timeout}s")

    def capture_output(self) -> None:
        """Background loop that reads moto stdout/stderr and appends to the buffer."""
        process = self.process
        if process is None or process.stdout is None:
            return
        for line in process.stdout:
            text = line.rstrip()
            if text:
                self.append_output(text)

    def append_output(self, line: str) -> None:
        """Thread-safe append to the rolling output buffer."""
        with self.output_lock:
            self.output_lines.append(line)

    def clear_output(self) -> None:
        """Wipe the rolling output buffer."""
        with self.output_lock:
            self.output_lines.clear()
