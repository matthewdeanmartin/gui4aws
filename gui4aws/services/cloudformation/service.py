"""ServiceDefinition for CloudFormation."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.cloudformation.actions import (
    ALL_ACTIONS,
    CANCEL_UPDATE_STACK,
    CDK_CONFIG,
    DELETE_STACK,
    DESCRIBE_STACK,
    LIST_STACKS,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="cloudformation",
    display_name="CloudFormation",
    boto3_service_name="cloudformation",
    cli_service_name="cloudformation",
    navigation_items=(
        NavigationItem(
            item_id="stacks",
            display_name="Stacks",
            default_action_id=LIST_STACKS.action_id,
            filter_fields=(
                InputField(
                    name="stack_status_filter",
                    label="Status filter (comma-sep)",
                    required=False,
                    help_text="e.g. CREATE_COMPLETE,UPDATE_COMPLETE — leave blank for all.",
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_STACK.action_id,
                    button_label="Describe",
                    prefill={"stack_name": "name"},
                ),
                RowAction(
                    action_id=CANCEL_UPDATE_STACK.action_id,
                    button_label="Cancel Update",
                    prefill={"stack_name": "name"},
                ),
                RowAction(
                    action_id=DELETE_STACK.action_id,
                    button_label="Delete Stack",
                    prefill={"stack_name": "name"},
                ),
                RowAction(
                    action_id="cdk://launch",
                    button_label="CDK",
                    prefill={"stack_name": "name"},
                ),
                RowAction(
                    action_id="terraform://launch",
                    button_label="Terraform",
                    prefill={},
                ),
            ),
        ),
        NavigationItem(
            item_id="cdk_config",
            display_name="CDK Config",
            default_action_id=CDK_CONFIG.action_id,
            filter_fields=(
                InputField(
                    name="account_id",
                    label="Account ID",
                    required=False,
                    default="000000000000",
                    help_text="12-digit AWS account ID. Use 000000000000 for moto/robotocore.",
                ),
                InputField(
                    name="region",
                    label="Region",
                    required=False,
                    default="us-east-1",
                ),
                InputField(
                    name="endpoint_url",
                    label="Endpoint URL (optional)",
                    required=False,
                    help_text="http://localhost:5000 (moto) or http://localhost:4566 (robotocore).",
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
