from __future__ import annotations

import datetime
from typing import Any
from gui4aws.services.ecs.views import (
    to_cluster_summaries,
    to_service_summaries,
    to_task_summaries,
    to_task_definition_summaries,
)
from gui4aws.services.networking.views import (
    to_vpc_summaries,
    to_subnet_summaries,
    to_security_group_summaries,
    to_security_group_rule_summaries,
    to_alb_summaries,
    to_target_group_summaries,
)
from gui4aws.services.cloudwatch.views import (
    to_alarm_summaries,
    to_log_group_summaries,
    to_log_stream_summaries,
    to_log_event_summaries,
)
from gui4aws.services.athena.views import (
    to_workgroup_summaries,
    to_query_execution_summaries,
)
from gui4aws.services.ssm.views import to_parameter_summaries
from gui4aws.services.sns.views import (
    to_topic_summaries,
    to_subscription_summaries,
)
from gui4aws.services.ses.views import (
    to_identity_summaries,
    to_template_summaries,
)
from gui4aws.services.lambdas.views import to_function_summaries
from gui4aws.services.cloudformation.views import to_stack_summaries
from gui4aws.services.iam.views import (
    to_user_summaries,
    to_group_summaries,
    to_role_summaries,
    to_policy_summaries,
)
from gui4aws.services.backup.views import (
    to_backup_vault_summaries,
    to_backup_plan_summaries,
    to_recovery_point_summaries,
    to_backup_job_summaries,
    to_recovery_point_by_job_summaries,
    to_restore_job_summaries,
)

# ECS Tests
def test_ecs_views():
    # Clusters
    resp = {"clusters": [{"clusterName": "c1", "status": "ACTIVE", "runningTasksCount": 1}]}
    sums = to_cluster_summaries(resp)
    assert len(sums) == 1
    assert sums[0].cluster_name == "c1"

    resp = {"clusterArns": ["arn:aws:ecs:region:account:cluster/c2"]}
    sums = to_cluster_summaries(resp)
    assert len(sums) == 1
    assert sums[0].cluster_name == "c2"

    assert to_cluster_summaries({}) == []

    # Services
    resp = {"services": [{"serviceName": "s1", "clusterArn": "arn:.../c1", "status": "ACTIVE"}]}
    sums = to_service_summaries(resp)
    assert len(sums) == 1
    assert sums[0].service_name == "s1"
    assert sums[0].cluster_name == "c1"

    resp = {"serviceArns": ["arn:aws:ecs:region:account:service/c1/s2"]}
    sums = to_service_summaries(resp)
    assert len(sums) == 1
    assert sums[0].service_name == "s2"

    # Tasks
    resp = {"tasks": [{"taskArn": "arn:.../t1", "clusterArn": "arn:.../c1", "lastStatus": "RUNNING"}]}
    sums = to_task_summaries(resp)
    assert len(sums) == 1
    assert sums[0].task_id == "t1"

    resp = {"taskArns": ["arn:aws:ecs:region:account:task/c1/t2"]}
    sums = to_task_summaries(resp)
    assert len(sums) == 1
    assert sums[0].task_id == "t2"

    # Task Definitions
    resp = {"taskDefinitionArns": ["arn:...:task-definition/family:1"]}
    sums = to_task_definition_summaries(resp)
    assert len(sums) == 1
    assert sums[0].family == "family"
    assert sums[0].revision == "1"

    resp = {"taskDefinition": {"taskDefinitionArn": "arn:...:task-definition/family:2", "family": "family", "revision": 2}}
    sums = to_task_definition_summaries(resp)
    assert len(sums) == 1
    assert sums[0].revision == "2"

    # Edge case: family:revision string without ARN
    resp = {"taskDefinitionArns": ["family:3"]}
    sums = to_task_definition_summaries(resp)
    assert sums[0].family == "family"
    assert sums[0].revision == "3"

# Networking Tests
def test_networking_views():
    # VPCs
    resp = {"Vpcs": [{"VpcId": "vpc-1", "Tags": [{"Key": "Name", "Value": "my-vpc"}]}]}
    sums = to_vpc_summaries(resp)
    assert sums[0].name == "my-vpc"

    resp = {"Vpcs": [{"VpcId": "vpc-2"}]}
    sums = to_vpc_summaries(resp)
    assert sums[0].name is None

    # Subnets
    resp = {"Subnets": [{"SubnetId": "subnet-1", "VpcId": "vpc-1"}]}
    sums = to_subnet_summaries(resp)
    assert sums[0].subnet_id == "subnet-1"

    # SGs
    resp = {"SecurityGroups": [{"GroupId": "sg-1", "GroupName": "web"}]}
    sums = to_security_group_summaries(resp)
    assert sums[0].group_name == "web"

    # SG Rules
    resp = {"SecurityGroupRules": [{"SecurityGroupRuleId": "sgr-1", "IsEgress": False, "IpProtocol": "tcp", "FromPort": 80, "ToPort": 80, "CidrIpv4": "0.0.0.0/0"}]}
    sums = to_security_group_rule_summaries(resp)
    assert sums[0].rule_id == "sgr-1"
    assert sums[0].direction == "inbound"

    # SG Rules - Path 2 (describe_security_groups)
    resp = {"SecurityGroups": [{"IpPermissions": [{"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "1.1.1.1/32"}]}]}]}
    sums = to_security_group_rule_summaries(resp)
    assert sums[0].from_port == "443"
    assert sums[0].cidr == "1.1.1.1/32"

    # ALBs
    resp = {"LoadBalancers": [{"LoadBalancerName": "alb-1", "State": {"Code": "active"}}]}
    sums = to_alb_summaries(resp)
    assert sums[0].name == "alb-1"
    assert sums[0].state == "active"

    # Target Groups
    resp = {"TargetGroups": [{"TargetGroupName": "tg-1", "Port": 80}]}
    sums = to_target_group_summaries(resp)
    assert sums[0].name == "tg-1"
    assert sums[0].port == 80

# CloudWatch Tests
def test_cloudwatch_views():
    # Alarms
    resp = {"MetricAlarms": [{"AlarmName": "a1", "Threshold": 80.0}]}
    sums = to_alarm_summaries(resp)
    assert sums[0].name == "a1"
    assert sums[0].threshold == "80.0"

    # Log Groups
    resp = {"logGroups": [{"logGroupName": "lg1", "retentionInDays": 7}]}
    sums = to_log_group_summaries(resp)
    assert sums[0].name == "lg1"
    assert sums[0].retention_days == 7

    # Log Streams
    resp = {"logStreams": [{"logStreamName": "ls1", "lastEventTimestamp": 1600000000000}]}
    sums = to_log_stream_summaries(resp)
    assert sums[0].stream_name == "ls1"
    assert "2020-" in sums[0].last_event_time

    # Log Events
    resp = {"events": [{"timestamp": 1600000000000, "message": "hello\n"}]}
    sums = to_log_event_summaries(resp)
    assert sums[0].message == "hello"

# Athena Tests
def test_athena_views():
    # Workgroups
    resp = {"WorkGroups": [{"Name": "wg1", "State": "ENABLED"}]}
    sums = to_workgroup_summaries(resp)
    assert sums[0].name == "wg1"

    resp = {"WorkGroup": {"Name": "wg2", "Configuration": {"Description": "desc"}}}
    sums = to_workgroup_summaries(resp)
    assert sums[0].name == "wg2"
    assert sums[0].description == "desc"

    # Query Executions
    resp = {"QueryExecutionIds": ["q1"]}
    sums = to_query_execution_summaries(resp)
    assert sums[0].query_execution_id == "q1"

    resp = {"QueryExecution": {"QueryExecutionId": "q2", "Query": "SELECT 1", "Status": {"State": "SUCCEEDED"}}}
    sums = to_query_execution_summaries(resp)
    assert sums[0].query_execution_id == "q2"
    assert sums[0].query == "SELECT 1"

# SSM Tests
def test_ssm_views():
    resp = {"Parameters": [{"Name": "p1", "Type": "String", "Value": "v1"}]}
    sums = to_parameter_summaries(resp)
    assert sums[0].name == "p1"
    assert sums[0].type == "String"

# SNS Tests
def test_sns_views():
    resp = {"Topics": [{"TopicArn": "arn:aws:sns:region:account:topic1"}]}
    sums = to_topic_summaries(resp)
    assert sums[0].name == "topic1"

    resp = {"Subscriptions": [{"SubscriptionArn": "arn:aws:sns:region:account:topic1:sub1", "TopicArn": "t1", "Protocol": "sqs"}]}
    sums = to_subscription_summaries(resp)
    assert sums[0].subscription_id == "sub1"
    assert sums[0].status == "Confirmed"

    resp = {"Subscriptions": [{"SubscriptionArn": "PendingConfirmation", "TopicArn": "t1", "Protocol": "email"}]}
    sums = to_subscription_summaries(resp)
    assert sums[0].subscription_id == "PendingConfirmation"
    assert sums[0].status == "PendingConfirmation"

# SES Tests
def test_ses_views():
    resp = {"Identities": ["example.com", "user@example.com"], "VerificationAttributes": {"example.com": {"VerificationStatus": "Success"}}}
    sums = to_identity_summaries(resp)
    assert sums[0].identity == "example.com"
    assert sums[0].identity_type == "domain"
    assert sums[1].identity_type == "email"

    resp = {"TemplatesMetadata": [{"Name": "t1", "CreatedTimestamp": datetime.datetime(2023, 1, 1)}]}
    sums = to_template_summaries(resp)
    assert sums[0].name == "t1"

# Lambda Tests
def test_lambda_views():
    resp = {"Functions": [{"FunctionName": "f1", "Runtime": "python3.9", "MemorySize": 128}]}
    sums = to_function_summaries(resp)
    assert sums[0].name == "f1"
    assert sums[0].memory_size == 128

# CloudFormation Tests
def test_cloudformation_views():
    resp = {"Stacks": [{"StackName": "stack1", "StackStatus": "CREATE_COMPLETE"}]}
    sums = to_stack_summaries(resp)
    assert sums[0].name == "stack1"

# IAM Tests
def test_iam_views():
    resp = {"Users": [{"UserName": "u1", "UserId": "id1"}]}
    sums = to_user_summaries(resp)
    assert sums[0].name == "u1"

    resp = {"Groups": [{"GroupName": "g1"}]}
    sums = to_group_summaries(resp)
    assert sums[0].name == "g1"

    resp = {"Roles": [{"RoleName": "r1"}]}
    sums = to_role_summaries(resp)
    assert sums[0].name == "r1"

    resp = {"Policies": [{"PolicyName": "p1"}]}
    sums = to_policy_summaries(resp)
    assert sums[0].name == "p1"

# Backup Tests
def test_backup_views():
    resp = {"BackupVaultList": [{"BackupVaultName": "v1", "NumberOfRecoveryPoints": 5}]}
    sums = to_backup_vault_summaries(resp)
    assert sums[0].vault_name == "v1"

    resp = {"BackupPlansList": [{"BackupPlanId": "id1", "BackupPlanName": "p1"}]}
    sums = to_backup_plan_summaries(resp)
    assert sums[0].plan_name == "p1"

    resp = {"RecoveryPoints": [{"RecoveryPointArn": "arn1", "BackupVaultName": "v1", "Status": "COMPLETED"}]}
    sums = to_recovery_point_summaries(resp)
    assert sums[0].recovery_point_arn == "arn1"

    resp = {"BackupJobs": [{"BackupJobId": "j1", "State": "COMPLETED", "RecoveryPointArn": "arn1"}]}
    sums = to_backup_job_summaries(resp)
    assert sums[0].job_id == "j1"

    sums = to_recovery_point_by_job_summaries(resp)
    assert sums[0].recovery_point_arn == "arn1"

    resp = {"RestoreJobs": [{"RestoreJobId": "rj1", "Status": "COMPLETED"}]}
    sums = to_restore_job_summaries(resp)
    assert sums[0].job_id == "rj1"
