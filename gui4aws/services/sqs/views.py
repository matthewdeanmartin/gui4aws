"""Normalization functions: raw boto3 response -> list[Summary] for SQS."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from gui4aws.services.sqs.models import QueueSummary

__all__ = ["to_queue_summaries"]

_URL_PATTERN = re.compile(r"https?://sqs\.([^.]+)\.amazonaws\.com/(\d+)/(.+)")


def _arn_from_url(url: str) -> str | None:
    """Derive an SQS ARN from a standard queue URL."""
    m = _URL_PATTERN.match(url.rstrip("/"))
    if m:
        region, account_id, queue_name = m.groups()
        return f"arn:aws:sqs:{region}:{account_id}:{queue_name}"
    return None


def to_queue_summaries(response: Mapping[str, Any]) -> list[QueueSummary]:
    """Convert a raw boto3 SQS queue response into a list of QueueSummary objects."""
    queues = response.get("Queues", []) or []
    summaries: list[QueueSummary] = []
    for queue in queues:
        url = str(queue.get("QueueUrl", ""))
        attrs = queue.get("Attributes", {}) or {}
        name = url.rstrip("/").rsplit("/", 1)[-1]
        summaries.append(
            QueueSummary(
                name=name,
                url=url,
                approximate_messages=attrs.get("ApproximateNumberOfMessages"),
                visibility_timeout=attrs.get("VisibilityTimeout"),
                arn=attrs.get("QueueArn") or _arn_from_url(url),
            )
        )
    urls = response.get("QueueUrls", []) or []
    for url in urls:
        name = url.rstrip("/").rsplit("/", 1)[-1]
        summaries.append(
            QueueSummary(
                name=name,
                url=url,
                approximate_messages=None,
                visibility_timeout=None,
                arn=_arn_from_url(url),
            )
        )
    return summaries
