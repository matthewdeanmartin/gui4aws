"""CloudFormation action definitions."""

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
from gui4aws.services.cloudformation.views import to_stack_summaries

__all__ = [
    "ALL_ACTIONS",
    "CANCEL_UPDATE_STACK",
    "CDK_CONFIG",
    "DELETE_STACK",
    "DESCRIBE_STACK",
    "LIST_STACKS",
]


def _list_stacks_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    status_filter = inputs.get("stack_status_filter", "").strip()
    if status_filter:
        params["StackStatusFilter"] = [s.strip() for s in status_filter.split(",") if s.strip()]
    return params


def _list_stacks_cli_args(inputs: Mapping[str, str]) -> list[str]:
    args: list[str] = []
    status_filter = inputs.get("stack_status_filter", "").strip()
    if status_filter:
        args += ["--stack-status-filter"] + [s.strip() for s in status_filter.split(",") if s.strip()]
    return args


LIST_STACKS = ActionDefinition(
    action_id="cloudformation.list_stacks",
    display_name="List stacks",
    service_id="cloudformation",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="stack_status_filter",
            label="Status filter (comma-sep, optional)",
            required=False,
            help_text="e.g. CREATE_COMPLETE,UPDATE_COMPLETE — leave blank for all stacks.",
        ),
    ),
    cli_template=CliTemplate(service="cloudformation", command="describe-stacks"),
    boto3_template=Boto3Template(service="cloudformation", operation="describe_stacks"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "status", "description", "creation_time", "last_updated_time"),
        title="CloudFormation Stacks",
    ),
    iam_permissions=("cloudformation:DescribeStacks",),
    description="List CloudFormation stacks. Filter by status to narrow results (e.g. hide deleted stacks).",
    view=to_stack_summaries,
    cli_args_builder=_list_stacks_cli_args,
    boto3_params_builder=_list_stacks_boto3_params,
)


DESCRIBE_STACK = ActionDefinition(
    action_id="cloudformation.describe_stack",
    display_name="Describe stack",
    service_id="cloudformation",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="stack_name", label="Stack name or ARN", required=True),),
    cli_template=CliTemplate(
        service="cloudformation",
        command="describe-stacks",
        arg_map={"stack_name": "stack-name"},
    ),
    boto3_template=Boto3Template(
        service="cloudformation",
        operation="describe_stacks",
        param_map={"stack_name": "StackName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Stack details"),
    iam_permissions=("cloudformation:DescribeStacks",),
    description="Describe a specific CloudFormation stack including its outputs and parameters.",
)


DELETE_STACK = ActionDefinition(
    action_id="cloudformation.delete_stack",
    display_name="Delete stack",
    service_id="cloudformation",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="stack_name",
            label="Stack name or ARN",
            required=True,
            help_text="All resources created by this stack will be deleted.",
        ),
        InputField(
            name="retain_resources",
            label="Resources to retain (comma-sep logical IDs, optional)",
            required=False,
            help_text="Logical resource IDs to keep after stack deletion.",
        ),
    ),
    cli_template=CliTemplate(
        service="cloudformation",
        command="delete-stack",
        arg_map={"stack_name": "stack-name"},
    ),
    boto3_template=Boto3Template(
        service="cloudformation",
        operation="delete_stack",
        param_map={"stack_name": "StackName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete stack result"),
    iam_permissions=("cloudformation:DeleteStack",),
    description="Delete a CloudFormation stack and (by default) all its resources.",
    cache_refresh_nav_ids=("stacks",),
)


CANCEL_UPDATE_STACK = ActionDefinition(
    action_id="cloudformation.cancel_update_stack",
    display_name="Cancel update",
    service_id="cloudformation",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="stack_name",
            label="Stack name or ARN",
            required=True,
            help_text="Stack must currently be in UPDATE_IN_PROGRESS state.",
        ),
    ),
    cli_template=CliTemplate(
        service="cloudformation",
        command="cancel-update-stack",
        arg_map={"stack_name": "stack-name"},
    ),
    boto3_template=Boto3Template(
        service="cloudformation",
        operation="cancel_update_stack",
        param_map={"stack_name": "StackName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Cancel update result"),
    iam_permissions=("cloudformation:CancelUpdateStack",),
    description="Cancel a stack update that is currently in progress.",
    cache_refresh_nav_ids=("stacks",),
)


def _cdk_config_text(inputs: Mapping[str, str]) -> str:
    account = inputs.get("account_id", "").strip() or "000000000000"
    region = inputs.get("region", "").strip() or "us-east-1"
    endpoint = inputs.get("endpoint_url", "").strip()

    env_block = f"""# Shell environment variables
export CDK_DEFAULT_ACCOUNT={account}
export CDK_DEFAULT_REGION={region}"""

    if endpoint:
        env_block += f"""
export AWS_ENDPOINT_URL={endpoint}"""

    cdk_json_block = f"""// cdk.json  (merge into the "context" key)
{{
  "context": {{
    "@aws-cdk/core:bootstrapQualifier": "demo",
    "aws:cdk:enable-path-metadata": false
  }},
  "env": {{
    "account": "{account}",
    "region": "{region}"
  }}
}}"""

    python_env_block = f"""# Python CDK app — pass env explicitly
import aws_cdk as cdk

app = cdk.App()
env = cdk.Environment(account="{account}", region="{region}")
MyStack(app, "MyStack", env=env)
app.synth()"""

    bootstrap_note = ""
    if endpoint:
        bootstrap_note = f"""
# CDK bootstrap against a local endpoint
# NOTE: bootstrap may fail against moto (limited CloudFormation support).
# Robotocore has better coverage. Run once before cdk deploy:
#
#   cdk bootstrap aws://{account}/{region} \\
#       --toolkit-stack-name CDKToolkit \\
#       --qualifier demo
#
# If bootstrap fails, try deploying without it using:
#   cdk deploy --require-approval never
"""
    else:
        bootstrap_note = f"""
# CDK bootstrap against real AWS (run once per account/region):
#   cdk bootstrap aws://{account}/{region}
"""

    workflow = """# Typical workflow
cdk synth          # generate CloudFormation template (no AWS calls)
cdk diff           # compare deployed stack with local template
cdk deploy         # deploy (requires bootstrap if using assets)
cdk destroy        # tear down"""

    return "\n\n".join(
        [
            "=== Shell Environment Variables ===",
            env_block,
            "=== cdk.json snippet ===",
            cdk_json_block,
            "=== Python CDK app env ===",
            python_env_block,
            "=== Bootstrap ===",
            bootstrap_note.strip(),
            "=== Workflow ===",
            workflow,
        ]
    )


CDK_CONFIG = ActionDefinition(
    action_id="cloudformation.cdk_config",
    display_name="CDK config info",
    service_id="cloudformation",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
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
            help_text="AWS region, e.g. us-east-1.",
        ),
        InputField(
            name="endpoint_url",
            label="Endpoint URL (optional)",
            required=False,
            help_text="http://localhost:5000 (moto) or http://localhost:4566 (robotocore). Leave blank for real AWS.",
        ),
    ),
    cli_template=CliTemplate(service="cloudformation", command="list-stacks"),
    boto3_template=Boto3Template(service="cloudformation", operation="list_stacks"),
    result_view=ResultViewDefinition(kind=ResultViewKind.TEXT, title="CDK config"),
    iam_permissions=(),
    description=(
        "Copy-paste CDK configuration for this endpoint. "
        "Fill in Account ID, Region, and Endpoint URL above, then click Refresh. "
        "The output panel shows shell exports, cdk.json snippet, and workflow commands ready to copy."
    ),
    text_generator=_cdk_config_text,
)


ALL_ACTIONS = (
    LIST_STACKS,
    DESCRIBE_STACK,
    DELETE_STACK,
    CANCEL_UPDATE_STACK,
    CDK_CONFIG,
)
