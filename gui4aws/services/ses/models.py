"""Normalized SES summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["IdentitySummary", "TemplateSummary"]


@dataclass(frozen=True)
class IdentitySummary:
    identity: str
    identity_type: str
    verification_status: str | None
    dkim_enabled: bool


@dataclass(frozen=True)
class TemplateSummary:
    name: str
    created_timestamp: str | None
