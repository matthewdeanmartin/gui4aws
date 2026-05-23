"""ServiceDefinition for networking (VPC, subnets, security groups, ALB, target groups)."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition, SubAction
from gui4aws.services.networking.actions import (
    ALL_ACTIONS,
    DESCRIBE_LOAD_BALANCERS,
    DESCRIBE_SECURITY_GROUPS,
    DESCRIBE_SUBNETS,
    DESCRIBE_TARGET_GROUPS,
    DESCRIBE_VPCS,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="networking",
    display_name="Networking",
    boto3_service_name="ec2",
    cli_service_name="ec2",
    navigation_items=(
        NavigationItem(
            item_id="vpcs",
            display_name="VPCs",
            default_action_id=DESCRIBE_VPCS.action_id,
            sub_action=SubAction(
                action_id=DESCRIBE_SUBNETS.action_id,
                panel_label="Subnets",
                prefill={"vpc_id": "vpc_id"},
                columns=("subnet_id", "name", "cidr_block", "availability_zone", "available_ip_count", "state"),
            ),
        ),
        NavigationItem(
            item_id="subnets",
            display_name="Subnets",
            default_action_id=DESCRIBE_SUBNETS.action_id,
        ),
        NavigationItem(
            item_id="security_groups",
            display_name="Security Groups",
            default_action_id=DESCRIBE_SECURITY_GROUPS.action_id,
        ),
        NavigationItem(
            item_id="load_balancers",
            display_name="Load Balancers",
            default_action_id=DESCRIBE_LOAD_BALANCERS.action_id,
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_TARGET_GROUPS.action_id,
                    button_label="View Target Groups",
                    prefill={"load_balancer_arn": "arn"},
                ),
            ),
            sub_action=SubAction(
                action_id=DESCRIBE_TARGET_GROUPS.action_id,
                panel_label="Target Groups",
                prefill={"load_balancer_arn": "arn"},
                columns=("name", "protocol", "port", "target_type", "health_check_path"),
            ),
        ),
        NavigationItem(
            item_id="target_groups",
            display_name="Target Groups",
            default_action_id=DESCRIBE_TARGET_GROUPS.action_id,
        ),
    ),
    actions=ALL_ACTIONS,
)
