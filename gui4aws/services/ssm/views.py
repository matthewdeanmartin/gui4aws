"""Normalization functions: raw boto3 response -> list[Summary] for SSM Parameter Store."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.ssm.models import ParameterSummary

__all__ = ["to_parameter_summaries"]


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def to_parameter_summaries(response: Mapping[str, Any]) -> list[ParameterSummary]:
    # describe_parameters returns "Parameters"; get_parameters_by_path returns "Parameters" too
    params = response.get("Parameters", []) or []
    summaries: list[ParameterSummary] = []
    for p in params:
        last_modified = p.get("LastModifiedDate")
        summaries.append(
            ParameterSummary(
                name=str(p.get("Name", "")),
                type=optional_str(p.get("Type")),
                description=optional_str(p.get("Description")),
                last_modified_date=str(last_modified) if last_modified else None,
                version=optional_int(p.get("Version")),
                tier=optional_str(p.get("Tier")),
                arn=optional_str(p.get("ARN")),
            )
        )
    return summaries
