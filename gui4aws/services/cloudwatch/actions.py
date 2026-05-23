"""CloudWatch action definitions (alarms + log groups)."""

from __future__ import annotations

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.cloudwatch.views import (
    to_alarm_summaries,
    to_log_event_summaries,
    to_log_group_summaries,
    to_log_stream_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_LOG_GROUP",
    "DELETE_ALARM",
    "DELETE_LOG_GROUP",
    "DESCRIBE_ALARM",
    "DESCRIBE_ALARMS",
    "GET_LOG_EVENTS",
    "LIST_LOG_GROUPS",
    "LIST_LOG_STREAMS",
]


DESCRIBE_ALARMS = ActionDefinition(
    action_id="cloudwatch.describe_alarms",
    display_name="List alarms",
    service_id="cloudwatch",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="alarm_name_prefix",
            label="Alarm name prefix (optional)",
            required=False,
        ),
        InputField(
            name="state_value",
            label="State filter",
            kind="choice",
            choices=("", "OK", "ALARM", "INSUFFICIENT_DATA"),
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="cloudwatch",
        command="describe-alarms",
        arg_map={"alarm_name_prefix": "alarm-name-prefix", "state_value": "state-value"},
    ),
    boto3_template=Boto3Template(
        service="cloudwatch",
        operation="describe_alarms",
        param_map={"alarm_name_prefix": "AlarmNamePrefix", "state_value": "StateValue"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "state", "metric_name", "namespace", "comparison", "threshold", "description"),
        title="CloudWatch Alarms",
    ),
    iam_permissions=("cloudwatch:DescribeAlarms",),
    description="List CloudWatch metric alarms, optionally filtered by name prefix or state.",
    view=to_alarm_summaries,
)


DESCRIBE_ALARM = ActionDefinition(
    action_id="cloudwatch.describe_alarm",
    display_name="Describe alarm",
    service_id="cloudwatch",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="alarm_names", label="Alarm name", required=True),
    ),
    cli_template=CliTemplate(
        service="cloudwatch",
        command="describe-alarms",
        arg_map={"alarm_names": "alarm-names"},
    ),
    boto3_template=Boto3Template(
        service="cloudwatch",
        operation="describe_alarms",
        param_map={"alarm_names": "AlarmNames"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Alarm details"),
    iam_permissions=("cloudwatch:DescribeAlarms",),
    description="Describe a specific CloudWatch alarm.",
)


DELETE_ALARM = ActionDefinition(
    action_id="cloudwatch.delete_alarm",
    display_name="Delete alarm",
    service_id="cloudwatch",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="alarm_name", label="Alarm name", required=True),
    ),
    cli_template=CliTemplate(
        service="cloudwatch",
        command="delete-alarms",
        arg_map={"alarm_name": "alarm-names"},
    ),
    boto3_template=Boto3Template(
        service="cloudwatch",
        operation="delete_alarms",
        param_map={"alarm_name": "AlarmNames"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete alarm result"),
    iam_permissions=("cloudwatch:DeleteAlarms",),
    description="Delete a CloudWatch alarm.",
    cache_refresh_nav_ids=("alarms",),
)


LIST_LOG_GROUPS = ActionDefinition(
    action_id="cloudwatch.list_log_groups",
    display_name="List log groups",
    service_id="cloudwatch",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="log_group_name_prefix",
            label="Log group name prefix (optional)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="logs",
        command="describe-log-groups",
        arg_map={"log_group_name_prefix": "log-group-name-prefix"},
    ),
    boto3_template=Boto3Template(
        service="logs",
        operation="describe_log_groups",
        param_map={"log_group_name_prefix": "logGroupNamePrefix"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "retention_days", "stored_bytes", "arn"),
        title="CloudWatch Log Groups",
    ),
    iam_permissions=("logs:DescribeLogGroups",),
    description="List CloudWatch Logs log groups.",
    view=to_log_group_summaries,
)


CREATE_LOG_GROUP = ActionDefinition(
    action_id="cloudwatch.create_log_group",
    display_name="Create log group",
    service_id="cloudwatch",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="log_group_name", label="Log group name", required=True),
        InputField(
            name="retention_in_days",
            label="Retention (days)",
            kind="int",
            required=False,
            help_text="Leave blank for no expiry. Common values: 7, 14, 30, 60, 90, 365.",
        ),
    ),
    cli_template=CliTemplate(
        service="logs",
        command="create-log-group",
        arg_map={"log_group_name": "log-group-name"},
    ),
    boto3_template=Boto3Template(
        service="logs",
        operation="create_log_group",
        param_map={"log_group_name": "logGroupName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create log group result"),
    iam_permissions=("logs:CreateLogGroup",),
    description="Create a new CloudWatch Logs log group.",
    cache_refresh_nav_ids=("log_groups",),
)


DELETE_LOG_GROUP = ActionDefinition(
    action_id="cloudwatch.delete_log_group",
    display_name="Delete log group",
    service_id="cloudwatch",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="log_group_name",
            label="Log group name",
            required=True,
            help_text="All log streams and events in this group will be permanently deleted.",
        ),
    ),
    cli_template=CliTemplate(
        service="logs",
        command="delete-log-group",
        arg_map={"log_group_name": "log-group-name"},
    ),
    boto3_template=Boto3Template(
        service="logs",
        operation="delete_log_group",
        param_map={"log_group_name": "logGroupName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete log group result"),
    iam_permissions=("logs:DeleteLogGroup",),
    description="Delete a CloudWatch Logs log group and all its data.",
    cache_refresh_nav_ids=("log_groups",),
)


LIST_LOG_STREAMS = ActionDefinition(
    action_id="cloudwatch.list_log_streams",
    display_name="List log streams",
    service_id="cloudwatch",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="log_group_name", label="Log group name", required=True),
        InputField(
            name="log_stream_name_prefix",
            label="Stream name prefix (optional)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="logs",
        command="describe-log-streams",
        arg_map={"log_group_name": "log-group-name", "log_stream_name_prefix": "log-stream-name-prefix"},
    ),
    boto3_template=Boto3Template(
        service="logs",
        operation="describe_log_streams",
        param_map={"log_group_name": "logGroupName", "log_stream_name_prefix": "logStreamNamePrefix"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("stream_name", "last_event_time", "first_event_time", "stored_bytes"),
        title="Log Streams",
    ),
    iam_permissions=("logs:DescribeLogStreams",),
    description="List log streams within a log group.",
    view=to_log_stream_summaries,
)


GET_LOG_EVENTS = ActionDefinition(
    action_id="cloudwatch.get_log_events",
    display_name="Get log events",
    service_id="cloudwatch",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="log_group_name", label="Log group name", required=True),
        InputField(name="log_stream_name", label="Log stream name", required=True),
        InputField(
            name="limit",
            label="Max events (default 100)",
            kind="int",
            required=False,
            default="100",
            help_text="Number of log events to retrieve (1-10000).",
        ),
    ),
    cli_template=CliTemplate(
        service="logs",
        command="get-log-events",
        arg_map={
            "log_group_name": "log-group-name",
            "log_stream_name": "log-stream-name",
            "limit": "limit",
        },
    ),
    boto3_template=Boto3Template(
        service="logs",
        operation="get_log_events",
        param_map={
            "log_group_name": "logGroupName",
            "log_stream_name": "logStreamName",
            "limit": "limit",
        },
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("timestamp", "message"),
        title="Log Events",
    ),
    iam_permissions=("logs:GetLogEvents",),
    description="Retrieve log events from a specific log stream.",
    view=to_log_event_summaries,
)


ALL_ACTIONS = (
    DESCRIBE_ALARMS,
    DESCRIBE_ALARM,
    DELETE_ALARM,
    LIST_LOG_GROUPS,
    CREATE_LOG_GROUP,
    DELETE_LOG_GROUP,
    LIST_LOG_STREAMS,
    GET_LOG_EVENTS,
)
