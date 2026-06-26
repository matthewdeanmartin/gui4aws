"""Tests for the emulator-verification guard that keeps demo data off real AWS."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from gui4aws.demo_resources.verification import (
    EmulatorBackend,
    EmulatorVerificationError,
    verify_emulator,
)


class _Handler(BaseHTTPRequestHandler):
    # Set per-server: which signature this fake endpoint exposes.
    flavor = "none"

    def log_message(self, *args: object) -> None:  # silence test server noise
        del args

    def do_GET(self) -> None:  # BaseHTTPRequestHandler API requires this name
        flavor = type(self).flavor
        if flavor == "moto" and self.path.rstrip("/") == "/moto-api":
            self._ok(b"<html>moto dashboard</html>")
        elif flavor == "robotocore" and self.path == "/_localstack/health":
            self._ok(json.dumps({"services": {"s3": "running"}, "version": "x"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def _ok(self, body: bytes) -> None:
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _serve(flavor: str) -> Iterator[str]:
    handler = type(f"_H_{flavor}", (_Handler,), {"flavor": flavor})
    server = HTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


@pytest.fixture
def moto_endpoint() -> Iterator[str]:
    yield from _serve("moto")


@pytest.fixture
def robotocore_endpoint() -> Iterator[str]:
    yield from _serve("robotocore")


@pytest.fixture
def blank_endpoint() -> Iterator[str]:
    # Responds 404 to everything — looks like a generic server, not an emulator.
    yield from _serve("none")


def test_verifies_moto(moto_endpoint: str) -> None:
    verified = verify_emulator(moto_endpoint)
    assert verified.backend is EmulatorBackend.MOTO
    assert verified.is_robotocore is False
    assert verified.endpoint_url == moto_endpoint


def test_verifies_robotocore(robotocore_endpoint: str) -> None:
    verified = verify_emulator(robotocore_endpoint)
    assert verified.backend is EmulatorBackend.ROBOTOCORE
    assert verified.is_robotocore is True


def test_rejects_none_url() -> None:
    with pytest.raises(EmulatorVerificationError):
        verify_emulator(None)


def test_rejects_real_aws_url_without_probing() -> None:
    # Should never even attempt to connect to a real AWS endpoint.
    with pytest.raises(EmulatorVerificationError, match="real AWS"):
        verify_emulator("https://rds.us-east-1.amazonaws.com")


def test_rejects_unrecognized_endpoint(blank_endpoint: str) -> None:
    # A reachable server that isn't moto/robotocore must be refused.
    with pytest.raises(EmulatorVerificationError, match="Moto or Robotocore"):
        verify_emulator(blank_endpoint)


def test_rejects_unreachable_endpoint() -> None:
    # Nothing listening here -> not verifiable.
    with pytest.raises(EmulatorVerificationError):
        verify_emulator("http://127.0.0.1:1")
