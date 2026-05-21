"""Helpers for moto-backed tests.

We currently rely on moto's mocked-in-process backend (``mock_aws``), not the moto_server HTTP
mode. That means in tests we use boto3 directly under the decorator/context rather than
configuring an endpoint URL. Code that runs against ``moto_server`` for end-to-end style still
goes through ``EndpointMode.MOTO``.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

__all__ = ["AWS_TEST_ACCOUNT_ID", "AWS_TEST_REGION", "mock_aws_context"]

AWS_TEST_REGION = "us-east-1"
AWS_TEST_ACCOUNT_ID = "123456789012"


@contextmanager
def mock_aws_context() -> Any:
    """Yield an active ``moto.mock_aws`` context.

    Importing moto lazily means projects that don't have moto installed can still import this
    module — the call site, not the import site, sees the ImportError.
    """
    from moto import mock_aws  # local import; moto is a dev/test dep only

    with mock_aws():
        yield
