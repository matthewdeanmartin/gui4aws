"""Normalization functions: raw boto3 response -> list[Summary] for ECS."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.ecs.models import (
    EcsClusterSummary,
    EcsServiceSummary,
    EcsTaskDefinitionSummary,
    EcsTaskSummary,
)

__all__ = [
    "to_cluster_summaries",
    "to_service_summaries",
    "to_task_definition_summaries",
    "to_task_summaries",
]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _arn_to_name(arn: str) -> str:
    """Extract the last path segment from an ARN."""
    return arn.split("/")[-1] if "/" in arn else arn


def _arn_to_family_revision(arn: str) -> tuple[str, str]:
    """Extract family and revision from a task definition ARN or family:revision string."""
    # arn:aws:ecs:...:task-definition/family:revision  OR  family:revision  OR  family
    name = _arn_to_name(arn)
    if ":" in name:
        parts = name.rsplit(":", 1)
        return parts[0], parts[1]
    return name, ""


def to_cluster_summaries(response: Mapping[str, Any]) -> list[EcsClusterSummary]:
    # describe_clusters returns {"clusters": [{clusterName, ...}]}
    # list_clusters returns {"clusterArns": ["arn:...", ...]}
    clusters = response.get("clusters", []) or []
    arns = response.get("clusterArns", []) or []
    summaries: list[EcsClusterSummary] = []
    for c in clusters:
        summaries.append(
            EcsClusterSummary(
                cluster_name=str(c.get("clusterName", "")),
                status=str(c.get("status", "")),
                running_tasks=int(c.get("runningTasksCount", 0)),
                pending_tasks=int(c.get("pendingTasksCount", 0)),
                active_services=int(c.get("activeServicesCount", 0)),
                arn=_optional_str(c.get("clusterArn")),
            )
        )
    for arn in arns:
        summaries.append(
            EcsClusterSummary(
                cluster_name=_arn_to_name(arn),
                status="",
                running_tasks=0,
                pending_tasks=0,
                active_services=0,
                arn=arn,
            )
        )
    return summaries


def to_service_summaries(response: Mapping[str, Any]) -> list[EcsServiceSummary]:
    # describe_services returns {"services": [{serviceName, ...}]}
    # list_services returns {"serviceArns": ["arn:...", ...]}
    services = response.get("services", []) or []
    arns = response.get("serviceArns", []) or []
    summaries: list[EcsServiceSummary] = []
    for s in services:
        cluster_arn = str(s.get("clusterArn", ""))
        summaries.append(
            EcsServiceSummary(
                service_name=str(s.get("serviceName", "")),
                cluster_name=_arn_to_name(cluster_arn),
                status=str(s.get("status", "")),
                desired_count=int(s.get("desiredCount", 0)),
                running_count=int(s.get("runningCount", 0)),
                pending_count=int(s.get("pendingCount", 0)),
                task_definition=_optional_str(s.get("taskDefinition")),
                launch_type=_optional_str(s.get("launchType")),
                arn=_optional_str(s.get("serviceArn")),
            )
        )
    for arn in arns:
        summaries.append(
            EcsServiceSummary(
                service_name=_arn_to_name(arn),
                cluster_name="",
                status="",
                desired_count=0,
                running_count=0,
                pending_count=0,
                task_definition=None,
                launch_type=None,
                arn=arn,
            )
        )
    return summaries


def to_task_summaries(response: Mapping[str, Any]) -> list[EcsTaskSummary]:
    # describe_tasks returns {"tasks": [{taskArn, ...}]}
    # list_tasks returns {"taskArns": ["arn:...", ...]}
    tasks = response.get("tasks", []) or []
    arns = response.get("taskArns", []) or []
    summaries: list[EcsTaskSummary] = []
    for t in tasks:
        task_arn = str(t.get("taskArn", ""))
        cluster_arn = str(t.get("clusterArn", ""))
        summaries.append(
            EcsTaskSummary(
                task_id=_arn_to_name(task_arn),
                cluster_name=_arn_to_name(cluster_arn),
                task_definition=_optional_str(t.get("taskDefinitionArn")),
                last_status=str(t.get("lastStatus", "")),
                desired_status=str(t.get("desiredStatus", "")),
                launch_type=_optional_str(t.get("launchType")),
                arn=_optional_str(t.get("taskArn")),
            )
        )
    for arn in arns:
        summaries.append(
            EcsTaskSummary(
                task_id=_arn_to_name(arn),
                cluster_name="",
                task_definition=None,
                last_status="",
                desired_status="",
                launch_type=None,
                arn=arn,
            )
        )
    return summaries


def to_task_definition_summaries(response: Mapping[str, Any]) -> list[EcsTaskDefinitionSummary]:
    # list_task_definitions returns {"taskDefinitionArns": [...]}
    # describe_task_definition returns {"taskDefinition": {...}}
    arns = response.get("taskDefinitionArns", []) or []
    summaries: list[EcsTaskDefinitionSummary] = []
    for arn in arns:
        family, revision = _arn_to_family_revision(arn)
        summaries.append(
            EcsTaskDefinitionSummary(
                task_definition_arn=arn,
                family=family,
                revision=revision,
                status=None,
            )
        )
    td = response.get("taskDefinition")
    if td:
        arn = str(td.get("taskDefinitionArn", ""))
        summaries.append(
            EcsTaskDefinitionSummary(
                task_definition_arn=arn,
                family=str(td.get("family", _arn_to_family_revision(arn)[0])),
                revision=str(td.get("revision", _arn_to_family_revision(arn)[1])),
                status=_optional_str(td.get("status")),
            )
        )
    return summaries
