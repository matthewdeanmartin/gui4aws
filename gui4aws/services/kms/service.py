"""ServiceDefinition for KMS."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.kms.actions import (
    ALL_ACTIONS,
    CREATE_ALIAS,
    CREATE_KEY,
    DELETE_ALIAS,
    DESCRIBE_KEY,
    DISABLE_KEY,
    ENABLE_KEY,
    LIST_ALIASES,
    LIST_GRANTS,
    LIST_KEYS,
    SCHEDULE_KEY_DELETION,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="kms",
    display_name="KMS",
    boto3_service_name="kms",
    cli_service_name="kms",
    navigation_items=(
        NavigationItem(
            item_id="keys",
            display_name="Keys",
            default_action_id=LIST_KEYS.action_id,
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_KEY.action_id,
                    button_label="Describe Key",
                    prefill={"key_id": "key_id"},
                ),
                RowAction(
                    action_id=ENABLE_KEY.action_id,
                    button_label="Enable Key",
                    prefill={"key_id": "key_id"},
                ),
                RowAction(
                    action_id=DISABLE_KEY.action_id,
                    button_label="Disable Key",
                    prefill={"key_id": "key_id"},
                ),
                RowAction(
                    action_id=SCHEDULE_KEY_DELETION.action_id,
                    button_label="Schedule Deletion",
                    prefill={"key_id": "key_id"},
                ),
            ),
        ),
        NavigationItem(
            item_id="aliases",
            display_name="Aliases",
            default_action_id=LIST_ALIASES.action_id,
            row_actions=(
                RowAction(
                    action_id=CREATE_ALIAS.action_id,
                    button_label="Create Alias",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_ALIAS.action_id,
                    button_label="Delete Alias",
                    prefill={"alias_name": "alias_name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="grants",
            display_name="Grants",
            default_action_id=LIST_GRANTS.action_id,
            filter_fields=(
                InputField(
                    name="key_id",
                    label="Key ID or ARN",
                    required=True,
                    help_text="Enter a key ID to view its grants.",
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
