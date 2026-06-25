"""Aurora action definitions."""

# pylint: disable=too-many-lines

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

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
    to_db_cluster_parameter_group_summaries,
    to_db_parameter_group_summaries,
    to_db_subnet_group_summaries,
    to_instance_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_DB_CLUSTER",
    "CREATE_DB_CLUSTER_SNAPSHOT",
    "CREATE_DB_INSTANCE",
    "DELETE_DB_CLUSTER",
    "DELETE_DB_INSTANCE",
    "DESCRIBE_DB_CLUSTERS",
    "DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS",
    "DESCRIBE_DB_CLUSTER_SNAPSHOTS",
    "DESCRIBE_DB_INSTANCES",
    "DESCRIBE_DB_PARAMETER_GROUPS",
    "DESCRIBE_DB_SUBNET_GROUPS",
    "FAILOVER_DB_CLUSTER",
    "MODIFY_DB_CLUSTER_PASSWORD",
    "REBOOT_DB_INSTANCE",
    "RESTORE_DB_CLUSTER_FROM_SNAPSHOT",
    "START_DB_CLUSTER",
    "START_DB_INSTANCE",
    "STOP_DB_CLUSTER",
    "STOP_DB_INSTANCE",
]


def truthy(value: str | None) -> bool:
    """Return True if the value represents a boolean true in the GUI or CLI."""
    return str(value or "").strip().lower() in {"true", "yes", "1", "on"}


def append_cli_value(argv: list[str], flag: str, value: str | None) -> None:
    """Append a flag and its value to argv if the value is non-empty."""
    text = str(value or "").strip()
    if text:
        argv.extend([f"--{flag}", text])


def append_cli_bool(argv: list[str], flag: str, value: str | None) -> None:
    """Append a boolean flag or its --no- counterpart to argv."""
    if value is None or not str(value).strip():
        return
    argv.append(f"--{flag}" if truthy(value) else f"--no-{flag}")


def append_cli_list(argv: list[str], flag: str, value: str | None) -> None:
    """Append a flag followed by a list of comma-separated values to argv."""
    items = [item.strip() for item in str(value or "").split(",") if item.strip()]
    if items:
        argv.append(f"--{flag}")
        argv.extend(items)


def common_cluster_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Build a base dictionary of Boto3 parameters shared by Aurora cluster operations."""
    params: dict[str, Any] = {
        "DBClusterIdentifier": inputs["cluster_identifier"],
        "Engine": inputs["engine"],
        "MasterUsername": inputs["master_username"],
        "MasterUserPassword": inputs["master_user_password"],
    }
    if inputs.get("engine_version"):
        params["EngineVersion"] = inputs["engine_version"]
    if inputs.get("db_subnet_group_name"):
        params["DBSubnetGroupName"] = inputs["db_subnet_group_name"]
    if inputs.get("vpc_security_group_ids"):
        params["VpcSecurityGroupIds"] = [
            item.strip() for item in inputs["vpc_security_group_ids"].split(",") if item.strip()
        ]
    if inputs.get("db_cluster_parameter_group_name"):
        params["DBClusterParameterGroupName"] = inputs["db_cluster_parameter_group_name"]
    if inputs.get("storage_encrypted"):
        params["StorageEncrypted"] = truthy(inputs.get("storage_encrypted"))
    if inputs.get("deletion_protection"):
        params["DeletionProtection"] = truthy(inputs.get("deletion_protection"))
    if inputs.get("enable_http_endpoint"):
        params["EnableHttpEndpoint"] = truthy(inputs.get("enable_http_endpoint"))
    return params


def cluster_scaling_params(inputs: Mapping[str, str], kind: str) -> dict[str, Any]:
    """Calculate scaling configuration parameters for Serverless v1 or v2."""
    scaling: dict[str, float] = {}
    if inputs.get("serverless_min_capacity"):
        scaling["MinCapacity"] = float(inputs["serverless_min_capacity"])
    if inputs.get("serverless_max_capacity"):
        scaling["MaxCapacity"] = float(inputs["serverless_max_capacity"])
    if not scaling:
        return {}
    if kind == "serverless-v1":
        return {"ScalingConfiguration": scaling}
    if kind == "serverless-v2":
        return {"ServerlessV2ScalingConfiguration": scaling}
    return {}


def cluster_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Map GUI inputs to Boto3 parameters for cluster creation."""
    params = common_cluster_params(inputs)
    cluster_kind = inputs.get("cluster_kind", "provisioned")
    params["EngineMode"] = "serverless" if cluster_kind == "serverless-v1" else "provisioned"
    params.update(cluster_scaling_params(inputs, cluster_kind))
    return params


def cluster_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map GUI inputs to AWS CLI arguments for cluster creation."""
    argv: list[str] = []
    append_cli_value(argv, "db-cluster-identifier", inputs.get("cluster_identifier"))
    append_cli_value(argv, "engine", inputs.get("engine"))
    cluster_kind = inputs.get("cluster_kind", "provisioned")
    append_cli_value(argv, "engine-mode", "serverless" if cluster_kind == "serverless-v1" else "provisioned")
    append_cli_value(argv, "master-username", inputs.get("master_username"))
    append_cli_value(argv, "master-user-password", inputs.get("master_user_password"))
    append_cli_value(argv, "engine-version", inputs.get("engine_version"))
    append_cli_value(argv, "db-subnet-group-name", inputs.get("db_subnet_group_name"))
    append_cli_list(argv, "vpc-security-group-ids", inputs.get("vpc_security_group_ids"))
    append_cli_value(argv, "db-cluster-parameter-group-name", inputs.get("db_cluster_parameter_group_name"))
    append_cli_bool(argv, "storage-encrypted", inputs.get("storage_encrypted"))
    append_cli_bool(argv, "deletion-protection", inputs.get("deletion_protection"))
    append_cli_bool(argv, "enable-http-endpoint", inputs.get("enable_http_endpoint"))

    min_capacity = inputs.get("serverless_min_capacity", "").strip()
    max_capacity = inputs.get("serverless_max_capacity", "").strip()
    scaling_parts = [
        part
        for part in (
            f"MinCapacity={min_capacity}" if min_capacity else "",
            f"MaxCapacity={max_capacity}" if max_capacity else "",
        )
        if part
    ]
    if scaling_parts:
        flag = (
            "scaling-configuration"
            if cluster_kind == "serverless-v1"
            else "serverless-v2-scaling-configuration" if cluster_kind == "serverless-v2" else ""
        )
        if flag:
            append_cli_value(argv, flag, ",".join(scaling_parts))
    return argv


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
            "running_state",
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


DESCRIBE_DB_SUBNET_GROUPS = ActionDefinition(
    action_id="aurora.describe_db_subnet_groups",
    display_name="Describe DB subnet groups",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="subnet_group_name",
            label="DB subnet group name",
            required=False,
            help_text="Filter to one DB subnet group (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-subnet-groups",
        arg_map={"subnet_group_name": "db-subnet-group-name"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_subnet_groups",
        param_map={"subnet_group_name": "DBSubnetGroupName"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("subnet_group_name", "vpc_id", "subnet_count", "status", "arn"),
        title="DB subnet groups",
    ),
    iam_permissions=("rds:DescribeDBSubnetGroups",),
    description="List DB subnet groups available for Aurora clusters.",
    view=to_db_subnet_group_summaries,
)


DESCRIBE_DB_PARAMETER_GROUPS = ActionDefinition(
    action_id="aurora.describe_db_parameter_groups",
    display_name="Describe DB parameter groups",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="parameter_group_name",
            label="DB parameter group name",
            required=False,
            help_text="Filter to one DB parameter group (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-parameter-groups",
        arg_map={"parameter_group_name": "db-parameter-group-name"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_parameter_groups",
        param_map={"parameter_group_name": "DBParameterGroupName"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("parameter_group_name", "family", "description", "arn"),
        title="DB parameter groups",
    ),
    iam_permissions=("rds:DescribeDBParameterGroups",),
    description="List instance-level DB parameter groups that Aurora instances can use.",
    view=to_db_parameter_group_summaries,
)


DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS = ActionDefinition(
    action_id="aurora.describe_db_cluster_parameter_groups",
    display_name="Describe DB cluster parameter groups",
    service_id="aurora",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster_parameter_group_name",
            label="DB cluster parameter group name",
            required=False,
            help_text="Filter to one cluster parameter group (optional).",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="describe-db-cluster-parameter-groups",
        arg_map={"cluster_parameter_group_name": "db-cluster-parameter-group-name"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="describe_db_cluster_parameter_groups",
        param_map={"cluster_parameter_group_name": "DBClusterParameterGroupName"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("cluster_parameter_group_name", "family", "description", "arn"),
        title="DB cluster parameter groups",
    ),
    iam_permissions=("rds:DescribeDBClusterParameterGroups",),
    description="List cluster-level parameter groups that Aurora clusters can use.",
    view=to_db_cluster_parameter_group_summaries,
)


CREATE_DB_CLUSTER = ActionDefinition(
    action_id="aurora.create_db_cluster",
    display_name="Create DB cluster",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="cluster_identifier", label="Cluster identifier", required=True),
        InputField(
            name="engine",
            label="Engine",
            kind="choice",
            choices=("aurora-mysql", "aurora-postgresql"),
            required=True,
        ),
        InputField(
            name="cluster_kind",
            label="Cluster kind",
            kind="choice",
            choices=("provisioned", "serverless-v1", "serverless-v2"),
            required=True,
            default="provisioned",
            help_text=(
                "Provisioned = normal cluster. Serverless v1 uses EngineMode=serverless. "
                "Serverless v2 stays provisioned and uses the Serverless v2 capacity fields."
            ),
        ),
        InputField(name="master_username", label="Master username", required=True, default="admin"),
        InputField(name="master_user_password", label="Master user password", required=True, is_secret=True),
        InputField(name="engine_version", label="Engine version"),
        InputField(name="db_subnet_group_name", label="DB subnet group"),
        InputField(
            name="vpc_security_group_ids",
            label="VPC security group IDs",
            kind="list",
            help_text="Comma-separated security group IDs.",
        ),
        InputField(name="db_cluster_parameter_group_name", label="DB cluster parameter group"),
        InputField(
            name="serverless_min_capacity",
            label="Serverless min capacity",
            kind="float",
            help_text="Used for serverless v1/v2 when supplied.",
        ),
        InputField(
            name="serverless_max_capacity",
            label="Serverless max capacity",
            kind="float",
            help_text="Used for serverless v1/v2 when supplied.",
        ),
        InputField(name="storage_encrypted", label="Storage encrypted", kind="bool", default="false"),
        InputField(name="deletion_protection", label="Deletion protection", kind="bool", default="false"),
        InputField(
            name="enable_http_endpoint",
            label="Enable Data API / HTTP endpoint",
            kind="bool",
            default="false",
        ),
    ),
    cli_template=CliTemplate(service="rds", command="create-db-cluster"),
    boto3_template=Boto3Template(service="rds", operation="create_db_cluster"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create cluster result"),
    iam_permissions=("rds:CreateDBCluster", "rds:DescribeDBClusters"),
    description=(
        "Create an Aurora cluster. The form surfaces provisioned clusters plus Aurora Serverless "
        "v1 and v2; serverless v2 uses the capacity range while the cluster stays provisioned."
    ),
    cache_refresh_nav_ids=("clusters", "instances"),
    cli_args_builder=cluster_cli_args,
    boto3_params_builder=cluster_boto3_params,
)


CREATE_DB_INSTANCE = ActionDefinition(
    action_id="aurora.create_db_instance",
    display_name="Create DB instance",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="instance_identifier", label="Instance identifier", required=True),
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=True,
            help_text="Aurora instances belong to a cluster; this is prefilled when a cluster is selected.",
        ),
        InputField(name="instance_class", label="DB instance class", required=True, default="db.t3.medium"),
        InputField(
            name="engine",
            label="Engine",
            kind="choice",
            choices=("aurora-mysql", "aurora-postgresql"),
            required=True,
        ),
        InputField(name="db_parameter_group_name", label="DB parameter group"),
        InputField(name="promotion_tier", label="Promotion tier", kind="int"),
        InputField(name="publicly_accessible", label="Publicly accessible", kind="bool", default="false"),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="create-db-instance",
        arg_map={
            "instance_identifier": "db-instance-identifier",
            "cluster_identifier": "db-cluster-identifier",
            "instance_class": "db-instance-class",
            "engine": "engine",
            "db_parameter_group_name": "db-parameter-group-name",
            "promotion_tier": "promotion-tier",
            "publicly_accessible": "publicly-accessible",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="create_db_instance",
        param_map={
            "instance_identifier": "DBInstanceIdentifier",
            "cluster_identifier": "DBClusterIdentifier",
            "instance_class": "DBInstanceClass",
            "engine": "Engine",
            "db_parameter_group_name": "DBParameterGroupName",
            "promotion_tier": "PromotionTier",
            "publicly_accessible": "PubliclyAccessible",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create instance result"),
    iam_permissions=("rds:CreateDBInstance", "rds:DescribeDBInstances"),
    description=(
        "Create an Aurora DB instance. Aurora instances are cluster members rather than orphaned "
        "standalone resources; use instance class db.serverless for a serverless v2 reader/writer."
    ),
    cache_refresh_nav_ids=("clusters", "instances"),
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
        InputField(
            name="vpc_security_group_ids",
            label="VPC security group IDs",
            kind="list",
            help_text="Comma-separated security group IDs.",
        ),
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
    cache_refresh_nav_ids=("clusters", "instances", "snapshots"),
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
    cache_refresh_nav_ids=("clusters", "snapshots"),
)


START_DB_CLUSTER = ActionDefinition(
    action_id="aurora.start_db_cluster",
    display_name="Start DB cluster",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="start-db-cluster",
        arg_map={"cluster_identifier": "db-cluster-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="start_db_cluster",
        param_map={"cluster_identifier": "DBClusterIdentifier"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Start cluster result"),
    iam_permissions=("rds:StartDBCluster",),
    description="Start an Aurora DB cluster that has been stopped.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


STOP_DB_CLUSTER = ActionDefinition(
    action_id="aurora.stop_db_cluster",
    display_name="Stop DB cluster",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="stop-db-cluster",
        arg_map={"cluster_identifier": "db-cluster-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="stop_db_cluster",
        param_map={"cluster_identifier": "DBClusterIdentifier"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Stop cluster result"),
    iam_permissions=("rds:StopDBCluster",),
    description="Stop an Aurora DB cluster.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


FAILOVER_DB_CLUSTER = ActionDefinition(
    action_id="aurora.failover_db_cluster",
    display_name="Fail over DB cluster",
    service_id="aurora",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=True,
        ),
        InputField(
            name="target_db_instance_identifier",
            label="Target DB instance identifier",
            required=False,
            help_text="Optional target instance to promote during failover.",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="failover-db-cluster",
        arg_map={
            "cluster_identifier": "db-cluster-identifier",
            "target_db_instance_identifier": "target-db-instance-identifier",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="failover_db_cluster",
        param_map={
            "cluster_identifier": "DBClusterIdentifier",
            "target_db_instance_identifier": "TargetDBInstanceIdentifier",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Failover result"),
    iam_permissions=("rds:FailoverDBCluster",),
    description="Force an Aurora failover to another cluster member.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


DELETE_DB_CLUSTER = ActionDefinition(
    action_id="aurora.delete_db_cluster",
    display_name="Delete DB cluster",
    service_id="aurora",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="cluster_identifier",
            label="Cluster identifier",
            required=True,
        ),
        InputField(
            name="skip_final_snapshot",
            label="Skip final snapshot",
            kind="bool",
            required=False,
            default="false",
        ),
        InputField(
            name="final_snapshot_identifier",
            label="Final snapshot identifier",
            required=False,
            help_text="Required when Skip final snapshot is false.",
        ),
        InputField(
            name="delete_automated_backups",
            label="Delete automated backups",
            kind="bool",
            required=False,
            default="true",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="delete-db-cluster",
        arg_map={
            "cluster_identifier": "db-cluster-identifier",
            "skip_final_snapshot": "skip-final-snapshot",
            "final_snapshot_identifier": "final-db-snapshot-identifier",
            "delete_automated_backups": "delete-automated-backups",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="delete_db_cluster",
        param_map={
            "cluster_identifier": "DBClusterIdentifier",
            "skip_final_snapshot": "SkipFinalSnapshot",
            "final_snapshot_identifier": "FinalDBSnapshotIdentifier",
            "delete_automated_backups": "DeleteAutomatedBackups",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete cluster result"),
    iam_permissions=("rds:DeleteDBCluster",),
    description="Delete an Aurora DB cluster. Keep final snapshot disabled only if you really want to skip it.",
    cache_refresh_nav_ids=("clusters", "instances", "snapshots"),
)


START_DB_INSTANCE = ActionDefinition(
    action_id="aurora.start_db_instance",
    display_name="Start DB instance",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="instance_identifier",
            label="Instance identifier",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="start-db-instance",
        arg_map={"instance_identifier": "db-instance-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="start_db_instance",
        param_map={"instance_identifier": "DBInstanceIdentifier"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Start instance result"),
    iam_permissions=("rds:StartDBInstance",),
    description="Start a DB instance.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


STOP_DB_INSTANCE = ActionDefinition(
    action_id="aurora.stop_db_instance",
    display_name="Stop DB instance",
    service_id="aurora",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="instance_identifier",
            label="Instance identifier",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="stop-db-instance",
        arg_map={"instance_identifier": "db-instance-identifier"},
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="stop_db_instance",
        param_map={"instance_identifier": "DBInstanceIdentifier"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Stop instance result"),
    iam_permissions=("rds:StopDBInstance",),
    description="Stop a DB instance.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


REBOOT_DB_INSTANCE = ActionDefinition(
    action_id="aurora.reboot_db_instance",
    display_name="Reboot DB instance",
    service_id="aurora",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="instance_identifier",
            label="Instance identifier",
            required=True,
        ),
        InputField(
            name="force_failover",
            label="Force failover",
            kind="bool",
            required=False,
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="reboot-db-instance",
        arg_map={
            "instance_identifier": "db-instance-identifier",
            "force_failover": "force-failover",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="reboot_db_instance",
        param_map={
            "instance_identifier": "DBInstanceIdentifier",
            "force_failover": "ForceFailover",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Reboot instance result"),
    iam_permissions=("rds:RebootDBInstance",),
    description="Reboot a DB instance. Force failover only when you want the writer to move.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


DELETE_DB_INSTANCE = ActionDefinition(
    action_id="aurora.delete_db_instance",
    display_name="Delete DB instance",
    service_id="aurora",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="instance_identifier",
            label="Instance identifier",
            required=True,
        ),
        InputField(
            name="skip_final_snapshot",
            label="Skip final snapshot",
            kind="bool",
            required=False,
            default="true",
        ),
        InputField(
            name="final_snapshot_identifier",
            label="Final snapshot identifier",
            required=False,
            help_text="Required when Skip final snapshot is false.",
        ),
        InputField(
            name="delete_automated_backups",
            label="Delete automated backups",
            kind="bool",
            required=False,
            default="true",
        ),
    ),
    cli_template=CliTemplate(
        service="rds",
        command="delete-db-instance",
        arg_map={
            "instance_identifier": "db-instance-identifier",
            "skip_final_snapshot": "skip-final-snapshot",
            "final_snapshot_identifier": "final-db-snapshot-identifier",
            "delete_automated_backups": "delete-automated-backups",
        },
    ),
    boto3_template=Boto3Template(
        service="rds",
        operation="delete_db_instance",
        param_map={
            "instance_identifier": "DBInstanceIdentifier",
            "skip_final_snapshot": "SkipFinalSnapshot",
            "final_snapshot_identifier": "FinalDBSnapshotIdentifier",
            "delete_automated_backups": "DeleteAutomatedBackups",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete instance result"),
    iam_permissions=("rds:DeleteDBInstance",),
    description="Delete a DB instance. Aurora cluster members usually skip a final instance snapshot.",
    cache_refresh_nav_ids=("clusters", "instances"),
)


def _modify_cluster_password_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Build boto3 params for modify_db_cluster (master password only)."""
    return {
        "DBClusterIdentifier": inputs["cluster_identifier"],
        "MasterUserPassword": inputs["new_master_password"],
        "ApplyImmediately": True,
    }


def _modify_cluster_password_cli(inputs: Mapping[str, str]) -> list[str]:
    args: list[str] = []
    append_cli_value(args, "db-cluster-identifier", inputs.get("cluster_identifier"))
    append_cli_value(args, "master-user-password", inputs.get("new_master_password"))
    args.append("--apply-immediately")
    return args


MODIFY_DB_CLUSTER_PASSWORD = ActionDefinition(
    action_id="aurora.modify_db_cluster_password",
    display_name="Update master password",
    service_id="aurora",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="cluster_identifier", label="Cluster identifier", required=True),
        InputField(
            name="engine",
            label="Engine",
            kind="choice",
            choices=("aurora-mysql", "aurora-postgresql"),
            required=False,
            default="aurora-mysql",
            help_text="Prefilled from the selected cluster. Used when saving the connection string to keyring.",
        ),
        InputField(
            name="master_username",
            label="Master username",
            required=True,
            default="admin",
            help_text="Stored in keyring alongside the new password.",
        ),
        InputField(
            name="new_master_password",
            label="New master password",
            required=True,
            is_secret=True,
            help_text="Password is applied immediately and also saved to the keyring as a connection string.",
        ),
        InputField(
            name="host",
            label="Cluster endpoint (host)",
            required=False,
            help_text="Writer endpoint to store in keyring. Prefilled from the cluster endpoint when available.",
        ),
        InputField(
            name="port",
            label="Port",
            kind="int",
            required=False,
            help_text="3306 for MySQL, 5432 for PostgreSQL.",
        ),
        InputField(
            name="database",
            label="Default database (optional)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(service="rds", command="modify-db-cluster"),
    boto3_template=Boto3Template(service="rds", operation="modify_db_cluster"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Modify cluster result"),
    iam_permissions=("rds:ModifyDBCluster",),
    description=(
        "Update the master password for an Aurora DB cluster. "
        "The new password is applied immediately and saved to the OS keyring "
        "as a JSON connection string under service='gui4aws' so the SQL runner can use it."
    ),
    cache_refresh_nav_ids=("clusters",),
    boto3_params_builder=_modify_cluster_password_params,
    cli_args_builder=_modify_cluster_password_cli,
)


ALL_ACTIONS = (
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_INSTANCES,
    DESCRIBE_DB_SUBNET_GROUPS,
    DESCRIBE_DB_PARAMETER_GROUPS,
    DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS,
    CREATE_DB_CLUSTER,
    CREATE_DB_INSTANCE,
    CREATE_DB_CLUSTER_SNAPSHOT,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
    START_DB_CLUSTER,
    STOP_DB_CLUSTER,
    FAILOVER_DB_CLUSTER,
    DELETE_DB_CLUSTER,
    START_DB_INSTANCE,
    STOP_DB_INSTANCE,
    REBOOT_DB_INSTANCE,
    DELETE_DB_INSTANCE,
    MODIFY_DB_CLUSTER_PASSWORD,
)
