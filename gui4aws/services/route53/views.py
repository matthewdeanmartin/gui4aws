"""Normalization functions for Route 53."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.route53.models import HostedZoneSummary, RecordSetSummary

__all__ = ["bare_zone_id", "to_hosted_zone_summaries", "to_record_set_summaries"]


def bare_zone_id(zone_id: str) -> str:
    """Strip the ``/hostedzone/`` prefix Route 53 returns on zone ids.

    Accepts either the prefixed form (``/hostedzone/ABC123``) or an already-bare
    id and always returns the bare id.
    """
    return zone_id.rsplit("/", 1)[-1] if zone_id else zone_id


def to_hosted_zone_summaries(response: Mapping[str, Any]) -> list[HostedZoneSummary]:
    """Convert a raw boto3 ListHostedZones response into HostedZoneSummary objects."""
    zones = response.get("HostedZones", []) or []
    results = []
    for z in zones:
        config = z.get("Config", {}) or {}
        results.append(
            HostedZoneSummary(
                zone_id=bare_zone_id(z.get("Id", "")),
                name=z.get("Name", ""),
                private=bool(config.get("PrivateZone", False)),
                record_count=z.get("ResourceRecordSetCount"),
                comment=config.get("Comment") or None,
            )
        )
    return results


def to_record_set_summaries(response: Mapping[str, Any]) -> list[RecordSetSummary]:
    """Convert a raw boto3 ListResourceRecordSets response into RecordSetSummary objects."""
    record_sets = response.get("ResourceRecordSets", []) or []
    results = []
    for rs in record_sets:
        values = [r.get("Value", "") for r in rs.get("ResourceRecords", []) or []]
        alias = rs.get("AliasTarget", {}) or {}
        results.append(
            RecordSetSummary(
                name=rs.get("Name", ""),
                type=rs.get("Type", ""),
                ttl=rs.get("TTL"),
                records=", ".join(values),
                alias_target=alias.get("DNSName") or None,
            )
        )
    return results
