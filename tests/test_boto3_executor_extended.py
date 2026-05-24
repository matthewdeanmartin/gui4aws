"""Extended tests for Boto3Executor, focusing on error paths and coercion."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from botocore.exceptions import BotoCoreError, ClientError

from gui4aws.execution.boto3_executor import Boto3Executor, Boto3Failure, coerce_value
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.models import ActionDefinition, Boto3Template


def test_coerce_value():
    assert coerce_value("123", "int") == 123
    assert coerce_value("1.23", "float") == 1.23
    assert coerce_value("true", "bool") is True
    assert coerce_value("NO", "bool") is False
    assert coerce_value("a, b , c", "list") == ["a", "b", "c"]
    assert coerce_value("pure string", "text") == "pure string"


def test_execute_client_error():
    config = EndpointConfig(mode=EndpointMode.MOTO)
    executor = Boto3Executor(profile_name=None, region_name="us-east-1", endpoint_config=config)

    action = MagicMock(spec=ActionDefinition)
    action.boto3_template = Boto3Template(service="s3", operation="list_buckets")
    action.boto3_params_builder = None
    action.input_fields = []

    # Mock client to raise ClientError
    with patch.object(executor, "build_client") as mock_build:
        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = ClientError(
            {"Error": {"Code": "NoSuchBucket", "Message": "The bucket does not exist"}}, "ListBuckets"
        )
        mock_build.return_value = mock_client

        result = executor.execute(action, {})

        assert isinstance(result, Boto3Failure)
        assert result.aws_error_code == "NoSuchBucket"
        assert "The bucket does not exist" in result.message
        assert result.exception_class == "ClientError"


def test_execute_botocore_error():
    config = EndpointConfig(mode=EndpointMode.MOTO)
    executor = Boto3Executor(profile_name=None, region_name="us-east-1", endpoint_config=config)

    action = MagicMock(spec=ActionDefinition)
    action.boto3_template = Boto3Template(service="s3", operation="list_buckets")
    action.boto3_params_builder = None
    action.input_fields = []

    # Mock client to raise BotoCoreError
    with patch.object(executor, "build_client") as mock_build:
        mock_client = MagicMock()
        mock_client.list_buckets.side_effect = BotoCoreError()
        mock_build.return_value = mock_client

        result = executor.execute(action, {})

        assert isinstance(result, Boto3Failure)
        assert result.aws_error_code is None
        assert result.exception_class == "BotoCoreError"


def test_build_client_real_aws():
    config = EndpointConfig(mode=EndpointMode.AWS)
    executor = Boto3Executor(profile_name="test-profile", region_name="us-east-1", endpoint_config=config)

    with patch("boto3.Session") as mock_session_class:
        mock_session = MagicMock()
        mock_session_class.return_value = mock_session

        executor.build_client("s3")

        mock_session_class.assert_called_with(profile_name="test-profile", region_name="us-east-1")
        mock_session.client.assert_called()
