"""Normalization functions for AWS Backup responses."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from gui4aws.services.backup.models import (
    BackupJobSummary,
    BackupPlanSummary,
    BackupVaultSummary,
    RecoveryPointByJobSummary,
    RecoveryPointSummary,
    RestoreJobSummary,
)

__all__ = [
    "to_backup_job_summaries",
    "to_backup_plan_summaries",
    "to_backup_vault_summaries",
    "to_recovery_point_by_job_summaries",
    "to_recovery_point_summaries",
    "to_restore_job_summaries",
]


def to_backup_vault_summaries(response: Mapping[str, Any]) -> list[BackupVaultSummary]:
    """``list_backup_vaults`` -> list[BackupVaultSummary]."""
    vaults = response.get("BackupVaultList", []) or []
    return [
        BackupVaultSummary(
            vault_name=str(vault.get("BackupVaultName", "")),
            arn=optional_str(vault.get("BackupVaultArn")),
            creation_date=optional_datetime(vault.get("CreationDate")),
            number_of_recovery_points=int(vault.get("NumberOfRecoveryPoints", 0) or 0),
            locked=bool(vault.get("Locked", False)),
        )
        for vault in vaults
    ]


def to_backup_plan_summaries(response: Mapping[str, Any]) -> list[BackupPlanSummary]:
    """``list_backup_plans`` -> list[BackupPlanSummary]."""
    plans = response.get("BackupPlansList", []) or []
    return [
        BackupPlanSummary(
            plan_id=str(plan.get("BackupPlanId", "")),
            plan_name=str(plan.get("BackupPlanName", "")),
            version_id=optional_str(plan.get("VersionId")),
            arn=optional_str(plan.get("BackupPlanArn")),
            creation_date=optional_datetime(plan.get("CreationDate")),
        )
        for plan in plans
    ]


def to_recovery_point_summaries(response: Mapping[str, Any]) -> list[RecoveryPointSummary]:
    """``list_recovery_points_by_backup_vault`` -> list[RecoveryPointSummary]."""
    points = response.get("RecoveryPoints", []) or []
    summaries: list[RecoveryPointSummary] = []
    for point in points:
        recovery_arn = point.get("RecoveryPointArn") or ""
        summaries.append(
            RecoveryPointSummary(
                recovery_point_arn=str(recovery_arn),
                vault_name=str(point.get("BackupVaultName", "")),
                resource_arn=optional_str(point.get("ResourceArn")),
                resource_type=optional_str(point.get("ResourceType")),
                status=str(point.get("Status", "")),
                creation_date=optional_datetime(point.get("CreationDate")),
            )
        )
    return summaries


def to_backup_job_summaries(response: Mapping[str, Any]) -> list[BackupJobSummary]:
    """``list_backup_jobs`` -> list[BackupJobSummary]."""
    jobs = response.get("BackupJobs", []) or []
    return [
        BackupJobSummary(
            job_id=str(job.get("BackupJobId", "")),
            vault_name=optional_str(job.get("BackupVaultName")),
            resource_arn=optional_str(job.get("ResourceArn")),
            resource_type=optional_str(job.get("ResourceType")),
            state=str(job.get("State", "")),
            percent_done=optional_str(job.get("PercentDone")),
            creation_date=optional_datetime(job.get("CreationDate")),
            recovery_point_arn=optional_str(job.get("RecoveryPointArn")),
        )
        for job in jobs
    ]


def to_recovery_point_by_job_summaries(response: Mapping[str, Any]) -> list[RecoveryPointByJobSummary]:
    """``list_backup_jobs`` -> list[RecoveryPointByJobSummary].

    Workaround for robotocore: list_recovery_points_by_backup_vault returns empty
    even after successful backup jobs.  We surface recovery points from completed
    backup jobs instead so the UI has something to restore from.
    """
    jobs = response.get("BackupJobs", []) or []
    results: list[RecoveryPointByJobSummary] = []
    for job in jobs:
        rp_arn = optional_str(job.get("RecoveryPointArn"))
        if not rp_arn:
            continue
        results.append(
            RecoveryPointByJobSummary(
                recovery_point_arn=rp_arn,
                job_id=str(job.get("BackupJobId", "")),
                vault_name=optional_str(job.get("BackupVaultName")),
                resource_arn=optional_str(job.get("ResourceArn")),
                resource_type=optional_str(job.get("ResourceType")),
                state=str(job.get("State", "")),
                creation_date=optional_datetime(job.get("CreationDate")),
            )
        )
    return results


def to_restore_job_summaries(response: Mapping[str, Any]) -> list[RestoreJobSummary]:
    """``list_restore_jobs`` -> list[RestoreJobSummary]."""
    jobs = response.get("RestoreJobs", []) or []
    return [
        RestoreJobSummary(
            job_id=str(job.get("RestoreJobId", "")),
            recovery_point_arn=optional_str(job.get("RecoveryPointArn")),
            resource_type=optional_str(job.get("ResourceType")),
            status=str(job.get("Status", "")),
            percent_done=optional_str(job.get("PercentDone")),
            created_resource_arn=optional_str(job.get("CreatedResourceArn")),
            creation_date=optional_datetime(job.get("CreationDate")),
        )
        for job in jobs
    ]


def optional_str(value: Any) -> str | None:
    """Return value as str, or None for blank/None."""
    if value is None:
        return None
    text = str(value)
    return text or None


def optional_datetime(value: Any) -> datetime | None:
    """Pass datetimes through; return None for missing values."""
    if isinstance(value, datetime):
        return value
    return None
