"""Normalized SNS summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SubscriptionSummary", "TopicSummary"]


@dataclass(frozen=True)
class TopicSummary:
    """Summary information for an SNS topic."""

    name: str
    arn: str


@dataclass(frozen=True)
class SubscriptionSummary:
    """Summary information for an SNS subscription."""

    subscription_id: str
    topic_arn: str
    protocol: str
    endpoint: str | None
    status: str | None
    arn: str | None
