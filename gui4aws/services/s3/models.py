"""Normalized S3 summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["BucketSummary", "S3ObjectSummary"]


@dataclass(frozen=True)
class BucketSummary:
    name: str
    region: str | None
    creation_date: str | None
    versioning_enabled: bool


@dataclass(frozen=True)
class S3ObjectSummary:
    key: str
    size: int | None
    last_modified: str | None
    storage_class: str | None
