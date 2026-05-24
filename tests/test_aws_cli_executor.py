"""Tests for AwsCliExecutor using subprocess stubbing."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from gui4aws.execution.aws_cli_executor import (
    AwsCliExecutor,
    AwsCliFailure,
    AwsCliResult,
    parse_aws_cli_error,
    quote_for_shell,
)
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.models import ActionDefinition, CliTemplate, InputField


def test_quote_for_shell():
    assert quote_for_shell(["aws", "s3", "ls"]) == "aws s3 ls"
    assert quote_for_shell(["aws", "s3", "ls", "s3://my bucket"]) == "aws s3 ls 's3://my bucket'"
    assert quote_for_shell(["can't"]) == "'can'\\''t'"


def test_parse_aws_cli_error():
    assert parse_aws_cli_error("\n\nAn error occurred\n") == "An error occurred"
    assert parse_aws_cli_error("") == "aws CLI exited non-zero"


def test_build_argv():
    config = EndpointConfig(mode=EndpointMode.MOTO)
    executor = AwsCliExecutor(profile_name="p1", region_name="us-west-2", endpoint_config=config, aws_binary="/usr/bin/aws")
    
    action = ActionDefinition(
        action_id="test.act",
        display_name="Test",
        service_id="test",
        risk_level=1,
        input_fields=(
            InputField(name="f1", label="L1", kind="text"),
            InputField(name="f2", label="L2", kind="bool"),
            InputField(name="f3", label="L3", kind="list"),
        ),
        cli_template=CliTemplate(
            service="s3",
            command="ls",
            arg_map={"f1": "bucket", "f2": "recursive", "f3": "include"}
        ),
        boto3_template=MagicMock(),
        result_view=MagicMock(),
        iam_permissions=(),
    )
    
    argv = executor.build_argv(action, {"f1": "myb", "f2": "true", "f3": "a,b"})
    
    assert "/usr/bin/aws" in argv
    assert "s3" in argv
    assert "ls" in argv
    assert "--region" in argv
    assert "us-west-2" in argv
    assert "--profile" in argv
    assert "p1" in argv
    assert "--endpoint-url" in argv
    assert "http://127.0.0.1:5000" in argv
    assert "--bucket" in argv
    assert "myb" in argv
    assert "--recursive" in argv
    assert "--include" in argv
    assert "a" in argv
    assert "b" in argv


def test_execute_success():
    config = EndpointConfig(mode=EndpointMode.AWS)
    executor = AwsCliExecutor(profile_name=None, region_name="us-east-1", endpoint_config=config)
    
    action = MagicMock(spec=ActionDefinition)
    action.cli_template = CliTemplate(service="s3", command="ls")
    action.cli_args_builder = None
    action.input_fields = []
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"Buckets": []}',
            stderr=""
        )
        
        result = executor.execute(action, {})
        
        assert isinstance(result, AwsCliResult)
        assert result.exit_code == 0
        assert result.parsed_json == {"Buckets": []}


def test_execute_failure():
    config = EndpointConfig(mode=EndpointMode.AWS)
    executor = AwsCliExecutor(profile_name=None, region_name="us-east-1", endpoint_config=config)
    
    action = MagicMock(spec=ActionDefinition)
    action.cli_template = CliTemplate(service="s3", command="ls")
    action.cli_args_builder = None
    action.input_fields = []
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=255,
            stdout="",
            stderr="An error occurred"
        )
        
        result = executor.execute(action, {})
        
        assert isinstance(result, AwsCliFailure)
        assert result.exit_code == 255
        assert result.reason == "An error occurred"


def test_execute_not_found():
    executor = AwsCliExecutor(None, "us-east-1", EndpointConfig(), aws_binary="no-such-aws")
    
    action = MagicMock(spec=ActionDefinition)
    action.cli_template = CliTemplate(service="s3", command="ls")
    action.cli_args_builder = None
    action.input_fields = []

    with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
        result = executor.execute(action, {})
        assert isinstance(result, AwsCliFailure)
        assert "not found" in result.reason or "not found" in result.stderr


def test_execute_timeout():
    executor = AwsCliExecutor(None, "us-east-1", EndpointConfig())
    
    action = MagicMock(spec=ActionDefinition)
    action.cli_template = CliTemplate(service="s3", command="ls")
    action.cli_args_builder = None
    action.input_fields = []

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["aws"], 10)):
        result = executor.execute(action, {})
        assert isinstance(result, AwsCliFailure)
        assert "timeout" in result.reason
