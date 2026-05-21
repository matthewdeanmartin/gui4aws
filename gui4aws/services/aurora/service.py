"""ServiceDefinition for Aurora."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.aurora.actions import (
    ALL_ACTIONS,
    CREATE_DB_CLUSTER_SNAPSHOT,
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_INSTANCES,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="aurora",
    display_name="Aurora",
    boto3_service_name="rds",
    cli_service_name="rds",
    navigation_items=(
        NavigationItem(
            item_id="clusters",
            display_name="Clusters",
            default_action_id=DESCRIBE_DB_CLUSTERS.action_id,
            row_actions=(
                RowAction(
                    action_id=CREATE_DB_CLUSTER_SNAPSHOT.action_id,
                    button_label="Create Snapshot",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
            ),
        ),
        NavigationItem(
            item_id="snapshots",
            display_name="Snapshots",
            default_action_id=DESCRIBE_DB_CLUSTER_SNAPSHOTS.action_id,
            row_actions=(
                RowAction(
                    action_id=RESTORE_DB_CLUSTER_FROM_SNAPSHOT.action_id,
                    button_label="Restore from Snapshot",
                    prefill={"snapshot_identifier": "snapshot_identifier"},
                ),
            ),
        ),
        NavigationItem(
            item_id="instances",
            display_name="Instances",
            default_action_id=DESCRIBE_DB_INSTANCES.action_id,
        ),
    ),
    actions=ALL_ACTIONS,
)
