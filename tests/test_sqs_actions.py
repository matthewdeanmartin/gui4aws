"""Moto-backed tests for SQS actions."""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.sqs.actions import (
    CREATE_QUEUE,
    DELETE_QUEUE,
    LIST_QUEUES,
    PURGE_QUEUE,
    RECEIVE_MESSAGES,
    SEND_MESSAGE,
)
from gui4aws.services.sqs.views import to_queue_summaries


def test_list_queues_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_QUEUES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_queue_summaries(result.response)
    assert summaries == []


def test_create_queue_and_list(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(CREATE_QUEUE, inputs={"queue_name": "test-queue"})
    assert isinstance(result, Boto3Result)
    assert "QueueUrl" in result.response

    list_result = context.execute(LIST_QUEUES, inputs={})
    assert isinstance(list_result, Boto3Result)
    summaries = to_queue_summaries(list_result.response)
    assert any(s.name == "test-queue" for s in summaries)


def test_create_queue_appears_with_prefix_filter(mock_aws_env: None) -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    sqs.create_queue(QueueName="alpha-queue")
    sqs.create_queue(QueueName="beta-queue")

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_QUEUES, inputs={"queue_name_prefix": "alpha"})
    assert isinstance(result, Boto3Result)
    summaries = to_queue_summaries(result.response)
    assert len(summaries) == 1
    assert summaries[0].name == "alpha-queue"


def test_delete_queue(mock_aws_env: None) -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    url = sqs.create_queue(QueueName="delete-me")["QueueUrl"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(DELETE_QUEUE, inputs={"queue_url": url})
    assert isinstance(result, Boto3Result)

    remaining = sqs.list_queues().get("QueueUrls", [])
    assert url not in remaining


def test_send_and_receive_message(mock_aws_env: None) -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    url = sqs.create_queue(QueueName="msg-queue")["QueueUrl"]

    context = AppContext(region_name="us-east-1")
    send_result = context.execute(
        SEND_MESSAGE,
        inputs={"queue_url": url, "message_body": "hello world", "delay_seconds": "0"},
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
    assert messages[0]["Body"] == "hello world"


def test_purge_queue_removes_messages(mock_aws_env: None) -> None:
    sqs = boto3.client("sqs", region_name="us-east-1")
    url = sqs.create_queue(QueueName="purge-queue")["QueueUrl"]
    sqs.send_message(QueueUrl=url, MessageBody="msg1")
    sqs.send_message(QueueUrl=url, MessageBody="msg2")

    context = AppContext(region_name="us-east-1")
    result = context.execute(PURGE_QUEUE, inputs={"queue_url": url})
    assert isinstance(result, Boto3Result)

    attrs = sqs.get_queue_attributes(QueueUrl=url, AttributeNames=["ApproximateNumberOfMessages"])
    assert attrs["Attributes"]["ApproximateNumberOfMessages"] == "0"


def test_queue_summary_name_extracted_from_url(mock_aws_env: None) -> None:
    """to_queue_summaries extracts the queue name from the URL path."""
    fake_response = {"QueueUrls": ["http://localhost:4566/000000000000/my-queue"]}
    summaries = to_queue_summaries(fake_response)
    assert len(summaries) == 1
    assert summaries[0].name == "my-queue"
    assert summaries[0].url == "http://localhost:4566/000000000000/my-queue"
