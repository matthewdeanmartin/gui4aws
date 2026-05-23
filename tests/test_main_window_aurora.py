"""Aurora-specific MainWindow helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.gui.main_window import MainWindow
from gui4aws.services.aurora.service import SERVICE as AURORA_SERVICE
from gui4aws.services.service_registry import ServiceRegistry


@dataclass
class _FakePanel:
    sub_tables: list[tuple[str, list[Any], list[str]]] = field(default_factory=list)

    def show_sub_table(self, label: str, rows: list[Any], columns: list[str]) -> None:
        self.sub_tables.append((label, list(rows), list(columns)))


@dataclass
class _FakeContext:
    registry: ServiceRegistry


def test_dispatch_result_filters_aurora_sub_table_rows_to_selected_cluster() -> None:
    """Aurora's sub-table follows the selected cluster instead of showing every instance."""
    window = object.__new__(MainWindow)
    window.context = _FakeContext(ServiceRegistry((AURORA_SERVICE,)))
    window.main_panel = _FakePanel()
    window._current_service_id = "aurora"
    window._nav_generation = 11

    clusters = next(item for item in AURORA_SERVICE.navigation_items if item.item_id == "clusters")
    assert clusters.sub_action is not None
    result = Boto3Result(
        service="rds",
        operation="describe_db_instances",
        region="us-east-1",
        duration_seconds=0.1,
        request_params={},
        response={
            "DBInstances": [
                {
                    "DBInstanceIdentifier": "cluster-a-1",
                    "DBClusterIdentifier": "cluster-a",
                    "Engine": "aurora-postgresql",
                    "DBInstanceClass": "db.t3.medium",
                    "DBInstanceStatus": "available",
                },
                {
                    "DBInstanceIdentifier": "cluster-b-1",
                    "DBClusterIdentifier": "cluster-b",
                    "Engine": "aurora-postgresql",
                    "DBInstanceClass": "db.t3.medium",
                    "DBInstanceStatus": "available",
                },
            ]
        },
    )

    window.dispatch_result(
        "sub_ok",
        clusters.sub_action,
        (result, {"cluster_identifier": "cluster-a"}),
        generation=11,
    )

    assert len(window.main_panel.sub_tables) == 1
    label, rows, columns = window.main_panel.sub_tables[0]
    assert label == "Instances"
    assert columns == ["instance_identifier", "running_state", "status", "is_writer", "engine"]
    assert [row.instance_identifier for row in rows] == ["cluster-a-1"]
