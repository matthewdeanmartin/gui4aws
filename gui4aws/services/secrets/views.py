"""Normalization functions: raw boto3 response -> list[Summary] for Secrets Manager."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.secrets.models import SecretSummary

__all__ = ["to_secret_summaries"]


def optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:19]


def to_secret_summaries(response: Mapping[str, Any]) -> list[SecretSummary]:
    secrets = response.get("SecretList", []) or []
    summaries: list[SecretSummary] = []
    for s in secrets:
        deletion_date = s.get("DeletedDate")
        summaries.append(
            SecretSummary(
                name=str(s.get("Name", "")),
                description=optional_str(s.get("Description")),
                last_changed_date=fmt_date(s.get("LastChangedDate")),
                last_accessed_date=fmt_date(s.get("LastAccessedDate")),
                rotation_enabled=bool(s.get("RotationEnabled", False)),
                deleted=deletion_date is not None,
                deletion_date=fmt_date(deletion_date),
                arn=optional_str(s.get("ARN")),
                kms_key_id=optional_str(s.get("KmsKeyId")),
            )
        )
    return summaries
