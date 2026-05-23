"""ServiceDefinition for SES."""
from __future__ import annotations
from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.ses.actions import (
    ALL_ACTIONS, DELETE_IDENTITY, LIST_IDENTITIES, LIST_TEMPLATES, VERIFY_EMAIL_IDENTITY,
)

__all__ = ["SERVICE"]

SERVICE = ServiceDefinition(
    service_id="ses",
    display_name="SES",
    boto3_service_name="ses",
    cli_service_name="ses",
    navigation_items=(
        NavigationItem(
            item_id="identities",
            display_name="Identities",
            default_action_id=LIST_IDENTITIES.action_id,
            row_actions=(
                RowAction(
                    action_id=VERIFY_EMAIL_IDENTITY.action_id,
                    button_label="Verify Email",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_IDENTITY.action_id,
                    button_label="Delete Identity",
                    prefill={"identity": "identity"},
                ),
            ),
        ),
        NavigationItem(
            item_id="templates",
            display_name="Templates",
            default_action_id=LIST_TEMPLATES.action_id,
        ),
    ),
    actions=ALL_ACTIONS,
)
