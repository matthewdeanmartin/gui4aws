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


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _fmt_date(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)[:19]


def to_key_summaries(response: Mapping[str, Any]) -> list[KmsKeySummary]:
    keys = response.get("Keys", []) or []
    summaries: list[KmsKeySummary] = []
    for k in keys:
        meta = k.get("KeyMetadata") or k
        summaries.append(
            KmsKeySummary(
                key_id=str(meta.get("KeyId", k.get("KeyId", ""))),
                key_arn=_optional_str(meta.get("Arn", k.get("KeyArn"))),
                description=_optional_str(meta.get("Description")),
                key_state=_optional_str(meta.get("KeyState")),
                key_usage=_optional_str(meta.get("KeyUsage")),
                key_spec=_optional_str(meta.get("KeySpec")),
                origin=_optional_str(meta.get("Origin")),
                enabled=bool(meta.get("Enabled", False)),
                creation_date=_fmt_date(meta.get("CreationDate")),
            )
        )
    # describe_key returns a single key under KeyMetadata
    if "KeyMetadata" in response:
        meta = response["KeyMetadata"]
        summaries.append(
            KmsKeySummary(
                key_id=str(meta.get("KeyId", "")),
                key_arn=_optional_str(meta.get("Arn")),
                description=_optional_str(meta.get("Description")),
                key_state=_optional_str(meta.get("KeyState")),
                key_usage=_optional_str(meta.get("KeyUsage")),
                key_spec=_optional_str(meta.get("KeySpec")),
                origin=_optional_str(meta.get("Origin")),
                enabled=bool(meta.get("Enabled", False)),
                creation_date=_fmt_date(meta.get("CreationDate")),
            )
        )
    return summaries


def to_alias_summaries(response: Mapping[str, Any]) -> list[KmsAliasSummary]:
    aliases = response.get("Aliases", []) or []
    summaries: list[KmsAliasSummary] = []
    for a in aliases:
        summaries.append(
            KmsAliasSummary(
                alias_name=str(a.get("AliasName", "")),
                target_key_id=_optional_str(a.get("TargetKeyId")),
                alias_arn=_optional_str(a.get("AliasArn")),
                creation_date=_fmt_date(a.get("CreationDate")),
                last_updated_date=_fmt_date(a.get("LastUpdatedDate")),
            )
        )
    return summaries


def to_grant_summaries(response: Mapping[str, Any]) -> list[KmsGrantSummary]:
    grants = response.get("Grants", []) or []
    summaries: list[KmsGrantSummary] = []
    for g in grants:
        ops = g.get("Operations") or []
        summaries.append(
            KmsGrantSummary(
                grant_id=str(g.get("GrantId", "")),
                key_id=_optional_str(g.get("KeyId")),
                name=_optional_str(g.get("Name")),
                grantee_principal=_optional_str(g.get("GranteePrincipal")),
                operations=", ".join(ops),
                creation_date=_fmt_date(g.get("CreationDate")),
            )
        )
    return summaries
