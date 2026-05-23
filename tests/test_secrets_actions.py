"""Moto-backed tests for Secrets Manager actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.secrets.actions import (
    CREATE_SECRET,
    DELETE_SECRET,
    DESCRIBE_SECRET,
    LIST_SECRETS,
    PUT_SECRET_VALUE,
    RESTORE_SECRET,
)
from gui4aws.services.secrets.views import to_secret_summaries


def test_list_secrets_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "false"})
    assert isinstance(result, Boto3Result)
    summaries = to_secret_summaries(result.response)
    assert summaries == []


def test_create_secret_and_list(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    create_result = context.execute(
        CREATE_SECRET,
        inputs={"name": "my-secret", "description": "test", "secret_string": '{"key": "value"}'},
    )
    assert isinstance(create_result, Boto3Result)
    assert "ARN" in create_result.response

    list_result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "false"})
    assert isinstance(list_result, Boto3Result)
    summaries = to_secret_summaries(list_result.response)
    assert any(s.name == "my-secret" for s in summaries)


def test_describe_secret(mock_aws_env: None) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(Name="describe-me", SecretString="s3cr3t")

    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_SECRET, inputs={"secret_id": "describe-me"})
    assert isinstance(result, Boto3Result)
    assert result.response.get("Name") == "describe-me"


def test_put_secret_value(mock_aws_env: None) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(Name="rotatable", SecretString="initial-value")

    context = AppContext(region_name="us-east-1")
    result = context.execute(
        PUT_SECRET_VALUE,
        inputs={"secret_id": "rotatable", "secret_string": "new-value"},
    )
    assert isinstance(result, Boto3Result)
    assert result.response.get("Name") == "rotatable"

    value = sm.get_secret_value(SecretId="rotatable")["SecretString"]
    assert value == "new-value"


def test_delete_and_restore_secret(mock_aws_env: None) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(Name="restore-me", SecretString="data")

    context = AppContext(region_name="us-east-1")

    del_result = context.execute(
        DELETE_SECRET,
        inputs={"secret_id": "restore-me", "recovery_window_in_days": "7"},
    )
    assert isinstance(del_result, Boto3Result)

    # Secret is now pending deletion — visible when include_deleted=true
    list_result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "true"})
    assert isinstance(list_result, Boto3Result)
    summaries = to_secret_summaries(list_result.response)
    deleted = next((s for s in summaries if s.name == "restore-me"), None)
    assert deleted is not None
    assert deleted.deleted is True

    restore_result = context.execute(RESTORE_SECRET, inputs={"secret_id": "restore-me"})
    assert isinstance(restore_result, Boto3Result)
    assert restore_result.response.get("Name") == "restore-me"


def test_secret_summary_fields(mock_aws_env: None) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(Name="field-check", SecretString="x", Description="My desc")

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "false"})
    assert isinstance(result, Boto3Result)
    summaries = to_secret_summaries(result.response)
    secret = next(s for s in summaries if s.name == "field-check")
    assert secret.description == "My desc"
    assert secret.deleted is False


def test_list_secrets_name_prefix_filter(mock_aws_env: None) -> None:
    sm = boto3.client("secretsmanager", region_name="us-east-1")
    sm.create_secret(Name="prod/api-key", SecretString="prod")
    sm.create_secret(Name="dev/api-key", SecretString="dev")

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_SECRETS, inputs={"name_prefix": "prod", "include_deleted": "false"})
    assert isinstance(result, Boto3Result)
    summaries = to_secret_summaries(result.response)
    assert all("prod" in s.name for s in summaries)
    assert not any("dev" in s.name for s in summaries)
