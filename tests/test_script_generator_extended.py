"""Extended tests for script_generator.py."""

from __future__ import annotations

from unittest.mock import MagicMock

from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.script_generator import (
    generate_cli_script,
    generate_python_script,
)
from gui4aws.models import ActionDefinition, Boto3Template, CliTemplate, InputField, RiskLevel


def test_generate_cli_script_with_profile_and_endpoint():
    config = EndpointConfig(mode=EndpointMode.MOTO)
    action = ActionDefinition(
        action_id="s3.ls",
        display_name="List S3",
        service_id="s3",
        risk_level=RiskLevel.READ_ONLY,
        input_fields=(),
        cli_template=CliTemplate(service="s3", command="ls"),
        boto3_template=MagicMock(),
        result_view=MagicMock(),
        iam_permissions=(),
    )

    script = generate_cli_script(
        action,
        {},
        profile_name="dev",
        region_name="us-east-1",
        endpoint_config=config
    )

    assert "aws s3 ls" in script
    assert "--profile dev" in script
    assert "--endpoint-url http://127.0.0.1:5000" in script
    assert "--region us-east-1" in script


def test_generate_python_script_with_params():
    config = EndpointConfig(mode=EndpointMode.AWS)
    action = ActionDefinition(
        action_id="s3.put",
        display_name="Put S3",
        service_id="s3",
        risk_level=RiskLevel.SAFE_WRITE,
        input_fields=(
            InputField(name="bucket", label="B", kind="text"),
            InputField(name="key", label="K", kind="text"),
        ),
        cli_template=MagicMock(),
        boto3_template=Boto3Template(
            service="s3",
            operation="put_object",
            param_map={"bucket": "Bucket", "key": "Key"}
        ),
        result_view=MagicMock(),
        iam_permissions=(),
    )

    script = generate_python_script(
        action,
        {"bucket": "my-bucket", "key": "my-key"},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=config
    )

    assert "import boto3" in script
    assert "client.put_object(" in script
    assert "Bucket='my-bucket'" in script
    assert "Key='my-key'" in script
    assert "endpoint_url" not in script


def test_generate_cli_script_with_builder():
    config = EndpointConfig(mode=EndpointMode.AWS)
    action = ActionDefinition(
        action_id="custom.act",
        display_name="Custom",
        service_id="s3",
        risk_level=RiskLevel.READ_ONLY,
        input_fields=(),
        cli_template=CliTemplate(service="s3", command="ls"),
        boto3_template=MagicMock(),
        result_view=MagicMock(),
        iam_permissions=(),
        cli_args_builder=lambda inputs: ["--custom-flag", "custom-val"]
    )

    script = generate_cli_script(
        action,
        {},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=config
    )

    assert "--custom-flag custom-val" in script


def test_generate_python_script_with_builder():
    config = EndpointConfig(mode=EndpointMode.AWS)
    action = ActionDefinition(
        action_id="custom.act",
        display_name="Custom",
        service_id="s3",
        risk_level=RiskLevel.READ_ONLY,
        input_fields=(),
        cli_template=MagicMock(),
        boto3_template=Boto3Template(service="s3", operation="put_object"),
        result_view=MagicMock(),
        iam_permissions=(),
        boto3_params_builder=lambda inputs: {"CustomParam": "CustomValue"}
    )

    script = generate_python_script(
        action,
        {},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=config
    )

    assert "CustomParam='CustomValue'" in script
