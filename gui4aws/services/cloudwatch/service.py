"""ServiceDefinition for CloudWatch (alarms + log groups)."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition, SubAction
from gui4aws.services.cloudwatch.actions import (
    ALL_ACTIONS,
    CREATE_LOG_GROUP,
    DELETE_ALARM,
    DELETE_LOG_GROUP,
    DESCRIBE_ALARM,
    DESCRIBE_ALARMS,
    GET_LOG_EVENTS,
    LIST_LOG_GROUPS,
    LIST_LOG_STREAMS,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="cloudwatch",
    display_name="CloudWatch",
    boto3_service_name="cloudwatch",
    cli_service_name="cloudwatch",
    navigation_items=(
        NavigationItem(
            item_id="alarms",
            display_name="Alarms",
            default_action_id=DESCRIBE_ALARMS.action_id,
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_ALARM.action_id,
                    button_label="Describe",
                    prefill={"alarm_names": "name"},
                ),
                RowAction(
                    action_id=DELETE_ALARM.action_id,
                    button_label="Delete Alarm",
                    prefill={"alarm_name": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="log_groups",
            display_name="Log Groups",
            default_action_id=LIST_LOG_GROUPS.action_id,
            row_actions=(
                RowAction(
                    action_id=LIST_LOG_STREAMS.action_id,
                    button_label="View Streams",
                    prefill={"log_group_name": "name"},
                ),
                RowAction(
                    action_id=CREATE_LOG_GROUP.action_id,
                    button_label="Create Log Group",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_LOG_GROUP.action_id,
                    button_label="Delete Log Group",
                    prefill={"log_group_name": "name"},
                ),
            ),
            sub_action=SubAction(
                action_id=LIST_LOG_STREAMS.action_id,
                panel_label="Log Streams",
                prefill={"log_group_name": "name"},
                columns=("stream_name", "last_event_time", "first_event_time"),
                row_actions=(
                    RowAction(
                        action_id=GET_LOG_EVENTS.action_id,
                        button_label="View Events",
                        prefill={"log_stream_name": "stream_name"},
                    ),
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
