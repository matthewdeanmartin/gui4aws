"""Secrets Manager action definitions."""

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
from gui4aws.services.secrets.views import to_secret_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_SECRET",
    "DELETE_SECRET",
    "DESCRIBE_SECRET",
    "LIST_SECRETS",
    "PUT_SECRET_VALUE",
    "RESTORE_SECRET",
]


def list_secrets_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Map UI inputs to boto3 list_secrets parameters."""
    params: dict[str, Any] = {}
    include_deleted = inputs.get("include_deleted", "false").lower() == "true"
    if include_deleted:
        # IncludePlannedDeletion shows secrets scheduled for deletion
        params["IncludePlannedDeletion"] = True
    if inputs.get("name_prefix"):
        params["Filters"] = [{"Key": "name", "Values": [inputs["name_prefix"]]}]
    return params


def list_secrets_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map UI inputs to AWS CLI list-secrets arguments."""
    args: list[str] = []
    if inputs.get("include_deleted", "false").lower() == "true":
        args += ["--include-planned-deletion"]
    if inputs.get("name_prefix"):
        args += ["--filters", f"Key=name,Values={inputs['name_prefix']}"]
    return args


LIST_SECRETS = ActionDefinition(
    action_id="secrets.list_secrets",
    display_name="List secrets",
    service_id="secrets",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="name_prefix",
            label="Name prefix filter (optional)",
            required=False,
            help_text="Partial secret name to filter by.",
        ),
        InputField(
            name="include_deleted",
            label="Include deleted (pending deletion)",
            kind="bool",
            default="true",
            help_text="Show secrets scheduled for deletion alongside active ones.",
        ),
    ),
    cli_template=CliTemplate(service="secretsmanager", command="list-secrets"),
    boto3_template=Boto3Template(service="secretsmanager", operation="list_secrets"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "description", "deleted", "deletion_date", "rotation_enabled", "last_changed_date"),
        title="Secrets",
    ),
    iam_permissions=("secretsmanager:ListSecrets",),
    description="List secrets. Enable 'Include deleted' to also show secrets pending deletion.",
    view=to_secret_summaries,
    cli_args_builder=list_secrets_cli_args,
    boto3_params_builder=list_secrets_boto3_params,
)


DESCRIBE_SECRET = ActionDefinition(
    action_id="secrets.describe_secret",
    display_name="Describe secret",
    service_id="secrets",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="secret_id",
            label="Secret name or ARN",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="secretsmanager",
        command="describe-secret",
        arg_map={"secret_id": "secret-id"},
    ),
    boto3_template=Boto3Template(
        service="secretsmanager",
        operation="describe_secret",
        param_map={"secret_id": "SecretId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Secret details"),
    iam_permissions=("secretsmanager:DescribeSecret",),
    description="Describe a single secret (no secret value returned).",
)


CREATE_SECRET = ActionDefinition(
    action_id="secrets.create_secret",
    display_name="Create secret",
    service_id="secrets",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="name", label="Secret name", required=True),
        InputField(name="description", label="Description", required=False),
        InputField(
            name="secret_string",
            label="Secret value",
            kind="multiline",
            required=True,
            help_text="Plain text or JSON string.",
        ),
    ),
    cli_template=CliTemplate(
        service="secretsmanager",
        command="create-secret",
        arg_map={"name": "name", "description": "description", "secret_string": "secret-string"},
    ),
    boto3_template=Boto3Template(
        service="secretsmanager",
        operation="create_secret",
        param_map={"name": "Name", "description": "Description", "secret_string": "SecretString"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create secret result"),
    iam_permissions=("secretsmanager:CreateSecret",),
    description="Create a new secret.",
    cache_refresh_nav_ids=("secrets",),
)


PUT_SECRET_VALUE = ActionDefinition(
    action_id="secrets.put_secret_value",
    display_name="Put secret value",
    service_id="secrets",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="secret_id", label="Secret name or ARN", required=True),
        InputField(
            name="secret_string",
            label="New secret value",
            kind="multiline",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="secretsmanager",
        command="put-secret-value",
        arg_map={"secret_id": "secret-id", "secret_string": "secret-string"},
    ),
    boto3_template=Boto3Template(
        service="secretsmanager",
        operation="put_secret_value",
        param_map={"secret_id": "SecretId", "secret_string": "SecretString"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Put secret value result"),
    iam_permissions=("secretsmanager:PutSecretValue",),
    description="Update the value of an existing secret.",
    cache_refresh_nav_ids=("secrets",),
)


DELETE_SECRET = ActionDefinition(
    action_id="secrets.delete_secret",
    display_name="Delete secret",
    service_id="secrets",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="secret_id", label="Secret name or ARN", required=True),
        InputField(
            name="recovery_window_in_days",
            label="Recovery window (days, 7-30)",
            kind="int",
            required=False,
            default="30",
            help_text="Sets a soft-delete window. Leave blank to force-delete immediately with no recovery.",
        ),
    ),
    cli_template=CliTemplate(
        service="secretsmanager",
        command="delete-secret",
        arg_map={
            "secret_id": "secret-id",
            "recovery_window_in_days": "recovery-window-in-days",
        },
    ),
    boto3_template=Boto3Template(
        service="secretsmanager",
        operation="delete_secret",
        param_map={
            "secret_id": "SecretId",
            "recovery_window_in_days": "RecoveryWindowInDays",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete secret result"),
    iam_permissions=("secretsmanager:DeleteSecret",),
    description=(
        "Schedule a secret for deletion. With a recovery window the secret is soft-deleted and "
        "can be restored before the window expires. Deleted secrets remain visible in the list "
        "with 'deleted=yes' until the window passes."
    ),
    cache_refresh_nav_ids=("secrets",),
)


RESTORE_SECRET = ActionDefinition(
    action_id="secrets.restore_secret",
    display_name="Restore secret",
    service_id="secrets",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="secret_id",
            label="Secret name or ARN",
            required=True,
            help_text="Name or ARN of the secret pending deletion to restore.",
        ),
    ),
    cli_template=CliTemplate(
        service="secretsmanager",
        command="restore-secret",
        arg_map={"secret_id": "secret-id"},
    ),
    boto3_template=Boto3Template(
        service="secretsmanager",
        operation="restore_secret",
        param_map={"secret_id": "SecretId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Restore secret result"),
    iam_permissions=("secretsmanager:RestoreSecret",),
    description=(
        "Cancel a pending deletion and restore the secret to active status. "
        "Only works while the secret is still within its recovery window."
    ),
    cache_refresh_nav_ids=("secrets",),
)


ALL_ACTIONS = (
    LIST_SECRETS,
    DESCRIBE_SECRET,
    CREATE_SECRET,
    PUT_SECRET_VALUE,
    DELETE_SECRET,
    RESTORE_SECRET,
)
