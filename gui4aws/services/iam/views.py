"""Normalization functions for IAM."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.iam.models import GroupSummary, PolicySummary, RoleSummary, UserSummary

__all__ = ["to_group_summaries", "to_policy_summaries", "to_role_summaries", "to_user_summaries"]


def fmt(value: Any) -> str | None:
    """Format a datetime value as a string, truncated to seconds."""
    if value is None:
        return None
    return str(value)[:19]


def to_user_summaries(response: Mapping[str, Any]) -> list[UserSummary]:
    """Convert a raw boto3 ListUsers response into a list of UserSummary objects."""
    users = response.get("Users", []) or []
    return [
        UserSummary(
            name=u.get("UserName", ""),
            user_id=u.get("UserId") or None,
            arn=u.get("Arn") or None,
            path=u.get("Path") or None,
            created=fmt(u.get("CreateDate")),
            password_last_used=fmt(u.get("PasswordLastUsed")),
        )
        for u in users
    ]


def to_group_summaries(response: Mapping[str, Any]) -> list[GroupSummary]:
    """Convert a raw boto3 ListGroups response into a list of GroupSummary objects."""
    groups = response.get("Groups", []) or []
    return [
        GroupSummary(
            name=g.get("GroupName", ""),
            group_id=g.get("GroupId") or None,
            arn=g.get("Arn") or None,
            path=g.get("Path") or None,
            created=fmt(g.get("CreateDate")),
        )
        for g in groups
    ]


def to_role_summaries(response: Mapping[str, Any]) -> list[RoleSummary]:
    """Convert a raw boto3 ListRoles response into a list of RoleSummary objects."""
    roles = response.get("Roles", []) or []
    return [
        RoleSummary(
            name=r.get("RoleName", ""),
            role_id=r.get("RoleId") or None,
            arn=r.get("Arn") or None,
            path=r.get("Path") or None,
            created=fmt(r.get("CreateDate")),
            description=r.get("Description") or None,
        )
        for r in roles
    ]


def to_policy_summaries(response: Mapping[str, Any]) -> list[PolicySummary]:
    """Convert a raw boto3 ListPolicies response into a list of PolicySummary objects."""
    policies = response.get("Policies", []) or []
    return [
        PolicySummary(
            name=p.get("PolicyName", ""),
            policy_id=p.get("PolicyId") or None,
            arn=p.get("Arn") or None,
            scope=p.get("Scope") or None,
            attachment_count=p.get("AttachmentCount"),
            created=fmt(p.get("CreateDate")),
            updated=fmt(p.get("UpdateDate")),
        )
        for p in policies
    ]
