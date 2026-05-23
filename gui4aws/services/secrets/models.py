"""Normalized Secrets Manager summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["SecretSummary"]


@dataclass(frozen=True)
class SecretSummary:
    name: str
    description: str | None
    last_changed_date: str | None
    last_accessed_date: str | None
    rotation_enabled: bool
    deleted: bool
    deletion_date: str | None
    arn: str | None
    kms_key_id: str | None
