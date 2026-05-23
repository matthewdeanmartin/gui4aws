"""Normalization functions for SNS."""
from __future__ import annotations
from collections.abc import Mapping
from typing import Any
from gui4aws.services.sns.models import TopicSummary, SubscriptionSummary

__all__ = ["to_topic_summaries", "to_subscription_summaries"]

def to_topic_summaries(response: Mapping[str, Any]) -> list[TopicSummary]:
    topics = response.get("Topics", []) or []
    results = []
    for t in topics:
        arn = t.get("TopicArn", "")
        name = arn.split(":")[-1] if arn else ""
        results.append(TopicSummary(name=name, arn=arn))
    return results

def to_subscription_summaries(response: Mapping[str, Any]) -> list[SubscriptionSummary]:
    subs = response.get("Subscriptions", []) or []
    results = []
    for s in subs:
        arn = s.get("SubscriptionArn", "")
        sub_id = arn.split(":")[-1] if arn and not arn.startswith("PendingConfirmation") else arn
        results.append(SubscriptionSummary(
            subscription_id=sub_id,
            topic_arn=s.get("TopicArn", ""),
            protocol=s.get("Protocol", ""),
            endpoint=s.get("Endpoint") or None,
            status="PendingConfirmation" if arn == "PendingConfirmation" else "Confirmed",
            arn=arn if arn != "PendingConfirmation" else None,
        ))
    return results
