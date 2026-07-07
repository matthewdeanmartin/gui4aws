"""Moto-backed tests for CloudFormation actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.cloudformation.actions import (
    CDK_CONFIG,
    DELETE_STACK,
    DESCRIBE_STACK,
    LIST_STACKS,
    cdk_config_text,
    list_stacks_boto3_params,
    list_stacks_cli_args,
)
from gui4aws.services.cloudformation.service import SERVICE as CLOUDFORMATION_SERVICE
from gui4aws.services.cloudformation.views import to_stack_summaries


def test_list_stacks_builders():
    """Test the pure builder functions."""
    inputs = {"stack_status_filter": "CREATE_COMPLETE,UPDATE_COMPLETE"}

    params = list_stacks_boto3_params(inputs)
    assert params == {"StackStatusFilter": ["CREATE_COMPLETE", "UPDATE_COMPLETE"]}

    args = list_stacks_cli_args(inputs)
    assert args == ["--stack-status-filter", "CREATE_COMPLETE", "UPDATE_COMPLETE"]

    # Empty case
    assert list_stacks_boto3_params({}) == {}
    assert list_stacks_cli_args({}) == []


def test_list_stacks_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_STACKS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_stack_summaries(result.response)
    assert summaries == []


def test_create_and_delete_stack(mock_aws_env: None) -> None:
    cfn = boto3.client("cloudformation", region_name="us-east-1")
    template = {"AWSTemplateFormatVersion": "2010-09-09", "Resources": {"MyBucket": {"Type": "AWS::S3::Bucket"}}}
    import json

    cfn.create_stack(StackName="test-stack", TemplateBody=json.dumps(template))

    context = AppContext(region_name="us-east-1")

    # List
    list_result = context.execute(LIST_STACKS, inputs={})
    summaries = to_stack_summaries(list_result.response)
    assert any(s.name == "test-stack" for s in summaries)

    # Describe
    desc_result = context.execute(DESCRIBE_STACK, inputs={"stack_name": "test-stack"})
    assert isinstance(desc_result, Boto3Result)
    assert desc_result.response["Stacks"][0]["StackName"] == "test-stack"

    # Delete
    del_result = context.execute(DELETE_STACK, inputs={"stack_name": "test-stack"})
    assert isinstance(del_result, Boto3Result)


def test_cdk_config_text_includes_active_connection() -> None:
    """The CDK helper reports connection fields supplied by MainWindow/AppContext."""
    text = cdk_config_text(
        {
            "account_id": "123456789012",
            "region": "us-west-2",
            "endpoint_url": "http://localhost:4566",
            "target": "Robotocore",
            "arn": "arn:aws:sts::123456789012:assumed-role/Admin/gui4aws",
            "user_id": "AROATEST:gui4aws",
        }
    )

    assert "=== Active Connection ===" in text
    assert "Account:  123456789012" in text
    assert "Region:   us-west-2" in text
    assert "Target:   Robotocore" in text
    assert "Endpoint: http://localhost:4566" in text
    assert "export CDK_DEFAULT_ACCOUNT=123456789012" in text
    assert "export CDK_DEFAULT_REGION=us-west-2" in text


def test_cdk_config_nav_has_no_manual_connection_fields() -> None:
    """CDK config is filled from the active context rather than duplicate filter UI."""
    nav = next(item for item in CLOUDFORMATION_SERVICE.navigation_items if item.item_id == "cdk_config")
    assert nav.filter_fields == ()
    assert {field.name for field in CDK_CONFIG.input_fields} >= {"account_id", "region", "endpoint_url"}
