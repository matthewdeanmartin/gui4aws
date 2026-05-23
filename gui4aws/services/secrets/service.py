"""ServiceDefinition for Secrets Manager."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.secrets.actions import (
    ALL_ACTIONS,
    CREATE_SECRET,
    DELETE_SECRET,
    DESCRIBE_SECRET,
    LIST_SECRETS,
    PUT_SECRET_VALUE,
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
                    action_id=DELETE_SECRET.action_id,
                    button_label="Delete",
                    prefill={"secret_id": "name"},
                ),
                RowAction(
                    action_id=CREATE_SECRET.action_id,
                    button_label="Create Secret",
                    prefill={},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
