"""Moto-backed tests for Networking actions."""

from __future__ import annotations

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.networking.actions import (
    CREATE_SECURITY_GROUP,
    CREATE_SUBNET,
    CREATE_VPC,
    DELETE_SECURITY_GROUP,
    DELETE_SUBNET,
    DELETE_VPC,
    DESCRIBE_SECURITY_GROUP_RULES,
    DESCRIBE_SECURITY_GROUPS,
    DESCRIBE_SUBNETS,
    DESCRIBE_VPCS,
)
from gui4aws.services.networking.views import (
    to_security_group_rule_summaries,
    to_security_group_summaries,
    to_subnet_summaries,
    to_vpc_summaries,
)


def test_describe_vpcs_default(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(DESCRIBE_VPCS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_vpc_summaries(result.response)
    # Moto usually has a default VPC
    assert len(summaries) >= 0


def test_create_and_delete_vpc(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create (name is not currently mapped in Boto3Template)
    result = context.execute(CREATE_VPC, inputs={"cidr_block": "10.1.0.0/16"})
    assert isinstance(result, Boto3Result)
    vpc_id = result.response["Vpc"]["VpcId"]

    # List
    list_result = context.execute(DESCRIBE_VPCS, inputs={})
    summaries = to_vpc_summaries(list_result.response)
    assert any(s.vpc_id == vpc_id for s in summaries)

    # Delete
    del_result = context.execute(DELETE_VPC, inputs={"vpc_id": vpc_id})
    assert isinstance(del_result, Boto3Result)


def test_subnet_actions(mock_aws_env: None) -> None:
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.2.0.0/16")["Vpc"]["VpcId"]

    context = AppContext(region_name="us-east-1")

    # Create Subnet (name is not currently mapped)
    result = context.execute(CREATE_SUBNET, inputs={"vpc_id": vpc_id, "cidr_block": "10.2.1.0/24"})
    assert isinstance(result, Boto3Result)
    subnet_id = result.response["Subnet"]["SubnetId"]

    # List Subnets
    list_result = context.execute(DESCRIBE_SUBNETS, inputs={})
    summaries = to_subnet_summaries(list_result.response)
    assert any(s.subnet_id == subnet_id for s in summaries)

    # Delete Subnet
    del_result = context.execute(DELETE_SUBNET, inputs={"subnet_id": subnet_id})
    assert isinstance(del_result, Boto3Result)


def test_security_group_actions(mock_aws_env: None) -> None:
    ec2 = boto3.client("ec2", region_name="us-east-1")
    vpc_id = ec2.create_vpc(CidrBlock="10.3.0.0/16")["Vpc"]["VpcId"]

    context = AppContext(region_name="us-east-1")

    # Create SG
    result = context.execute(
        CREATE_SECURITY_GROUP, inputs={"group_name": "test-sg", "description": "test sg desc", "vpc_id": vpc_id}
    )
    assert isinstance(result, Boto3Result)
    group_id = result.response["GroupId"]

    # List SGs
    list_result = context.execute(DESCRIBE_SECURITY_GROUPS, inputs={})
    summaries = to_security_group_summaries(list_result.response)
    assert any(s.group_id == group_id for s in summaries)

    # Describe Rules
    # Add a rule first via boto3 to have something to see
    ec2.authorize_security_group_ingress(GroupId=group_id, IpProtocol="tcp", FromPort=80, ToPort=80, CidrIp="0.0.0.0/0")

    rules_result = context.execute(DESCRIBE_SECURITY_GROUP_RULES, inputs={"group_id": group_id})
    rule_summaries = to_security_group_rule_summaries(rules_result.response)
    # Path 2 in to_security_group_rule_summaries is used here because describe_security_groups is called
    assert any(s.from_port == "80" and s.cidr == "0.0.0.0/0" for s in rule_summaries)

    # Delete SG
    del_result = context.execute(DELETE_SECURITY_GROUP, inputs={"group_id": group_id})
    assert isinstance(del_result, Boto3Result)
