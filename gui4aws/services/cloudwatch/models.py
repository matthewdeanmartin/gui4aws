"""Normalized CloudWatch summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AlarmSummary", "LogEventSummary", "LogGroupSummary", "LogStreamSummary"]


@dataclass(frozen=True)
class AlarmSummary:
    """Summary information for a CloudWatch alarm."""

    name: str
    state: str | None
    metric_name: str | None
    namespace: str | None
    comparison: str | None
    threshold: str | None
    description: str | None
    arn: str | None


@dataclass(frozen=True)
class LogGroupSummary:
    """Summary information for a CloudWatch log group."""

    name: str
    retention_days: int | None
    stored_bytes: int | None
    arn: str | None


@dataclass(frozen=True)
class LogStreamSummary:
    """Summary information for a CloudWatch log stream."""

    stream_name: str
    last_event_time: str | None
    first_event_time: str | None
    stored_bytes: int | None


@dataclass(frozen=True)
class LogEventSummary:
    """Summary of a single CloudWatch log event."""

    timestamp: str
    message: str
