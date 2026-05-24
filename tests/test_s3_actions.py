"""Moto-backed tests for S3 actions."""

from __future__ import annotations


import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.s3.actions import (
    CREATE_BUCKET,
    DELETE_BUCKET,
    LIST_BUCKETS,
    LIST_OBJECTS,
)
from gui4aws.services.s3.views import to_bucket_summaries, to_object_summaries


def test_list_buckets_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_bucket_summaries(result.response)
    assert summaries == []


def test_create_bucket_and_list(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    create_result = context.execute(CREATE_BUCKET, inputs={"bucket_name": "my-test-bucket", "region": ""})
    assert isinstance(create_result, Boto3Result)

    list_result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(list_result, Boto3Result)
    summaries = to_bucket_summaries(list_result.response)
    assert any(s.name == "my-test-bucket" for s in summaries)


def test_delete_bucket(mock_aws_env: None) -> None:
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="delete-me-bucket")

    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_BUCKET, inputs={"bucket_name": "delete-me-bucket"})
    assert isinstance(result, Boto3Result)

    remaining = [b["Name"] for b in s3.list_buckets()["Buckets"]]
    assert "delete-me-bucket" not in remaining


def test_list_objects_empty_bucket(mock_aws_env: None) -> None:
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="empty-bucket")

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_OBJECTS, inputs={"bucket_name": "empty-bucket", "prefix": "", "max_keys": "200"})
    assert isinstance(result, Boto3Result)
    summaries = to_object_summaries(result.response)
    assert summaries == []


def test_list_objects_with_planted_objects(mock_aws_env: None) -> None:
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="obj-bucket")
    s3.put_object(Bucket="obj-bucket", Key="logs/2024/jan.txt", Body=b"data")
    s3.put_object(Bucket="obj-bucket", Key="logs/2024/feb.txt", Body=b"data")
    s3.put_object(Bucket="obj-bucket", Key="reports/q1.csv", Body=b"csv")

    context = AppContext(region_name="us-east-1")
    result = context.execute(
        LIST_OBJECTS,
        inputs={"bucket_name": "obj-bucket", "prefix": "logs/", "max_keys": "200"},
    )
    assert isinstance(result, Boto3Result)
    summaries = to_object_summaries(result.response)
    keys = [s.key for s in summaries]
    assert "logs/2024/jan.txt" in keys
    assert "logs/2024/feb.txt" in keys
    assert "reports/q1.csv" not in keys


def test_bucket_summary_has_name_and_creation_date(mock_aws_env: None) -> None:
    s3 = boto3.client("s3", region_name="us-east-1")
    s3.create_bucket(Bucket="summary-bucket")

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_bucket_summaries(result.response)
    bucket = next(s for s in summaries if s.name == "summary-bucket")
    assert bucket.creation_date is not None


def test_multiple_buckets_all_appear(mock_aws_env: None) -> None:
    s3 = boto3.client("s3", region_name="us-east-1")
    for name in ("bucket-a", "bucket-b", "bucket-c"):
        s3.create_bucket(Bucket=name)

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_bucket_summaries(result.response)
    names = {s.name for s in summaries}
    assert {"bucket-a", "bucket-b", "bucket-c"}.issubset(names)
