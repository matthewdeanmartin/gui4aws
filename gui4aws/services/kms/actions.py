"""KMS action definitions."""

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
from gui4aws.services.kms.views import to_alias_summaries, to_grant_summaries, to_key_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_ALIAS",
    "CREATE_KEY",
    "DELETE_ALIAS",
    "DESCRIBE_KEY",
    "DISABLE_KEY",
    "ENABLE_KEY",
    "LIST_ALIASES",
    "LIST_GRANTS",
    "LIST_KEYS",
    "SCHEDULE_KEY_DELETION",
]


def create_key_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    params: dict[str, Any] = {}
    if inputs.get("description"):
        params["Description"] = inputs["description"]
    key_usage = inputs.get("key_usage", "ENCRYPT_DECRYPT")
    if key_usage:
        params["KeyUsage"] = key_usage
    key_spec = inputs.get("key_spec", "SYMMETRIC_DEFAULT")
    if key_spec:
        params["KeySpec"] = key_spec
    if inputs.get("multi_region", "false").lower() == "true":
        params["MultiRegion"] = True
    return params


def create_key_cli_args(inputs: Mapping[str, str]) -> list[str]:
    args: list[str] = []
    if inputs.get("description"):
        args += ["--description", inputs["description"]]
    if inputs.get("key_usage"):
        args += ["--key-usage", inputs["key_usage"]]
    if inputs.get("key_spec"):
        args += ["--key-spec", inputs["key_spec"]]
    if inputs.get("multi_region", "false").lower() == "true":
        args += ["--multi-region"]
    return args


LIST_KEYS = ActionDefinition(
    action_id="kms.list_keys",
    display_name="List keys",
    service_id="kms",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="kms", command="list-keys", arg_map={}),
    boto3_template=Boto3Template(service="kms", operation="list_keys", param_map={}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("key_id", "key_arn", "key_state", "key_usage", "enabled", "description"),
        title="KMS Keys",
    ),
    iam_permissions=("kms:ListKeys",),
    description="List KMS keys in the current region.",
    view=to_key_summaries,
)


DESCRIBE_KEY = ActionDefinition(
    action_id="kms.describe_key",
    display_name="Describe key",
    service_id="kms",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="key_id",
            label="Key ID or ARN or alias",
            required=True,
            help_text="Key ID, ARN, alias name (alias/...) or alias ARN.",
        ),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="describe-key",
        arg_map={"key_id": "key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="describe_key",
        param_map={"key_id": "KeyId"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("key_id", "key_arn", "key_state", "key_usage", "key_spec", "origin", "enabled", "creation_date"),
        title="KMS Key Detail",
    ),
    iam_permissions=("kms:DescribeKey",),
    description="Describe a single KMS key by ID, ARN, or alias.",
    view=to_key_summaries,
)


LIST_ALIASES = ActionDefinition(
    action_id="kms.list_aliases",
    display_name="List aliases",
    service_id="kms",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="key_id",
            label="Key ID (optional filter)",
            required=False,
            help_text="Leave blank to list all aliases.",
        ),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="list-aliases",
        arg_map={"key_id": "key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="list_aliases",
        param_map={"key_id": "KeyId"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("alias_name", "target_key_id", "alias_arn", "last_updated_date"),
        title="KMS Aliases",
    ),
    iam_permissions=("kms:ListAliases",),
    description="List KMS key aliases, optionally filtered by key ID.",
    view=to_alias_summaries,
)


LIST_GRANTS = ActionDefinition(
    action_id="kms.list_grants",
    display_name="List grants",
    service_id="kms",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="key_id",
            label="Key ID or ARN",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="list-grants",
        arg_map={"key_id": "key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="list_grants",
        param_map={"key_id": "KeyId"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("grant_id", "key_id", "name", "grantee_principal", "operations", "creation_date"),
        title="KMS Grants",
    ),
    iam_permissions=("kms:ListGrants",),
    description="List grants for a KMS key.",
    view=to_grant_summaries,
)


CREATE_KEY = ActionDefinition(
    action_id="kms.create_key",
    display_name="Create key",
    service_id="kms",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="description", label="Description", required=False),
        InputField(
            name="key_usage",
            label="Key usage",
            kind="choice",
            choices=("ENCRYPT_DECRYPT", "SIGN_VERIFY", "GENERATE_VERIFY_MAC"),
            default="ENCRYPT_DECRYPT",
        ),
        InputField(
            name="key_spec",
            label="Key spec",
            kind="choice",
            choices=(
                "SYMMETRIC_DEFAULT",
                "RSA_2048",
                "RSA_3072",
                "RSA_4096",
                "ECC_NIST_P256",
                "ECC_NIST_P384",
                "ECC_NIST_P521",
                "HMAC_256",
            ),
            default="SYMMETRIC_DEFAULT",
        ),
        InputField(
            name="multi_region",
            label="Multi-region key",
            kind="bool",
            default="false",
        ),
    ),
    cli_template=CliTemplate(service="kms", command="create-key"),
    boto3_template=Boto3Template(service="kms", operation="create_key"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create key result"),
    iam_permissions=("kms:CreateKey",),
    description="Create a new KMS key.",
    cache_refresh_nav_ids=("keys", "aliases"),
    cli_args_builder=create_key_cli_args,
    boto3_params_builder=create_key_boto3_params,
)


CREATE_ALIAS = ActionDefinition(
    action_id="kms.create_alias",
    display_name="Create alias",
    service_id="kms",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="alias_name",
            label="Alias name",
            required=True,
            help_text="Must begin with 'alias/' (e.g. alias/my-key).",
        ),
        InputField(name="target_key_id", label="Target key ID or ARN", required=True),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="create-alias",
        arg_map={"alias_name": "alias-name", "target_key_id": "target-key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="create_alias",
        param_map={"alias_name": "AliasName", "target_key_id": "TargetKeyId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create alias result"),
    iam_permissions=("kms:CreateAlias",),
    description="Create an alias for a KMS key.",
    cache_refresh_nav_ids=("aliases",),
)


DELETE_ALIAS = ActionDefinition(
    action_id="kms.delete_alias",
    display_name="Delete alias",
    service_id="kms",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="alias_name",
            label="Alias name",
            required=True,
            help_text="Must begin with 'alias/'.",
        ),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="delete-alias",
        arg_map={"alias_name": "alias-name"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="delete_alias",
        param_map={"alias_name": "AliasName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete alias result"),
    iam_permissions=("kms:DeleteAlias",),
    description="Delete a KMS key alias.",
    cache_refresh_nav_ids=("aliases",),
)


ENABLE_KEY = ActionDefinition(
    action_id="kms.enable_key",
    display_name="Enable key",
    service_id="kms",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(InputField(name="key_id", label="Key ID or ARN", required=True),),
    cli_template=CliTemplate(
        service="kms",
        command="enable-key",
        arg_map={"key_id": "key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="enable_key",
        param_map={"key_id": "KeyId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Enable key result"),
    iam_permissions=("kms:EnableKey",),
    description="Re-enable a disabled KMS key.",
    cache_refresh_nav_ids=("keys",),
)


DISABLE_KEY = ActionDefinition(
    action_id="kms.disable_key",
    display_name="Disable key",
    service_id="kms",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="key_id", label="Key ID or ARN", required=True),),
    cli_template=CliTemplate(
        service="kms",
        command="disable-key",
        arg_map={"key_id": "key-id"},
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="disable_key",
        param_map={"key_id": "KeyId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Disable key result"),
    iam_permissions=("kms:DisableKey",),
    description="Disable a KMS key (prevents use but does not delete).",
    cache_refresh_nav_ids=("keys",),
)


SCHEDULE_KEY_DELETION = ActionDefinition(
    action_id="kms.schedule_key_deletion",
    display_name="Schedule key deletion",
    service_id="kms",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="key_id", label="Key ID or ARN", required=True),
        InputField(
            name="pending_window_in_days",
            label="Pending window (days)",
            kind="int",
            default="30",
            help_text="7-30 days. Key is deleted after this period.",
        ),
    ),
    cli_template=CliTemplate(
        service="kms",
        command="schedule-key-deletion",
        arg_map={
            "key_id": "key-id",
            "pending_window_in_days": "pending-window-in-days",
        },
    ),
    boto3_template=Boto3Template(
        service="kms",
        operation="schedule_key_deletion",
        param_map={
            "key_id": "KeyId",
            "pending_window_in_days": "PendingWindowInDays",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Schedule deletion result"),
    iam_permissions=("kms:ScheduleKeyDeletion",),
    description="Schedule a KMS key for deletion after a waiting period.",
    cache_refresh_nav_ids=("keys",),
)


ALL_ACTIONS = (
    LIST_KEYS,
    DESCRIBE_KEY,
    LIST_ALIASES,
    LIST_GRANTS,
    CREATE_KEY,
    CREATE_ALIAS,
    DELETE_ALIAS,
    ENABLE_KEY,
    DISABLE_KEY,
    SCHEDULE_KEY_DELETION,
)
