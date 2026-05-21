"""Moto-backed tests for Aurora actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.aurora.actions import (
    DESCRIBE_DB_CLUSTERS,
    DESCRIBE_DB_CLUSTER_SNAPSHOTS,
    DESCRIBE_DB_INSTANCES,
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
