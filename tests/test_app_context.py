"""AppContext mode / profile / region / endpoint changes."""

from __future__ import annotations

from typing import Any

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


class FakeStsClient:
    """Small STS double for account identity tests."""

    def get_caller_identity(self) -> dict[str, str]:
        """Return a stable fake caller identity."""
        return {
            "Account": "123456789012",
            "Arn": "arn:aws:sts::123456789012:assumed-role/Admin/gui4aws",
            "UserId": "AROATEST:gui4aws",
        }


def test_get_account_identity_uses_current_context(monkeypatch: Any) -> None:
    """STS caller identity is wrapped with the active toolbar connection settings."""
    requested_services: list[str] = []

    def fake_build_client(_self: Any, service_name: str) -> FakeStsClient:
        requested_services.append(service_name)
        return FakeStsClient()

    monkeypatch.setattr("gui4aws.execution.boto3_executor.Boto3Executor.build_client", fake_build_client)
    context = AppContext(profile_name="dev", region_name="us-west-2")
    context.set_endpoint(EndpointMode.ROBOTOCORE, "http://localhost:4566")

    identity = context.get_account_identity()

    assert requested_services == ["sts"]
    assert identity.account_id == "123456789012"
    assert identity.region == "us-west-2"
    assert identity.profile == "dev"
    assert identity.target == "Robotocore"
    assert identity.endpoint_url == "http://localhost:4566"
