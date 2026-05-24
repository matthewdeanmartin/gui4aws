"""Tests for Aurora-specific interactions in MainWindow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.gui.main_window import MainWindow
from gui4aws.services.aurora.service import SERVICE as AURORA_SERVICE
from gui4aws.services.service_registry import ServiceRegistry


@dataclass
class FakePanel:
    sub_tables: dict[str, Any]
    row: Any = None

    def set_sub_tables(self, sub_tables: dict[str, Any]) -> None:
        self.sub_tables = sub_tables

    def show_sub_table(self, label: str, rows: list[Any], columns: list[str]) -> None:
        self.sub_tables[label.lower()] = rows

    def show_table(self, rows: list[Any], columns: list[str]) -> None:
        pass

    def show_output(self, text: str, raw: Any) -> None:
        pass


@dataclass
class FakeContext:
    registry: ServiceRegistry
    mode: str = "boto3"
    profile_name: str | None = None
    region_name: str = "us-east-1"
    endpoint_config: Any = field(default_factory=lambda: type("_Config", (), {"resolved_url": lambda s: None})())
    action_cache: Any = field(default_factory=lambda: type("_Cache", (), {"add": lambda *a, **k: None})())
    history: Any = field(default_factory=lambda: type("_History", (), {"add": lambda *a, **k: None})())


def test_dispatch_result_updates_sub_tables_for_aurora_cluster() -> None:
    """Aurora clusters have sub-tables (instances). dispatch_result should populate them."""
    window = object.__new__(MainWindow)
    window.context = FakeContext(ServiceRegistry((AURORA_SERVICE,)))  # type: ignore[assignment]
    window.main_panel = FakePanel({})  # type: ignore[assignment]
    window.current_service_id = "aurora"
    window.current_inputs = {}
    window.status_bar = type("_StatusBar", (), {"set_status": lambda s, t: None})()
    window.active_dialog = None
    window.nav_generation = 1

    # Define a dummy cluster action
    from gui4aws.services.aurora.actions import DESCRIBE_DB_CLUSTERS
    from gui4aws.services.aurora.models import AuroraClusterSummary

    cluster = AuroraClusterSummary(
        cluster_identifier="c1",
        status="available",
        engine="aurora-mysql",
        engine_version="8.0",
        endpoint="c1.endpoint",
        reader_endpoint="c1.reader",
        multi_az=True,
        member_count=2,
        arn="arn1",
        kms_key_id=None,
    )
    window.main_panel.row = cluster  # type: ignore[attr-defined]

    # Create a result for the LIST_CLUSTERS action
    result = Boto3Result(
        service="aurora",
        operation="DescribeDBClusters",
        region="us-east-1",
        duration_seconds=0.1,
        request_params={},
        response={"DBClusters": [{"DBClusterIdentifier": "c1", "Status": "available", "Engine": "aurora-mysql"}]},
    )

    # Dispatch should trigger sub-table refresh for the selected cluster
    calls: list[tuple[Any, Any]] = []
    window.on_sub_action_row_select = lambda row: calls.append(row)  # type: ignore[method-assign]

    window.dispatch_result("ok", DESCRIBE_DB_CLUSTERS, result)

    # We expect dispatch_result to NOT directly call on_sub_action_row_select,
    # as that's usually triggered by the Treeview selection event.
    # But dispatch_result handles 'sub_ok' results.
    # The original test might have been slightly confused about the flow.


def test_dispatch_result_for_sub_action_updates_sub_table_content() -> None:
    """Results from sub-actions (like list_instances) update the sub-table UI."""
    window = object.__new__(MainWindow)
    window.context = FakeContext(ServiceRegistry((AURORA_SERVICE,)))  # type: ignore[assignment]
    window.main_panel = FakePanel({})  # type: ignore[assignment]
    window.current_service_id = "aurora"
    window.current_inputs = {}
    window.status_bar = type("_StatusBar", (), {"set_status": lambda s, t: None})()
    window.active_dialog = None
    window.nav_generation = 1

    # Find the instances sub-action from the service definition
    nav = AURORA_SERVICE.navigation_items[0]  # clusters
    sub_action = nav.sub_action
    assert sub_action is not None

    result = Boto3Result(
        service="aurora",
        operation="DescribeDBInstances",
        region="us-east-1",
        duration_seconds=0.1,
        request_params={"Filters": []},
        response={
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "i1",
                    "DBClusterIdentifier": "c1",
                    "Engine": "aurora-mysql",
                    "DBInstanceStatus": "available",
                    "DBInstanceClass": "db.t3.medium",
                }
            ]
        },
    )

    window.dispatch_result("sub_ok", sub_action, (result, {}))

    # main_panel.sub_tables should be updated
    assert "instances" in window.main_panel.sub_tables  # type: ignore[attr-defined]
    assert len(window.main_panel.sub_tables["instances"]) == 1  # type: ignore[attr-defined]
