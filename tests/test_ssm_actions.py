"""Moto-backed tests for SSM actions."""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.ssm.actions import (
    DELETE_PARAMETER,
    DESCRIBE_PARAMETERS,
    GET_PARAMETER,
    GET_PARAMETERS_BY_PATH,
    PUT_PARAMETER,
)
from gui4aws.services.ssm.views import to_parameter_summaries


def test_describe_parameters_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_PARAMETERS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_parameter_summaries(result.response)
    assert summaries == []


def test_put_and_get_parameter(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    
    # Put
    result = context.execute(
        PUT_PARAMETER,
        inputs={
            "name": "test-param",
            "value": "test-value",
            "type": "String",
            "description": "test-desc"
        }
    )
    assert isinstance(result, Boto3Result)
    assert "Version" in result.response

    # Get
    get_result = context.execute(GET_PARAMETER, inputs={"name": "test-param"})
    assert isinstance(get_result, Boto3Result)
    assert get_result.response["Parameter"]["Value"] == "test-value"

    # Describe
    desc_result = context.execute(DESCRIBE_PARAMETERS, inputs={})
    summaries = to_parameter_summaries(desc_result.response)
    assert any(s.name == "test-param" for s in summaries)


def test_get_parameters_by_path(mock_aws_env: None) -> None:
    ssm = boto3.client("ssm", region_name="us-east-1")
    ssm.put_parameter(Name="/app/db/host", Value="localhost", Type="String")
    ssm.put_parameter(Name="/app/db/port", Value="5432", Type="String")
    ssm.put_parameter(Name="/other/key", Value="val", Type="String")

    context = AppContext(region_name="us-east-1")
    result = context.execute(GET_PARAMETERS_BY_PATH, inputs={"path": "/app/", "recursive": "true"})
    assert isinstance(result, Boto3Result)
    summaries = to_parameter_summaries(result.response)
    assert len(summaries) == 2
    names = {s.name for s in summaries}
    assert "/app/db/host" in names
    assert "/app/db/port" in names
    assert "/other/key" not in names


def test_delete_parameter(mock_aws_env: None) -> None:
    ssm = boto3.client("ssm", region_name="us-east-1")
    ssm.put_parameter(Name="delete-me", Value="val", Type="String")

    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_PARAMETER, inputs={"name": "delete-me"})
    assert isinstance(result, Boto3Result)

    # Verify deleted
    with pytest.raises(Exception): # boto3 client error
        ssm.get_parameter(Name="delete-me")
    
    desc_result = context.execute(DESCRIBE_PARAMETERS, inputs={})
    summaries = to_parameter_summaries(desc_result.response)
    assert not any(s.name == "delete-me" for s in summaries)
