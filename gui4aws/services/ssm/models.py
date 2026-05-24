"""Normalized SSM Parameter Store summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["ParameterSummary"]


@dataclass(frozen=True)
class ParameterSummary:
    """Summary information for an SSM parameter."""

    name: str
    type: str | None
    description: str | None
    last_modified_date: str | None
    version: int | None
    tier: str | None
    arn: str | None
