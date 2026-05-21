"""Aurora action definitions.

Phase 2 ships read-only actions plus the restore-from-snapshot definition (script generation
only; the restore is exercised in phase 4).
"""

from __future__ import annotations

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.aurora.views import (
    to_cluster_snapshot_summaries,
    to_cluster_summaries,
    to_instance_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_DB_CLUSTER_SNAPSHOT",
    "DESCRIBE_DB_CLUSTERS",
    "DESCRIBE_DB_CLUSTER_SNAPSHOTS",
    "DESCRIBE_DB_INSTANCES",
    "RESTORE_DB_CLUSTER_FROM_SNAPSHOT",
]


DESCRIBE_DB_CLUSTERS = ActionDefinition(
    action_id="aurora.describe_db_clusters",
    display_name="Describe DB clusters",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=False,
            help_text="Filter to a single cluster (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-clusters",
        arg_map={"cluster_identifier": "db-cluster-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_clusters",
        param_map={"cluster_identifier": "DBClusterIdentifier"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=(
            "cluster_identifier",
            "engine",
            "engine_version",
            "status",
            "endpoint",
            "reader_endpoint",
            "member_count",
        ),
        title="Aurora clusters",
    ),
    iam_permissions=("rds:DescribeDBClusters",),
    description="List Aurora DB clusters in the current region.",
    view=to_cluster_summaries,
)


DESCRIBE_DB_CLUSTER_SNAPSHOTS = ActionDefinition(
    action_id="aurora.describe_db_cluster_snapshots",
    display_name="Describe DB cluster snapshots",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=False,
            help_text="Filter to snapshots from one cluster (optional).",
        ),
        InputField(
            name="snapshot_identifier",
            label="Snapshot identifier",
            required=False,
            help_text="Filter to one snapshot (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-cluster-snapshots",
        arg_map={
            "cluster_identifier": "db-cluster-identifier",
            "snapshot_identifier": "db-cluster-snapshot-identifier",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_cluster_snapshots",
        param_map={
            "cluster_identifier": "DBClusterIdentifier",
            "snapshot_identifier": "DBClusterSnapshotIdentifier",
        },
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=(
            "snapshot_identifier",
            "cluster_identifier",
            "engine",
            "engine_version",
            "status",
            "snapshot_type",
            "percent_progress",
        ),
        title="Aurora cluster snapshots",
    ),
    iam_permissions=("rds:DescribeDBClusterSnapshots",),
    description="List Aurora DB cluster snapshots.",
    view=to_cluster_snapshot_summaries,
)


DESCRIBE_DB_INSTANCES = ActionDefinition(
    action_id="aurora.describe_db_instances",
    display_name="Describe DB instances",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="instance_identifier",
            label="Instance identifier",
            required=False,
            help_text="Filter to one instance (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-instances",
        arg_map={"instance_identifier": "db-instance-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_instances",
        param_map={"instance_identifier": "DBInstanceIdentifier"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=(
            "instance_identifier",
            "cluster_identifier",
            "engine",
            "instance_class",
            "status",
            "is_writer",
        ),
        title="Aurora cluster member instances",
    ),
    iam_permissions=("rds:DescribeDBInstances",),
    description="List Aurora cluster member instances.",
    view=to_instance_summaries,
)


RESTORE_DB_CLUSTER_FROM_SNAPSHOT = ActionDefinition(
    action_id="aurora.restore_db_cluster_from_snapshot",
    display_name="Restore DB cluster from snapshot",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="new_cluster_identifier",
            label="New cluster identifier",
            required=True,
        ),
        InputField(
            name="snapshot_identifier",
            label="Source snapshot identifier (ARN ok)",
            required=True,
        ),
        InputField(
            name="engine",
            label="Engine",
            kind="choice",
            choices=("aurora-mysql", "aurora-postgresql"),
            required=True,
        ),
        InputField(name="engine_version", label="Engine version"),
        InputField(name="db_subnet_group_name", label="DB subnet group"),
        InputField(name="vpc_security_group_ids", label="VPC security group IDs (comma-sep)"),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="restore-db-cluster-from-snapshot",
        arg_map={
            "new_cluster_identifier": "db-cluster-identifier",
            "snapshot_identifier": "snapshot-identifier",
            "engine": "engine",
            "engine_version": "engine-version",
            "db_subnet_group_name": "db-subnet-group-name",
            "vpc_security_group_ids": "vpc-security-group-ids",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="restore_db_cluster_from_snapshot",
        param_map={
            "new_cluster_identifier": "DBClusterIdentifier",
            "snapshot_identifier": "SnapshotIdentifier",
            "engine": "Engine",
            "engine_version": "EngineVersion",
            "db_subnet_group_name": "DBSubnetGroupName",
            "vpc_security_group_ids": "VpcSecurityGroupIds",
        },
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.RAW_JSON,
        title="Restore result",
    ),
    iam_permissions=(
        "rds:RestoreDBClusterFromSnapshot",
        "rds:DescribeDBClusters",
    ),
    description=(
        "Create a new Aurora DB cluster from an existing DB cluster snapshot. Does not "
        "automatically redirect applications — see the generated runbook for follow-up steps."
    ),
)


CREATE_DB_CLUSTER_SNAPSHOT = ActionDefinition(
    action_id="aurora.create_db_cluster_snapshot",
    display_name="Create DB cluster snapshot",
    service_id="aurora",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Source cluster identifier",
            required=True,
        ),
        InputField(
            name="snapshot_identifier",
            label="New snapshot identifier",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="create-db-cluster-snapshot",
        arg_map={
            "cluster_identifier": "db-cluster-identifier",
            "snapshot_identifier": "db-cluster-snapshot-identifier",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="create_db_cluster_snapshot",
        param_map={
            "cluster_identifier": "DBClusterIdentifier",
            "snapshot_identifier": "DBClusterSnapshotIdentifier",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Snapshot result"),
    iam_permissions=("rds:CreateDBClusterSnapshot",),
    description="Create a new manual snapshot of an Aurora DB cluster.",
)


ALL_ACTIONS = (
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_INSTANCES,
    CREATE_DB_CLUSTER_SNAPSHOT,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
)
