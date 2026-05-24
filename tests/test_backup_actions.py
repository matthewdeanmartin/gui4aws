"""Moto-backed tests for AWS Backup actions.

Moto 5.2 supports backup vaults and plans but returns ``Not yet implemented`` for jobs and
recovery points. Tests for those operations are marked ``integration`` and skipped by default.
"""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Failure, Boto3Result
from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.execution.script_generator import generate_python_script
from gui4aws.services.backup.actions import (
    CREATE_BACKUP_PLAN,
    CREATE_BACKUP_VAULT,
    DELETE_BACKUP_PLAN,
    DELETE_BACKUP_VAULT,
    LIST_BACKUP_JOBS,
    LIST_BACKUP_PLANS,
    LIST_BACKUP_VAULTS,
    LIST_RECOVERY_POINTS_BY_BACKUP_VAULT,
    LIST_RECOVERY_POINTS_BY_JOB,
    LIST_RESTORE_JOBS,
    START_BACKUP_JOB,
    START_RESTORE_JOB,
    UPDATE_BACKUP_PLAN,
)


def test_start_backup_job_python_script() -> None:
    """Builder for start_backup_job correctly handles lifecycle."""
    text = generate_python_script(
        START_BACKUP_JOB,
        inputs={"vault_name": "v1", "resource_arn": "arn:s3:::b1", "lifecycle_delete_after_days": "7"},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "BackupVaultName='v1'" in text
    assert "'DeleteAfterDays': 7" in text


def test_start_restore_job_python_script() -> None:
    """Builder for start_restore_job correctly handles metadata."""
    text = generate_python_script(
        START_RESTORE_JOB,
        inputs={"recovery_point_arn": "rp1", "new_cluster_identifier": "new-c", "engine": "aurora-mysql"},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "RecoveryPointArn='rp1'" in text
    assert "'DBClusterIdentifier': 'new-c'" in text
    assert "'Engine': 'aurora-mysql'" in text


def test_list_recovery_points_by_job_view_empty() -> None:
    """View handles empty job list correctly."""
    summaries = LIST_RECOVERY_POINTS_BY_JOB.view({"BackupJobs": []})  # type: ignore
    assert summaries == []


def test_list_restore_jobs_view() -> None:
    """View handles restore jobs correctly."""
    resp = {
        "RestoreJobs": [
            {
                "RestoreJobId": "rj1",
                "Status": "COMPLETED",
                "ResourceType": "RDS",
                "CreatedResourceArn": "arn:rds",
                "CreationDate": "2023-01-01",
            }
        ]
    }
    summaries = LIST_RESTORE_JOBS.view(resp)  # type: ignore
    assert len(summaries) == 1
    assert summaries[0].job_id == "rj1"


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


def test_create_backup_plan_via_action(mock_aws_env: None) -> None:
    """The create-backup-plan action creates a plan and schedule."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-plan")
    context = AppContext(region_name="us-east-1")
    result = context.execute(
        CREATE_BACKUP_PLAN,
        inputs={
            "plan_name": "plan-action",
            "rule_name": "daily",
            "target_vault_name": "vault-plan",
            "schedule_expression": "cron(0 5 ? * * *)",
            "start_window_minutes": "60",
        },
    )
    assert isinstance(result, Boto3Result)
    summaries = LIST_BACKUP_PLANS.view(backup.list_backup_plans())  # type: ignore[misc]
    assert any(summary.plan_name == "plan-action" for summary in summaries)


def test_delete_backup_vault_via_action(mock_aws_env: None) -> None:
    """Delete vault action removes an empty vault."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-delete")
    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_BACKUP_VAULT, inputs={"vault_name": "vault-delete"})
    assert isinstance(result, Boto3Result)
    names = {vault["BackupVaultName"] for vault in backup.list_backup_vaults()["BackupVaultList"]}
    assert "vault-delete" not in names


def test_delete_backup_plan_via_action(mock_aws_env: None) -> None:
    """Delete plan action removes an existing backup plan."""
    backup = boto3.client("backup", region_name="us-east-1")
    backup.create_backup_vault(BackupVaultName="vault-delete-plan")
    created = backup.create_backup_plan(
        BackupPlan={
            "BackupPlanName": "plan-delete",
            "Rules": [
                {
                    "RuleName": "daily",
                    "TargetBackupVaultName": "vault-delete-plan",
                    "ScheduleExpression": "cron(0 5 ? * * *)",
                }
            ],
        }
    )
    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_BACKUP_PLAN, inputs={"plan_id": created["BackupPlanId"]})
    assert isinstance(result, Boto3Result)
    assert backup.list_backup_plans()["BackupPlansList"] == []


def test_update_backup_plan_python_script_contains_schedule_payload() -> None:
    """Edit-schedule UI emits a complete nested backup-plan payload."""
    text = generate_python_script(
        UPDATE_BACKUP_PLAN,
        inputs={
            "plan_id": "plan-123",
            "plan_name": "plan-1",
            "rule_name": "daily",
            "target_vault_name": "vault-1",
            "schedule_expression": "cron(0 6 ? * * *)",
            "completion_window_minutes": "120",
            "lifecycle_delete_after_days": "35",
        },
        profile_name="default",
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "client.update_backup_plan(" in text
    assert "BackupPlanId='plan-123'" in text
    assert "'BackupPlanName': 'plan-1'" in text
    assert "'RuleName': 'daily'" in text
    assert "'TargetBackupVaultName': 'vault-1'" in text
    assert "'ScheduleExpression': 'cron(0 6 ? * * *)'" in text
    assert "'CompletionWindowMinutes': 120" in text
    assert "'DeleteAfterDays': 35" in text


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
