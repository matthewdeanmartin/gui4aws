"""AWS Backup action definitions."""

from __future__ import annotations

import json
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
from gui4aws.services.backup.views import (
    to_backup_job_summaries,
    to_backup_plan_summaries,
    to_backup_vault_summaries,
    to_recovery_point_summaries,
    to_restore_job_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_BACKUP_PLAN",
    "CREATE_BACKUP_VAULT",
    "DELETE_BACKUP_PLAN",
    "DELETE_BACKUP_VAULT",
    "LIST_BACKUP_JOBS",
    "LIST_BACKUP_PLANS",
    "LIST_BACKUP_VAULTS",
    "LIST_RECOVERY_POINTS_BY_BACKUP_VAULT",
    "LIST_RESTORE_JOBS",
    "UPDATE_BACKUP_PLAN",
]


def _build_backup_plan_document(inputs: Mapping[str, str]) -> dict[str, Any]:
    rule: dict[str, Any] = {
        "RuleName": inputs["rule_name"],
        "TargetBackupVaultName": inputs["target_vault_name"],
        "ScheduleExpression": inputs["schedule_expression"],
    }
    if inputs.get("start_window_minutes"):
        rule["StartWindowMinutes"] = int(inputs["start_window_minutes"])
    if inputs.get("completion_window_minutes"):
        rule["CompletionWindowMinutes"] = int(inputs["completion_window_minutes"])
    lifecycle: dict[str, Any] = {}
    if inputs.get("lifecycle_move_to_cold_storage_after_days"):
        lifecycle["MoveToColdStorageAfterDays"] = int(inputs["lifecycle_move_to_cold_storage_after_days"])
    if inputs.get("lifecycle_delete_after_days"):
        lifecycle["DeleteAfterDays"] = int(inputs["lifecycle_delete_after_days"])
    if lifecycle:
        rule["Lifecycle"] = lifecycle
    return {
        "BackupPlanName": inputs["plan_name"],
        "Rules": [rule],
    }


def _backup_plan_cli_json(inputs: Mapping[str, str]) -> str:
    return json.dumps(_build_backup_plan_document(inputs), separators=(",", ":"))


def _create_backup_plan_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    return {"BackupPlan": _build_backup_plan_document(inputs)}


def _create_backup_plan_cli_args(inputs: Mapping[str, str]) -> list[str]:
    return ["--backup-plan", _backup_plan_cli_json(inputs)]


def _update_backup_plan_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    return {
        "BackupPlanId": inputs["plan_id"],
        "BackupPlan": _build_backup_plan_document(inputs),
    }


def _update_backup_plan_cli_args(inputs: Mapping[str, str]) -> list[str]:
    return [
        "--backup-plan-id",
        inputs["plan_id"],
        "--backup-plan",
        _backup_plan_cli_json(inputs),
    ]


LIST_BACKUP_VAULTS = ActionDefinition(
    action_id="backup.list_backup_vaults",
    display_name="List backup vaults",
    service_id="backup",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="backup", command="list-backup-vaults"),
    boto3_template=Boto3Template(service="backup", operation="list_backup_vaults"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("vault_name", "number_of_recovery_points", "locked", "creation_date", "arn"),
        title="Backup vaults",
    ),
    iam_permissions=("backup:ListBackupVaults",),
    description="List all AWS Backup vaults in the current region.",
    view=to_backup_vault_summaries,
)


LIST_BACKUP_PLANS = ActionDefinition(
    action_id="backup.list_backup_plans",
    display_name="List backup plans",
    service_id="backup",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="include_deleted",
            label="Include deleted plans",
            kind="bool",
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="list-backup-plans",
        arg_map={"include_deleted": "include-deleted"},
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="list_backup_plans",
        param_map={"include_deleted": "IncludeDeleted"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("plan_id", "plan_name", "version_id", "creation_date", "arn"),
        title="Backup plans",
    ),
    iam_permissions=("backup:ListBackupPlans",),
    description="List AWS Backup plans (current version of each).",
    view=to_backup_plan_summaries,
)


LIST_RECOVERY_POINTS_BY_BACKUP_VAULT = ActionDefinition(
    action_id="backup.list_recovery_points_by_backup_vault",
    display_name="List recovery points in vault",
    service_id="backup",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="vault_name", label="Vault name", required=True),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="list-recovery-points-by-backup-vault",
        arg_map={"vault_name": "backup-vault-name"},
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="list_recovery_points_by_backup_vault",
        param_map={"vault_name": "BackupVaultName"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=(
            "recovery_point_arn",
            "resource_type",
            "resource_arn",
            "status",
            "creation_date",
        ),
        title="Recovery points",
    ),
    iam_permissions=("backup:ListRecoveryPointsByBackupVault",),
    description=(
        "List recovery points inside a backup vault. (Moto: not implemented; needs real AWS or "
        "a different emulator.)"
    ),
    view=to_recovery_point_summaries,
)


LIST_BACKUP_JOBS = ActionDefinition(
    action_id="backup.list_backup_jobs",
    display_name="List backup jobs",
    service_id="backup",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="by_state",
            label="Filter by state",
            kind="choice",
            choices=(
                "",
                "CREATED",
                "PENDING",
                "RUNNING",
                "ABORTING",
                "ABORTED",
                "COMPLETED",
                "FAILED",
                "EXPIRED",
            ),
        ),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="list-backup-jobs",
        arg_map={"by_state": "by-state"},
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="list_backup_jobs",
        param_map={"by_state": "ByState"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("job_id", "state", "resource_type", "vault_name", "creation_date"),
        title="Backup jobs",
    ),
    iam_permissions=("backup:ListBackupJobs",),
    description="List recent AWS Backup jobs. (Moto: not implemented.)",
    view=to_backup_job_summaries,
)


LIST_RESTORE_JOBS = ActionDefinition(
    action_id="backup.list_restore_jobs",
    display_name="List restore jobs",
    service_id="backup",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="backup", command="list-restore-jobs"),
    boto3_template=Boto3Template(service="backup", operation="list_restore_jobs"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("job_id", "status", "resource_type", "creation_date"),
        title="Restore jobs",
    ),
    iam_permissions=("backup:ListRestoreJobs",),
    description="List recent AWS Backup restore jobs. (Moto: not implemented.)",
    view=to_restore_job_summaries,
)


CREATE_BACKUP_VAULT = ActionDefinition(
    action_id="backup.create_backup_vault",
    display_name="Create backup vault",
    service_id="backup",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="vault_name", label="Vault name", required=True),
        InputField(
            name="encryption_key_arn",
            label="KMS key ARN (optional)",
            help_text="Defaults to the AWS-managed key if blank.",
        ),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="create-backup-vault",
        arg_map={
            "vault_name": "backup-vault-name",
            "encryption_key_arn": "encryption-key-arn",
        },
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="create_backup_vault",
        param_map={
            "vault_name": "BackupVaultName",
            "encryption_key_arn": "EncryptionKeyArn",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create vault result"),
    iam_permissions=("backup:CreateBackupVault",),
    description="Create a new AWS Backup vault.",
    cache_refresh_nav_ids=("vaults",),
)


DELETE_BACKUP_VAULT = ActionDefinition(
    action_id="backup.delete_backup_vault",
    display_name="Delete backup vault",
    service_id="backup",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="vault_name", label="Vault name", required=True),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="delete-backup-vault",
        arg_map={"vault_name": "backup-vault-name"},
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="delete_backup_vault",
        param_map={"vault_name": "BackupVaultName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete vault result"),
    iam_permissions=("backup:DeleteBackupVault",),
    description="Delete an empty AWS Backup vault.",
    cache_refresh_nav_ids=("vaults",),
)


CREATE_BACKUP_PLAN = ActionDefinition(
    action_id="backup.create_backup_plan",
    display_name="Create backup plan",
    service_id="backup",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="plan_name", label="Plan name", required=True),
        InputField(name="rule_name", label="Schedule name", required=True),
        InputField(name="target_vault_name", label="Target vault name", required=True),
        InputField(name="schedule_expression", label="Schedule expression", required=True),
        InputField(name="start_window_minutes", label="Start window minutes", kind="int"),
        InputField(name="completion_window_minutes", label="Completion window minutes", kind="int"),
        InputField(
            name="lifecycle_move_to_cold_storage_after_days",
            label="Move to cold storage after days",
            kind="int",
        ),
        InputField(name="lifecycle_delete_after_days", label="Delete after days", kind="int"),
    ),
    cli_template=CliTemplate(service="backup", command="create-backup-plan"),
    boto3_template=Boto3Template(service="backup", operation="create_backup_plan"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create backup plan result"),
    iam_permissions=("backup:CreateBackupPlan", "backup:ListBackupPlans"),
    description="Create a backup plan with one schedule rule.",
    cache_refresh_nav_ids=("plans",),
    cli_args_builder=_create_backup_plan_cli_args,
    boto3_params_builder=_create_backup_plan_boto3_params,
)


UPDATE_BACKUP_PLAN = ActionDefinition(
    action_id="backup.update_backup_plan",
    display_name="Update backup plan schedule",
    service_id="backup",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="plan_id", label="Plan ID", required=True),
        InputField(name="plan_name", label="Plan name", required=True),
        InputField(name="rule_name", label="Schedule name", required=True),
        InputField(name="target_vault_name", label="Target vault name", required=True),
        InputField(name="schedule_expression", label="Schedule expression", required=True),
        InputField(name="start_window_minutes", label="Start window minutes", kind="int"),
        InputField(name="completion_window_minutes", label="Completion window minutes", kind="int"),
        InputField(
            name="lifecycle_move_to_cold_storage_after_days",
            label="Move to cold storage after days",
            kind="int",
        ),
        InputField(name="lifecycle_delete_after_days", label="Delete after days", kind="int"),
    ),
    cli_template=CliTemplate(service="backup", command="update-backup-plan"),
    boto3_template=Boto3Template(service="backup", operation="update_backup_plan"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Update backup plan result"),
    iam_permissions=("backup:UpdateBackupPlan", "backup:ListBackupPlans"),
    description=(
        "Replace a backup plan's current schedule definition. Moto does not implement the write "
        "path yet, but the UI and generated scripts are ready for real AWS."
    ),
    cache_refresh_nav_ids=("plans",),
    cli_args_builder=_update_backup_plan_cli_args,
    boto3_params_builder=_update_backup_plan_boto3_params,
)


DELETE_BACKUP_PLAN = ActionDefinition(
    action_id="backup.delete_backup_plan",
    display_name="Delete backup plan",
    service_id="backup",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="plan_id", label="Plan ID", required=True),
    ),
    cli_template=CliTemplate(
        service="backup",
        command="delete-backup-plan",
        arg_map={"plan_id": "backup-plan-id"},
    ),
    boto3_template=Boto3Template(
        service="backup",
        operation="delete_backup_plan",
        param_map={"plan_id": "BackupPlanId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete backup plan result"),
    iam_permissions=("backup:DeleteBackupPlan",),
    description="Delete a backup plan.",
    cache_refresh_nav_ids=("plans",),
)


ALL_ACTIONS = (
    LIST_BACKUP_VAULTS,
    LIST_BACKUP_PLANS,
    LIST_RECOVERY_POINTS_BY_BACKUP_VAULT,
    LIST_BACKUP_JOBS,
    LIST_RESTORE_JOBS,
    CREATE_BACKUP_VAULT,
    DELETE_BACKUP_VAULT,
    CREATE_BACKUP_PLAN,
    UPDATE_BACKUP_PLAN,
    DELETE_BACKUP_PLAN,
)
