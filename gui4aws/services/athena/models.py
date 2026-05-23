"""Normalized Athena summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AthenaQueryExecutionSummary",
    "AthenaWorkGroupSummary",
]


@dataclass(frozen=True)
class AthenaWorkGroupSummary:
    name: str
    state: str | None
    description: str | None
    creation_time: str | None


@dataclass(frozen=True)
class AthenaQueryExecutionSummary:
    query_execution_id: str
    query: str | None
    state: str | None
    state_change_reason: str | None
    workgroup: str | None
    submission_date: str | None
    completion_date: str | None
    data_scanned_in_bytes: int | None
