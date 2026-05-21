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
import time
import urllib.error
import urllib.request

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


def _find_free_port() -> int:
    """Ask the OS for an available TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return s.getsockname()[1]


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
        self.process: subprocess.Popen[bytes] | None = None
        self.saved_env: dict[str, str | None] = {}
        self.port: int = 0

    @property
    def running(self) -> bool:
        """True when the moto server subprocess is alive."""
        return self.process is not None and self.process.poll() is None

    @property
    def endpoint_url(self) -> str:
        """The HTTP URL the moto server listens on."""
        return f"http://{MOTO_HOST}:{self.port}"

    def start(self, timeout: float = 10.0) -> None:
        """Launch the moto server subprocess and block until it is ready.

        Raises RuntimeError if moto is not installed or the server doesn't come up in time.
        """
        if self.running:
            return

        try:
            import moto  # noqa: F401
        except ImportError as exc:
            raise RuntimeError("moto is not installed; add it to dev deps") from exc

        self.port = _find_free_port()
        cmd = [sys.executable, "-m", "moto.server", "-H", MOTO_HOST, "-p", str(self.port)]
        logger.info("starting moto server: %s", " ".join(cmd))

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

        self._inject_credentials()

        try:
            self._wait_ready(timeout)
        except RuntimeError:
            # Collect whatever output the server produced before dying.
            stderr_output = ""
            if self.process.stdout:
                try:
                    stderr_output = self.process.stdout.read(4096).decode(errors="replace")
                except Exception:
                    pass
            self.stop()
            raise RuntimeError(
                f"moto server did not come up within {timeout}s on port {self.port}.\n"
                f"Server output:\n{stderr_output or '(none)'}"
            )

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
        self._restore_credentials()

    def _inject_credentials(self) -> None:
        for key, value in _ENV_VARS.items():
            self.saved_env[key] = os.environ.get(key)
            os.environ[key] = value

    def _restore_credentials(self) -> None:
        for key, saved in self.saved_env.items():
            if saved is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = saved
        self.saved_env.clear()

    def _wait_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            # Fail fast if the process already exited.
            if self.process is not None and self.process.poll() is not None:
                raise RuntimeError(f"moto server process exited with code {self.process.returncode}")
            try:
                urllib.request.urlopen(self.endpoint_url, timeout=1)
                return
            except (urllib.error.URLError, OSError):
                time.sleep(0.25)
        raise RuntimeError(f"moto server did not respond within {timeout}s")
