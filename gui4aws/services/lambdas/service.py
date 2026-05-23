"""ServiceDefinition for Lambda."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.lambdas.actions import (
    ALL_ACTIONS,
    CREATE_FUNCTION,
    DELETE_FUNCTION,
    GET_FUNCTION,
    INVOKE_FUNCTION,
    LIST_FUNCTIONS,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="lambda",
    display_name="Lambda",
    boto3_service_name="lambda",
    cli_service_name="lambda",
    navigation_items=(
        NavigationItem(
            item_id="functions",
            display_name="Functions",
            default_action_id=LIST_FUNCTIONS.action_id,
            row_actions=(
                RowAction(
                    action_id=GET_FUNCTION.action_id,
                    button_label="Get Details",
                    prefill={"function_name": "name"},
                ),
                RowAction(
                    action_id=INVOKE_FUNCTION.action_id,
                    button_label="Invoke",
                    prefill={"function_name": "name"},
                ),
                RowAction(
                    action_id=CREATE_FUNCTION.action_id,
                    button_label="Create Function",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_FUNCTION.action_id,
                    button_label="Delete",
                    prefill={"function_name": "name"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
