"""Seed a demo Route 53 hosted zone with a couple of record sets."""

from __future__ import annotations

import logging
import uuid
from typing import Any

logger = logging.getLogger(__name__)

_ZONE_NAME = "demo.internal."


def seed_route53(r53: Any) -> dict[str, list[str]]:
    """Seed a hosted zone plus a few record sets.

    Creates ``demo.internal.`` and adds an A record and a TXT record so the
    GUI has record-set data to browse. The zone comment carries the
    ``gui4aws:demo`` marker (Route 53 zones have no tags on creation).
    """
    created: dict[str, list[str]] = {"hosted_zones": [], "record_sets": []}

    zone_id: str | None = None
    try:
        resp = r53.create_hosted_zone(
            Name=_ZONE_NAME,
            CallerReference=f"gui4aws-demo-{uuid.uuid4()}",
            HostedZoneConfig={"Comment": "gui4aws:demo hosted zone"},
        )
        zone_id = resp["HostedZone"]["Id"].rsplit("/", 1)[-1]
        logger.info("created hosted zone %s (%s)", _ZONE_NAME, zone_id)
        created["hosted_zones"].append(zone_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("skipped hosted zone: %s", exc)

    if zone_id:
        changes: list[dict[str, Any]] = [
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": f"www.{_ZONE_NAME}",
                    "Type": "A",
                    "TTL": 300,
                    "ResourceRecords": [{"Value": "10.0.0.10"}],
                },
            },
            {
                "Action": "UPSERT",
                "ResourceRecordSet": {
                    "Name": _ZONE_NAME,
                    "Type": "TXT",
                    "TTL": 300,
                    "ResourceRecords": [{"Value": '"gui4aws-demo"'}],
                },
            },
        ]
        for change in changes:
            rrset = change["ResourceRecordSet"]
            label = f"{rrset['Name']} {rrset['Type']}"
            try:
                r53.change_resource_record_sets(
                    HostedZoneId=zone_id,
                    ChangeBatch={"Comment": "gui4aws:demo", "Changes": [change]},
                )
                logger.info("created record set %s", label)
                created["record_sets"].append(label)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped record set %s: %s", label, exc)

    return created
