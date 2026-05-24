"""Moto-backed tests for CloudWatch actions."""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.cloudwatch.actions import (
    CREATE_LOG_GROUP,
    DELETE_ALARM,
    DELETE_LOG_GROUP,
    DESCRIBE_ALARM,
    DESCRIBE_ALARMS,
    GET_LOG_EVENTS,
    LIST_LOG_GROUPS,
    LIST_LOG_STREAMS,
)
from gui4aws.services.cloudwatch.views import (
    to_alarm_summaries,
    to_log_event_summaries,
    to_log_group_summaries,
    to_log_stream_summaries,
)


def test_describe_alarms_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_ALARMS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_alarm_summaries(result.response)
    assert summaries == []


def test_alarm_actions(mock_aws_env: None) -> None:
    cw = boto3.client("cloudwatch", region_name="us-east-1")
    cw.put_metric_alarm(
        AlarmName="test-alarm",
        MetricName="CPU",
        Namespace="AWS/EC2",
        Threshold=80.0,
        ComparisonOperator="GreaterThanThreshold",
        EvaluationPeriods=1,
        Period=60,
    )

    context = AppContext(region_name="us-east-1")
    
    # List
    list_result = context.execute(DESCRIBE_ALARMS, inputs={})
    summaries = to_alarm_summaries(list_result.response)
    assert any(s.name == "test-alarm" for s in summaries)

    # Describe
    desc_result = context.execute(DESCRIBE_ALARM, inputs={"alarm_names": "test-alarm"})
    assert isinstance(desc_result, Boto3Result)
    assert desc_result.response["MetricAlarms"][0]["AlarmName"] == "test-alarm"

    # Delete
    del_result = context.execute(DELETE_ALARM, inputs={"alarm_name": "test-alarm"})
    assert isinstance(del_result, Boto3Result)


def test_log_actions(mock_aws_env: None) -> None:
    logs = boto3.client("logs", region_name="us-east-1")
    
    context = AppContext(region_name="us-east-1")
    
    # Create Log Group
    result = context.execute(CREATE_LOG_GROUP, inputs={"log_group_name": "test-lg"})
    assert isinstance(result, Boto3Result)

    # List Log Groups
    list_result = context.execute(LIST_LOG_GROUPS, inputs={})
    summaries = to_log_group_summaries(list_result.response)
    assert any(s.name == "test-lg" for s in summaries)

    # Create stream and event via boto3
    logs.create_log_stream(logGroupName="test-lg", logStreamName="test-stream")
    import datetime
    now_ms = int(datetime.datetime.now().timestamp() * 1000)
    logs.put_log_events(
        logGroupName="test-lg",
        logStreamName="test-stream",
        logEvents=[{"timestamp": now_ms, "message": "hello"}]
    )

    # List Streams
    streams_result = context.execute(LIST_LOG_STREAMS, inputs={"log_group_name": "test-lg"})
    summaries = to_log_stream_summaries(streams_result.response)
    assert any(s.stream_name == "test-stream" for s in summaries)

    # Get Events
    events_result = context.execute(
        GET_LOG_EVENTS,
        inputs={"log_group_name": "test-lg", "log_stream_name": "test-stream"}
    )
    summaries = to_log_event_summaries(events_result.response)
    assert any(s.message == "hello" for s in summaries)

    # Delete Log Group
    del_result = context.execute(DELETE_LOG_GROUP, inputs={"log_group_name": "test-lg"})
    assert isinstance(del_result, Boto3Result)
