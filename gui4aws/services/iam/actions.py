"""IAM action definitions."""

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
from gui4aws.services.iam.views import to_group_summaries, to_policy_summaries, to_role_summaries, to_user_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_GROUP",
    "CREATE_ROLE",
    "CREATE_USER",
    "DELETE_GROUP",
    "DELETE_ROLE",
    "DELETE_USER",
    "GET_POLICY",
    "GET_POLICY_DOCUMENT",
    "GET_ROLE",
    "GET_USER",
    "LIST_GROUPS",
    "LIST_POLICIES",
    "LIST_ROLES",
    "LIST_USERS",
]


def list_policies_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Build boto3 parameters for list_policies, filtering by scope."""
    params: dict[str, Any] = {}
    scope = inputs.get("scope", "Local").strip()
    if scope:
        params["Scope"] = scope
    if inputs.get("only_attached", "").lower() in ("true", "yes", "1"):
        params["OnlyAttached"] = True
    return params


def list_policies_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map UI inputs to AWS CLI list-policies arguments."""
    args: list[str] = []
    scope = inputs.get("scope", "Local").strip()
    if scope:
        args += ["--scope", scope]
    if inputs.get("only_attached", "").lower() in ("true", "yes", "1"):
        args += ["--only-attached"]
    return args


def _get_policy_document(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    """Fetch the active policy document by chaining get_policy → get_policy_version."""
    policy_arn = inputs.get("policy_arn", "").strip()
    policy_resp = client.get_policy(PolicyArn=policy_arn)
    default_version_id = policy_resp["Policy"]["DefaultVersionId"]
    version_resp = client.get_policy_version(PolicyArn=policy_arn, VersionId=default_version_id)
    doc = version_resp.get("PolicyVersion", {}).get("Document", {})
    return {
        "PolicyArn": policy_arn,
        "VersionId": default_version_id,
        "Document": doc,
        "Policy": policy_resp.get("Policy", {}),
    }


LIST_USERS = ActionDefinition(
    action_id="iam.list_users",
    display_name="List users",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="iam", command="list-users"),
    boto3_template=Boto3Template(service="iam", operation="list_users"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "user_id", "path", "created", "password_last_used"),
        title="IAM Users",
    ),
    iam_permissions=("iam:ListUsers",),
    description="List IAM users in this account.",
    view=to_user_summaries,
)

GET_USER = ActionDefinition(
    action_id="iam.get_user",
    display_name="Get user",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="user_name", label="User name", required=True),),
    cli_template=CliTemplate(service="iam", command="get-user", arg_map={"user_name": "user-name"}),
    boto3_template=Boto3Template(service="iam", operation="get_user", param_map={"user_name": "UserName"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="User detail"),
    iam_permissions=("iam:GetUser",),
    description="Get details for a specific IAM user.",
)

CREATE_USER = ActionDefinition(
    action_id="iam.create_user",
    display_name="Create user",
    service_id="iam",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="user_name", label="User name", required=True),
        InputField(
            name="path",
            label="Path (optional)",
            required=False,
            default="/",
            help_text="IAM path prefix, e.g. /engineering/",
        ),
    ),
    cli_template=CliTemplate(service="iam", command="create-user", arg_map={"user_name": "user-name", "path": "path"}),
    boto3_template=Boto3Template(
        service="iam", operation="create_user", param_map={"user_name": "UserName", "path": "Path"}
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create user result"),
    iam_permissions=("iam:CreateUser",),
    description="Create a new IAM user.",
    cache_refresh_nav_ids=("users",),
)

DELETE_USER = ActionDefinition(
    action_id="iam.delete_user",
    display_name="Delete user",
    service_id="iam",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="user_name", label="User name", required=True),),
    cli_template=CliTemplate(service="iam", command="delete-user", arg_map={"user_name": "user-name"}),
    boto3_template=Boto3Template(service="iam", operation="delete_user", param_map={"user_name": "UserName"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete user result"),
    iam_permissions=("iam:DeleteUser",),
    description="Delete an IAM user (must have no attached policies, groups, or access keys).",
    cache_refresh_nav_ids=("users",),
)

LIST_GROUPS = ActionDefinition(
    action_id="iam.list_groups",
    display_name="List groups",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="iam", command="list-groups"),
    boto3_template=Boto3Template(service="iam", operation="list_groups"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "group_id", "path", "created"),
        title="IAM Groups",
    ),
    iam_permissions=("iam:ListGroups",),
    description="List IAM groups.",
    view=to_group_summaries,
)

CREATE_GROUP = ActionDefinition(
    action_id="iam.create_group",
    display_name="Create group",
    service_id="iam",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="group_name", label="Group name", required=True),
        InputField(name="path", label="Path (optional)", required=False, default="/"),
    ),
    cli_template=CliTemplate(
        service="iam", command="create-group", arg_map={"group_name": "group-name", "path": "path"}
    ),
    boto3_template=Boto3Template(
        service="iam", operation="create_group", param_map={"group_name": "GroupName", "path": "Path"}
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create group result"),
    iam_permissions=("iam:CreateGroup",),
    description="Create a new IAM group.",
    cache_refresh_nav_ids=("groups",),
)

DELETE_GROUP = ActionDefinition(
    action_id="iam.delete_group",
    display_name="Delete group",
    service_id="iam",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="group_name", label="Group name", required=True),),
    cli_template=CliTemplate(service="iam", command="delete-group", arg_map={"group_name": "group-name"}),
    boto3_template=Boto3Template(service="iam", operation="delete_group", param_map={"group_name": "GroupName"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete group result"),
    iam_permissions=("iam:DeleteGroup",),
    description="Delete an IAM group (must have no users or attached policies).",
    cache_refresh_nav_ids=("groups",),
)

LIST_ROLES = ActionDefinition(
    action_id="iam.list_roles",
    display_name="List roles",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="iam", command="list-roles"),
    boto3_template=Boto3Template(service="iam", operation="list_roles"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "role_id", "path", "created", "description"),
        title="IAM Roles",
    ),
    iam_permissions=("iam:ListRoles",),
    description="List IAM roles.",
    view=to_role_summaries,
)

GET_ROLE = ActionDefinition(
    action_id="iam.get_role",
    display_name="Get role",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="role_name", label="Role name", required=True),),
    cli_template=CliTemplate(service="iam", command="get-role", arg_map={"role_name": "role-name"}),
    boto3_template=Boto3Template(service="iam", operation="get_role", param_map={"role_name": "RoleName"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Role detail"),
    iam_permissions=("iam:GetRole",),
    description="Get details for a specific IAM role including trust policy.",
)

CREATE_ROLE = ActionDefinition(
    action_id="iam.create_role",
    display_name="Create role",
    service_id="iam",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="role_name", label="Role name", required=True),
        InputField(
            name="assume_role_policy",
            label="Trust policy (JSON)",
            required=True,
            kind="multiline",
            help_text='JSON AssumeRolePolicyDocument, e.g. {"Version":"2012-10-17","Statement":[...]}',
        ),
        InputField(name="description", label="Description", required=False),
    ),
    cli_template=CliTemplate(
        service="iam",
        command="create-role",
        arg_map={
            "role_name": "role-name",
            "assume_role_policy": "assume-role-policy-document",
            "description": "description",
        },
    ),
    boto3_template=Boto3Template(
        service="iam",
        operation="create_role",
        param_map={
            "role_name": "RoleName",
            "assume_role_policy": "AssumeRolePolicyDocument",
            "description": "Description",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create role result"),
    iam_permissions=("iam:CreateRole",),
    description="Create a new IAM role with a trust policy.",
    cache_refresh_nav_ids=("roles",),
)

DELETE_ROLE = ActionDefinition(
    action_id="iam.delete_role",
    display_name="Delete role",
    service_id="iam",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="role_name", label="Role name", required=True),),
    cli_template=CliTemplate(service="iam", command="delete-role", arg_map={"role_name": "role-name"}),
    boto3_template=Boto3Template(service="iam", operation="delete_role", param_map={"role_name": "RoleName"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete role result"),
    iam_permissions=("iam:DeleteRole",),
    description="Delete an IAM role (must have no attached policies or instance profiles).",
    cache_refresh_nav_ids=("roles",),
)

LIST_POLICIES = ActionDefinition(
    action_id="iam.list_policies",
    display_name="List policies",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="scope",
            label="Scope",
            kind="choice",
            choices=("Local", "AWS", "All"),
            default="Local",
            required=False,
            help_text="Local = customer-managed; AWS = AWS-managed; All = both.",
        ),
        InputField(
            name="only_attached",
            label="Only attached",
            kind="bool",
            default="false",
            required=False,
            help_text="Show only policies with at least one attachment.",
        ),
    ),
    cli_template=CliTemplate(service="iam", command="list-policies", arg_map={"scope": "scope"}),
    boto3_template=Boto3Template(service="iam", operation="list_policies", param_map={"scope": "Scope"}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "scope", "attachment_count", "created", "updated"),
        title="IAM Policies",
    ),
    iam_permissions=("iam:ListPolicies",),
    description="List IAM policies (default: customer-managed only).",
    view=to_policy_summaries,
    cli_args_builder=list_policies_cli_args,
    boto3_params_builder=list_policies_boto3_params,
)

GET_POLICY = ActionDefinition(
    action_id="iam.get_policy",
    display_name="Get policy",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="policy_arn", label="Policy ARN", required=True),),
    cli_template=CliTemplate(service="iam", command="get-policy", arg_map={"policy_arn": "policy-arn"}),
    boto3_template=Boto3Template(service="iam", operation="get_policy", param_map={"policy_arn": "PolicyArn"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Policy detail"),
    iam_permissions=("iam:GetPolicy",),
    description="Get details for a specific IAM policy.",
)

GET_POLICY_DOCUMENT = ActionDefinition(
    action_id="iam.get_policy_document",
    display_name="Get policy document",
    service_id="iam",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="policy_arn", label="Policy ARN", required=True),),
    cli_template=CliTemplate(
        service="iam",
        command="get-policy-version",
        arg_map={"policy_arn": "policy-arn"},
    ),
    boto3_template=Boto3Template(service="iam", operation="get_policy_version", param_map={}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Policy document"),
    iam_permissions=("iam:GetPolicy", "iam:GetPolicyVersion"),
    description="Fetch and display the active policy document (default version).",
    boto3_execute_fn=_get_policy_document,
)


ALL_ACTIONS = (
    LIST_USERS,
    GET_USER,
    CREATE_USER,
    DELETE_USER,
    LIST_GROUPS,
    CREATE_GROUP,
    DELETE_GROUP,
    LIST_ROLES,
    GET_ROLE,
    CREATE_ROLE,
    DELETE_ROLE,
    LIST_POLICIES,
    GET_POLICY,
    GET_POLICY_DOCUMENT,
)
