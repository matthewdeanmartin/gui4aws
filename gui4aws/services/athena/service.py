"""ServiceDefinition for Athena."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.athena.actions import (
    ALL_ACTIONS,
    CREATE_WORK_GROUP,
    DELETE_WORK_GROUP,
    GET_QUERY_EXECUTION,
    LIST_QUERY_EXECUTIONS,
    LIST_WORK_GROUPS,
    STOP_QUERY_EXECUTION,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="athena",
    display_name="Athena",
    boto3_service_name="athena",
    cli_service_name="athena",
    navigation_items=(
        NavigationItem(
            item_id="workgroups",
            display_name="Workgroups",
            default_action_id=LIST_WORK_GROUPS.action_id,
            row_actions=(
                RowAction(
                    action_id=CREATE_WORK_GROUP.action_id,
                    button_label="Create Workgroup",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_WORK_GROUP.action_id,
                    button_label="Delete Workgroup",
                    prefill={"work_group": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="executions",
            display_name="Query Executions",
            default_action_id=LIST_QUERY_EXECUTIONS.action_id,
            filter_fields=(
                InputField(
                    name="work_group",
                    label="Workgroup",
                    required=False,
                    help_text="Leave blank for the primary workgroup.",
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=GET_QUERY_EXECUTION.action_id,
                    button_label="Get Details",
                    prefill={"query_execution_id": "query_execution_id"},
                ),
                RowAction(
                    action_id=STOP_QUERY_EXECUTION.action_id,
                    button_label="Stop Query",
                    prefill={"query_execution_id": "query_execution_id"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
