"""ServiceDefinition for SSM Parameter Store."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.ssm.actions import (
    ALL_ACTIONS,
    DELETE_PARAMETER,
    DESCRIBE_PARAMETERS,
    GET_PARAMETER,
    GET_PARAMETERS_BY_PATH,
    PUT_PARAMETER,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="ssm",
    display_name="SSM Parameters",
    boto3_service_name="ssm",
    cli_service_name="ssm",
    navigation_items=(
        NavigationItem(
            item_id="parameters",
            display_name="Parameters",
            default_action_id=DESCRIBE_PARAMETERS.action_id,
            row_actions=(
                RowAction(
                    action_id=GET_PARAMETER.action_id,
                    button_label="Get Value",
                    prefill={"name": "name"},
                ),
                RowAction(
                    action_id=PUT_PARAMETER.action_id,
                    button_label="Update",
                    prefill={"name": "name"},
                ),
                RowAction(
                    action_id=DELETE_PARAMETER.action_id,
                    button_label="Delete",
                    prefill={"name": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="by_path",
            display_name="By Path",
            default_action_id=GET_PARAMETERS_BY_PATH.action_id,
            filter_fields=(
                InputField(
                    name="path",
                    label="Path",
                    required=True,
                    default="/",
                    help_text="Hierarchical prefix, e.g. /myapp/prod/",
                ),
                InputField(
                    name="recursive",
                    label="Recursive",
                    kind="bool",
                    required=False,
                    default="true",
                ),
                InputField(
                    name="with_decryption",
                    label="Decrypt",
                    kind="bool",
                    required=False,
                    default="false",
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=GET_PARAMETER.action_id,
                    button_label="Get Value",
                    prefill={"name": "name"},
                ),
                RowAction(
                    action_id=PUT_PARAMETER.action_id,
                    button_label="Update",
                    prefill={"name": "name"},
                ),
                RowAction(
                    action_id=DELETE_PARAMETER.action_id,
                    button_label="Delete",
                    prefill={"name": "name"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
