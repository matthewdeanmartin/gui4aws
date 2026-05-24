"""Normalized networking summaries (VPC, subnets, security groups, ALB, target groups)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = [
    "AlbSummary",
    "SecurityGroupRuleSummary",
    "SecurityGroupSummary",
    "SubnetSummary",
    "TargetGroupSummary",
    "VpcSummary",
]


@dataclass(frozen=True)
class VpcSummary:
    """Summary information for an Amazon VPC."""

    vpc_id: str
    name: str | None
    cidr_block: str
    state: str
    is_default: bool


@dataclass(frozen=True)
class SubnetSummary:
    """Summary information for a VPC subnet."""

    subnet_id: str
    name: str | None
    vpc_id: str
    cidr_block: str
    availability_zone: str
    available_ip_count: int
    state: str


@dataclass(frozen=True)
class SecurityGroupSummary:
    """Summary information for a VPC security group."""

    group_id: str
    group_name: str
    vpc_id: str | None
    description: str


@dataclass(frozen=True)
class SecurityGroupRuleSummary:
    """Summary information for a single security group rule."""

    rule_id: str
    direction: str  # "inbound" or "outbound"
    protocol: str
    from_port: str
    to_port: str
    cidr: str
    description: str | None


@dataclass(frozen=True)
class AlbSummary:
    """Summary information for an Application Load Balancer (ALB)."""

    name: str
    dns_name: str | None
    scheme: str | None
    state: str | None
    vpc_id: str | None
    type: str | None
    arn: str | None


@dataclass(frozen=True)
class TargetGroupSummary:
    """Summary information for an ELB target group."""

    name: str
    protocol: str | None
    port: int | None
    vpc_id: str | None
    target_type: str | None
    health_check_path: str | None
    arn: str | None
