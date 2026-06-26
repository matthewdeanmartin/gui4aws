"""Positive verification that a demo-seeding target is a local emulator.

Creating demo resources on **real AWS** would make real, billable infrastructure
— so it must be impossible. This module is the code-level guard: before any demo
resource is written, the target endpoint is *probed* for a Moto- or
Robotocore/LocalStack-specific signature that real AWS does not expose.

The seeding entry point will not create anything unless it holds a
:class:`VerifiedEmulator` produced here. There is deliberately **no** way to
obtain one for an ``https://*.amazonaws.com`` endpoint.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass
from enum import Enum

__all__ = [
    "EmulatorBackend",
    "EmulatorVerificationError",
    "VerifiedEmulator",
    "verify_emulator",
]

logger = logging.getLogger(__name__)

# Probe budget. Local emulators answer near-instantly; a slow/absent response is
# treated as "not an emulator" rather than waited on.
_PROBE_TIMEOUT = 3.0


class EmulatorBackend(str, Enum):
    """A local AWS emulator that demo seeding is allowed to target."""

    MOTO = "moto"
    ROBOTOCORE = "robotocore"


@dataclass(frozen=True)
class VerifiedEmulator:
    """Proof token that ``endpoint_url`` was confirmed to be a local emulator.

    Only :func:`verify_emulator` constructs this. ``seed_demo_resources``
    requires one, so demo data can never be written to an unverified target.
    """

    backend: EmulatorBackend
    endpoint_url: str

    @property
    def is_robotocore(self) -> bool:
        """True when the verified backend is Robotocore (richer demo data)."""
        return self.backend is EmulatorBackend.ROBOTOCORE


class EmulatorVerificationError(RuntimeError):
    """Raised when an endpoint cannot be positively confirmed as a local emulator."""


def _http_get(url: str, *, timeout: float) -> tuple[int, bytes]:
    """GET *url*, returning ``(status, body)``. Raises on network failure."""
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # nosec B310 - fixed localhost emulator probe
        return resp.status, resp.read()


def _looks_like_aws(endpoint_url: str) -> bool:
    """Cheap belt-and-suspenders reject of obvious real-AWS endpoints."""
    lowered = endpoint_url.lower()
    return "amazonaws.com" in lowered or "amazonaws.com.cn" in lowered


def _probe_moto(endpoint_url: str) -> bool:
    """True if ``{endpoint}/moto-api/`` answers — a path real AWS never serves."""
    url = endpoint_url.rstrip("/") + "/moto-api/"
    try:
        status, _ = _http_get(url, timeout=_PROBE_TIMEOUT)
    except urllib.error.HTTPError as exc:
        # moto historically answers 200 here; any non-2xx means "not moto".
        logger.debug("moto probe %s -> HTTP %s", url, exc.code)
        return False
    except (urllib.error.URLError, OSError) as exc:
        logger.debug("moto probe %s failed: %s", url, exc)
        return False
    return 200 <= status < 300


def _probe_robotocore(endpoint_url: str) -> bool:
    """True if ``{endpoint}/_localstack/health`` answers with LocalStack-shaped JSON."""
    url = endpoint_url.rstrip("/") + "/_localstack/health"
    try:
        status, body = _http_get(url, timeout=_PROBE_TIMEOUT)
    except (urllib.error.URLError, OSError) as exc:
        logger.debug("robotocore probe %s failed: %s", url, exc)
        return False
    if not 200 <= status < 300:
        return False
    try:
        payload = json.loads(body.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return False
    # LocalStack/Robotocore health reports a "services" (and usually "version") map.
    return isinstance(payload, dict) and "services" in payload


def verify_emulator(endpoint_url: str | None) -> VerifiedEmulator:
    """Probe *endpoint_url* and confirm it is a Moto or Robotocore emulator.

    Args:
        endpoint_url: The resolved endpoint the demo data would be written to.

    Returns:
        A :class:`VerifiedEmulator` proof token.

    Raises:
        EmulatorVerificationError: If no URL is given, the URL looks like real
            AWS, or neither emulator signature is found.
    """
    if not endpoint_url:
        raise EmulatorVerificationError(
            "Demo seeding requires a local emulator endpoint. Start Moto or Robotocore first."
        )
    if _looks_like_aws(endpoint_url):
        raise EmulatorVerificationError(f"Refusing to seed demo resources: {endpoint_url} is a real AWS endpoint.")

    if _probe_moto(endpoint_url):
        logger.info("verified Moto emulator at %s", endpoint_url)
        return VerifiedEmulator(EmulatorBackend.MOTO, endpoint_url)
    if _probe_robotocore(endpoint_url):
        logger.info("verified Robotocore emulator at %s", endpoint_url)
        return VerifiedEmulator(EmulatorBackend.ROBOTOCORE, endpoint_url)

    raise EmulatorVerificationError(
        f"Could not confirm {endpoint_url} is a Moto or Robotocore emulator. "
        "Demo seeding is only allowed against a verified local emulator."
    )
