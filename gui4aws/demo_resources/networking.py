"""Seed demo VPCs, subnets, security groups, and load balancers."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import tags

logger = logging.getLogger(__name__)


def seed_networking(ec2: Any, elbv2: Any) -> dict[str, list[str]]:
    """Seed core networking infrastructure including VPCs, subnets, and load balancers.

    Sets up a functional network environment with security groups and an Application
    Load Balancer (ALB) targeting an IP-based target group to illustrate how the
    GUI visualizes networking dependencies.
    """
    created: dict[str, list[str]] = {
        "vpcs": [],
        "subnets": [],
        "security_groups": [],
        "load_balancers": [],
        "target_groups": [],
    }

    vpc_id: str | None = None
    try:
        resp = ec2.create_vpc(
            CidrBlock="10.0.0.0/16",
            TagSpecifications=[
                {
                    "ResourceType": "vpc",
                    "Tags": tags({"Key": "Name", "Value": "demo-vpc"}),
                }
            ],
        )
        vpc_id = resp["Vpc"]["VpcId"]
        logger.info("created VPC %s", vpc_id)
        created["vpcs"].append(vpc_id)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("skipped VPC: %s", exc)

    subnet_ids: list[str] = []
    if vpc_id:
        for i, (cidr, az) in enumerate([("10.0.1.0/24", "us-east-1a"), ("10.0.2.0/24", "us-east-1b")]):
            name = f"demo-subnet-{i + 1}"
            try:
                resp = ec2.create_subnet(
                    VpcId=vpc_id,
                    CidrBlock=cidr,
                    AvailabilityZone=az,
                    TagSpecifications=[
                        {
                            "ResourceType": "subnet",
                            "Tags": tags({"Key": "Name", "Value": name}),
                        }
                    ],
                )
                subnet_id = resp["Subnet"]["SubnetId"]
                subnet_ids.append(subnet_id)
                logger.info("created subnet %s", subnet_id)
                created["subnets"].append(subnet_id)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped subnet %s: %s", name, exc)

    sg_id: str | None = None
    if vpc_id:
        try:
            resp = ec2.create_security_group(
                GroupName="demo-sg",
                Description="Demo security group for gui4aws",
                VpcId=vpc_id,
                TagSpecifications=[
                    {
                        "ResourceType": "security-group",
                        "Tags": tags({"Key": "Name", "Value": "demo-sg"}),
                    }
                ],
            )
            sg_id = resp["GroupId"]
            logger.info("created security group %s", sg_id)
            created["security_groups"].append(sg_id)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped security group: %s", exc)

    if subnet_ids:
        try:
            resp = elbv2.create_load_balancer(
                Name="demo-alb",
                Subnets=subnet_ids,
                SecurityGroups=[sg_id] if sg_id else [],
                Scheme="internet-facing",
                Type="application",
                Tags=tags({"Key": "Name", "Value": "demo-alb"}),
            )
            alb_arn = resp["LoadBalancers"][0]["LoadBalancerArn"]
            logger.info("created ALB %s", alb_arn)
            created["load_balancers"].append(alb_arn)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped ALB: %s", exc)

    if vpc_id:
        try:
            resp = elbv2.create_target_group(
                Name="demo-tg",
                Protocol="HTTP",
                Port=80,
                VpcId=vpc_id,
                TargetType="ip",
                HealthCheckPath="/health",
                Tags=tags({"Key": "Name", "Value": "demo-tg"}),
            )
            tg_arn = resp["TargetGroups"][0]["TargetGroupArn"]
            logger.info("created target group %s", tg_arn)
            created["target_groups"].append(tg_arn)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped target group: %s", exc)

    return created
