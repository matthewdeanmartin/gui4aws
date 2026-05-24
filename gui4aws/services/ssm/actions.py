"""SSM Parameter Store action definitions."""

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
from gui4aws.services.ssm.views import to_parameter_summaries

__all__ = [
    "ALL_ACTIONS",
    "DELETE_PARAMETER",
    "DESCRIBE_PARAMETERS",
    "GET_PARAMETER",
    "GET_PARAMETERS_BY_PATH",
    "PUT_PARAMETER",
]


DESCRIBE_PARAMETERS = ActionDefinition(
    action_id="ssm.describe_parameters",
    display_name="Describe parameters",
    service_id="ssm",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="name_filter",
            label="Name contains (optional)",
            required=False,
            help_text="Substring to filter parameter names.",
        ),
    ),
    cli_template=CliTemplate(
        service="ssm",
        command="describe-parameters",
        arg_map={},
    ),
    boto3_template=Boto3Template(
        service="ssm",
        operation="describe_parameters",
        param_map={},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "type", "tier", "version", "last_modified_date", "description"),
        title="SSM Parameters",
    ),
    iam_permissions=("ssm:DescribeParameters",),
    description="List SSM Parameter Store parameters in the current region.",
    view=to_parameter_summaries,
)


GET_PARAMETERS_BY_PATH = ActionDefinition(
    action_id="ssm.get_parameters_by_path",
    display_name="Get parameters by path",
    service_id="ssm",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="path",
            label="Path prefix",
            required=True,
            default="/",
            help_text="Hierarchical path prefix, e.g. /myapp/prod/",
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
            label="Decrypt SecureString values",
            kind="bool",
            required=False,
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="ssm",
        command="get-parameters-by-path",
        arg_map={"path": "path", "recursive": "recursive", "with_decryption": "with-decryption"},
    ),
    boto3_template=Boto3Template(
        service="ssm",
        operation="get_parameters_by_path",
        param_map={"path": "Path", "recursive": "Recursive", "with_decryption": "WithDecryption"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "type", "tier", "version", "last_modified_date"),
        title="SSM Parameters by path",
    ),
    iam_permissions=("ssm:GetParametersByPath",),
    description="Retrieve all parameters under a given path hierarchy.",
    view=to_parameter_summaries,
)


GET_PARAMETER = ActionDefinition(
    action_id="ssm.get_parameter",
    display_name="Get parameter value",
    service_id="ssm",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="name", label="Parameter name", required=True),
        InputField(
            name="with_decryption",
            label="Decrypt SecureString",
            kind="bool",
            required=False,
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="ssm",
        command="get-parameter",
        arg_map={"name": "name", "with_decryption": "with-decryption"},
    ),
    boto3_template=Boto3Template(
        service="ssm",
        operation="get_parameter",
        param_map={"name": "Name", "with_decryption": "WithDecryption"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Parameter value"),
    iam_permissions=("ssm:GetParameter",),
    description="Get the value of a single SSM parameter.",
)


PUT_PARAMETER = ActionDefinition(
    action_id="ssm.put_parameter",
    display_name="Put parameter",
    service_id="ssm",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="name", label="Parameter name", required=True),
        InputField(name="value", label="Value", kind="multiline", required=True),
        InputField(
            name="type",
            label="Type",
            kind="choice",
            choices=("String", "StringList", "SecureString"),
            required=False,
            default="String",
        ),
        InputField(name="description", label="Description", required=False),
        InputField(
            name="overwrite",
            label="Overwrite existing",
            kind="bool",
            required=False,
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="ssm",
        command="put-parameter",
        arg_map={
            "name": "name",
            "value": "value",
            "type": "type",
            "description": "description",
            "overwrite": "overwrite",
        },
    ),
    boto3_template=Boto3Template(
        service="ssm",
        operation="put_parameter",
        param_map={
            "name": "Name",
            "value": "Value",
            "type": "Type",
            "description": "Description",
            "overwrite": "Overwrite",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Put parameter result"),
    iam_permissions=("ssm:PutParameter",),
    description="Create or update an SSM parameter.",
    cache_refresh_nav_ids=("parameters", "by_path"),
)


DELETE_PARAMETER = ActionDefinition(
    action_id="ssm.delete_parameter",
    display_name="Delete parameter",
    service_id="ssm",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="name", label="Parameter name", required=True),),
    cli_template=CliTemplate(
        service="ssm",
        command="delete-parameter",
        arg_map={"name": "name"},
    ),
    boto3_template=Boto3Template(
        service="ssm",
        operation="delete_parameter",
        param_map={"name": "Name"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.NONE, title=""),
    iam_permissions=("ssm:DeleteParameter",),
    description="Permanently delete an SSM parameter.",
    cache_refresh_nav_ids=("parameters", "by_path"),
)


ALL_ACTIONS = (
    DESCRIBE_PARAMETERS,
    GET_PARAMETERS_BY_PATH,
    GET_PARAMETER,
    PUT_PARAMETER,
    DELETE_PARAMETER,
)
