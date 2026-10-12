"""Normalized Route 53 summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["HostedZoneSummary", "RecordSetSummary"]


@dataclass(frozen=True)
class HostedZoneSummary:
    """Summary information for a Route 53 hosted zone."""

    zone_id: str
    name: str
    private: bool
    record_count: int | None
    comment: str | None


@dataclass(frozen=True)
class RecordSetSummary:
    """Summary information for a Route 53 resource record set."""

    name: str
    type: str
    ttl: int | None
    records: str
    alias_target: str | None
