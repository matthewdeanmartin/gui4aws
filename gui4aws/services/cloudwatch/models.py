"""Normalized CloudWatch summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AlarmSummary", "LogGroupSummary", "LogStreamSummary", "LogEventSummary"]


@dataclass(frozen=True)
class AlarmSummary:
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
    name: str
    retention_days: int | None
    stored_bytes: int | None
    arn: str | None


@dataclass(frozen=True)
class LogStreamSummary:
    stream_name: str
    last_event_time: str | None
    first_event_time: str | None
    stored_bytes: int | None


@dataclass(frozen=True)
class LogEventSummary:
    timestamp: str
    message: str
