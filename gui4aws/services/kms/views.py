"""Normalization functions: raw boto3 response -> list[Summary] for KMS."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.kms.models import KmsAliasSummary, KmsGrantSummary, KmsKeySummary

__all__ = [
    "to_alias_summaries",
    "to_grant_summaries",
    "to_key_summaries",
]


def optional_str(value: Any) -> str | None:
    """Convert a value to a string, returning None if the result is empty or the input was None."""
    if value is None:
        return None
    text = str(value)
    return text or None


def fmt_date(value: Any) -> str | None:
    """Format a datetime value as a string, truncated to seconds."""
    if value is None:
        return None
    return str(value)[:19]


def to_key_summaries(response: Mapping[str, Any]) -> list[KmsKeySummary]:
    """Convert a raw boto3 KMS key response into a list of KmsKeySummary objects."""
    keys = response.get("Keys", []) or []
    summaries: list[KmsKeySummary] = []
    for k in keys:
        meta = k.get("KeyMetadata") or k
        summaries.append(
            KmsKeySummary(
                key_id=str(meta.get("KeyId", k.get("KeyId", ""))),
                key_arn=optional_str(meta.get("Arn", k.get("KeyArn"))),
                description=optional_str(meta.get("Description")),
                key_state=optional_str(meta.get("KeyState")),
                key_usage=optional_str(meta.get("KeyUsage")),
                key_spec=optional_str(meta.get("KeySpec")),
                origin=optional_str(meta.get("Origin")),
                enabled=bool(meta.get("Enabled", False)),
                creation_date=fmt_date(meta.get("CreationDate")),
            )
        )
    # describe_key returns a single key under KeyMetadata
    if "KeyMetadata" in response:
        meta = response["KeyMetadata"]
        summaries.append(
            KmsKeySummary(
                key_id=str(meta.get("KeyId", "")),
                key_arn=optional_str(meta.get("Arn")),
                description=optional_str(meta.get("Description")),
                key_state=optional_str(meta.get("KeyState")),
                key_usage=optional_str(meta.get("KeyUsage")),
                key_spec=optional_str(meta.get("KeySpec")),
                origin=optional_str(meta.get("Origin")),
                enabled=bool(meta.get("Enabled", False)),
                creation_date=fmt_date(meta.get("CreationDate")),
            )
        )
    return summaries


def to_alias_summaries(response: Mapping[str, Any]) -> list[KmsAliasSummary]:
    """Convert a raw boto3 KMS alias response into a list of KmsAliasSummary objects."""
    aliases = response.get("Aliases", []) or []
    summaries: list[KmsAliasSummary] = []
    for a in aliases:
        summaries.append(
            KmsAliasSummary(
                alias_name=str(a.get("AliasName", "")),
                target_key_id=optional_str(a.get("TargetKeyId")),
                alias_arn=optional_str(a.get("AliasArn")),
                creation_date=fmt_date(a.get("CreationDate")),
                last_updated_date=fmt_date(a.get("LastUpdatedDate")),
            )
        )
    return summaries


def to_grant_summaries(response: Mapping[str, Any]) -> list[KmsGrantSummary]:
    """Convert a raw boto3 KMS grant response into a list of KmsGrantSummary objects."""
    grants = response.get("Grants", []) or []
    summaries: list[KmsGrantSummary] = []
    for g in grants:
        ops = g.get("Operations") or []
        summaries.append(
            KmsGrantSummary(
                grant_id=str(g.get("GrantId", "")),
                key_id=optional_str(g.get("KeyId")),
                name=optional_str(g.get("Name")),
                grantee_principal=optional_str(g.get("GranteePrincipal")),
                operations=", ".join(ops),
                creation_date=fmt_date(g.get("CreationDate")),
            )
        )
    return summaries
