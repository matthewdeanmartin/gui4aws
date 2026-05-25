"""ServiceDefinition for Aurora."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition, SubAction
from gui4aws.services.aurora.actions import (
    ALL_ACTIONS,
    CREATE_DB_CLUSTER,
    CREATE_DB_CLUSTER_SNAPSHOT,
    CREATE_DB_INSTANCE,
    DELETE_DB_CLUSTER,
    DELETE_DB_INSTANCE,
    DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_INSTANCES,
    DESCRIBE_DB_PARAMETER_GROUPS,
    DESCRIBE_DB_SUBNET_GROUPS,
    FAILOVER_DB_CLUSTER,
    MODIFY_DB_CLUSTER_PASSWORD,
    REBOOT_DB_INSTANCE,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
    START_DB_CLUSTER,
    START_DB_INSTANCE,
    STOP_DB_CLUSTER,
    STOP_DB_INSTANCE,
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
            filter_fields=(InputField(name="cluster_identifier", label="Cluster identifier"),),
            row_actions=(
                RowAction(
                    action_id=CREATE_DB_CLUSTER.action_id,
                    button_label="Create Cluster",
                    prefill={},
                ),
                RowAction(
                    action_id=CREATE_DB_INSTANCE.action_id,
                    button_label="Create Instance",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id=CREATE_DB_CLUSTER_SNAPSHOT.action_id,
                    button_label="Create Snapshot",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id=START_DB_CLUSTER.action_id,
                    button_label="Start Cluster",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id=STOP_DB_CLUSTER.action_id,
                    button_label="Stop Cluster",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id=FAILOVER_DB_CLUSTER.action_id,
                    button_label="Fail Over",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id=DELETE_DB_CLUSTER.action_id,
                    button_label="Delete Cluster",
                    prefill={"cluster_identifier": "cluster_identifier"},
                ),
                RowAction(
                    action_id="backup.start_backup_job",
                    button_label="Back Up (AWS Backup)",
                    prefill={"resource_arn": "arn"},
                ),
                RowAction(
                    action_id="kms.describe_key",
                    button_label="View KMS Key",
                    prefill={"key_id": "kms_key_id"},
                ),
                RowAction(
                    action_id=MODIFY_DB_CLUSTER_PASSWORD.action_id,
                    button_label="Update Password",
                    prefill={
                        "cluster_identifier": "cluster_identifier",
                        "engine": "engine",
                        "host": "endpoint",
                    },
                ),
                RowAction(
                    action_id="sql://query",
                    button_label="Query",
                    prefill={},
                ),
            ),
            sub_action=SubAction(
                action_id=DESCRIBE_DB_INSTANCES.action_id,
                panel_label="Instances",
                prefill={"cluster_identifier": "cluster_identifier"},
                columns=("instance_identifier", "running_state", "status", "is_writer", "engine"),
                row_actions=(
                    RowAction(
                        action_id=START_DB_INSTANCE.action_id,
                        button_label="Start Instance",
                        prefill={"instance_identifier": "instance_identifier"},
                    ),
                    RowAction(
                        action_id=STOP_DB_INSTANCE.action_id,
                        button_label="Stop Instance",
                        prefill={"instance_identifier": "instance_identifier"},
                    ),
                    RowAction(
                        action_id=REBOOT_DB_INSTANCE.action_id,
                        button_label="Reboot Instance",
                        prefill={"instance_identifier": "instance_identifier"},
                    ),
                    RowAction(
                        action_id=DELETE_DB_INSTANCE.action_id,
                        button_label="Delete Instance",
                        prefill={"instance_identifier": "instance_identifier"},
                    ),
                ),
            ),
        ),
        NavigationItem(
            item_id="snapshots",
            display_name="Snapshots",
            default_action_id=DESCRIBE_DB_CLUSTER_SNAPSHOTS.action_id,
            filter_fields=(
                InputField(name="cluster_identifier", label="Cluster identifier"),
                InputField(name="snapshot_identifier", label="Snapshot identifier"),
            ),
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
            filter_fields=(InputField(name="instance_identifier", label="Instance identifier"),),
            row_actions=(
                RowAction(
                    action_id=CREATE_DB_INSTANCE.action_id,
                    button_label="Create Instance",
                    prefill={},
                ),
                RowAction(
                    action_id=START_DB_INSTANCE.action_id,
                    button_label="Start Instance",
                    prefill={"instance_identifier": "instance_identifier"},
                ),
                RowAction(
                    action_id=STOP_DB_INSTANCE.action_id,
                    button_label="Stop Instance",
                    prefill={"instance_identifier": "instance_identifier"},
                ),
                RowAction(
                    action_id=REBOOT_DB_INSTANCE.action_id,
                    button_label="Reboot Instance",
                    prefill={"instance_identifier": "instance_identifier"},
                ),
                RowAction(
                    action_id=DELETE_DB_INSTANCE.action_id,
                    button_label="Delete Instance",
                    prefill={"instance_identifier": "instance_identifier"},
                ),
            ),
        ),
        NavigationItem(
            item_id="db_subnet_groups",
            display_name="DB Subnet Groups",
            default_action_id=DESCRIBE_DB_SUBNET_GROUPS.action_id,
            filter_fields=(InputField(name="subnet_group_name", label="DB subnet group name"),),
        ),
        NavigationItem(
            item_id="db_parameter_groups",
            display_name="DB Parameter Groups",
            default_action_id=DESCRIBE_DB_PARAMETER_GROUPS.action_id,
            filter_fields=(InputField(name="parameter_group_name", label="DB parameter group name"),),
        ),
        NavigationItem(
            item_id="db_cluster_parameter_groups",
            display_name="DB Cluster Parameter Groups",
            default_action_id=DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS.action_id,
            filter_fields=(InputField(name="cluster_parameter_group_name", label="DB cluster parameter group name"),),
        ),
    ),
    actions=ALL_ACTIONS,
)
