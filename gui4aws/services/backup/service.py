"""ServiceDefinition for AWS Backup."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.backup.actions import (
    ALL_ACTIONS,
    CREATE_BACKUP_PLAN,
    CREATE_BACKUP_VAULT,
    DELETE_BACKUP_PLAN,
    DELETE_BACKUP_VAULT,
    LIST_BACKUP_JOBS,
    LIST_BACKUP_PLANS,
    LIST_BACKUP_VAULTS,
    LIST_RECOVERY_POINTS_BY_BACKUP_VAULT,
    LIST_RESTORE_JOBS,
    UPDATE_BACKUP_PLAN,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="backup",
    display_name="AWS Backup",
    boto3_service_name="backup",
    cli_service_name="backup",
    navigation_items=(
        NavigationItem(
            item_id="vaults",
            display_name="Backup Vaults",
            default_action_id=LIST_BACKUP_VAULTS.action_id,
            row_actions=(
                RowAction(
                    action_id=LIST_RECOVERY_POINTS_BY_BACKUP_VAULT.action_id,
                    button_label="View Recovery Points",
                    prefill={"vault_name": "vault_name"},
                ),
                RowAction(
                    action_id=CREATE_BACKUP_VAULT.action_id,
                    button_label="Create Vault",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_BACKUP_VAULT.action_id,
                    button_label="Delete Vault",
                    prefill={"vault_name": "vault_name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="plans",
            display_name="Backup Plans",
            default_action_id=LIST_BACKUP_PLANS.action_id,
            filter_fields=(
                InputField(name="include_deleted", label="Include deleted plans", kind="bool", default="false"),
            ),
            row_actions=(
                RowAction(
                    action_id=CREATE_BACKUP_PLAN.action_id,
                    button_label="Add Schedule",
                    prefill={},
                ),
                RowAction(
                    action_id=UPDATE_BACKUP_PLAN.action_id,
                    button_label="Edit Schedule",
                    prefill={"plan_id": "plan_id", "plan_name": "plan_name"},
                ),
                RowAction(
                    action_id=DELETE_BACKUP_PLAN.action_id,
                    button_label="Delete Plan",
                    prefill={"plan_id": "plan_id"},
                ),
            ),
        ),
        NavigationItem(
            item_id="jobs",
            display_name="Jobs",
            default_action_id=LIST_BACKUP_JOBS.action_id,
        ),
        NavigationItem(
            item_id="restore_jobs",
            display_name="Restore Jobs",
            default_action_id=LIST_RESTORE_JOBS.action_id,
        ),
    ),
    actions=ALL_ACTIONS,
)
