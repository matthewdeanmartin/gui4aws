"""Moto-backed tests for Route 53 actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.route53.actions import (
    CREATE_HOSTED_ZONE,
    DELETE_HOSTED_ZONE,
    DELETE_RECORD_SET,
    GET_HOSTED_ZONE,
    LIST_HOSTED_ZONES,
    LIST_RECORD_SETS,
    UPSERT_RECORD_SET,
    build_change_batch,
    create_hosted_zone_params,
)
from gui4aws.services.route53.views import (
    bare_zone_id,
    to_hosted_zone_summaries,
    to_record_set_summaries,
)


def test_bare_zone_id() -> None:
    assert bare_zone_id("/hostedzone/ABC123") == "ABC123"
    assert bare_zone_id("ABC123") == "ABC123"
    assert bare_zone_id("") == ""


def test_create_hosted_zone_params_public() -> None:
    params = create_hosted_zone_params({"name": "example.com", "comment": "hi"})
    assert params["Name"] == "example.com"
    assert params["CallerReference"].startswith("gui4aws-")
    assert params["HostedZoneConfig"]["Comment"] == "hi"
    assert "VPC" not in params


def test_create_hosted_zone_params_private() -> None:
    params = create_hosted_zone_params(
        {"name": "internal.example.com", "private": "true", "vpc_id": "vpc-123", "vpc_region": "us-west-2"}
    )
    assert params["HostedZoneConfig"]["PrivateZone"] is True
    assert params["VPC"] == {"VPCRegion": "us-west-2", "VPCId": "vpc-123"}


def test_build_change_batch() -> None:
    batch = build_change_batch(
        {"record_name": "www.example.com", "record_type": "A", "ttl": "60", "value": "1.2.3.4\n5.6.7.8"},
        "UPSERT",
    )
    change = batch["Changes"][0]
    assert change["Action"] == "UPSERT"
    rrset = change["ResourceRecordSet"]
    assert rrset["Name"] == "www.example.com"
    assert rrset["TTL"] == 60
    assert rrset["ResourceRecords"] == [{"Value": "1.2.3.4"}, {"Value": "5.6.7.8"}]


def test_hosted_zone_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create
    result = context.execute(CREATE_HOSTED_ZONE, inputs={"name": "example.com", "comment": "demo"})
    assert isinstance(result, Boto3Result)
    zone_id = result.response["HostedZone"]["Id"].rsplit("/", 1)[-1]

    # List
    list_result = context.execute(LIST_HOSTED_ZONES, inputs={})
    summaries = to_hosted_zone_summaries(list_result.response)
    assert any(s.name == "example.com." for s in summaries)
    assert any(s.zone_id == zone_id for s in summaries)

    # Get
    get_result = context.execute(GET_HOSTED_ZONE, inputs={"zone_id": zone_id})
    assert isinstance(get_result, Boto3Result)
    assert get_result.response["HostedZone"]["Name"] == "example.com."

    # Get accepts the prefixed form too.
    get_prefixed = context.execute(GET_HOSTED_ZONE, inputs={"zone_id": f"/hostedzone/{zone_id}"})
    assert isinstance(get_prefixed, Boto3Result)


def test_record_set_actions(mock_aws_env: None) -> None:
    r53 = boto3.client("route53", region_name="us-east-1")
    zone_id = r53.create_hosted_zone(Name="records.test.", CallerReference="setup-1")["HostedZone"]["Id"].rsplit(
        "/", 1
    )[-1]

    context = AppContext(region_name="us-east-1")

    # Upsert an A record.
    upsert = context.execute(
        UPSERT_RECORD_SET,
        inputs={
            "zone_id": zone_id,
            "record_name": "www.records.test.",
            "record_type": "A",
            "ttl": "300",
            "value": "1.2.3.4",
        },
    )
    assert isinstance(upsert, Boto3Result)

    # List and assert present.
    list_result = context.execute(LIST_RECORD_SETS, inputs={"zone_id": zone_id})
    summaries = to_record_set_summaries(list_result.response)
    a_records = [s for s in summaries if s.type == "A" and s.name == "www.records.test."]
    assert a_records and a_records[0].records == "1.2.3.4"

    # Delete it.
    delete = context.execute(
        DELETE_RECORD_SET,
        inputs={
            "zone_id": zone_id,
            "record_name": "www.records.test.",
            "record_type": "A",
            "ttl": "300",
            "value": "1.2.3.4",
        },
    )
    assert isinstance(delete, Boto3Result)

    # Gone. (Drop the cached pre-delete list first, as the GUI does via
    # DELETE_RECORD_SET.cache_refresh_nav_ids.)
    context.invalidate_read_cache("route53")
    after = context.execute(LIST_RECORD_SETS, inputs={"zone_id": zone_id})
    after_summaries = to_record_set_summaries(after.response)
    assert not any(s.name == "www.records.test." and s.type == "A" for s in after_summaries)

    # Clean up the zone (only SOA/NS remain).
    del_zone = context.execute(DELETE_HOSTED_ZONE, inputs={"zone_id": zone_id})
    assert isinstance(del_zone, Boto3Result)
