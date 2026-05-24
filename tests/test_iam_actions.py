"""Moto-backed tests for IAM actions."""

from __future__ import annotations

import json

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.iam.actions import (
    CREATE_GROUP,
    CREATE_ROLE,
    CREATE_USER,
    DELETE_GROUP,
    DELETE_ROLE,
    DELETE_USER,
    GET_POLICY,
    GET_ROLE,
    GET_USER,
    LIST_GROUPS,
    LIST_POLICIES,
    LIST_ROLES,
    LIST_USERS,
    _list_policies_boto3_params,
    _list_policies_cli_args,
)
from gui4aws.services.iam.views import (
    to_group_summaries,
    to_policy_summaries,
    to_role_summaries,
    to_user_summaries,
)


def test_list_policies_builders():
    """Test pure builders for LIST_POLICIES."""
    inputs = {"scope": "AWS"}
    assert _list_policies_boto3_params(inputs) == {"Scope": "AWS"}
    assert _list_policies_cli_args(inputs) == ["--scope", "AWS"]


def test_user_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create
    result = context.execute(CREATE_USER, inputs={"user_name": "test-user"})
    assert isinstance(result, Boto3Result)
    assert result.response["User"]["UserName"] == "test-user"

    # List
    list_result = context.execute(LIST_USERS, inputs={})
    summaries = to_user_summaries(list_result.response)
    assert any(s.name == "test-user" for s in summaries)

    # Get
    get_result = context.execute(GET_USER, inputs={"user_name": "test-user"})
    assert isinstance(get_result, Boto3Result)
    assert get_result.response["User"]["UserName"] == "test-user"

    # Delete
    del_result = context.execute(DELETE_USER, inputs={"user_name": "test-user"})
    assert isinstance(del_result, Boto3Result)


def test_group_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create
    result = context.execute(CREATE_GROUP, inputs={"group_name": "test-group"})
    assert isinstance(result, Boto3Result)

    # List
    list_result = context.execute(LIST_GROUPS, inputs={})
    summaries = to_group_summaries(list_result.response)
    assert any(s.name == "test-group" for s in summaries)

    # Delete
    del_result = context.execute(DELETE_GROUP, inputs={"group_name": "test-group"})
    assert isinstance(del_result, Boto3Result)


def test_role_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Principal": {"Service": "ec2.amazonaws.com"}, "Action": "sts:AssumeRole"}],
    }

    # Create
    result = context.execute(
        CREATE_ROLE, inputs={"role_name": "test-role", "assume_role_policy": json.dumps(trust_policy)}
    )
    assert isinstance(result, Boto3Result)

    # List
    list_result = context.execute(LIST_ROLES, inputs={})
    summaries = to_role_summaries(list_result.response)
    assert any(s.name == "test-role" for s in summaries)

    # Get
    get_result = context.execute(GET_ROLE, inputs={"role_name": "test-role"})
    assert isinstance(get_result, Boto3Result)

    # Delete
    del_result = context.execute(DELETE_ROLE, inputs={"role_name": "test-role"})
    assert isinstance(del_result, Boto3Result)


def test_policy_actions(mock_aws_env: None) -> None:
    iam = boto3.client("iam", region_name="us-east-1")
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [{"Effect": "Allow", "Action": "s3:ListAllMyBuckets", "Resource": "*"}],
    }
    policy_arn = iam.create_policy(PolicyName="test-policy", PolicyDocument=json.dumps(policy_doc))["Policy"]["Arn"]

    context = AppContext(region_name="us-east-1")

    # List
    list_result = context.execute(LIST_POLICIES, inputs={"scope": "Local"})
    summaries = to_policy_summaries(list_result.response)
    assert any(s.name == "test-policy" for s in summaries)

    # Get
    get_result = context.execute(GET_POLICY, inputs={"policy_arn": policy_arn})
    assert isinstance(get_result, Boto3Result)
    assert get_result.response["Policy"]["Arn"] == policy_arn
