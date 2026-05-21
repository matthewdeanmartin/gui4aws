"""EndpointConfig tests."""

from __future__ import annotations

import pytest

from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode


def test_aws_mode_resolves_to_none() -> None:
    """Real AWS mode means no override URL."""
    assert EndpointConfig().resolved_url() is None


def test_moto_default_url() -> None:
    """Moto mode without URL defaults to the moto_server local URL."""
    assert EndpointConfig(mode=EndpointMode.MOTO).resolved_url() == "http://127.0.0.1:5000"


def test_custom_requires_url() -> None:
    """Custom mode must have a URL."""
    with pytest.raises(ValueError):
        EndpointConfig.for_mode(EndpointMode.CUSTOM, None)


def test_custom_preserves_url() -> None:
    """Custom URL is returned as-is."""
    config = EndpointConfig.for_mode(EndpointMode.CUSTOM, "http://localhost:1234")
    assert config.resolved_url() == "http://localhost:1234"
