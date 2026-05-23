"""Normalized AWS Backup summaries."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

__all__ = [
    "BackupJobSummary",
    "BackupPlanSummary",
    "BackupVaultSummary",
    "RecoveryPointByJobSummary",
    "RecoveryPointSummary",
    "RestoreJobSummary",
]


@dataclass(frozen=True)
class BackupVaultSummary:
    """One AWS Backup vault."""

    vault_name: str
    arn: str | None
    creation_date: datetime | None
    number_of_recovery_points: int
    locked: bool


@dataclass(frozen=True)
class BackupPlanSummary:
    """One AWS Backup plan (current version)."""

    plan_id: str
    plan_name: str
    version_id: str | None
    arn: str | None
    creation_date: datetime | None


@dataclass(frozen=True)
class RecoveryPointSummary:
    """One recovery point inside a vault (from list_recovery_points_by_backup_vault)."""

    recovery_point_arn: str
    vault_name: str
    resource_arn: str | None
    resource_type: str | None
    status: str
    creation_date: datetime | None


@dataclass(frozen=True)
class RecoveryPointByJobSummary:
    """Recovery point surfaced from a completed backup job.

    Used as a workaround when list_recovery_points_by_backup_vault returns empty
    (a known robotocore limitation).  The data comes from list_backup_jobs.
    """

    recovery_point_arn: str
    job_id: str
    vault_name: str | None
    resource_arn: str | None
    resource_type: str | None
    state: str
    creation_date: datetime | None


@dataclass(frozen=True)
class BackupJobSummary:
    """One backup job."""

    job_id: str
    vault_name: str | None
    resource_arn: str | None
    resource_type: str | None
    state: str
    percent_done: str | None
    creation_date: datetime | None
    recovery_point_arn: str | None


@dataclass(frozen=True)
class RestoreJobSummary:
    """One restore job."""

    job_id: str
    recovery_point_arn: str | None
    resource_type: str | None
    status: str
    percent_done: str | None
    created_resource_arn: str | None
    creation_date: datetime | None
