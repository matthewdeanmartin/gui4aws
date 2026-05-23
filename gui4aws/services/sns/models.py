"""Normalized SNS summaries."""
from __future__ import annotations
from dataclasses import dataclass

__all__ = ["TopicSummary", "SubscriptionSummary"]

@dataclass(frozen=True)
class TopicSummary:
    name: str
    arn: str

@dataclass(frozen=True)
class SubscriptionSummary:
    subscription_id: str
    topic_arn: str
    protocol: str
    endpoint: str | None
    status: str | None
    arn: str | None
