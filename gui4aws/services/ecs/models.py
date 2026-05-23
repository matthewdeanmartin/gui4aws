"""Normalized ECS summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "EcsClusterSummary",
    "EcsServiceSummary",
    "EcsTaskDefinitionSummary",
    "EcsTaskSummary",
]


@dataclass(frozen=True)
class EcsClusterSummary:
    cluster_name: str
    status: str
    running_tasks: int
    pending_tasks: int
    active_services: int
    arn: str | None


@dataclass(frozen=True)
class EcsServiceSummary:
    service_name: str
    cluster_name: str
    status: str
    desired_count: int
    running_count: int
    pending_count: int
    task_definition: str | None
    launch_type: str | None
    arn: str | None


@dataclass(frozen=True)
class EcsTaskSummary:
    task_id: str
    cluster_name: str
    task_definition: str | None
    last_status: str
    desired_status: str
    launch_type: str | None
    arn: str | None


@dataclass(frozen=True)
class EcsTaskDefinitionSummary:
    task_definition_arn: str
    family: str
    revision: str
    status: str | None
