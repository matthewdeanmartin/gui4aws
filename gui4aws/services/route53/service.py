"""ServiceDefinition for Route 53."""

from __future__ import annotations

from gui4aws.models import (
    EagerChoiceSource,
    InputField,
    NavigationItem,
    RowAction,
    ServiceDefinition,
)
from gui4aws.services.route53.actions import (
    ALL_ACTIONS,
    CREATE_HOSTED_ZONE,
    DELETE_HOSTED_ZONE,
    DELETE_RECORD_SET,
    GET_HOSTED_ZONE,
    LIST_HOSTED_ZONES,
    LIST_RECORD_SETS,
    UPSERT_RECORD_SET,
)

__all__ = ["SERVICE"]


_ZONES_SOURCE = EagerChoiceSource(
    action_id=LIST_HOSTED_ZONES.action_id,
    jmespath="HostedZones[].Id",
)


SERVICE = ServiceDefinition(
    service_id="route53",
    display_name="Route 53",
    boto3_service_name="route53",
    cli_service_name="route53",
    navigation_items=(
        # ── Hosted Zones ──────────────────────────────────────────────────────
        NavigationItem(
            item_id="hosted_zones",
            display_name="Hosted Zones",
            default_action_id=LIST_HOSTED_ZONES.action_id,
            row_actions=(
                RowAction(
                    action_id=GET_HOSTED_ZONE.action_id,
                    button_label="Get Zone",
                    prefill={"zone_id": "zone_id"},
                ),
                RowAction(
                    action_id=LIST_RECORD_SETS.action_id,
                    button_label="List Records",
                    prefill={"zone_id": "zone_id"},
                ),
                RowAction(
                    action_id=CREATE_HOSTED_ZONE.action_id,
                    button_label="Create Zone",
                    prefill={},
                ),
                RowAction(
                    action_id=UPSERT_RECORD_SET.action_id,
                    button_label="Add Record",
                    prefill={"zone_id": "zone_id"},
                ),
                RowAction(
                    action_id=DELETE_HOSTED_ZONE.action_id,
                    button_label="Delete Zone",
                    prefill={"zone_id": "zone_id"},
                ),
            ),
        ),
        # ── Record Sets ───────────────────────────────────────────────────────
        NavigationItem(
            item_id="record_sets",
            display_name="Record Sets",
            default_action_id=LIST_RECORD_SETS.action_id,
            filter_fields=(
                InputField(
                    name="zone_id",
                    label="Hosted zone",
                    kind="choice",
                    required=True,
                    help_text="Pick a hosted zone to list its record sets.",
                ),
            ),
            eager_choices={"zone_id": _ZONES_SOURCE},
            row_actions=(
                RowAction(
                    action_id=UPSERT_RECORD_SET.action_id,
                    button_label="Upsert Record",
                    prefill={
                        "zone_id": "zone_id",
                        "record_name": "name",
                        "record_type": "type",
                        "ttl": "ttl",
                        "value": "records",
                    },
                ),
                RowAction(
                    action_id=DELETE_RECORD_SET.action_id,
                    button_label="Delete Record",
                    prefill={
                        "zone_id": "zone_id",
                        "record_name": "name",
                        "record_type": "type",
                        "ttl": "ttl",
                        "value": "records",
                    },
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
