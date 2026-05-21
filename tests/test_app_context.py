"""AppContext mode / profile / region / endpoint changes."""

from __future__ import annotations

import pytest

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode


def test_default_mode_is_boto3() -> None:
    """Default AppContext is in boto3 mode."""
    context = AppContext()
    assert context.mode is ExecutionMode.BOTO3
    assert context.endpoint_config.mode is EndpointMode.AWS


def test_set_mode_changes_executor() -> None:
    """Flipping mode changes which executor we get."""
    context = AppContext()
    context.set_mode(ExecutionMode.AWS_CLI)
    assert context.mode is ExecutionMode.AWS_CLI


def test_set_endpoint_custom_requires_url() -> None:
    """Custom endpoint mode without a URL is rejected."""
    context = AppContext()
    with pytest.raises(ValueError):
        context.set_endpoint(EndpointMode.CUSTOM, None)


def test_set_endpoint_moto_defaults_to_localhost() -> None:
    """Moto endpoint with no URL falls back to 127.0.0.1:5000."""
    context = AppContext()
    context.set_endpoint(EndpointMode.MOTO)
    assert context.endpoint_config.resolved_url() == "http://127.0.0.1:5000"


def test_set_profile_to_empty_means_env() -> None:
    """Setting profile to None means rely on environment."""
    context = AppContext(profile_name="foo")
    context.set_profile(None)
    assert context.profile_name is None


def test_registry_loaded_by_default() -> None:
    """The default registry includes Aurora and Backup services."""
    context = AppContext()
    service_ids = {service.service_id for service in context.registry}
    assert "aurora" in service_ids
    assert "backup" in service_ids


def test_endpoint_config_resolved_aws_is_none() -> None:
    """EndpointMode.AWS resolves to no URL."""
    config = EndpointConfig()
    assert config.resolved_url() is None
