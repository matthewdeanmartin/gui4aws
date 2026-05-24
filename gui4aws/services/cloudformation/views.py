"""Normalization functions: raw boto3 response -> list[Summary] for CloudFormation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.cloudformation.models import StackSummary

__all__ = ["to_stack_summaries"]


def fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:19]


def to_stack_summaries(response: Mapping[str, Any]) -> list[StackSummary]:
    stacks = response.get("Stacks", []) or []
    summaries: list[StackSummary] = []
    for s in stacks:
        summaries.append(
            StackSummary(
                name=str(s.get("StackName", "")),
                status=s.get("StackStatus") or None,
                description=s.get("Description") or None,
                creation_time=fmt_date(s.get("CreationTime")),
                last_updated_time=fmt_date(s.get("LastUpdatedTime")),
                arn=s.get("StackId") or None,
            )
        )
    return summaries
