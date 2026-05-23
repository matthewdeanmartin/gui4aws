"""Normalized networking summaries (VPC, subnets, security groups, ALB, target groups)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AlbSummary",
    "SecurityGroupSummary",
    "SubnetSummary",
    "TargetGroupSummary",
    "VpcSummary",
]


@dataclass(frozen=True)
class VpcSummary:
    vpc_id: str
    name: str | None
    cidr_block: str
    state: str
    is_default: bool


@dataclass(frozen=True)
class SubnetSummary:
    subnet_id: str
    name: str | None
    vpc_id: str
    cidr_block: str
    availability_zone: str
    available_ip_count: int
    state: str


@dataclass(frozen=True)
class SecurityGroupSummary:
    group_id: str
    group_name: str
    vpc_id: str | None
    description: str


@dataclass(frozen=True)
class AlbSummary:
    name: str
    dns_name: str | None
    scheme: str | None
    state: str | None
    vpc_id: str | None
    type: str | None
    arn: str | None


@dataclass(frozen=True)
class TargetGroupSummary:
    name: str
    protocol: str | None
    port: int | None
    vpc_id: str | None
    target_type: str | None
    health_check_path: str | None
    arn: str | None
