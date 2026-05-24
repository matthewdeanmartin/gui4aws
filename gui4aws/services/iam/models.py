"""Normalized IAM summaries."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["GroupSummary", "PolicySummary", "RoleSummary", "UserSummary"]


@dataclass(frozen=True)
class UserSummary:
    """Summary information for an IAM user."""

    name: str
    user_id: str | None
    arn: str | None
    path: str | None
    created: str | None
    password_last_used: str | None


@dataclass(frozen=True)
class GroupSummary:
    """Summary information for an IAM group."""

    name: str
    group_id: str | None
    arn: str | None
    path: str | None
    created: str | None


@dataclass(frozen=True)
class RoleSummary:
    """Summary information for an IAM role."""

    name: str
    role_id: str | None
    arn: str | None
    path: str | None
    created: str | None
    description: str | None


@dataclass(frozen=True)
class PolicySummary:
    """Summary information for an IAM policy."""

    name: str
    policy_id: str | None
    arn: str | None
    scope: str | None
    attachment_count: int | None
    created: str | None
    updated: str | None
