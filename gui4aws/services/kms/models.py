"""Normalized KMS summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "KmsAliasSummary",
    "KmsGrantSummary",
    "KmsKeySummary",
]


@dataclass(frozen=True)
class KmsKeySummary:
    key_id: str
    key_arn: str | None
    description: str | None
    key_state: str | None
    key_usage: str | None
    key_spec: str | None
    origin: str | None
    enabled: bool
    creation_date: str | None


@dataclass(frozen=True)
class KmsAliasSummary:
    alias_name: str
    target_key_id: str | None
    alias_arn: str | None
    creation_date: str | None
    last_updated_date: str | None


@dataclass(frozen=True)
class KmsGrantSummary:
    grant_id: str
    key_id: str | None
    name: str | None
    grantee_principal: str | None
    operations: str
    creation_date: str | None
