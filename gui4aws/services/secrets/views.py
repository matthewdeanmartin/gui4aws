"""Normalization functions: raw boto3 response -> list[Summary] for Secrets Manager."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.secrets.models import SecretSummary

__all__ = ["to_secret_summaries"]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def to_secret_summaries(response: Mapping[str, Any]) -> list[SecretSummary]:
    secrets = response.get("SecretList", []) or []
    summaries: list[SecretSummary] = []
    for s in secrets:
        last_changed = s.get("LastChangedDate")
        last_accessed = s.get("LastAccessedDate")
        summaries.append(
            SecretSummary(
                name=str(s.get("Name", "")),
                description=_optional_str(s.get("Description")),
                last_changed_date=str(last_changed) if last_changed else None,
                last_accessed_date=str(last_accessed) if last_accessed else None,
                rotation_enabled=bool(s.get("RotationEnabled", False)),
                arn=_optional_str(s.get("ARN")),
            )
        )
    return summaries
