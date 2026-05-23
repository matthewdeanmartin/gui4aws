"""Lambda action definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.lambdas.views import to_function_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_FUNCTION",
    "DELETE_FUNCTION",
    "GET_FUNCTION",
    "INVOKE_FUNCTION",
    "LIST_FUNCTIONS",
]


def _create_function_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    import json

    params: dict[str, Any] = {
        "FunctionName": inputs["function_name"],
        "Runtime": inputs.get("runtime", "python3.11"),
        "Role": inputs["role_arn"],
        "Handler": inputs.get("handler", "handler.handler"),
    }
    zip_path = inputs.get("zip_file_path", "")
    if zip_path:
        try:
            with open(zip_path, "rb") as fh:
                params["Code"] = {"ZipFile": fh.read()}
        except OSError:
            params["Code"] = {"ZipFile": b""}
    else:
        params["Code"] = {"ZipFile": b""}
    description = inputs.get("description", "")
    if description:
        params["Description"] = description
    return params


def _create_function_cli_args(inputs: Mapping[str, str]) -> list[str]:
    args = [
        "--function-name", inputs["function_name"],
        "--runtime", inputs.get("runtime", "python3.11"),
        "--role", inputs["role_arn"],
        "--handler", inputs.get("handler", "handler.handler"),
    ]
    zip_path = inputs.get("zip_file_path", "")
    if zip_path:
        args += ["--zip-file", f"fileb://{zip_path}"]
    if inputs.get("description"):
        args += ["--description", inputs["description"]]
    return args


def _invoke_function_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    import json

    params: dict[str, Any] = {"FunctionName": inputs["function_name"]}
    payload = inputs.get("payload", "")
    if payload:
        params["Payload"] = payload.encode("utf-8")
    invocation_type = inputs.get("invocation_type", "RequestResponse")
    if invocation_type:
        params["InvocationType"] = invocation_type
    return params


def _invoke_function_cli_args(inputs: Mapping[str, str]) -> list[str]:
    args = ["--function-name", inputs["function_name"]]
    if inputs.get("payload"):
        args += ["--payload", inputs["payload"]]
    if inputs.get("invocation_type"):
        args += ["--invocation-type", inputs["invocation_type"]]
    return args


LIST_FUNCTIONS = ActionDefinition(
    action_id="lambda.list_functions",
    display_name="List functions",
    service_id="lambda",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="lambda", command="list-functions"),
    boto3_template=Boto3Template(service="lambda", operation="list_functions"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "runtime", "handler", "state", "memory_size", "timeout", "last_modified"),
        title="Lambda Functions",
    ),
    iam_permissions=("lambda:ListFunctions",),
    description="List Lambda functions in the current region.",
    view=to_function_summaries,
)


GET_FUNCTION = ActionDefinition(
    action_id="lambda.get_function",
    display_name="Get function",
    service_id="lambda",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="function_name", label="Function name or ARN", required=True),
    ),
    cli_template=CliTemplate(
        service="lambda",
        command="get-function",
        arg_map={"function_name": "function-name"},
    ),
    boto3_template=Boto3Template(
        service="lambda",
        operation="get_function",
        param_map={"function_name": "FunctionName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Function details"),
    iam_permissions=("lambda:GetFunction",),
    description="Get details about a Lambda function including the code location.",
)


CREATE_FUNCTION = ActionDefinition(
    action_id="lambda.create_function",
    display_name="Create function",
    service_id="lambda",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="function_name", label="Function name", required=True),
        InputField(
            name="runtime",
            label="Runtime",
            kind="choice",
            choices=("python3.11", "python3.12", "python3.13", "nodejs20.x", "java21"),
            default="python3.11",
            required=True,
        ),
        InputField(name="role_arn", label="Execution role ARN", required=True),
        InputField(name="handler", label="Handler", required=False, default="handler.handler"),
        InputField(name="zip_file_path", label="Zip file path (local)", required=False, help_text="Absolute path to the deployment zip."),
        InputField(name="description", label="Description", required=False),
    ),
    cli_template=CliTemplate(service="lambda", command="create-function"),
    boto3_template=Boto3Template(service="lambda", operation="create_function"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create function result"),
    iam_permissions=("lambda:CreateFunction", "iam:PassRole"),
    description="Create a new Lambda function from a local deployment zip.",
    cache_refresh_nav_ids=("functions",),
    cli_args_builder=_create_function_cli_args,
    boto3_params_builder=_create_function_boto3_params,
)


DELETE_FUNCTION = ActionDefinition(
    action_id="lambda.delete_function",
    display_name="Delete function",
    service_id="lambda",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="function_name", label="Function name or ARN", required=True),
        InputField(
            name="qualifier",
            label="Version or alias (optional)",
            required=False,
            help_text="Leave blank to delete the whole function. Specify a version or alias to delete only that qualifier.",
        ),
    ),
    cli_template=CliTemplate(
        service="lambda",
        command="delete-function",
        arg_map={"function_name": "function-name", "qualifier": "qualifier"},
    ),
    boto3_template=Boto3Template(
        service="lambda",
        operation="delete_function",
        param_map={"function_name": "FunctionName", "qualifier": "Qualifier"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete function result"),
    iam_permissions=("lambda:DeleteFunction",),
    description="Delete a Lambda function (or a specific version/alias).",
    cache_refresh_nav_ids=("functions",),
)


INVOKE_FUNCTION = ActionDefinition(
    action_id="lambda.invoke_function",
    display_name="Invoke function",
    service_id="lambda",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="function_name", label="Function name or ARN", required=True),
        InputField(
            name="payload",
            label="Event payload (JSON)",
            kind="multiline",
            required=False,
            default="{}",
            help_text="JSON event to pass to the function.",
        ),
        InputField(
            name="invocation_type",
            label="Invocation type",
            kind="choice",
            choices=("RequestResponse", "Event", "DryRun"),
            default="RequestResponse",
        ),
    ),
    cli_template=CliTemplate(service="lambda", command="invoke"),
    boto3_template=Boto3Template(service="lambda", operation="invoke"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Invoke result"),
    iam_permissions=("lambda:InvokeFunction",),
    description="Invoke a Lambda function synchronously or asynchronously.",
    cli_args_builder=_invoke_function_cli_args,
    boto3_params_builder=_invoke_function_boto3_params,
)


ALL_ACTIONS = (
    LIST_FUNCTIONS,
    GET_FUNCTION,
    CREATE_FUNCTION,
    DELETE_FUNCTION,
    INVOKE_FUNCTION,
)
