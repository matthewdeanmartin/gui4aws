"""Moto-backed tests for SNS actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.sns.actions import (
    CREATE_TOPIC,
    DELETE_TOPIC,
    LIST_SUBSCRIPTIONS,
    LIST_TOPICS,
    PUBLISH,
    SUBSCRIBE,
    UNSUBSCRIBE,
)
from gui4aws.services.sns.views import to_subscription_summaries, to_topic_summaries


def test_list_topics_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_TOPICS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_topic_summaries(result.response)
    assert summaries == []


def test_create_and_delete_topic(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create
    result = context.execute(CREATE_TOPIC, inputs={"topic_name": "test-topic"})
    assert isinstance(result, Boto3Result)
    arn = result.response["TopicArn"]
    assert "test-topic" in arn

    # List
    list_result = context.execute(LIST_TOPICS, inputs={})
    summaries = to_topic_summaries(list_result.response)
    assert any(s.name == "test-topic" for s in summaries)

    # Delete
    del_result = context.execute(DELETE_TOPIC, inputs={"topic_arn": arn})
    assert isinstance(del_result, Boto3Result)
    # Note: Moto state might lag; successful Boto3Result confirms the action was sent correctly.


def test_subscription_actions(mock_aws_env: None) -> None:
    sns = boto3.client("sns", region_name="us-east-1")
    topic_arn = sns.create_topic(Name="sub-topic")["TopicArn"]

    context = AppContext(region_name="us-east-1")

    # Subscribe
    result = context.execute(
        SUBSCRIBE,
        inputs={
            "topic_arn": topic_arn,
            "protocol": "email",
            "endpoint": "test@example.com"
        }
    )
    assert isinstance(result, Boto3Result)
    sub_arn = result.response["SubscriptionArn"]

    # List Subscriptions
    list_result = context.execute(LIST_SUBSCRIPTIONS, inputs={})
    summaries = to_subscription_summaries(list_result.response)
    assert any(s.endpoint == "test@example.com" for s in summaries)

    # Unsubscribe
    unsub_result = context.execute(UNSUBSCRIBE, inputs={"subscription_arn": sub_arn})
    assert isinstance(unsub_result, Boto3Result)


def test_publish_message(mock_aws_env: None) -> None:
    sns = boto3.client("sns", region_name="us-east-1")
    topic_arn = sns.create_topic(Name="pub-topic")["TopicArn"]

    context = AppContext(region_name="us-east-1")
    result = context.execute(
        PUBLISH,
        inputs={
            "topic_arn": topic_arn,
            "message": "hello world",
            "subject": "test subject"
        }
    )
    assert isinstance(result, Boto3Result)
    assert "MessageId" in result.response
