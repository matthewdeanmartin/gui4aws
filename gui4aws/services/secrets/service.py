"""ServiceDefinition for Secrets Manager."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.secrets.actions import (
    ALL_ACTIONS,
    CREATE_SECRET,
    DELETE_SECRET,
    DESCRIBE_SECRET,
    LIST_SECRETS,
    PUT_SECRET_VALUE,
    RESTORE_SECRET,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="secrets",
    display_name="Secrets Manager",
    boto3_service_name="secretsmanager",
    cli_service_name="secretsmanager",
    navigation_items=(
        NavigationItem(
            item_id="secrets",
            display_name="Secrets",
            default_action_id=LIST_SECRETS.action_id,
            filter_fields=(
                InputField(
                    name="include_deleted",
                    label="Include deleted",
                    kind="bool",
                    default="true",
                    help_text="Show secrets pending deletion alongside active ones.",
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_SECRET.action_id,
                    button_label="Describe",
                    prefill={"secret_id": "name"},
                ),
                RowAction(
                    action_id=PUT_SECRET_VALUE.action_id,
                    button_label="Update Value",
                    prefill={"secret_id": "name"},
                ),
                RowAction(
                    action_id=RESTORE_SECRET.action_id,
                    button_label="Restore",
                    prefill={"secret_id": "name"},
                ),
                RowAction(
                    action_id=DELETE_SECRET.action_id,
                    button_label="Delete",
                    prefill={"secret_id": "name"},
                ),
                RowAction(
                    action_id=CREATE_SECRET.action_id,
                    button_label="Create Secret",
                    prefill={},
                ),
                RowAction(
                    action_id="kms.describe_key",
                    button_label="View KMS Key",
                    prefill={"key_id": "kms_key_id"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
