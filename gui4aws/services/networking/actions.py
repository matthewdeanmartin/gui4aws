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
    to_security_group_rule_summaries,
    to_security_group_summaries,
    to_subnet_summaries,
    to_target_group_summaries,
    to_vpc_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_SECURITY_GROUP",
    "CREATE_SUBNET",
    "CREATE_VPC",
    "DELETE_SECURITY_GROUP",
    "DELETE_SUBNET",
    "DELETE_VPC",
    "DESCRIBE_LOAD_BALANCERS",
    "DESCRIBE_SECURITY_GROUP_RULES",
    "DESCRIBE_SECURITY_GROUPS",
    "DESCRIBE_SUBNETS",
    "DESCRIBE_TARGET_GROUPS",
    "DESCRIBE_VPCS",
    "MODIFY_SUBNET_ATTRIBUTE",
    "MODIFY_VPC_ATTRIBUTE",
]


# ── VPCs ──────────────────────────────────────────────────────────────────────

DESCRIBE_VPCS = ActionDefinition(
    action_id="networking.describe_vpcs",
    display_name="Describe VPCs",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            kind="list",
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

CREATE_VPC = ActionDefinition(
    action_id="networking.create_vpc",
    display_name="Create VPC",
    service_id="networking",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="cidr_block",
            label="CIDR block",
            required=True,
            default="10.0.0.0/16",
            help_text="e.g. 10.0.0.0/16",
        ),
        InputField(name="name", label="Name tag", required=False),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="create-vpc",
        arg_map={"cidr_block": "cidr-block"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="create_vpc",
        param_map={"cidr_block": "CidrBlock"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create VPC result"),
    iam_permissions=("ec2:CreateVpc",),
    description="Create a new VPC with the given CIDR block.",
    cache_refresh_nav_ids=("vpcs",),
)

DELETE_VPC = ActionDefinition(
    action_id="networking.delete_vpc",
    display_name="Delete VPC",
    service_id="networking",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID",
            required=True,
            help_text="The VPC must have no subnets, IGWs, or security groups attached.",
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="delete-vpc",
        arg_map={"vpc_id": "vpc-id"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="delete_vpc",
        param_map={"vpc_id": "VpcId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete VPC result"),
    iam_permissions=("ec2:DeleteVpc",),
    description="Delete a VPC. The VPC must be empty (no subnets, gateways, etc.).",
    cache_refresh_nav_ids=("vpcs",),
)

MODIFY_VPC_ATTRIBUTE = ActionDefinition(
    action_id="networking.modify_vpc_attribute",
    display_name="Modify VPC attribute",
    service_id="networking",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="vpc_id", label="VPC ID", required=True),
        InputField(
            name="enable_dns_support",
            label="Enable DNS support",
            kind="bool",
            required=False,
            help_text="Controls whether DNS resolution via the Amazon DNS server is enabled.",
        ),
        InputField(
            name="enable_dns_hostnames",
            label="Enable DNS hostnames",
            kind="bool",
            required=False,
            help_text="Controls whether instances launched in the VPC receive public DNS hostnames.",
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="modify-vpc-attribute",
        arg_map={"vpc_id": "vpc-id", "enable_dns_support": "enable-dns-support", "enable_dns_hostnames": "enable-dns-hostnames"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="modify_vpc_attribute",
        param_map={"vpc_id": "VpcId", "enable_dns_support": "EnableDnsSupport", "enable_dns_hostnames": "EnableDnsHostnames"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Modify VPC result"),
    iam_permissions=("ec2:ModifyVpcAttribute",),
    description="Enable or disable DNS support / hostnames for a VPC.",
)


# ── Subnets ───────────────────────────────────────────────────────────────────

DESCRIBE_SUBNETS = ActionDefinition(
    action_id="networking.describe_subnets",
    display_name="Describe subnets",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            kind="list",
            required=False,
        ),
        InputField(
            name="subnet_id",
            label="Subnet ID (optional filter)",
            kind="list",
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

CREATE_SUBNET = ActionDefinition(
    action_id="networking.create_subnet",
    display_name="Create subnet",
    service_id="networking",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="vpc_id", label="VPC ID", required=True),
        InputField(
            name="cidr_block",
            label="CIDR block",
            required=True,
            help_text="Must be within the VPC CIDR, e.g. 10.0.1.0/24",
        ),
        InputField(
            name="availability_zone",
            label="Availability zone (optional)",
            required=False,
            help_text="e.g. us-east-1a. Leave blank to let AWS choose.",
        ),
        InputField(name="name", label="Name tag", required=False),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="create-subnet",
        arg_map={"vpc_id": "vpc-id", "cidr_block": "cidr-block", "availability_zone": "availability-zone"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="create_subnet",
        param_map={"vpc_id": "VpcId", "cidr_block": "CidrBlock", "availability_zone": "AvailabilityZone"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create subnet result"),
    iam_permissions=("ec2:CreateSubnet",),
    description="Create a subnet within a VPC.",
    cache_refresh_nav_ids=("subnets",),
)

DELETE_SUBNET = ActionDefinition(
    action_id="networking.delete_subnet",
    display_name="Delete subnet",
    service_id="networking",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="subnet_id",
            label="Subnet ID",
            required=True,
            help_text="The subnet must have no running instances.",
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="delete-subnet",
        arg_map={"subnet_id": "subnet-id"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="delete_subnet",
        param_map={"subnet_id": "SubnetId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete subnet result"),
    iam_permissions=("ec2:DeleteSubnet",),
    description="Delete a subnet.",
    cache_refresh_nav_ids=("subnets",),
)

MODIFY_SUBNET_ATTRIBUTE = ActionDefinition(
    action_id="networking.modify_subnet_attribute",
    display_name="Modify subnet attribute",
    service_id="networking",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="subnet_id", label="Subnet ID", required=True),
        InputField(
            name="map_public_ip_on_launch",
            label="Auto-assign public IP on launch",
            kind="bool",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="modify-subnet-attribute",
        arg_map={"subnet_id": "subnet-id", "map_public_ip_on_launch": "map-public-ip-on-launch"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="modify_subnet_attribute",
        param_map={"subnet_id": "SubnetId", "map_public_ip_on_launch": "MapPublicIpOnLaunch"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Modify subnet result"),
    iam_permissions=("ec2:ModifySubnetAttribute",),
    description="Toggle auto-assign public IP on launch for a subnet.",
)


# ── Security groups ───────────────────────────────────────────────────────────

DESCRIBE_SECURITY_GROUPS = ActionDefinition(
    action_id="networking.describe_security_groups",
    display_name="Describe security groups",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="vpc_id",
            label="VPC ID (optional filter)",
            kind="list",
            required=False,
        ),
        InputField(
            name="group_id",
            label="Security group ID (optional filter)",
            kind="list",
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

DESCRIBE_SECURITY_GROUP_RULES = ActionDefinition(
    action_id="networking.describe_security_group_rules",
    display_name="View security group rules",
    service_id="networking",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="group_id", label="Security group ID", kind="list", required=True),
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
        columns=("direction", "protocol", "from_port", "to_port", "cidr", "description"),
        title="Security Group Rules",
    ),
    iam_permissions=("ec2:DescribeSecurityGroups",),
    description="Show inbound and outbound rules for a security group.",
    view=to_security_group_rule_summaries,
)

CREATE_SECURITY_GROUP = ActionDefinition(
    action_id="networking.create_security_group",
    display_name="Create security group",
    service_id="networking",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="group_name", label="Group name", required=True),
        InputField(name="description", label="Description", required=True),
        InputField(name="vpc_id", label="VPC ID", required=True),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="create-security-group",
        arg_map={"group_name": "group-name", "description": "description", "vpc_id": "vpc-id"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="create_security_group",
        param_map={"group_name": "GroupName", "description": "Description", "vpc_id": "VpcId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create security group result"),
    iam_permissions=("ec2:CreateSecurityGroup",),
    description="Create a new security group in a VPC.",
    cache_refresh_nav_ids=("security_groups",),
)

DELETE_SECURITY_GROUP = ActionDefinition(
    action_id="networking.delete_security_group",
    display_name="Delete security group",
    service_id="networking",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="group_id",
            label="Security group ID",
            required=True,
            help_text="The group must not be referenced by any other security group rules.",
        ),
    ),
    cli_template=CliTemplate(
        service="ec2",
        command="delete-security-group",
        arg_map={"group_id": "group-id"},
    ),
    boto3_template=Boto3Template(
        service="ec2",
        operation="delete_security_group",
        param_map={"group_id": "GroupId"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete security group result"),
    iam_permissions=("ec2:DeleteSecurityGroup",),
    description="Delete a security group.",
    cache_refresh_nav_ids=("security_groups",),
)


# ── Load balancers / target groups ────────────────────────────────────────────

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
    CREATE_VPC,
    DELETE_VPC,
    MODIFY_VPC_ATTRIBUTE,
    DESCRIBE_SUBNETS,
    CREATE_SUBNET,
    DELETE_SUBNET,
    MODIFY_SUBNET_ATTRIBUTE,
    DESCRIBE_SECURITY_GROUPS,
    DESCRIBE_SECURITY_GROUP_RULES,
    CREATE_SECURITY_GROUP,
    DELETE_SECURITY_GROUP,
    DESCRIBE_LOAD_BALANCERS,
    DESCRIBE_TARGET_GROUPS,
)
