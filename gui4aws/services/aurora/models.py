"""Normalized Aurora summaries.

These dataclasses are what the GUI binds to. They are intentionally smaller than the raw boto3
responses — fields the user cares about, sourced from the boto3 keys we know exist (verified
against moto 5).
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AuroraClusterSnapshotSummary",
    "AuroraClusterSummary",
    "AuroraInstanceSummary",
]


@dataclass(frozen=True)
class AuroraClusterSummary:
    """One Aurora DB cluster."""

    cluster_identifier: str
    engine: str
    engine_version: str | None
    status: str
    endpoint: str | None
    reader_endpoint: str | None
    multi_az: bool
    member_count: int
    arn: str | None


@dataclass(frozen=True)
class AuroraClusterSnapshotSummary:
    """One Aurora DB cluster snapshot."""

    snapshot_identifier: str
    cluster_identifier: str
    engine: str | None
    engine_version: str | None
    status: str
    snapshot_type: str | None
    percent_progress: int | None
    arn: str | None


@dataclass(frozen=True)
class AuroraInstanceSummary:
    """One DB instance that is a member of an Aurora cluster."""

    instance_identifier: str
    cluster_identifier: str | None
    engine: str
    instance_class: str | None
    status: str
    is_writer: bool
    arn: str | None
