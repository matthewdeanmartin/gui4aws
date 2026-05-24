"""Pure unit tests — no AWS, no moto, no network.

Tests that verify model behaviour, builder functions, script generation,
and any logic that depends only on stdlib + the project's own modules.
"""

from __future__ import annotations

import pytest

from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.service_registry import ServiceRegistry

# ── ActionDefinition / InputField ────────────────────────────────────────────


def test_input_field_defaults() -> None:
    field = InputField(name="x", label="X")
    assert field.required is False
    assert field.kind == "string"
    assert field.default is None


def test_input_field_bool_kind() -> None:
    field = InputField(name="flag", label="Flag", kind="bool", default="true")
    assert field.kind == "bool"
    assert field.default == "true"


def test_action_definition_roundtrip_fields() -> None:
    action = ActionDefinition(
        action_id="test.list",
        display_name="List things",
        service_id="test",
        risk_level=RiskLevel.READ_ONLY,
        input_fields=(InputField(name="prefix", label="Prefix", required=False),),
        cli_template=CliTemplate(service="test", command="list-things"),
        boto3_template=Boto3Template(service="test", operation="list_things"),
        result_view=ResultViewDefinition(kind=ResultViewKind.TABLE, columns=("name",), title="Things"),
        iam_permissions=("test:ListThings",),
        description="List things.",
    )
    assert action.action_id == "test.list"
    assert action.risk_level is RiskLevel.READ_ONLY
    assert len(action.input_fields) == 1
    assert action.input_fields[0].name == "prefix"


def test_risk_level_values() -> None:
    """RiskLevel uses descriptive string values from the StrEnum."""
    assert RiskLevel.READ_ONLY.value == "read_only"
    assert RiskLevel.SAFE_WRITE.value == "safe_write"
    assert RiskLevel.COST_AFFECTING.value == "cost_affecting"
    assert RiskLevel.DESTRUCTIVE.value == "destructive"
    # All four levels are distinct.
    all_levels = [RiskLevel.READ_ONLY, RiskLevel.SAFE_WRITE, RiskLevel.COST_AFFECTING, RiskLevel.DESTRUCTIVE]
    assert len(set(all_levels)) == 4


# ── EndpointConfig ────────────────────────────────────────────────────────────


def test_endpoint_config_aws_returns_none_url() -> None:
    cfg = EndpointConfig(mode=EndpointMode.AWS)
    assert cfg.resolved_url() is None


def test_endpoint_config_moto_default_url() -> None:
    cfg = EndpointConfig(mode=EndpointMode.MOTO)
    assert cfg.resolved_url() == "http://127.0.0.1:5000"


def test_endpoint_config_moto_custom_url() -> None:
    cfg = EndpointConfig(mode=EndpointMode.MOTO, endpoint_url="http://127.0.0.1:9999")
    assert cfg.resolved_url() == "http://127.0.0.1:9999"


def test_endpoint_config_robotocore_default_url() -> None:
    cfg = EndpointConfig(mode=EndpointMode.ROBOTOCORE)
    assert cfg.resolved_url() == "http://localhost:4566"


def test_endpoint_config_for_mode_custom_requires_url() -> None:
    with pytest.raises(ValueError, match="endpoint_url is required"):
        EndpointConfig.for_mode(EndpointMode.CUSTOM)


def test_endpoint_config_for_mode_custom_with_url() -> None:
    cfg = EndpointConfig.for_mode(EndpointMode.CUSTOM, "http://localhost:1234")
    assert cfg.resolved_url() == "http://localhost:1234"


# ── ServiceRegistry ───────────────────────────────────────────────────────────


def test_service_registry_register_and_get() -> None:
    from gui4aws.services.secrets.service import SERVICE as SECRETS_SERVICE

    reg = ServiceRegistry()
    reg.register(SECRETS_SERVICE)
    assert reg.get("secrets") is SECRETS_SERVICE


def test_service_registry_duplicate_raises() -> None:
    from gui4aws.services.secrets.service import SERVICE as SECRETS_SERVICE

    reg = ServiceRegistry()
    reg.register(SECRETS_SERVICE)
    with pytest.raises(ValueError, match="already registered"):
        reg.register(SECRETS_SERVICE)


def test_service_registry_missing_raises() -> None:
    reg = ServiceRegistry()
    with pytest.raises(KeyError):
        reg.get("nonexistent")


def test_service_registry_len_and_iter() -> None:
    from gui4aws.services.s3.service import SERVICE as S3_SERVICE
    from gui4aws.services.sqs.service import SERVICE as SQS_SERVICE

    reg = ServiceRegistry((SQS_SERVICE, S3_SERVICE))
    assert len(reg) == 2
    ids = [svc.service_id for svc in reg]
    assert "sqs" in ids and "s3" in ids


# ── Script generation (no network needed) ────────────────────────────────────


def test_generate_python_script_for_list_secrets() -> None:
    from gui4aws.services.secrets.actions import LIST_SECRETS

    script = generate_python_script(
        LIST_SECRETS,
        inputs={"name_prefix": "demo", "include_deleted": "false"},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "secretsmanager" in script
    assert "list_secrets" in script
    assert "import boto3" in script


def test_generate_cli_script_for_list_secrets() -> None:
    from gui4aws.services.secrets.actions import LIST_SECRETS

    script = generate_cli_script(
        LIST_SECRETS,
        inputs={"name_prefix": "", "include_deleted": "false"},
        profile_name=None,
        region_name="eu-west-1",
        endpoint_config=EndpointConfig(),
    )
    assert "aws secretsmanager list-secrets" in script
    assert "eu-west-1" in script


def test_generate_python_script_for_create_queue() -> None:
    from gui4aws.services.sqs.actions import CREATE_QUEUE

    script = generate_python_script(
        CREATE_QUEUE,
        inputs={"queue_name": "my-queue", "visibility_timeout": "60"},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "create_queue" in script
    assert "my-queue" in script


def test_generate_python_script_with_moto_endpoint() -> None:
    from gui4aws.services.sqs.actions import LIST_QUEUES

    cfg = EndpointConfig(mode=EndpointMode.MOTO, endpoint_url="http://127.0.0.1:55000")
    script = generate_python_script(
        LIST_QUEUES,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=cfg,
    )
    assert "endpoint_url" in script
    assert "55000" in script


# ── InputField builder helpers ───────────────────────────────────────────────


def test_list_secrets_cli_args_builder_with_prefix() -> None:
    from gui4aws.services.secrets.actions import LIST_SECRETS

    assert LIST_SECRETS.cli_args_builder is not None
    args = LIST_SECRETS.cli_args_builder({"name_prefix": "myapp", "include_deleted": "false"})
    assert "--filters" in args


def test_list_secrets_cli_args_builder_include_deleted() -> None:
    from gui4aws.services.secrets.actions import LIST_SECRETS

    assert LIST_SECRETS.cli_args_builder is not None
    args = LIST_SECRETS.cli_args_builder({"include_deleted": "true"})
    assert "--include-planned-deletion" in args


def test_list_secrets_boto3_params_builder_include_deleted() -> None:
    from gui4aws.services.secrets.actions import LIST_SECRETS

    assert LIST_SECRETS.boto3_params_builder is not None
    params = LIST_SECRETS.boto3_params_builder({"include_deleted": "true"})
    assert params.get("IncludePlannedDeletion") is True


def test_kms_create_key_params_builder_defaults() -> None:
    from gui4aws.services.kms.actions import CREATE_KEY

    assert CREATE_KEY.boto3_params_builder is not None
    params = CREATE_KEY.boto3_params_builder({})
    assert params["KeyUsage"] == "ENCRYPT_DECRYPT"
    assert params["KeySpec"] == "SYMMETRIC_DEFAULT"


def test_kms_create_key_params_builder_multi_region() -> None:
    from gui4aws.services.kms.actions import CREATE_KEY

    assert CREATE_KEY.boto3_params_builder is not None
    params = CREATE_KEY.boto3_params_builder({"multi_region": "true"})
    assert params["MultiRegion"] is True


# ── MotoServerManager (no subprocess) ────────────────────────────────────────


def test_moto_server_manager_initial_state() -> None:
    from gui4aws.moto_server import MotoServerManager

    mgr = MotoServerManager()
    assert not mgr.running
    assert mgr.port == 0


def test_moto_server_manager_output_text_empty() -> None:
    from gui4aws.moto_server import MotoServerManager

    mgr = MotoServerManager()
    assert mgr.output_text() == ""


def test_moto_server_manager_snapshot_structure() -> None:
    from gui4aws.moto_server import MotoServerManager

    mgr = MotoServerManager()
    snap = mgr.snapshot()
    assert snap["running"] is False
    assert snap["port"] == 0
    assert snap["endpoint_url"] is None


# ── RobotocoreManager (no Docker) ────────────────────────────────────────────


def test_robotocore_manager_initial_state() -> None:
    from gui4aws.robotocore_server import RobotocoreManager

    mgr = RobotocoreManager()
    assert not mgr.running
    assert "4566" in mgr.endpoint_url


def test_robotocore_manager_snapshot_structure() -> None:
    from gui4aws.robotocore_server import RobotocoreManager

    mgr = RobotocoreManager()
    snap = mgr.snapshot()
    assert snap["running"] is False
    assert "endpoint_url" in snap


def test_robotocore_manager_reset_state_not_running_raises() -> None:
    from gui4aws.robotocore_server import RobotocoreManager

    mgr = RobotocoreManager()
    with pytest.raises(RuntimeError, match="not running"):
        mgr.reset_state()
