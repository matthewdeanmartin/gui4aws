"""Moto-backed tests for Lambda actions."""

from __future__ import annotations

import boto3
import pytest
import zipfile
import io
import os
import tempfile

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.lambdas.actions import (
    CREATE_FUNCTION,
    DELETE_FUNCTION,
    GET_FUNCTION,
    LIST_FUNCTIONS,
    _create_function_boto3_params,
)
from gui4aws.services.lambdas.views import to_function_summaries


def test_list_functions_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_FUNCTIONS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_function_summaries(result.response)
    assert summaries == []


def test_create_and_delete_function(mock_aws_env: None) -> None:
    iam = boto3.client("iam", region_name="us-east-1")
    role_arn = iam.create_role(
        RoleName="lambda-role",
        AssumeRolePolicyDocument='{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}'
    )["Role"]["Arn"]

    # Create dummy zip
    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        zip_path = tmp.name
        with zipfile.ZipFile(zip_path, "w") as z:
            z.writestr("handler.py", "def handler(event, context): return 'hello'")

    try:
        context = AppContext(region_name="us-east-1")
        
        # Create
        result = context.execute(
            CREATE_FUNCTION,
            inputs={
                "function_name": "test-func",
                "runtime": "python3.11",
                "role_arn": role_arn,
                "zip_file_path": zip_path
            }
        )
        assert isinstance(result, Boto3Result)
        assert result.response["FunctionName"] == "test-func"

        # List
        list_result = context.execute(LIST_FUNCTIONS, inputs={})
        summaries = to_function_summaries(list_result.response)
        assert any(s.name == "test-func" for s in summaries)

        # Get
        get_result = context.execute(GET_FUNCTION, inputs={"function_name": "test-func"})
        assert isinstance(get_result, Boto3Result)
        assert get_result.response["Configuration"]["FunctionName"] == "test-func"

        # Delete
        del_result = context.execute(DELETE_FUNCTION, inputs={"function_name": "test-func"})
        assert isinstance(del_result, Boto3Result)

    finally:
        if os.path.exists(zip_path):
            os.remove(zip_path)


def test_create_function_params_builder():
    """Test the pure builder for CREATE_FUNCTION."""
    inputs = {
        "function_name": "f1",
        "role_arn": "arn:role",
        "runtime": "python3.12"
    }
    params = _create_function_boto3_params(inputs)
    assert params["FunctionName"] == "f1"
    assert params["Role"] == "arn:role"
    assert params["Runtime"] == "python3.12"
    assert params["Code"] == {"ZipFile": b""}
