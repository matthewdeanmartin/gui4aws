"""Normalization functions for SES."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.ses.models import IdentitySummary, TemplateSummary

__all__ = ["to_identity_summaries", "to_template_summaries"]


def to_identity_summaries(response: Mapping[str, Any]) -> list[IdentitySummary]:
    identities = response.get("Identities", []) or []
    verification_attrs = response.get("VerificationAttributes", {}) or {}
    results = []
    for identity in identities:
        attrs = verification_attrs.get(identity, {})
        identity_type = "domain" if "." in identity and "@" not in identity else "email"
        results.append(
            IdentitySummary(
                identity=identity,
                identity_type=identity_type,
                verification_status=attrs.get("VerificationStatus") or None,
                dkim_enabled=bool(attrs.get("DkimEnabled", False)),
            )
        )
    return results


def to_template_summaries(response: Mapping[str, Any]) -> list[TemplateSummary]:
    templates = response.get("TemplatesMetadata", []) or []
    results = []
    for t in templates:
        created = t.get("CreatedTimestamp")
        results.append(
            TemplateSummary(
                name=t.get("Name", ""),
                created_timestamp=str(created)[:19] if created else None,
            )
        )
    return results
