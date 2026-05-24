"""Robotocore server manager.

Robotocore is a Docker-based local AWS emulator that listens on port 4566.
This module can either:
  - launch the container via ``docker run`` (like MotoServerManager does for moto)
  - or probe an already-running container

Typical usage::

    mgr = RobotocoreManager()
    mgr.start()     # docker run + health-check + credential injection
    mgr.stop()      # docker stop + credential restore
    mgr.restart()
    mgr.running     # True when container is up and reachable
    mgr.endpoint_url
"""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import time
import urllib.error
import urllib.request
from collections import deque
from typing import Any

__all__ = ["RobotocoreManager"]

logger = logging.getLogger(__name__)

ROBOTOCORE_DEFAULT_URL = "http://localhost:4566"
ROBOTOCORE_IMAGE = "ghcr.io/robotocore/robotocore:latest"
_CONTAINER_NAME = "gui4aws-robotocore"

_FAKE_KEY_ID = "testing"
_FAKE_SECRET = "testing"
_FAKE_TOKEN = "testing"
_FAKE_REGION = "us-east-1"

_ENV_VARS = {
    "AWS_ACCESS_KEY_ID": _FAKE_KEY_ID,
    "AWS_SECRET_ACCESS_KEY": _FAKE_SECRET,
    "AWS_SESSION_TOKEN": _FAKE_TOKEN,
    "AWS_DEFAULT_REGION": _FAKE_REGION,
    "AWS_CONFIG_FILE": "",
    "AWS_SHARED_CREDENTIALS_FILE": "",
}


class RobotocoreManager:
    """Start, stop, and monitor a robotocore Docker container.

    The manager uses a named container (``gui4aws-robotocore``) so that
    subsequent ``start()`` calls can reuse or remove the existing one.
    """

    def __init__(self) -> None:
        self._endpoint_url: str = ROBOTOCORE_DEFAULT_URL
        self._running: bool = False
        self.saved_env: dict[str, str | None] = {}
        self._output_lock = threading.RLock()
        self._output_lines: deque[str] = deque(maxlen=2000)
        self._log_reader_thread: threading.Thread | None = None
        self._container_name: str = _CONTAINER_NAME

    @property
    def running(self) -> bool:
        return self._running

    @property
    def endpoint_url(self) -> str:
        return self._endpoint_url

    # ── Public API ────────────────────────────────────────────────────────────

    def start(self, endpoint_url: str | None = None, timeout: float = 120.0) -> None:
        """Connect to or launch robotocore at *endpoint_url*.

        Decision tree
        -------------
        1. If the manager already considers itself running → no-op.
        2. Probe the URL with a short timeout.  If it responds, adopt it as
           already-running (the container was started externally, or survived a
           previous timeout).  No ``docker run`` needed.
        3. Otherwise run ``docker run -d`` and wait up to *timeout* seconds for
           the endpoint to respond.  The long default covers a first-time image
           pull that Docker performs implicitly.

        Raises RuntimeError if Docker is unavailable or the endpoint does not
        respond within *timeout* seconds.
        """
        if self._running:
            return

        url = endpoint_url or ROBOTOCORE_DEFAULT_URL
        self._endpoint_url = url

        # ── Step 1: probe for an already-running instance ─────────────────────
        if self._is_reachable(probe_timeout=2.0):
            self._append_output(f"=== robotocore already running at {url} — adopting ===")
            self._inject_credentials()
            self._running = True
            logger.info("robotocore adopted at %s", url)
            return

        # ── Step 2: launch a new container ────────────────────────────────────
        self._clear_output()
        self._append_output(f"=== starting robotocore at {url} ===")
        self._append_output(f"(waiting up to {timeout}s — first run may pull the image)")

        self._docker_run(url)
        self._inject_credentials()

        try:
            self._wait_ready(timeout)
        except RuntimeError as exc:
            output = self.output_text(max_lines=80)
            # Don't stop the container — it may still be pulling the image.
            # Just reset Python state so the user can retry.
            self._restore_credentials()
            raise RuntimeError(
                f"robotocore did not respond within {timeout}s at {url}.\n"
                "The container may still be starting (first-run image pull can take a minute).\n"
                "Click Start Robotocore again to reconnect once it is ready.\n\n"
                f"Output:\n{output or '(none)'}"
            ) from exc

        self._running = True
        self._append_output(f"=== robotocore ready at {url} ===")
        logger.info("robotocore running at %s", url)

    def stop(self) -> None:
        """Stop and remove the robotocore Docker container."""
        self._append_output("=== stopping robotocore ===")
        self._docker_stop()
        if self.saved_env:
            self._restore_credentials()
        self._running = False
        self._append_output("=== robotocore stopped ===")
        logger.info("robotocore stopped")

    def restart(self, endpoint_url: str | None = None, timeout: float = 30.0) -> None:
        """Stop then start robotocore."""
        self.stop()
        self.start(endpoint_url=endpoint_url, timeout=timeout)

    def reset_state(self) -> None:
        """POST /_localstack/state/reset to wipe all state without restarting the container.

        Raises RuntimeError if robotocore is not running or the request fails.
        """
        if not self._running:
            raise RuntimeError("Robotocore is not running")
        url = f"{self._endpoint_url}/_localstack/state/reset"
        req = urllib.request.Request(url, method="POST", data=b"")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:  # nosec B310
                body = resp.read()

                self._append_output(f"=== robotocore state reset: {resp.status} {body!r} ===")
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"Robotocore reset failed: HTTP {exc.code}") from exc
        except OSError as exc:
            raise RuntimeError(f"Robotocore reset failed: {exc}") from exc

    def pull(self) -> None:
        """Pull the latest robotocore Docker image in the background.

        Output is captured to the log. Raises RuntimeError if Docker is
        not available.
        """
        self._append_output(f"=== pulling {ROBOTOCORE_IMAGE} ===")
        try:
            proc = subprocess.Popen(
                ["docker", "pull", ROBOTOCORE_IMAGE],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
        except FileNotFoundError as exc:
            raise RuntimeError("docker not found — is Docker Desktop installed and running?") from exc
        if proc.stdout:
            for line in proc.stdout:
                text = line.rstrip()
                if text:
                    self._append_output(text)
        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"docker pull exited with code {proc.returncode}")
        self._append_output("=== pull complete ===")

    def output_text(self, *, max_lines: int | None = None) -> str:
        with self._output_lock:
            lines = list(self._output_lines)
        if max_lines is not None:
            lines = lines[-max_lines:]
        return "\n".join(lines)

    def snapshot(self) -> dict[str, Any]:
        with self._output_lock:
            lines = list(self._output_lines)
        return {
            "running": self._running,
            "endpoint_url": self._endpoint_url,
            "container_name": self._container_name,
            "output_line_count": len(lines),
            "recent_output": lines[-50:],
        }

    # ── Docker helpers ────────────────────────────────────────────────────────

    def _docker_run(self, url: str) -> None:
        # Parse port from URL (e.g. http://localhost:4566 → 4566).
        try:
            port = url.split(":")[-1].strip("/") or "4566"
        except Exception:
            port = "4566"

        # Remove any existing stopped container with the same name.
        subprocess.run(
            ["docker", "rm", "-f", self._container_name],
            capture_output=True,
            check=False,
        )

        cmd = [
            "docker", "run", "-d",
            "--name", self._container_name,
            "-p", f"{port}:4566",
            ROBOTOCORE_IMAGE,
        ]
        self._append_output("$ " + " ".join(cmd))
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", check=False)
        except FileNotFoundError as exc:
            raise RuntimeError("docker not found — is Docker Desktop installed and running?") from exc

        if result.stdout.strip():
            self._append_output(result.stdout.strip())
        if result.stderr.strip():
            self._append_output(result.stderr.strip())

        if result.returncode != 0:
            raise RuntimeError(
                f"docker run failed (exit {result.returncode}):\n{result.stderr.strip()}"
            )

        # Stream docker logs in background so the user can see what's happening.
        self._start_log_reader()

    def _docker_stop(self) -> None:
        for subcmd in (["docker", "stop", self._container_name],
                       ["docker", "rm", self._container_name]):
            result = subprocess.run(subcmd, capture_output=True, text=True, encoding="utf-8", check=False)
            if result.stdout.strip():
                self._append_output(result.stdout.strip())
            if result.stderr.strip():
                self._append_output(result.stderr.strip())

    def _start_log_reader(self) -> None:
        def read_logs() -> None:
            try:
                proc = subprocess.Popen(
                    ["docker", "logs", "-f", self._container_name],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                )
                if proc.stdout:
                    for line in proc.stdout:
                        text = line.rstrip()
                        if text:
                            self._append_output(text)
                        if not self._running and self._output_lines:
                            break
            except Exception as exc:
                self._append_output(f"[log reader error: {exc}]")

        self._log_reader_thread = threading.Thread(
            target=read_logs, name="robotocore-logs", daemon=True
        )
        self._log_reader_thread.start()

    # ── Health check ──────────────────────────────────────────────────────────

    def _is_reachable(self, *, probe_timeout: float = 2.0) -> bool:
        """Return True if the endpoint is already responding.

        Any HTTP response (including 4xx/5xx) means the server is up.
        Only a network-level failure (connection refused, timeout) means it is not.
        urllib raises HTTPError (a subclass of URLError) for 4xx/5xx — that
        still counts as reachable.
        """
        try:
            urllib.request.urlopen(self._endpoint_url, timeout=probe_timeout)  # nosec B310
            return True
        except urllib.error.HTTPError:
            # Server answered with an error code — it is listening.
            return True
        except (urllib.error.URLError, OSError):
            return False

    def _wait_ready(self, timeout: float) -> None:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self._is_reachable(probe_timeout=1.0):
                return
            time.sleep(0.5)
        raise RuntimeError(f"robotocore did not respond within {timeout}s")

    # ── Credential helpers ────────────────────────────────────────────────────

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

    # ── Output buffer ─────────────────────────────────────────────────────────

    def _append_output(self, line: str) -> None:
        with self._output_lock:
            self._output_lines.append(line)

    def _clear_output(self) -> None:
        with self._output_lock:
            self._output_lines.clear()
