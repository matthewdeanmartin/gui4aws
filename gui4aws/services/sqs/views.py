"""Normalization functions: raw boto3 response -> list[Summary] for SQS."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.sqs.models import QueueSummary

__all__ = ["to_queue_summaries"]


def to_queue_summaries(response: Mapping[str, Any]) -> list[QueueSummary]:
    """Convert a raw boto3 ListQueues response into a list of QueueSummary objects."""
    urls = response.get("QueueUrls", []) or []
    summaries: list[QueueSummary] = []
    for url in urls:
        # Extract queue name from the last path component of the URL
        name = url.rstrip("/").rsplit("/", 1)[-1]
        summaries.append(
            QueueSummary(
                name=name,
                url=url,
                approximate_messages=None,
                visibility_timeout=None,
                arn=None,
            )
        )
    return summaries
