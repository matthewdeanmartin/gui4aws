"""ServiceDefinition for networking (VPC, subnets, security groups, ALB, target groups)."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition, SubAction
from gui4aws.services.networking.actions import (
    ALL_ACTIONS,
    CREATE_SECURITY_GROUP,
    CREATE_SUBNET,
    CREATE_VPC,
    DELETE_SECURITY_GROUP,
    DELETE_SUBNET,
    DELETE_VPC,
    DESCRIBE_LOAD_BALANCERS,
    DESCRIBE_SECURITY_GROUP_RULES,
    DESCRIBE_SECURITY_GROUPS,
    DESCRIBE_SUBNETS,
    DESCRIBE_TARGET_GROUPS,
    DESCRIBE_VPCS,
    MODIFY_SUBNET_ATTRIBUTE,
    MODIFY_VPC_ATTRIBUTE,
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
            row_actions=(
                RowAction(
                    action_id=CREATE_VPC.action_id,
                    button_label="Create VPC",
                    prefill={},
                ),
                RowAction(
                    action_id=MODIFY_VPC_ATTRIBUTE.action_id,
                    button_label="Modify",
                    prefill={"vpc_id": "vpc_id"},
                ),
                RowAction(
                    action_id=DELETE_VPC.action_id,
                    button_label="Delete",
                    prefill={"vpc_id": "vpc_id"},
                ),
            ),
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
            row_actions=(
                RowAction(
                    action_id=CREATE_SUBNET.action_id,
                    button_label="Create Subnet",
                    prefill={"vpc_id": "vpc_id"},
                ),
                RowAction(
                    action_id=MODIFY_SUBNET_ATTRIBUTE.action_id,
                    button_label="Modify",
                    prefill={"subnet_id": "subnet_id"},
                ),
                RowAction(
                    action_id=DELETE_SUBNET.action_id,
                    button_label="Delete",
                    prefill={"subnet_id": "subnet_id"},
                ),
            ),
        ),
        NavigationItem(
            item_id="security_groups",
            display_name="Security Groups",
            default_action_id=DESCRIBE_SECURITY_GROUPS.action_id,
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_SECURITY_GROUP_RULES.action_id,
                    button_label="View Rules",
                    prefill={"group_id": "group_id"},
                ),
                RowAction(
                    action_id=CREATE_SECURITY_GROUP.action_id,
                    button_label="Create SG",
                    prefill={"vpc_id": "vpc_id"},
                ),
                RowAction(
                    action_id=DELETE_SECURITY_GROUP.action_id,
                    button_label="Delete",
                    prefill={"group_id": "group_id"},
                ),
            ),
            sub_action=SubAction(
                action_id=DESCRIBE_SECURITY_GROUP_RULES.action_id,
                panel_label="Rules",
                prefill={"group_id": "group_id"},
                columns=("direction", "protocol", "from_port", "to_port", "cidr", "description"),
            ),
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
