"""Shared fixtures for robotocore tests.

These tests require a running robotocore (Docker) container at localhost:4566.
They are intentionally NOT in the ``tests/`` folder so they are excluded from
the default ``pytest`` run and from CI.

Run locally::

    uv run pytest tests_robotocore/ -v
"""

from __future__ import annotations

import os
from collections.abc import Iterator

import pytest

from gui4aws.robotocore_server import ROBOTOCORE_DEFAULT_URL, RobotocoreManager

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_SECURITY_TOKEN", "testing")
os.environ.setdefault("AWS_SESSION_TOKEN", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")


@pytest.fixture(scope="session")
def robotocore() -> Iterator[RobotocoreManager]:
    """Connect to or start a robotocore container; skip if Docker is unavailable."""
    mgr = RobotocoreManager()
    try:
        mgr.start(timeout=120)
    except RuntimeError as exc:
        pytest.skip(f"robotocore unavailable: {exc}")
    yield mgr
    mgr.stop()


@pytest.fixture(autouse=True)
def reset_robotocore(robotocore: RobotocoreManager) -> Iterator[None]:
    """Wipe robotocore state between tests."""
    yield
    try:
        robotocore.reset_state()
    except Exception:
        pass
