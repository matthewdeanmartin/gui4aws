"""Route 53 action definitions.

Route 53 is a global service; there is no region scoping. Record sets are nested
inside a hosted zone, so the record-set actions use ``boto3_execute_fn`` to inject
the ``HostedZoneId`` and (for writes) build the ``ChangeBatch`` structure that the
single ``change_resource_record_sets`` API requires.
"""

from __future__ import annotations

import uuid
from collections.abc import Mapping
from typing import Any, cast

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.route53.views import (
    bare_zone_id,
    to_hosted_zone_summaries,
    to_record_set_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_HOSTED_ZONE",
    "DELETE_HOSTED_ZONE",
    "DELETE_RECORD_SET",
    "GET_HOSTED_ZONE",
    "LIST_HOSTED_ZONES",
    "LIST_RECORD_SETS",
    "UPSERT_RECORD_SET",
    "build_change_batch",
    "create_hosted_zone_params",
]

_RECORD_TYPES = ("A", "AAAA", "CNAME", "TXT", "MX", "NS", "SRV", "PTR")


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("true", "yes", "1")


def create_hosted_zone_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Build boto3 parameters for ``create_hosted_zone``.

    ``CallerReference`` must be unique per request, so a fresh uuid is generated.
    A ``VPC`` block is only included for private zones with a vpc id supplied.
    """
    params: dict[str, Any] = {
        "Name": inputs.get("name", "").strip(),
        "CallerReference": f"gui4aws-{uuid.uuid4()}",
    }
    config: dict[str, Any] = {}
    comment = inputs.get("comment", "").strip()
    if comment:
        config["Comment"] = comment
    private = _truthy(inputs.get("private", ""))
    if private:
        config["PrivateZone"] = True
    if config:
        params["HostedZoneConfig"] = config
    vpc_id = inputs.get("vpc_id", "").strip()
    if private and vpc_id:
        params["VPC"] = {
            "VPCRegion": inputs.get("vpc_region", "").strip() or "us-east-1",
            "VPCId": vpc_id,
        }
    return params


def _create_hosted_zone(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return cast("dict[str, Any]", client.create_hosted_zone(**create_hosted_zone_params(inputs)))


def _get_hosted_zone(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return cast("dict[str, Any]", client.get_hosted_zone(Id=bare_zone_id(inputs.get("zone_id", "").strip())))


def _delete_hosted_zone(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return cast("dict[str, Any]", client.delete_hosted_zone(Id=bare_zone_id(inputs.get("zone_id", "").strip())))


def _list_record_sets(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return cast(
        "dict[str, Any]",
        client.list_resource_record_sets(HostedZoneId=bare_zone_id(inputs.get("zone_id", "").strip())),
    )


def build_change_batch(inputs: Mapping[str, str], action: str) -> dict[str, Any]:
    """Build a Route 53 ``ChangeBatch`` for a single UPSERT/DELETE change.

    Values are taken one-per-line from the ``value`` input. The comment records
    that gui4aws made the change.
    """
    values = [line.strip() for line in inputs.get("value", "").splitlines() if line.strip()]
    record_set: dict[str, Any] = {
        "Name": inputs.get("record_name", "").strip(),
        "Type": inputs.get("record_type", "").strip(),
        "TTL": int(inputs.get("ttl", "300") or "300"),
        "ResourceRecords": [{"Value": v} for v in values],
    }
    return {
        "Comment": f"gui4aws {action.lower()}",
        "Changes": [{"Action": action, "ResourceRecordSet": record_set}],
    }


def _change_record_set(client: Any, inputs: Mapping[str, str], action: str) -> Mapping[str, Any]:
    return cast(
        "dict[str, Any]",
        client.change_resource_record_sets(
            HostedZoneId=bare_zone_id(inputs.get("zone_id", "").strip()),
            ChangeBatch=build_change_batch(inputs, action),
        ),
    )


def _upsert_record_set(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return _change_record_set(client, inputs, "UPSERT")


def _delete_record_set(client: Any, inputs: Mapping[str, str]) -> Mapping[str, Any]:
    return _change_record_set(client, inputs, "DELETE")


# ── Hosted zones ──────────────────────────────────────────────────────────────

LIST_HOSTED_ZONES = ActionDefinition(
    action_id="route53.list_hosted_zones",
    display_name="List hosted zones",
    service_id="route53",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="route53", command="list-hosted-zones"),
    boto3_template=Boto3Template(service="route53", operation="list_hosted_zones"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("zone_id", "name", "private", "record_count", "comment"),
        title="Route 53 Hosted Zones",
    ),
    iam_permissions=("route53:ListHostedZones",),
    description="List Route 53 hosted zones in this account.",
    view=to_hosted_zone_summaries,
)

GET_HOSTED_ZONE = ActionDefinition(
    action_id="route53.get_hosted_zone",
    display_name="Get hosted zone",
    service_id="route53",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="zone_id", label="Hosted zone ID", required=True),),
    cli_template=CliTemplate(service="route53", command="get-hosted-zone", arg_map={"zone_id": "id"}),
    boto3_template=Boto3Template(service="route53", operation="get_hosted_zone", param_map={"zone_id": "Id"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Hosted zone detail"),
    iam_permissions=("route53:GetHostedZone",),
    description="Get details for a specific hosted zone.",
    boto3_execute_fn=_get_hosted_zone,
)

CREATE_HOSTED_ZONE = ActionDefinition(
    action_id="route53.create_hosted_zone",
    display_name="Create hosted zone",
    service_id="route53",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="name",
            label="Domain name",
            required=True,
            help_text="Fully-qualified domain name, e.g. example.com",
        ),
        InputField(name="comment", label="Comment", required=False),
        InputField(
            name="private",
            label="Private zone",
            kind="bool",
            default="false",
            required=False,
            help_text="Private hosted zones require a VPC id below.",
        ),
        InputField(name="vpc_id", label="VPC ID (private only)", required=False),
        InputField(name="vpc_region", label="VPC region (private only)", required=False),
    ),
    cli_template=CliTemplate(service="route53", command="create-hosted-zone", arg_map={"name": "name"}),
    boto3_template=Boto3Template(service="route53", operation="create_hosted_zone", param_map={"name": "Name"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create hosted zone result"),
    iam_permissions=("route53:CreateHostedZone",),
    description="Create a new public or private hosted zone.",
    boto3_execute_fn=_create_hosted_zone,
    boto3_params_builder=create_hosted_zone_params,
    cache_refresh_nav_ids=("hosted_zones",),
)

DELETE_HOSTED_ZONE = ActionDefinition(
    action_id="route53.delete_hosted_zone",
    display_name="Delete hosted zone",
    service_id="route53",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="zone_id", label="Hosted zone ID", required=True),),
    cli_template=CliTemplate(service="route53", command="delete-hosted-zone", arg_map={"zone_id": "id"}),
    boto3_template=Boto3Template(service="route53", operation="delete_hosted_zone", param_map={"zone_id": "Id"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete hosted zone result"),
    iam_permissions=("route53:DeleteHostedZone",),
    description="Delete a hosted zone (must contain only the default SOA/NS records).",
    boto3_execute_fn=_delete_hosted_zone,
    cache_refresh_nav_ids=("hosted_zones",),
)

# ── Record sets ───────────────────────────────────────────────────────────────

LIST_RECORD_SETS = ActionDefinition(
    action_id="route53.list_record_sets",
    display_name="List record sets",
    service_id="route53",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(InputField(name="zone_id", label="Hosted zone ID", required=True),),
    cli_template=CliTemplate(
        service="route53", command="list-resource-record-sets", arg_map={"zone_id": "hosted-zone-id"}
    ),
    boto3_template=Boto3Template(
        service="route53", operation="list_resource_record_sets", param_map={"zone_id": "HostedZoneId"}
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "type", "ttl", "records", "alias_target"),
        title="Route 53 Record Sets",
    ),
    iam_permissions=("route53:ListResourceRecordSets",),
    description="List the record sets in a hosted zone.",
    view=to_record_set_summaries,
    boto3_execute_fn=_list_record_sets,
)

UPSERT_RECORD_SET = ActionDefinition(
    action_id="route53.upsert_record_set",
    display_name="Create/update record set",
    service_id="route53",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="zone_id", label="Hosted zone ID", required=True),
        InputField(name="record_name", label="Record name", required=True, help_text="e.g. www.example.com"),
        InputField(
            name="record_type",
            label="Type",
            kind="choice",
            choices=_RECORD_TYPES,
            default="A",
        ),
        InputField(name="ttl", label="TTL (seconds)", kind="int", default="300"),
        InputField(
            name="value",
            label="Value(s)",
            required=True,
            kind="multiline",
            help_text="One value per line, e.g. an IP for an A record.",
        ),
    ),
    cli_template=CliTemplate(
        service="route53", command="change-resource-record-sets", arg_map={"zone_id": "hosted-zone-id"}
    ),
    boto3_template=Boto3Template(
        service="route53", operation="change_resource_record_sets", param_map={"zone_id": "HostedZoneId"}
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Upsert record set result"),
    iam_permissions=("route53:ChangeResourceRecordSets",),
    description="Create or replace a record set (UPSERT) in a hosted zone.",
    boto3_execute_fn=_upsert_record_set,
    cache_refresh_nav_ids=("record_sets",),
)

DELETE_RECORD_SET = ActionDefinition(
    action_id="route53.delete_record_set",
    display_name="Delete record set",
    service_id="route53",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="zone_id", label="Hosted zone ID", required=True),
        InputField(name="record_name", label="Record name", required=True),
        InputField(
            name="record_type",
            label="Type",
            kind="choice",
            choices=_RECORD_TYPES,
            default="A",
        ),
        InputField(name="ttl", label="TTL (seconds)", kind="int", default="300"),
        InputField(
            name="value",
            label="Value(s)",
            required=True,
            kind="multiline",
            help_text="Must exactly match the existing record's value(s), one per line.",
        ),
    ),
    cli_template=CliTemplate(
        service="route53", command="change-resource-record-sets", arg_map={"zone_id": "hosted-zone-id"}
    ),
    boto3_template=Boto3Template(
        service="route53", operation="change_resource_record_sets", param_map={"zone_id": "HostedZoneId"}
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete record set result"),
    iam_permissions=("route53:ChangeResourceRecordSets",),
    description="Delete a record set. Name, type, TTL and values must match the existing record exactly.",
    boto3_execute_fn=_delete_record_set,
    cache_refresh_nav_ids=("record_sets",),
)


ALL_ACTIONS = (
    LIST_HOSTED_ZONES,
    GET_HOSTED_ZONE,
    CREATE_HOSTED_ZONE,
    DELETE_HOSTED_ZONE,
    LIST_RECORD_SETS,
    UPSERT_RECORD_SET,
    DELETE_RECORD_SET,
)
