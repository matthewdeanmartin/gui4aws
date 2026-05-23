"""Phase 4: safe-write flows end-to-end against moto."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.execution.script_generator import generate_python_script
from gui4aws.services.aurora.actions import (
    CREATE_DB_CLUSTER,
    CREATE_DB_CLUSTER_SNAPSHOT,
    CREATE_DB_INSTANCE,
    DELETE_DB_CLUSTER,
    DELETE_DB_INSTANCE,
    DESCRIBE_DB_CLUSTERS,
    FAILOVER_DB_CLUSTER,
    REBOOT_DB_INSTANCE,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
    START_DB_CLUSTER,
    START_DB_INSTANCE,
    STOP_DB_CLUSTER,
    STOP_DB_INSTANCE,
)
from gui4aws.services.backup.actions import (
    CREATE_BACKUP_PLAN,
    CREATE_BACKUP_VAULT,
    DELETE_BACKUP_PLAN,
    DELETE_BACKUP_VAULT,
    LIST_BACKUP_VAULTS,
    UPDATE_BACKUP_PLAN,
)


def test_create_db_cluster_snapshot_then_restore_creates_new_cluster(mock_aws_env: None) -> None:
    """Phase 4 acceptance #1: restore Aurora from snapshot end-to-end on moto."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="src-cluster",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
    )
    context = AppContext(region_name="us-east-1")

    snap_result = context.execute(
        CREATE_DB_CLUSTER_SNAPSHOT,
        inputs={"cluster_identifier": "src-cluster", "snapshot_identifier": "src-snap"},
    )
    assert isinstance(snap_result, Boto3Result)

    restore_result = context.execute(
        RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
        inputs={
            "new_cluster_identifier": "restored-cluster",
            "snapshot_identifier": "src-snap",
            "engine": "aurora-postgresql",
        },
    )
    assert isinstance(restore_result, Boto3Result)

    list_result = context.execute(DESCRIBE_DB_CLUSTERS, inputs={})
    assert isinstance(list_result, Boto3Result)
    identifiers = {cluster["DBClusterIdentifier"] for cluster in list_result.response["DBClusters"]}
    assert "restored-cluster" in identifiers
    assert "src-cluster" in identifiers


def test_create_backup_vault_then_list(mock_aws_env: None) -> None:
    """Phase 4 acceptance #2: create vault via the action, then list it back."""
    context = AppContext(region_name="us-east-1")
    create_result = context.execute(CREATE_BACKUP_VAULT, inputs={"vault_name": "phase4-vault"})
    assert isinstance(create_result, Boto3Result)

    list_result = context.execute(LIST_BACKUP_VAULTS, inputs={})
    assert isinstance(list_result, Boto3Result)
    names = {vault["BackupVaultName"] for vault in list_result.response["BackupVaultList"]}
    assert "phase4-vault" in names


def test_restore_python_script_matches_spec_example_shape() -> None:
    """Phase 4 acceptance #3: generated restore Python matches spec §17.2 shape.

    The spec shows:

        restore_response = rds_client.restore_db_cluster_from_snapshot(
            DBClusterIdentifier="restored-cluster",
            SnapshotIdentifier="arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot",
            Engine="aurora-postgresql",
        )

    We assert the call name, the three PascalCase kwargs, and the boto3 client construction.
    """
    inputs = {
        "new_cluster_identifier": "restored-cluster",
        "snapshot_identifier": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot",
        "engine": "aurora-postgresql",
    }
    text = generate_python_script(
        RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
        inputs=inputs,
        profile_name="default",
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "import boto3" in text
    assert "session = boto3.Session(profile_name='default', region_name='us-east-1')" in text
    assert 'session.client("rds")' in text
    assert "client.restore_db_cluster_from_snapshot(" in text
    assert "DBClusterIdentifier='restored-cluster'" in text
    assert "SnapshotIdentifier='arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot'" in text
    assert "Engine='aurora-postgresql'" in text


def test_aurora_service_exposes_write_navigation() -> None:
    """Write actions for Aurora are row-action buttons, not sidebar entries."""
    from gui4aws.services.aurora.service import SERVICE

    # Sidebar has only list/describe entries — no form-only items.
    item_ids = {item.item_id for item in SERVICE.navigation_items}
    assert "create_snapshot" not in item_ids
    assert "restore_from_snapshot" not in item_ids

    # Cluster actions stay on the selected cluster row.
    clusters = next(item for item in SERVICE.navigation_items if item.item_id == "clusters")
    cluster_action_ids = {ra.action_id for ra in clusters.row_actions}
    assert CREATE_DB_CLUSTER.action_id in cluster_action_ids
    assert CREATE_DB_INSTANCE.action_id in cluster_action_ids
    assert CREATE_DB_CLUSTER_SNAPSHOT.action_id in cluster_action_ids
    assert START_DB_CLUSTER.action_id in cluster_action_ids
    assert STOP_DB_CLUSTER.action_id in cluster_action_ids
    assert FAILOVER_DB_CLUSTER.action_id in cluster_action_ids
    assert DELETE_DB_CLUSTER.action_id in cluster_action_ids
    assert clusters.sub_action is not None
    instance_action_ids = {ra.action_id for ra in clusters.sub_action.row_actions}
    assert START_DB_INSTANCE.action_id in instance_action_ids
    assert STOP_DB_INSTANCE.action_id in instance_action_ids
    assert REBOOT_DB_INSTANCE.action_id in instance_action_ids
    assert DELETE_DB_INSTANCE.action_id in instance_action_ids

    # Restore is a row action on Snapshots.
    snapshots = next(item for item in SERVICE.navigation_items if item.item_id == "snapshots")
    assert any(ra.action_id == RESTORE_DB_CLUSTER_FROM_SNAPSHOT.action_id for ra in snapshots.row_actions)

    # Top-level Instances keeps the same instance actions on the root list.
    instances = next(item for item in SERVICE.navigation_items if item.item_id == "instances")
    top_level_instance_actions = {ra.action_id for ra in instances.row_actions}
    assert CREATE_DB_INSTANCE.action_id in top_level_instance_actions
    assert instance_action_ids <= top_level_instance_actions

    standalone_nav_ids = {item.item_id for item in SERVICE.navigation_items}
    assert "db_subnet_groups" in standalone_nav_ids
    assert "db_parameter_groups" in standalone_nav_ids
    assert "db_cluster_parameter_groups" in standalone_nav_ids


def test_backup_service_exposes_create_vault_navigation() -> None:
    """Backup vault and plan write actions stay on the list views."""
    from gui4aws.services.backup.service import SERVICE

    item_ids = {item.item_id for item in SERVICE.navigation_items}
    assert "create_vault" not in item_ids

    vaults = next(item for item in SERVICE.navigation_items if item.item_id == "vaults")
    assert any(ra.action_id == CREATE_BACKUP_VAULT.action_id for ra in vaults.row_actions)
    assert any(ra.action_id == DELETE_BACKUP_VAULT.action_id for ra in vaults.row_actions)

    plans = next(item for item in SERVICE.navigation_items if item.item_id == "plans")
    plan_action_ids = {ra.action_id for ra in plans.row_actions}
    assert CREATE_BACKUP_PLAN.action_id in plan_action_ids
    assert UPDATE_BACKUP_PLAN.action_id in plan_action_ids
    assert DELETE_BACKUP_PLAN.action_id in plan_action_ids
