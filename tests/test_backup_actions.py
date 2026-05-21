"""Moto-backed tests for AWS Backup actions.

Moto 5.2 supports backup vaults and plans but returns ``Not yet implemented`` for jobs and
recovery points. Tests for those operations are marked ``integration`` and skipped by default.
"""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Failure, Boto3Result
from gui4aws.services.backup.actions import (
    CREATE_BACKUP_VAULT,
    LIST_BACKUP_JOBS,
    LIST_BACKUP_PLANS,
    LIST_BACKUP_VAULTS,
    LIST_RECOVERY_POINTS_BY_BACKUP_VAULT,
)


def test_list_backup_vaults_returns_planted_vault(mock_aws_env: None) -> None:
    """Creating a vault makes it visible to the list action."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-1")
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BACKUP_VAULTS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = LIST_BACKUP_VAULTS.view(result.response)  # type: ignore[misc]
    assert any(summary.vault_name == "vault-1" for summary in summaries)


def test_create_backup_vault_via_action(mock_aws_env: None) -> None:
    """The CREATE_BACKUP_VAULT action actually creates a vault."""
    context = AppContext(region_name="us-east-1")
    result = context.execute(CREATE_BACKUP_VAULT, inputs={"vault_name": "vault-2"})
    assert isinstance(result, Boto3Result)
    backup = boto3.client("backup", region_name="us-east-1")
    names = {vault["BackupVaultName"] for vault in backup.list_backup_vaults()["BackupVaultList"]}
    assert "vault-2" in names


def test_list_backup_plans_returns_planted_plan(mock_aws_env: None) -> None:
    """Creating a plan makes it visible to the list action."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-3")
    backup.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "plan-3",
            "Rules": [
                {
                    "RuleName": "daily",
                    "TargetBackupVaultName": "vault-3",
                    "ScheduleExpression": "cron(0 5 ? * * *)",
                }
            ],
        }
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BACKUP_PLANS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = LIST_BACKUP_PLANS.view(result.response)  # type: ignore[misc]
    assert any(summary.plan_name == "plan-3" for summary in summaries)


@pytest.mark.integration
def test_list_recovery_points_against_moto_is_unimplemented(mock_aws_env: None) -> None:
    """Documenting moto's gap: the operation returns Not yet implemented."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-4")
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_RECOVERY_POINTS_BY_BACKUP_VAULT, inputs={"vault_name": "vault-4"})
    assert isinstance(result, Boto3Failure)


@pytest.mark.integration
def test_list_backup_jobs_against_moto_is_unimplemented(mock_aws_env: None) -> None:
    """Documenting moto's gap: list_backup_jobs is not implemented."""
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BACKUP_JOBS, inputs={})
    assert isinstance(result, Boto3Failure)
