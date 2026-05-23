"""Athena action definitions — shell implementation.

Most write operations (StartQueryExecution with full result handling) are marked
NOT_IMPLEMENTED and show an informational dialog rather than firing real API calls.
Read-only list/describe actions are fully wired.
"""

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
from gui4aws.services.athena.views import to_query_execution_summaries, to_workgroup_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_WORK_GROUP",
    "DELETE_WORK_GROUP",
    "GET_QUERY_EXECUTION",
    "LIST_QUERY_EXECUTIONS",
    "LIST_WORK_GROUPS",
    "START_QUERY_EXECUTION",
    "STOP_QUERY_EXECUTION",
]


LIST_WORK_GROUPS = ActionDefinition(
    action_id="athena.list_work_groups",
    display_name="List workgroups",
    service_id="athena",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="athena", command="list-work-groups", arg_map={}),
    boto3_template=Boto3Template(service="athena", operation="list_work_groups", param_map={}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "state", "description", "creation_time"),
        title="Athena Workgroups",
    ),
    iam_permissions=("athena:ListWorkGroups",),
    description="List Athena workgroups in the current region.",
    view=to_workgroup_summaries,
)


LIST_QUERY_EXECUTIONS = ActionDefinition(
    action_id="athena.list_query_executions",
    display_name="List query executions",
    service_id="athena",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="work_group",
            label="Workgroup (optional)",
            required=False,
            help_text="Filter by workgroup. Leave blank for the primary workgroup.",
        ),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="list-query-executions",
        arg_map={"work_group": "work-group"},
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="list_query_executions",
        param_map={"work_group": "WorkGroup"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("query_execution_id", "state", "workgroup", "submission_date", "data_scanned_in_bytes"),
        title="Athena Query Executions",
    ),
    iam_permissions=("athena:ListQueryExecutions",),
    description="List recent Athena query execution IDs.",
    view=to_query_execution_summaries,
)


GET_QUERY_EXECUTION = ActionDefinition(
    action_id="athena.get_query_execution",
    display_name="Get query execution",
    service_id="athena",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="query_execution_id", label="Query execution ID", required=True),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="get-query-execution",
        arg_map={"query_execution_id": "query-execution-id"},
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="get_query_execution",
        param_map={"query_execution_id": "QueryExecutionId"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("query_execution_id", "query", "state", "state_change_reason", "workgroup", "submission_date", "completion_date"),
        title="Query Execution Detail",
    ),
    iam_permissions=("athena:GetQueryExecution",),
    description="Get details of a single Athena query execution.",
    view=to_query_execution_summaries,
)


START_QUERY_EXECUTION = ActionDefinition(
    action_id="athena.start_query_execution",
    display_name="Start query execution",
    service_id="athena",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(
            name="query_string",
            label="SQL query",
            kind="multiline",
            required=True,
            help_text="SELECT statement or DDL to execute.",
        ),
        InputField(
            name="work_group",
            label="Workgroup",
            required=False,
            default="primary",
        ),
        InputField(
            name="output_location",
            label="Output S3 location",
            required=False,
            help_text="s3://bucket/prefix/ — required unless set in workgroup config.",
        ),
        InputField(
            name="database",
            label="Database (optional)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="start-query-execution",
        arg_map={
            "query_string": "query-string",
            "work_group": "work-group",
        },
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="start_query_execution",
        param_map={
            "query_string": "QueryString",
            "work_group": "WorkGroup",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Start query result"),
    iam_permissions=("athena:StartQueryExecution", "s3:PutObject"),
    description=(
        "Start an Athena query execution. Note: full result retrieval (GetQueryResults) "
        "is not yet implemented in this GUI — use the AWS console or CLI for result pages."
    ),
    cache_refresh_nav_ids=("executions",),
)


STOP_QUERY_EXECUTION = ActionDefinition(
    action_id="athena.stop_query_execution",
    display_name="Stop query execution",
    service_id="athena",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="query_execution_id", label="Query execution ID", required=True),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="stop-query-execution",
        arg_map={"query_execution_id": "query-execution-id"},
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="stop_query_execution",
        param_map={"query_execution_id": "QueryExecutionId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Stop query result"),
    iam_permissions=("athena:StopQueryExecution",),
    description="Stop a running Athena query execution.",
    cache_refresh_nav_ids=("executions",),
)


CREATE_WORK_GROUP = ActionDefinition(
    action_id="athena.create_work_group",
    display_name="Create workgroup",
    service_id="athena",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="name", label="Workgroup name", required=True),
        InputField(name="description", label="Description", required=False),
        InputField(
            name="output_location",
            label="Default output S3 location",
            required=False,
            help_text="s3://bucket/prefix/",
        ),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="create-work-group",
        arg_map={"name": "name", "description": "description"},
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="create_work_group",
        param_map={"name": "Name", "description": "Description"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create workgroup result"),
    iam_permissions=("athena:CreateWorkGroup",),
    description="Create a new Athena workgroup.",
    cache_refresh_nav_ids=("workgroups",),
)


DELETE_WORK_GROUP = ActionDefinition(
    action_id="athena.delete_work_group",
    display_name="Delete workgroup",
    service_id="athena",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="work_group", label="Workgroup name", required=True),
        InputField(
            name="recursive_delete_option",
            label="Recursively delete queries",
            kind="bool",
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="athena",
        command="delete-work-group",
        arg_map={
            "work_group": "work-group",
            "recursive_delete_option": "recursive-delete-option",
        },
    ),
    boto3_template=Boto3Template(
        service="athena",
        operation="delete_work_group",
        param_map={
            "work_group": "WorkGroup",
            "recursive_delete_option": "RecursiveDeleteOption",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete workgroup result"),
    iam_permissions=("athena:DeleteWorkGroup",),
    description="Delete an Athena workgroup.",
    cache_refresh_nav_ids=("workgroups",),
)


ALL_ACTIONS = (
    LIST_WORK_GROUPS,
    LIST_QUERY_EXECUTIONS,
    GET_QUERY_EXECUTION,
    START_QUERY_EXECUTION,
    STOP_QUERY_EXECUTION,
    CREATE_WORK_GROUP,
    DELETE_WORK_GROUP,
)
