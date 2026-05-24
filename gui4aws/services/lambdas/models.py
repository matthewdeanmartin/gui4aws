"""Normalized Lambda summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["FunctionSummary"]


@dataclass(frozen=True)
class FunctionSummary:
    """Summary information for an AWS Lambda function."""

    name: str
    runtime: str | None
    handler: str | None
    state: str | None
    last_modified: str | None
    memory_size: int | None
    timeout: int | None
    description: str | None
    arn: str | None
