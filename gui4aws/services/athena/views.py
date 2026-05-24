"""Normalization functions: raw boto3 response -> list[Summary] for Athena."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.athena.models import AthenaQueryExecutionSummary, AthenaWorkGroupSummary

__all__ = [
    "to_query_execution_summaries",
    "to_workgroup_summaries",
]


def optional_str(value: Any) -> str | None:
    """Return value as str, or None for blank/None."""
    if value is None:
        return None
    return str(value) or None


def fmt_date(value: Any) -> str | None:
    """Format a datetime object or string into a standard YYYY-MM-DD HH:MM:SS string."""
    if value is None:
        return None
    return str(value)[:19]


def to_workgroup_summaries(response: Mapping[str, Any]) -> list[AthenaWorkGroupSummary]:
    """Map ``list_work_groups`` or ``get_work_group`` response -> list[AthenaWorkGroupSummary]."""
    groups = response.get("WorkGroups", []) or []
    summaries: list[AthenaWorkGroupSummary] = []
    for g in groups:
        summaries.append(
            AthenaWorkGroupSummary(
                name=str(g.get("Name", "")),
                state=optional_str(g.get("State")),
                description=optional_str(g.get("Description")),
                creation_time=fmt_date(g.get("CreationTime")),
            )
        )
    # get_work_group returns {"WorkGroup": {...}}
    if "WorkGroup" in response:
        wg = response["WorkGroup"]
        summaries.append(
            AthenaWorkGroupSummary(
                name=str(wg.get("Name", "")),
                state=optional_str(wg.get("State")),
                description=optional_str((wg.get("Configuration") or {}).get("Description", wg.get("Description"))),
                creation_time=fmt_date(wg.get("CreationTime")),
            )
        )
    return summaries


def to_query_execution_summaries(response: Mapping[str, Any]) -> list[AthenaQueryExecutionSummary]:
    """Map query execution list/detail responses -> list[AthenaQueryExecutionSummary]."""
    # list_query_executions returns {"QueryExecutionIds": [...]}
    ids = response.get("QueryExecutionIds", []) or []
    summaries: list[AthenaQueryExecutionSummary] = []
    for qid in ids:
        summaries.append(
            AthenaQueryExecutionSummary(
                query_execution_id=str(qid),
                query=None,
                state=None,
                state_change_reason=None,
                workgroup=None,
                submission_date=None,
                completion_date=None,
                data_scanned_in_bytes=None,
            )
        )
    # get_query_execution and batch_get_query_execution
    executions: list[Any] = response.get("QueryExecutions", []) or []
    single = response.get("QueryExecution")
    if single:
        executions = [single]
    for qe in executions:
        status = qe.get("Status") or {}
        stats = qe.get("Statistics") or {}
        summaries.append(
            AthenaQueryExecutionSummary(
                query_execution_id=str(qe.get("QueryExecutionId", "")),
                query=optional_str(qe.get("Query")),
                state=optional_str(status.get("State")),
                state_change_reason=optional_str(status.get("StateChangeReason")),
                workgroup=optional_str(qe.get("WorkGroup")),
                submission_date=fmt_date(status.get("SubmissionDateTime")),
                completion_date=fmt_date(status.get("CompletionDateTime")),
                data_scanned_in_bytes=stats.get("DataScannedInBytes"),
            )
        )
    return summaries
