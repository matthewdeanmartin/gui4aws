"""Networking action definitions (VPC, subnets, security groups, ALB, target groups)."""

from __future__ import annotations

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.networking.views import (
    to_alb_summaries,
    to_security_group_summaries,
    to_subnet_summaries,
    to_target_group_summaries,
    to_vpc_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "DESCRIBE_LOAD_BALANCERS",
    "DESCRIBE_SECURITY_GROUPS",
    "DESCRIBE_SUBNETS",
    "DESCRIBE_TARGET_GROUPS",
    "DESCRIBE_VPCS",
]


DESCRIBE_VPCS = ActionDefinition(
    action_id="networking.describe_vpcs",
    display_name="Describe VPCs",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="describe-vpcs",
        arg_map={"vpc_id": "filters"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="describe_vpcs",
        param_map={"vpc_id": "VpcIds"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("vpc_id", "name", "cidr_block", "state", "is_default"),
        title="VPCs",
    ),
    iam_permissions=("ec2:DescribeVpcs",),
    description="List VPCs in the current region.",
    view=to_vpc_summaries,
)


DESCRIBE_SUBNETS = ActionDefinition(
    action_id="networking.describe_subnets",
    display_name="Describe subnets",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            required=False,
        ),
        InputField(
            name="subnet_id",
            label="Subnet ID (optional filter)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="describe-subnets",
        arg_map={"subnet_id": "subnet-ids"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="describe_subnets",
        param_map={"subnet_id": "SubnetIds"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("subnet_id", "name", "vpc_id", "cidr_block", "availability_zone", "available_ip_count", "state"),
        title="Subnets",
    ),
    iam_permissions=("ec2:DescribeSubnets",),
    description="List subnets, optionally filtered by VPC.",
    view=to_subnet_summaries,
)


DESCRIBE_SECURITY_GROUPS = ActionDefinition(
    action_id="networking.describe_security_groups",
    display_name="Describe security groups",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            required=False,
        ),
        InputField(
            name="group_id",
            label="Security group ID (optional filter)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="describe-security-groups",
        arg_map={"group_id": "group-ids"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="describe_security_groups",
        param_map={"group_id": "GroupIds"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("group_id", "group_name", "vpc_id", "description"),
        title="Security Groups",
    ),
    iam_permissions=("ec2:DescribeSecurityGroups",),
    description="List EC2 security groups in the current region.",
    view=to_security_group_summaries,
)


DESCRIBE_LOAD_BALANCERS = ActionDefinition(
    action_id="networking.describe_load_balancers",
    display_name="Describe load balancers",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="names",
            label="ALB names (comma-sep, optional)",
            kind="list",
            required=False,
        ),
        InputField(
            name="load_balancer_arns",
            label="ALB ARNs (comma-sep, optional)",
            kind="list",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="elbv2",
        command="describe-load-balancers",
        arg_map={"names": "names", "load_balancer_arns": "load-balancer-arns"},
    ),
    boto3_template=Boto3Template(
        service="elbv2",
        operation="describe_load_balancers",
        param_map={"names": "Names", "load_balancer_arns": "LoadBalancerArns"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "dns_name", "scheme", "state", "type", "vpc_id"),
        title="Application Load Balancers",
    ),
    iam_permissions=("elasticloadbalancing:DescribeLoadBalancers",),
    description="List ALBs (and NLBs) in the current region.",
    view=to_alb_summaries,
)


DESCRIBE_TARGET_GROUPS = ActionDefinition(
    action_id="networking.describe_target_groups",
    display_name="Describe target groups",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="load_balancer_arn",
            label="Load balancer ARN (optional filter)",
            required=False,
        ),
        InputField(
            name="target_group_arns",
            label="Target group ARNs (comma-sep, optional)",
            kind="list",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="elbv2",
        command="describe-target-groups",
        arg_map={
            "load_balancer_arn": "load-balancer-arn",
            "target_group_arns": "target-group-arns",
        },
    ),
    boto3_template=Boto3Template(
        service="elbv2",
        operation="describe_target_groups",
        param_map={
            "load_balancer_arn": "LoadBalancerArn",
            "target_group_arns": "TargetGroupArns",
        },
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "protocol", "port", "target_type", "health_check_path", "vpc_id"),
        title="Target Groups",
    ),
    iam_permissions=("elasticloadbalancing:DescribeTargetGroups",),
    description="List ELBv2 target groups, optionally filtered by load balancer.",
    view=to_target_group_summaries,
)


ALL_ACTIONS = (
    DESCRIBE_VPCS,
    DESCRIBE_SUBNETS,
    DESCRIBE_SECURITY_GROUPS,
    DESCRIBE_LOAD_BALANCERS,
    DESCRIBE_TARGET_GROUPS,
)
