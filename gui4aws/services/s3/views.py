"""Normalization functions: raw boto3 response -> list[Summary] for S3."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.s3.models import BucketSummary, S3ObjectSummary

__all__ = ["to_bucket_summaries", "to_object_summaries"]


def fmt_date(value: Any) -> str | None:
    """Format a datetime value as a string, truncated to seconds."""
    if value is None:
        return None
    return str(value)[:19]


def to_bucket_summaries(response: Mapping[str, Any]) -> list[BucketSummary]:
    """Convert a raw boto3 ListBuckets response into a list of BucketSummary objects."""
    buckets = response.get("Buckets", []) or []
    summaries: list[BucketSummary] = []
    for b in buckets:
        summaries.append(
            BucketSummary(
                name=str(b.get("Name", "")),
                region=b.get("BucketRegion") or b.get("LocationConstraint") or None,
                creation_date=fmt_date(b.get("CreationDate")),
                versioning_enabled=False,
            )
        )
    return summaries


def to_object_summaries(response: Mapping[str, Any]) -> list[S3ObjectSummary]:
    """Convert a raw boto3 ListObjectsV2 response into a list of S3ObjectSummary objects."""
    objects = response.get("Contents", []) or []
    summaries: list[S3ObjectSummary] = []
    for obj in objects:
        summaries.append(
            S3ObjectSummary(
                key=str(obj.get("Key", "")),
                size=obj.get("Size"),
                last_modified=fmt_date(obj.get("LastModified")),
                storage_class=obj.get("StorageClass") or None,
            )
        )
    return summaries
