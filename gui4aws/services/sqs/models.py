"""Normalized SQS summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["QueueSummary"]


@dataclass(frozen=True)
class QueueSummary:
    name: str
    url: str
    approximate_messages: str | None
    visibility_timeout: str | None
    arn: str | None
