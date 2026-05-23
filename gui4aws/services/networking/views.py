"""Normalization functions: raw boto3 response -> list[Summary] for networking resources."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from gui4aws.services.networking.models import (
    AlbSummary,
    SecurityGroupSummary,
    SubnetSummary,
    TargetGroupSummary,
    VpcSummary,
)

__all__ = [
    "to_alb_summaries",
    "to_security_group_summaries",
    "to_subnet_summaries",
    "to_target_group_summaries",
    "to_vpc_summaries",
]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _name_from_tags(tags: list[dict[str, str]]) -> str | None:
    for tag in tags or []:
        if tag.get("Key") == "Name":
            return tag.get("Value") or None
    return None


def to_vpc_summaries(response: Mapping[str, Any]) -> list[VpcSummary]:
    vpcs = response.get("Vpcs", []) or []
    summaries: list[VpcSummary] = []
    for v in vpcs:
        summaries.append(
            VpcSummary(
                vpc_id=str(v.get("VpcId", "")),
                name=_name_from_tags(v.get("Tags", [])),
                cidr_block=str(v.get("CidrBlock", "")),
                state=str(v.get("State", "")),
                is_default=bool(v.get("IsDefault", False)),
            )
        )
    return summaries


def to_subnet_summaries(response: Mapping[str, Any]) -> list[SubnetSummary]:
    subnets = response.get("Subnets", []) or []
    summaries: list[SubnetSummary] = []
    for s in subnets:
        summaries.append(
            SubnetSummary(
                subnet_id=str(s.get("SubnetId", "")),
                name=_name_from_tags(s.get("Tags", [])),
                vpc_id=str(s.get("VpcId", "")),
                cidr_block=str(s.get("CidrBlock", "")),
                availability_zone=str(s.get("AvailabilityZone", "")),
                available_ip_count=int(s.get("AvailableIpAddressCount", 0)),
                state=str(s.get("State", "")),
            )
        )
    return summaries


def to_security_group_summaries(response: Mapping[str, Any]) -> list[SecurityGroupSummary]:
    groups = response.get("SecurityGroups", []) or []
    summaries: list[SecurityGroupSummary] = []
    for g in groups:
        summaries.append(
            SecurityGroupSummary(
                group_id=str(g.get("GroupId", "")),
                group_name=str(g.get("GroupName", "")),
                vpc_id=_optional_str(g.get("VpcId")),
                description=str(g.get("Description", "")),
            )
        )
    return summaries


def to_alb_summaries(response: Mapping[str, Any]) -> list[AlbSummary]:
    lbs = response.get("LoadBalancers", []) or []
    summaries: list[AlbSummary] = []
    for lb in lbs:
        state = lb.get("State", {})
        summaries.append(
            AlbSummary(
                name=str(lb.get("LoadBalancerName", "")),
                dns_name=_optional_str(lb.get("DNSName")),
                scheme=_optional_str(lb.get("Scheme")),
                state=_optional_str(state.get("Code")) if isinstance(state, dict) else None,
                vpc_id=_optional_str(lb.get("VpcId")),
                type=_optional_str(lb.get("Type")),
                arn=_optional_str(lb.get("LoadBalancerArn")),
            )
        )
    return summaries


def to_target_group_summaries(response: Mapping[str, Any]) -> list[TargetGroupSummary]:
    tgs = response.get("TargetGroups", []) or []
    summaries: list[TargetGroupSummary] = []
    for tg in tgs:
        port = tg.get("Port")
        summaries.append(
            TargetGroupSummary(
                name=str(tg.get("TargetGroupName", "")),
                protocol=_optional_str(tg.get("Protocol")),
                port=int(port) if port is not None else None,
                vpc_id=_optional_str(tg.get("VpcId")),
                target_type=_optional_str(tg.get("TargetType")),
                health_check_path=_optional_str(tg.get("HealthCheckPath")),
                arn=_optional_str(tg.get("TargetGroupArn")),
            )
        )
    return summaries
