"""Normalization functions: raw boto3 response -> list[Summary] for CloudWatch."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.cloudwatch.models import AlarmSummary, LogEventSummary, LogGroupSummary, LogStreamSummary

__all__ = ["to_alarm_summaries", "to_log_event_summaries", "to_log_group_summaries", "to_log_stream_summaries"]


def optional_int(value: Any) -> int | None:
    """Safely convert a value to an integer, returning None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_alarm_summaries(response: Mapping[str, Any]) -> list[AlarmSummary]:
    """Convert a raw boto3 DescribeAlarms response into a list of AlarmSummary objects."""
    alarms = response.get("MetricAlarms", []) or []
    summaries: list[AlarmSummary] = []
    for a in alarms:
        threshold = a.get("Threshold")
        summaries.append(
            AlarmSummary(
                name=str(a.get("AlarmName", "")),
                state=a.get("StateValue") or None,
                metric_name=a.get("MetricName") or None,
                namespace=a.get("Namespace") or None,
                comparison=a.get("ComparisonOperator") or None,
                threshold=str(threshold) if threshold is not None else None,
                description=a.get("AlarmDescription") or None,
                arn=a.get("AlarmArn") or None,
            )
        )
    return summaries


def to_log_group_summaries(response: Mapping[str, Any]) -> list[LogGroupSummary]:
    """Convert a raw boto3 DescribeLogGroups response into a list of LogGroupSummary objects."""
    log_groups = response.get("logGroups", []) or []
    summaries: list[LogGroupSummary] = []
    for g in log_groups:
        summaries.append(
            LogGroupSummary(
                name=str(g.get("logGroupName", "")),
                retention_days=optional_int(g.get("retentionInDays")),
                stored_bytes=optional_int(g.get("storedBytes")),
                arn=g.get("arn") or None,
            )
        )
    return summaries


def fmt_ts(ms: Any) -> str | None:
    """Format a millisecond timestamp into a human-readable UTC date string."""
    if ms is None:
        return None
    try:
        from datetime import datetime, UTC

        return datetime.fromtimestamp(int(ms) / 1000, UTC).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:  # pylint: disable=broad-exception-caught
        return str(ms)


def to_log_stream_summaries(response: Mapping[str, Any]) -> list[LogStreamSummary]:
    """Convert a raw boto3 DescribeLogStreams response into a list of LogStreamSummary objects."""
    streams = response.get("logStreams", []) or []
    summaries: list[LogStreamSummary] = []
    for s in streams:
        summaries.append(
            LogStreamSummary(
                stream_name=str(s.get("logStreamName", "")),
                last_event_time=fmt_ts(s.get("lastEventTimestamp")),
                first_event_time=fmt_ts(s.get("firstEventTimestamp")),
                stored_bytes=optional_int(s.get("storedBytes")),
            )
        )
    return summaries


def to_log_event_summaries(response: Mapping[str, Any]) -> list[LogEventSummary]:
    """Convert a raw boto3 GetLogEvents response into a list of LogEventSummary objects."""
    events = response.get("events", []) or []
    summaries: list[LogEventSummary] = []
    for e in events:
        summaries.append(
            LogEventSummary(
                timestamp=fmt_ts(e.get("timestamp")) or "",
                message=str(e.get("message", "")).rstrip("\n"),
            )
        )
    return summaries
