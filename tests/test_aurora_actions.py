"""Moto-backed tests for Aurora actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.aurora.actions import (
    CREATE_DB_CLUSTER,
    CREATE_DB_INSTANCE,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS,
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_INSTANCES,
    DESCRIBE_DB_PARAMETER_GROUPS,
    DESCRIBE_DB_SUBNET_GROUPS,
)


def test_describe_db_clusters_returns_summaries(mock_aws_env: None) -> None:
    """A planted cluster comes back normalized."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="cluster-1",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_DB_CLUSTERS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = DESCRIBE_DB_CLUSTERS.view(result.response)  # type: ignore[misc]
    assert any(summary.cluster_identifier == "cluster-1" for summary in summaries)
    assert all(summary.engine == "aurora-postgresql" for summary in summaries)


def test_describe_db_cluster_snapshots_returns_summaries(mock_aws_env: None) -> None:
    """Creating a snapshot makes it visible to the describe action."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="cluster-2",
        Engine="aurora-mysql",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
    )
    rds.create_db_cluster_snapshot(
        DBClusterIdentifier="cluster-2",
        DBClusterSnapshotIdentifier="snap-2",
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_DB_CLUSTER_SNAPSHOTS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = DESCRIBE_DB_CLUSTER_SNAPSHOTS.view(result.response)  # type: ignore[misc]
    assert any(summary.snapshot_identifier == "snap-2" for summary in summaries)


def test_describe_db_instances_includes_standalone_with_no_cluster(mock_aws_env: None) -> None:
    """Standalone RDS instances appear with cluster_identifier=None (not filtered out).

    The Instances sidebar entry uses describe_db_instances which returns all instances.
    Filtering to cluster-only was removed because moto does not reliably populate
    DBClusterIdentifier on instances created via create_db_cluster.
    """
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_instance(
        DBInstanceIdentifier="standalone-1",
        DBInstanceClass="db.t3.micro",
        Engine="postgres",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
        AllocatedStorage=20,
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_DB_INSTANCES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = DESCRIBE_DB_INSTANCES.view(result.response)  # type: ignore[misc]
    standalone = next((s for s in summaries if s.instance_identifier == "standalone-1"), None)
    assert standalone is not None
    assert standalone.cluster_identifier is None
    assert standalone.running_state == "running"


def test_describe_db_instances_preserves_cluster_identifier_for_cluster_members(mock_aws_env: None) -> None:
    """Aurora cluster member instances keep their cluster identifier when boto3 returns it."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="cluster-3",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
    )
    rds.create_db_instance(
        DBInstanceIdentifier="cluster-3-instance-1",
        DBInstanceClass="db.t3.medium",
        Engine="aurora-postgresql",
        DBClusterIdentifier="cluster-3",
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_DB_INSTANCES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = DESCRIBE_DB_INSTANCES.view(result.response)  # type: ignore[misc]
    member = next((s for s in summaries if s.instance_identifier == "cluster-3-instance-1"), None)
    assert member is not None
    assert member.cluster_identifier == "cluster-3"
    assert member.running_state == "running"


def test_create_db_cluster_action_supports_serverless_v2(mock_aws_env: None) -> None:
    """The create-cluster form can create a serverless v2-compatible cluster."""
    context = AppContext(region_name="us-east-1")
    result = context.execute(
        CREATE_DB_CLUSTER,
        inputs={
            "cluster_identifier": "cluster-v2",
            "engine": "aurora-postgresql",
            "cluster_kind": "serverless-v2",
            "master_username": "admin",
            "master_user_password": "super-secret-password",
            "serverless_min_capacity": "0.5",
            "serverless_max_capacity": "2",
        },
    )
    assert isinstance(result, Boto3Result)
    cluster = result.response["DBCluster"]
    assert cluster["DBClusterIdentifier"] == "cluster-v2"
    assert cluster["EngineMode"] == "provisioned"
    assert cluster["ServerlessV2ScalingConfiguration"] == {"MinCapacity": 0.5, "MaxCapacity": 2.0}


def test_create_db_instance_action_creates_cluster_member(mock_aws_env: None) -> None:
    """Aurora instance creation targets a cluster rather than creating an orphan."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_cluster(
        DBClusterIdentifier="cluster-4",
        Engine="aurora-postgresql",
        MasterUsername="admin",
        MasterUserPassword="super-secret-password",
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(
        CREATE_DB_INSTANCE,
        inputs={
            "instance_identifier": "cluster-4-instance-1",
            "cluster_identifier": "cluster-4",
            "instance_class": "db.t3.medium",
            "engine": "aurora-postgresql",
        },
    )
    assert isinstance(result, Boto3Result)
    assert result.response["DBInstance"]["DBClusterIdentifier"] == "cluster-4"


def test_describe_db_subnet_groups_returns_planted_group(mock_aws_env: None) -> None:
    """Aurora tree exposes DB subnet groups."""
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc = ec2.create_vpc(CidrBlock="10.0.0.0/16")["Vpc"]["VpcId"]
    subnet_a = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.1.0/24", AvailabilityZone="us-east-1a")["Subnet"]["SubnetId"]
    subnet_b = ec2.create_subnet(VpcId=vpc, CidrBlock="10.0.2.0/24", AvailabilityZone="us-east-1b")["Subnet"]["SubnetId"]
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_subnet_group(
        DBSubnetGroupName="subnet-group-1",
        DBSubnetGroupDescription="Aurora subnets",
        SubnetIds=[subnet_a, subnet_b],
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_DB_SUBNET_GROUPS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = DESCRIBE_DB_SUBNET_GROUPS.view(result.response)  # type: ignore[misc]
    assert any(summary.subnet_group_name == "subnet-group-1" and summary.subnet_count == 2 for summary in summaries)


def test_describe_db_parameter_groups_returns_custom_groups(mock_aws_env: None) -> None:
    """Aurora tree exposes both instance and cluster parameter groups."""
    rds = boto3.client("rds", region_name="us-east-1")
    rds.create_db_parameter_group(
        DBParameterGroupName="param-group-1",
        DBParameterGroupFamily="aurora-postgresql14",
        Description="Aurora instance params",
    )
    rds.create_db_cluster_parameter_group(
        DBClusterParameterGroupName="cluster-param-group-1",
        DBParameterGroupFamily="aurora-postgresql14",
        Description="Aurora cluster params",
    )
    context = AppContext(region_name="us-east-1")

    instance_result = context.execute(DESCRIBE_DB_PARAMETER_GROUPS, inputs={})
    assert isinstance(instance_result, Boto3Result)
    instance_summaries = DESCRIBE_DB_PARAMETER_GROUPS.view(instance_result.response)  # type: ignore[misc]
    assert any(summary.parameter_group_name == "param-group-1" for summary in instance_summaries)

    cluster_result = context.execute(DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS, inputs={})
    assert isinstance(cluster_result, Boto3Result)
    cluster_summaries = DESCRIBE_DB_CLUSTER_PARAMETER_GROUPS.view(cluster_result.response)  # type: ignore[misc]
    assert any(
        summary.cluster_parameter_group_name == "cluster-param-group-1" for summary in cluster_summaries
    )
