"""Normalization functions: raw boto3 response -> list[Summary]."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.aurora.models import (
    AuroraClusterSnapshotSummary,
    AuroraClusterSummary,
    AuroraDbClusterParameterGroupSummary,
    AuroraDbParameterGroupSummary,
    AuroraDbSubnetGroupSummary,
    AuroraInstanceSummary,
)

__all__ = [
    "to_cluster_snapshot_summaries",
    "to_cluster_summaries",
    "to_db_cluster_parameter_group_summaries",
    "to_db_parameter_group_summaries",
    "to_db_subnet_group_summaries",
    "to_instance_summaries",
]


def to_cluster_summaries(response: Mapping[str, Any]) -> list[AuroraClusterSummary]:
    """Map ``describe_db_clusters`` response -> list[AuroraClusterSummary]."""
    clusters = response.get("DBClusters", []) or []
    summaries: list[AuroraClusterSummary] = []
    for cluster in clusters:
        members = cluster.get("DBClusterMembers", []) or []
        summaries.append(
            AuroraClusterSummary(
                cluster_identifier=str(cluster.get("DBClusterIdentifier", "")),
                engine=str(cluster.get("Engine", "")),
                engine_version=optional_str(cluster.get("EngineVersion")),
                status=str(cluster.get("Status", "")),
                endpoint=optional_str(cluster.get("Endpoint")),
                reader_endpoint=optional_str(cluster.get("ReaderEndpoint")),
                multi_az=bool(cluster.get("MultiAZ", False)),
                member_count=len(members),
                arn=optional_str(cluster.get("DBClusterArn")),
            )
        )
    return summaries


def to_cluster_snapshot_summaries(response: Mapping[str, Any]) -> list[AuroraClusterSnapshotSummary]:
    """Map ``describe_db_cluster_snapshots`` response -> list[AuroraClusterSnapshotSummary]."""
    snapshots = response.get("DBClusterSnapshots", []) or []
    summaries: list[AuroraClusterSnapshotSummary] = []
    for snap in snapshots:
        summaries.append(
            AuroraClusterSnapshotSummary(
                snapshot_identifier=str(snap.get("DBClusterSnapshotIdentifier", "")),
                cluster_identifier=str(snap.get("DBClusterIdentifier", "")),
                engine=optional_str(snap.get("Engine")),
                engine_version=optional_str(snap.get("EngineVersion")),
                status=str(snap.get("Status", "")),
                snapshot_type=optional_str(snap.get("SnapshotType")),
                percent_progress=optional_int(snap.get("PercentProgress")),
                arn=optional_str(snap.get("DBClusterSnapshotArn")),
            )
        )
    return summaries


def to_instance_summaries(response: Mapping[str, Any]) -> list[AuroraInstanceSummary]:
    """Map ``describe_db_instances`` response -> list[AuroraInstanceSummary].

    Shows all DB instances; cluster_identifier is None for standalone RDS instances.
    Moto does not always populate DBClusterIdentifier on cluster-member instances, so we
    do not filter on that field here.
    """
    instances = response.get("DBInstances", []) or []
    summaries: list[AuroraInstanceSummary] = []
    for instance in instances:
        cluster_id = instance.get("DBClusterIdentifier")
        summaries.append(
            AuroraInstanceSummary(
                instance_identifier=str(instance.get("DBInstanceIdentifier", "")),
                cluster_identifier=optional_str(cluster_id),
                engine=str(instance.get("Engine", "")),
                instance_class=optional_str(instance.get("DBInstanceClass")),
                running_state=instance_running_state(instance.get("DBInstanceStatus")),
                status=str(instance.get("DBInstanceStatus", "")),
                is_writer=is_instance_writer(instance),
                arn=optional_str(instance.get("DBInstanceArn")),
            )
        )
    return summaries


def to_db_subnet_group_summaries(response: Mapping[str, Any]) -> list[AuroraDbSubnetGroupSummary]:
    """Map ``describe_db_subnet_groups`` response -> list[AuroraDbSubnetGroupSummary]."""
    subnet_groups = response.get("DBSubnetGroups", []) or []
    return [
        AuroraDbSubnetGroupSummary(
            subnet_group_name=str(group.get("DBSubnetGroupName", "")),
            description=optional_str(group.get("DBSubnetGroupDescription")),
            vpc_id=optional_str(group.get("VpcId")),
            subnet_count=len(group.get("Subnets", []) or []),
            status=optional_str(group.get("SubnetGroupStatus")),
            arn=optional_str(group.get("DBSubnetGroupArn")),
        )
        for group in subnet_groups
    ]


def to_db_parameter_group_summaries(response: Mapping[str, Any]) -> list[AuroraDbParameterGroupSummary]:
    """Map ``describe_db_parameter_groups`` response -> Aurora DB parameter groups."""
    groups = response.get("DBParameterGroups", []) or []
    return [
        AuroraDbParameterGroupSummary(
            parameter_group_name=str(group.get("DBParameterGroupName", "")),
            family=str(group.get("DBParameterGroupFamily", "")),
            description=optional_str(group.get("Description")),
            arn=optional_str(group.get("DBParameterGroupArn")),
        )
        for group in groups
    ]


def to_db_cluster_parameter_group_summaries(
    response: Mapping[str, Any],
) -> list[AuroraDbClusterParameterGroupSummary]:
    """Map ``describe_db_cluster_parameter_groups`` response -> Aurora cluster parameter groups."""
    groups = response.get("DBClusterParameterGroups", []) or []
    return [
        AuroraDbClusterParameterGroupSummary(
            cluster_parameter_group_name=str(group.get("DBClusterParameterGroupName", "")),
            family=str(group.get("DBParameterGroupFamily", "")),
            description=optional_str(group.get("Description")),
            arn=optional_str(group.get("DBClusterParameterGroupArn")),
        )
        for group in groups
    ]


def is_instance_writer(instance: Mapping[str, Any]) -> bool:
    """Heuristic: an instance is the writer if its cluster member entry says so."""
    members = instance.get("DBClusterMembers") or []
    for member in members:
        if member.get("DBInstanceIdentifier") == instance.get("DBInstanceIdentifier"):
            return bool(member.get("IsClusterWriter", False))
    # boto3 returns DBClusterMembers on the cluster, not the instance. As a fallback, treat the
    # field "PromotionTier" == 0 as writer-eligible. Real writer status comes from the cluster
    # view; the GUI shows it there.
    return False


def instance_running_state(status: Any) -> str:
    """Summarize DBInstanceStatus into a simple running/stopped state."""
    text = str(status or "").strip().lower()
    if not text:
        return "unknown"
    if text == "stopped":
        return "stopped"
    if "stop" in text:
        return "stopping"
    if "start" in text:
        return "starting"
    return "running"


def optional_str(value: Any) -> str | None:
    """Return value as str, or None for blank/None."""
    if value is None:
        return None
    text = str(value)
    return text or None


def optional_int(value: Any) -> int | None:
    """Return value as int, or None if missing."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
