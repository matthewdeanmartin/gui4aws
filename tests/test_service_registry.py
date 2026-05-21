"""Service registry tests."""

from __future__ import annotations

import pytest

from gui4aws.models import NavigationItem, ServiceDefinition
from gui4aws.services.service_registry import ServiceRegistry, default_registry


def test_default_registry_has_aurora_and_backup() -> None:
    """Both phase-1 services are loaded by default."""
    registry = default_registry()
    service_ids = {service.service_id for service in registry}
    assert "aurora" in service_ids
    assert "backup" in service_ids


def test_aurora_has_clusters_navigation() -> None:
    """Aurora's sidebar entry exposes a Clusters item with a default action."""
    registry = default_registry()
    aurora = registry.get("aurora")
    clusters = next(item for item in aurora.navigation_items if item.item_id == "clusters")
    assert clusters.default_action_id == "aurora.describe_db_clusters"


def test_double_register_rejected() -> None:
    """Registering the same service_id twice raises."""
    registry = ServiceRegistry()
    fake = ServiceDefinition(
        service_id="fake",
        display_name="Fake",
        boto3_service_name="fake",
        cli_service_name="fake",
        navigation_items=(NavigationItem("only", "Only"),),
        actions=(),
    )
    registry.register(fake)
    with pytest.raises(ValueError):
        registry.register(fake)
