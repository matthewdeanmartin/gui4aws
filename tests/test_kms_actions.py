"""Moto-backed tests for KMS actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.kms.actions import (
    CREATE_ALIAS,
    CREATE_KEY,
    DELETE_ALIAS,
    DESCRIBE_KEY,
    DISABLE_KEY,
    ENABLE_KEY,
    LIST_ALIASES,
    LIST_KEYS,
    SCHEDULE_KEY_DELETION,
)
from gui4aws.services.kms.views import to_alias_summaries, to_key_summaries


def test_list_keys_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_KEYS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_key_summaries(result.response)
    # Moto may return AWS-managed keys; we assert the call succeeds and returns a list.
    assert isinstance(summaries, list)


def test_create_key_and_list(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    create_result = context.execute(
        CREATE_KEY,
        inputs={
            "description": "test key",
            "key_usage": "ENCRYPT_DECRYPT",
            "key_spec": "SYMMETRIC_DEFAULT",
            "multi_region": "false",
        },
    )
    assert isinstance(create_result, Boto3Result)
    key_id = create_result.response["KeyMetadata"]["KeyId"]

    list_result = context.execute(LIST_KEYS, inputs={})
    assert isinstance(list_result, Boto3Result)
    summaries = to_key_summaries(list_result.response)
    assert any(s.key_id == key_id for s in summaries)


def test_describe_key(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key(Description="desc-test")["KeyMetadata"]["KeyId"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_KEY, inputs={"key_id": key_id})
    assert isinstance(result, Boto3Result)
    summaries = to_key_summaries(result.response)
    assert any(s.key_id == key_id for s in summaries)


def test_create_and_list_alias(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(
        CREATE_ALIAS,
        inputs={"alias_name": "alias/my-test-key", "target_key_id": key_id},
    )
    assert isinstance(result, Boto3Result)

    list_result = context.execute(LIST_ALIASES, inputs={"key_id": ""})
    assert isinstance(list_result, Boto3Result)
    summaries = to_alias_summaries(list_result.response)
    assert any(s.alias_name == "alias/my-test-key" for s in summaries)


def test_delete_alias(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]
    kms.create_alias(AliasName="alias/to-delete", TargetKeyId=key_id)

    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_ALIAS, inputs={"alias_name": "alias/to-delete"})
    assert isinstance(result, Boto3Result)

    aliases = kms.list_aliases()["Aliases"]
    assert not any(a["AliasName"] == "alias/to-delete" for a in aliases)


def test_disable_and_enable_key(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]

    context = AppContext(region_name="us-east-1")

    disable_result = context.execute(DISABLE_KEY, inputs={"key_id": key_id})
    assert isinstance(disable_result, Boto3Result)
    assert kms.describe_key(KeyId=key_id)["KeyMetadata"]["KeyState"] == "Disabled"

    enable_result = context.execute(ENABLE_KEY, inputs={"key_id": key_id})
    assert isinstance(enable_result, Boto3Result)
    assert kms.describe_key(KeyId=key_id)["KeyMetadata"]["KeyState"] == "Enabled"


def test_schedule_key_deletion(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(
        SCHEDULE_KEY_DELETION,
        inputs={"key_id": key_id, "pending_window_in_days": "7"},
    )
    assert isinstance(result, Boto3Result)
    state = kms.describe_key(KeyId=key_id)["KeyMetadata"]["KeyState"]
    assert state == "PendingDeletion"


def test_key_summary_enabled_field(mock_aws_env: None) -> None:
    kms = boto3.client("kms", region_name="us-east-1")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_KEY, inputs={"key_id": key_id})
    assert isinstance(result, Boto3Result)
    summaries = to_key_summaries(result.response)
    assert len(summaries) == 1
    assert summaries[0].enabled is True
