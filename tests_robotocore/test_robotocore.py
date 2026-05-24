"""Robotocore integration tests.

These tests require Docker and a running robotocore container.  They are NOT
collected by the default ``pytest`` run (they live outside ``tests/``).

Run locally after ``docker`` is available::

    uv run pytest tests_robotocore/ -v

All assertions mirror the moto-backed tests in ``tests/`` so you can be
confident that the service layer behaves the same against both emulators.
"""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.robotocore_server import RobotocoreManager


def _ctx(robotocore: RobotocoreManager) -> AppContext:
    cfg = EndpointConfig(mode=EndpointMode.ROBOTOCORE, endpoint_url=robotocore.endpoint_url)
    return AppContext(region_name="us-east-1", endpoint_config=cfg)


def _client(robotocore: RobotocoreManager, service: str) -> boto3.client:  # type: ignore[type-arg]
    return boto3.client(service, region_name="us-east-1", endpoint_url=robotocore.endpoint_url)


# ── SQS ───────────────────────────────────────────────────────────────────────


def test_sqs_create_and_list_queues(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.sqs.actions import CREATE_QUEUE, LIST_QUEUES
    from gui4aws.services.sqs.views import to_queue_summaries

    context = _ctx(robotocore)
    context.execute(CREATE_QUEUE, inputs={"queue_name": "rc-queue-1", "visibility_timeout": "30"})

    result = context.execute(LIST_QUEUES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_queue_summaries(result.response)
    assert any(s.name == "rc-queue-1" for s in summaries)


def test_sqs_send_and_receive_message(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.sqs.actions import LIST_QUEUES, RECEIVE_MESSAGES, SEND_MESSAGE
    from gui4aws.services.sqs.views import to_queue_summaries

    sqs = _client(robotocore, "sqs")
    url = sqs.create_queue(QueueName="rc-msg-queue")["QueueUrl"]

    context = _ctx(robotocore)
    send_result = context.execute(
        SEND_MESSAGE,
        inputs={"queue_url": url, "message_body": "robotocore hello", "delay_seconds": "0"},
    )
    assert isinstance(send_result, Boto3Result)
    assert "MessageId" in send_result.response

    recv_result = context.execute(
        RECEIVE_MESSAGES,
        inputs={"queue_url": url, "max_number_of_messages": "1", "wait_time_seconds": "0"},
    )
    assert isinstance(recv_result, Boto3Result)
    messages = recv_result.response.get("Messages", [])
    assert len(messages) == 1
    assert messages[0]["Body"] == "robotocore hello"


# ── S3 ────────────────────────────────────────────────────────────────────────


def test_s3_create_and_list_buckets(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.s3.actions import CREATE_BUCKET, LIST_BUCKETS
    from gui4aws.services.s3.views import to_bucket_summaries

    context = _ctx(robotocore)
    context.execute(CREATE_BUCKET, inputs={"bucket_name": "rc-bucket-1", "region": ""})

    result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_bucket_summaries(result.response)
    assert any(s.name == "rc-bucket-1" for s in summaries)


def test_s3_list_objects_in_bucket(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.s3.actions import LIST_OBJECTS
    from gui4aws.services.s3.views import to_object_summaries

    s3 = _client(robotocore, "s3")
    s3.create_bucket(Bucket="rc-obj-bucket")
    s3.put_object(Bucket="rc-obj-bucket", Key="data/file1.txt", Body=b"hello")
    s3.put_object(Bucket="rc-obj-bucket", Key="data/file2.txt", Body=b"world")

    context = _ctx(robotocore)
    result = context.execute(
        LIST_OBJECTS,
        inputs={"bucket_name": "rc-obj-bucket", "prefix": "data/", "max_keys": "100"},
    )
    assert isinstance(result, Boto3Result)
    summaries = to_object_summaries(result.response)
    keys = [s.key for s in summaries]
    assert "data/file1.txt" in keys
    assert "data/file2.txt" in keys


# ── Secrets Manager ───────────────────────────────────────────────────────────


def test_secrets_create_and_list(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.secrets.actions import CREATE_SECRET, LIST_SECRETS
    from gui4aws.services.secrets.views import to_secret_summaries

    context = _ctx(robotocore)
    context.execute(
        CREATE_SECRET,
        inputs={"name": "rc-secret-1", "description": "rc test", "secret_string": "s3cr3t"},
    )

    result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "false"})
    assert isinstance(result, Boto3Result)
    summaries = to_secret_summaries(result.response)
    assert any(s.name == "rc-secret-1" for s in summaries)


def test_secrets_put_and_describe(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.secrets.actions import DESCRIBE_SECRET, PUT_SECRET_VALUE

    sm = _client(robotocore, "secretsmanager")
    sm.create_secret(Name="rc-rotate-secret", SecretString="old")

    context = _ctx(robotocore)
    context.execute(PUT_SECRET_VALUE, inputs={"secret_id": "rc-rotate-secret", "secret_string": "new-value"})

    result = context.execute(DESCRIBE_SECRET, inputs={"secret_id": "rc-rotate-secret"})
    assert isinstance(result, Boto3Result)
    assert result.response.get("Name") == "rc-rotate-secret"

    value = sm.get_secret_value(SecretId="rc-rotate-secret")["SecretString"]
    assert value == "new-value"


# ── KMS ───────────────────────────────────────────────────────────────────────


def test_kms_create_key_and_list(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.kms.actions import CREATE_KEY, LIST_KEYS
    from gui4aws.services.kms.views import to_key_summaries

    context = _ctx(robotocore)
    create_result = context.execute(
        CREATE_KEY,
        inputs={
            "description": "rc test key",
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


def test_kms_create_alias(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.kms.actions import CREATE_ALIAS, LIST_ALIASES
    from gui4aws.services.kms.views import to_alias_summaries

    kms = _client(robotocore, "kms")
    key_id = kms.create_key()["KeyMetadata"]["KeyId"]

    context = _ctx(robotocore)
    context.execute(CREATE_ALIAS, inputs={"alias_name": "alias/rc-test-key", "target_key_id": key_id})

    result = context.execute(LIST_ALIASES, inputs={"key_id": ""})
    assert isinstance(result, Boto3Result)
    summaries = to_alias_summaries(result.response)
    assert any(s.alias_name == "alias/rc-test-key" for s in summaries)


# ── Aurora (RDS) ──────────────────────────────────────────────────────────────


def test_aurora_create_cluster_and_describe(robotocore: RobotocoreManager) -> None:
    from gui4aws.services.aurora.actions import CREATE_DB_CLUSTER, DESCRIBE_DB_CLUSTERS

    context = _ctx(robotocore)
    context.execute(
        CREATE_DB_CLUSTER,
        inputs={
            "cluster_identifier": "rc-cluster-1",
            "engine": "aurora-postgresql",
            "cluster_kind": "provisioned",
            "master_username": "admin",
            "master_user_password": "Password123!",
            "serverless_min_capacity": "",
            "serverless_max_capacity": "",
        },
    )

    result = context.execute(DESCRIBE_DB_CLUSTERS, inputs={})
    assert isinstance(result, Boto3Result)
    from gui4aws.services.aurora.views import to_db_cluster_summaries

    summaries = to_db_cluster_summaries(result.response)
    assert any(s.cluster_identifier == "rc-cluster-1" for s in summaries)


# ── RobotocoreManager state ───────────────────────────────────────────────────


def test_robotocore_manager_running(robotocore: RobotocoreManager) -> None:
    assert robotocore.running
    assert "4566" in robotocore.endpoint_url


def test_robotocore_manager_snapshot(robotocore: RobotocoreManager) -> None:
    snap = robotocore.snapshot()
    assert snap["running"] is True
    assert "endpoint_url" in snap
