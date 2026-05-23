"""Normalization functions: raw boto3 response -> list[Summary] for Lambda."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.lambdas.models import FunctionSummary

__all__ = ["to_function_summaries"]


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:19]


def to_function_summaries(response: Mapping[str, Any]) -> list[FunctionSummary]:
    functions = response.get("Functions", []) or []
    summaries: list[FunctionSummary] = []
    for f in functions:
        summaries.append(
            FunctionSummary(
                name=str(f.get("FunctionName", "")),
                runtime=f.get("Runtime") or None,
                handler=f.get("Handler") or None,
                state=f.get("State") or None,
                last_modified=_fmt_date(f.get("LastModified")),
                memory_size=_optional_int(f.get("MemorySize")),
                timeout=_optional_int(f.get("Timeout")),
                description=f.get("Description") or None,
                arn=f.get("FunctionArn") or None,
            )
        )
    return summaries
