"""Normalized IAM summaries."""
from __future__ import annotations
from dataclasses import dataclass

__all__ = ["UserSummary", "GroupSummary", "RoleSummary", "PolicySummary"]

@dataclass(frozen=True)
class UserSummary:
    name: str
    user_id: str | None
    arn: str | None
    path: str | None
    created: str | None
    password_last_used: str | None

@dataclass(frozen=True)
class GroupSummary:
    name: str
    group_id: str | None
    arn: str | None
    path: str | None
    created: str | None

@dataclass(frozen=True)
class RoleSummary:
    name: str
    role_id: str | None
    arn: str | None
    path: str | None
    created: str | None
    description: str | None

@dataclass(frozen=True)
class PolicySummary:
    name: str
    policy_id: str | None
    arn: str | None
    scope: str | None
    attachment_count: int | None
    created: str | None
    updated: str | None
