"""Normalized CloudFormation summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["StackSummary"]


@dataclass(frozen=True)
class StackSummary:
    name: str
    status: str | None
    description: str | None
    creation_time: str | None
    last_updated_time: str | None
    arn: str | None
