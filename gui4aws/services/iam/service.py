"""ServiceDefinition for IAM."""

from __future__ import annotations

from gui4aws.models import InputField, NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.iam.actions import (
    ALL_ACTIONS,
    CREATE_GROUP,
    CREATE_ROLE,
    CREATE_USER,
    DELETE_GROUP,
    DELETE_ROLE,
    DELETE_USER,
    GET_POLICY,
    GET_POLICY_DOCUMENT,
    GET_ROLE,
    GET_USER,
    LIST_GROUPS,
    LIST_POLICIES,
    LIST_ROLES,
    LIST_USERS,
)

__all__ = ["SERVICE"]

SERVICE = ServiceDefinition(
    service_id="iam",
    display_name="IAM",
    boto3_service_name="iam",
    cli_service_name="iam",
    navigation_items=(
        NavigationItem(
            item_id="users",
            display_name="Users",
            default_action_id=LIST_USERS.action_id,
            row_actions=(
                RowAction(
                    action_id=GET_USER.action_id,
                    button_label="Get User",
                    prefill={"user_name": "name"},
                ),
                RowAction(
                    action_id=CREATE_USER.action_id,
                    button_label="Create User",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_USER.action_id,
                    button_label="Delete User",
                    prefill={"user_name": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="groups",
            display_name="Groups",
            default_action_id=LIST_GROUPS.action_id,
            row_actions=(
                RowAction(
                    action_id=CREATE_GROUP.action_id,
                    button_label="Create Group",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_GROUP.action_id,
                    button_label="Delete Group",
                    prefill={"group_name": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="roles",
            display_name="Roles",
            default_action_id=LIST_ROLES.action_id,
            row_actions=(
                RowAction(
                    action_id=GET_ROLE.action_id,
                    button_label="Get Role",
                    prefill={"role_name": "name"},
                ),
                RowAction(
                    action_id=CREATE_ROLE.action_id,
                    button_label="Create Role",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_ROLE.action_id,
                    button_label="Delete Role",
                    prefill={"role_name": "name"},
                ),
            ),
        ),
        NavigationItem(
            item_id="policies",
            display_name="Policies",
            default_action_id=LIST_POLICIES.action_id,
            filter_fields=(
                InputField(
                    name="scope",
                    label="Scope",
                    kind="choice",
                    choices=("Local", "AWS", "All"),
                    default="Local",
                    required=False,
                ),
                InputField(
                    name="only_attached",
                    label="Only attached",
                    kind="bool",
                    default="false",
                    required=False,
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=GET_POLICY.action_id,
                    button_label="Get Policy",
                    prefill={"policy_arn": "arn"},
                ),
                RowAction(
                    action_id=GET_POLICY_DOCUMENT.action_id,
                    button_label="View Document",
                    prefill={"policy_arn": "arn"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
