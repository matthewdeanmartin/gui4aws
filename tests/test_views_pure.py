from __future__ import annotations

import datetime
from typing import Any

from gui4aws.services.athena.views import (
    to_query_execution_summaries,
    to_workgroup_summaries,
)
from gui4aws.services.backup.views import (
    to_backup_job_summaries,
    to_backup_plan_summaries,
    to_backup_vault_summaries,
    to_recovery_point_by_job_summaries,
    to_recovery_point_summaries,
    to_restore_job_summaries,
)
from gui4aws.services.cloudformation.views import to_stack_summaries
from gui4aws.services.cloudwatch.views import (
    to_alarm_summaries,
    to_log_event_summaries,
    to_log_group_summaries,
    to_log_stream_summaries,
)
from gui4aws.services.ecs.views import (
    to_cluster_summaries,
    to_service_summaries,
    to_task_definition_summaries,
    to_task_summaries,
)
from gui4aws.services.iam.views import (
    to_group_summaries,
    to_policy_summaries,
    to_role_summaries,
    to_user_summaries,
)
from gui4aws.services.lambdas.views import to_function_summaries
from gui4aws.services.networking.views import (
    to_alb_summaries,
    to_security_group_rule_summaries,
    to_security_group_summaries,
    to_subnet_summaries,
    to_target_group_summaries,
    to_vpc_summaries,
)
from gui4aws.services.ses.views import (
    to_identity_summaries,
    to_template_summaries,
)
from gui4aws.services.sns.views import (
    to_subscription_summaries,
    to_topic_summaries,
)
from gui4aws.services.ssm.views import to_parameter_summaries


# ECS Tests
def test_ecs_views() -> None:
    # Clusters
    resp_c1: dict[str, Any] = {"clusters": [{"clusterName": "c1", "status": "ACTIVE", "runningTasksCount": 1}]}
    sums_c1 = to_cluster_summaries(resp_c1)
    assert len(sums_c1) == 1
    assert sums_c1[0].cluster_name == "c1"

    resp_c2: dict[str, Any] = {"clusterArns": ["arn:aws:ecs:region:account:cluster/c2"]}
    sums_c2 = to_cluster_summaries(resp_c2)
    assert len(sums_c2) == 1
    assert sums_c2[0].cluster_name == "c2"

    assert to_cluster_summaries({}) == []

    # Services
    resp_s1: dict[str, Any] = {"services": [{"serviceName": "s1", "clusterArn": "arn:.../c1", "status": "ACTIVE"}]}
    sums_s1 = to_service_summaries(resp_s1)
    assert len(sums_s1) == 1
    assert sums_s1[0].service_name == "s1"
    assert sums_s1[0].cluster_name == "c1"

    resp_s2: dict[str, Any] = {"serviceArns": ["arn:aws:ecs:region:account:service/c1/s2"]}
    sums_s2 = to_service_summaries(resp_s2)
    assert len(sums_s2) == 1
    assert sums_s2[0].service_name == "s2"

    # Tasks
    resp_t1: dict[str, Any] = {
        "tasks": [{"taskArn": "arn:.../t1", "clusterArn": "arn:.../c1", "lastStatus": "RUNNING"}]
    }
    sums_t1 = to_task_summaries(resp_t1)
    assert len(sums_t1) == 1
    assert sums_t1[0].task_id == "t1"

    resp_t2: dict[str, Any] = {"taskArns": ["arn:aws:ecs:region:account:task/c1/t2"]}
    sums_t2 = to_task_summaries(resp_t2)
    assert len(sums_t2) == 1
    assert sums_t2[0].task_id == "t2"

    # Task Definitions
    resp_td1: dict[str, Any] = {"taskDefinitionArns": ["arn:...:task-definition/family:1"]}
    sums_td1 = to_task_definition_summaries(resp_td1)
    assert len(sums_td1) == 1
    assert sums_td1[0].family == "family"
    assert sums_td1[0].revision == "1"

    resp_td2: dict[str, Any] = {
        "taskDefinition": {"taskDefinitionArn": "arn:...:task-definition/family:2", "family": "family", "revision": 2}
    }
    sums_td2 = to_task_definition_summaries(resp_td2)
    assert len(sums_td2) == 1
    assert sums_td2[0].revision == "2"

    # Edge case: family:revision string without ARN
    resp_td3: dict[str, Any] = {"taskDefinitionArns": ["family:3"]}
    sums_td3 = to_task_definition_summaries(resp_td3)
    assert sums_td3[0].family == "family"
    assert sums_td3[0].revision == "3"


# Networking Tests
def test_networking_views() -> None:
    # VPCs
    resp_vpc1: dict[str, Any] = {"Vpcs": [{"VpcId": "vpc-1", "Tags": [{"Key": "Name", "Value": "my-vpc"}]}]}
    sums_vpc1 = to_vpc_summaries(resp_vpc1)
    assert sums_vpc1[0].name == "my-vpc"

    resp_vpc2: dict[str, Any] = {"Vpcs": [{"VpcId": "vpc-2"}]}
    sums_vpc2 = to_vpc_summaries(resp_vpc2)
    assert sums_vpc2[0].name is None

    # Subnets
    resp_sub: dict[str, Any] = {"Subnets": [{"SubnetId": "subnet-1", "VpcId": "vpc-1"}]}
    sums_sub = to_subnet_summaries(resp_sub)
    assert sums_sub[0].subnet_id == "subnet-1"

    # SGs
    resp_sg: dict[str, Any] = {"SecurityGroups": [{"GroupId": "sg-1", "GroupName": "web"}]}
    sums_sg = to_security_group_summaries(resp_sg)
    assert sums_sg[0].group_name == "web"

    # SG Rules
    resp_sgr1: dict[str, Any] = {
        "SecurityGroupRules": [
            {
                "SecurityGroupRuleId": "sgr-1",
                "IsEgress": False,
                "IpProtocol": "tcp",
                "FromPort": 80,
                "ToPort": 80,
                "CidrIpv4": "0.0.0.0/0",
            }
        ]
    }
    sums_sgr1 = to_security_group_rule_summaries(resp_sgr1)
    assert sums_sgr1[0].rule_id == "sgr-1"
    assert sums_sgr1[0].direction == "inbound"

    # SG Rules - Path 2 (describe_security_groups)
    resp_sgr2: dict[str, Any] = {
        "SecurityGroups": [
            {
                "IpPermissions": [
                    {"IpProtocol": "tcp", "FromPort": 443, "ToPort": 443, "IpRanges": [{"CidrIp": "1.1.1.1/32"}]}
                ]
            }
        ]
    }
    sums_sgr2 = to_security_group_rule_summaries(resp_sgr2)
    assert sums_sgr2[0].from_port == "443"
    assert sums_sgr2[0].cidr == "1.1.1.1/32"

    # ALBs
    resp_alb: dict[str, Any] = {"LoadBalancers": [{"LoadBalancerName": "alb-1", "State": {"Code": "active"}}]}
    sums_alb = to_alb_summaries(resp_alb)
    assert sums_alb[0].name == "alb-1"
    assert sums_alb[0].state == "active"

    # Target Groups
    resp_tg: dict[str, Any] = {"TargetGroups": [{"TargetGroupName": "tg-1", "Port": 80}]}
    sums_tg = to_target_group_summaries(resp_tg)
    assert sums_tg[0].name == "tg-1"
    assert sums_tg[0].port == 80


# CloudWatch Tests
def test_cloudwatch_views() -> None:
    # Alarms
    resp_a: dict[str, Any] = {"MetricAlarms": [{"AlarmName": "a1", "Threshold": 80.0}]}
    sums_a = to_alarm_summaries(resp_a)
    assert sums_a[0].name == "a1"
    assert sums_a[0].threshold == "80.0"

    # Log Groups
    resp_lg: dict[str, Any] = {"logGroups": [{"logGroupName": "lg1", "retentionInDays": 7}]}
    sums_lg = to_log_group_summaries(resp_lg)
    assert sums_lg[0].name == "lg1"
    assert sums_lg[0].retention_days == 7

    # Log Streams
    resp_ls: dict[str, Any] = {"logStreams": [{"logStreamName": "ls1", "lastEventTimestamp": 1600000000000}]}
    sums_ls = to_log_stream_summaries(resp_ls)
    assert sums_ls[0].stream_name == "ls1"
    last_event_time = sums_ls[0].last_event_time
    assert last_event_time is not None
    assert "2020-" in last_event_time

    # Log Events
    resp_le: dict[str, Any] = {"events": [{"timestamp": 1600000000000, "message": "hello\n"}]}
    sums_le = to_log_event_summaries(resp_le)
    assert sums_le[0].message == "hello"


# Athena Tests
def test_athena_views() -> None:
    # Workgroups
    resp_wg1: dict[str, Any] = {"WorkGroups": [{"Name": "wg1", "State": "ENABLED"}]}
    sums_wg1 = to_workgroup_summaries(resp_wg1)
    assert sums_wg1[0].name == "wg1"

    resp_wg2: dict[str, Any] = {"WorkGroup": {"Name": "wg2", "Configuration": {"Description": "desc"}}}
    sums_wg2 = to_workgroup_summaries(resp_wg2)
    assert sums_wg2[0].name == "wg2"
    assert sums_wg2[0].description == "desc"

    # Query Executions
    resp_qe1: dict[str, Any] = {"QueryExecutionIds": ["q1"]}
    sums_qe1 = to_query_execution_summaries(resp_qe1)
    assert sums_qe1[0].query_execution_id == "q1"

    resp_qe2: dict[str, Any] = {
        "QueryExecution": {"QueryExecutionId": "q2", "Query": "SELECT 1", "Status": {"State": "SUCCEEDED"}}
    }
    sums_qe2 = to_query_execution_summaries(resp_qe2)
    assert sums_qe2[0].query_execution_id == "q2"
    assert sums_qe2[0].query == "SELECT 1"


# SSM Tests
def test_ssm_views() -> None:
    resp: dict[str, Any] = {"Parameters": [{"Name": "p1", "Type": "String", "Value": "v1"}]}
    sums = to_parameter_summaries(resp)
    assert sums[0].name == "p1"
    assert sums[0].type == "String"


# SNS Tests
def test_sns_views() -> None:
    resp_t: dict[str, Any] = {"Topics": [{"TopicArn": "arn:aws:sns:region:account:topic1"}]}
    sums_t = to_topic_summaries(resp_t)
    assert sums_t[0].name == "topic1"

    resp_s1: dict[str, Any] = {
        "Subscriptions": [
            {"SubscriptionArn": "arn:aws:sns:region:account:topic1:sub1", "TopicArn": "t1", "Protocol": "sqs"}
        ]
    }
    sums_s1 = to_subscription_summaries(resp_s1)
    assert sums_s1[0].subscription_id == "sub1"
    assert sums_s1[0].status == "Confirmed"

    resp_s2: dict[str, Any] = {
        "Subscriptions": [{"SubscriptionArn": "PendingConfirmation", "TopicArn": "t1", "Protocol": "email"}]
    }
    sums_s2 = to_subscription_summaries(resp_s2)
    assert sums_s2[0].subscription_id == "PendingConfirmation"
    assert sums_s2[0].status == "PendingConfirmation"


# SES Tests
def test_ses_views() -> None:
    resp_id: dict[str, Any] = {
        "Identities": ["example.com", "user@example.com"],
        "VerificationAttributes": {"example.com": {"VerificationStatus": "Success"}},
    }
    sums_id = to_identity_summaries(resp_id)
    assert sums_id[0].identity == "example.com"
    assert sums_id[0].identity_type == "domain"
    assert sums_id[1].identity_type == "email"

    resp_tm: dict[str, Any] = {"TemplatesMetadata": [{"Name": "t1", "CreatedTimestamp": datetime.datetime(2023, 1, 1)}]}
    sums_tm = to_template_summaries(resp_tm)
    assert sums_tm[0].name == "t1"


# Lambda Tests
def test_lambda_views() -> None:
    resp: dict[str, Any] = {"Functions": [{"FunctionName": "f1", "Runtime": "python3.9", "MemorySize": 128}]}
    sums = to_function_summaries(resp)
    assert sums[0].name == "f1"
    assert sums[0].memory_size == 128


# CloudFormation Tests
def test_cloudformation_views() -> None:
    resp: dict[str, Any] = {"Stacks": [{"StackName": "stack1", "StackStatus": "CREATE_COMPLETE"}]}
    sums = to_stack_summaries(resp)
    assert sums[0].name == "stack1"


# IAM Tests
def test_iam_views() -> None:
    resp_u: dict[str, Any] = {"Users": [{"UserName": "u1", "UserId": "id1"}]}
    sums_u = to_user_summaries(resp_u)
    assert sums_u[0].name == "u1"

    resp_g: dict[str, Any] = {"Groups": [{"GroupName": "g1"}]}
    sums_g = to_group_summaries(resp_g)
    assert sums_g[0].name == "g1"

    resp_r: dict[str, Any] = {"Roles": [{"RoleName": "r1"}]}
    sums_r = to_role_summaries(resp_r)
    assert sums_r[0].name == "r1"

    resp_p: dict[str, Any] = {"Policies": [{"PolicyName": "p1"}]}
    sums_p = to_policy_summaries(resp_p)
    assert sums_p[0].name == "p1"


# Backup Tests
def test_backup_views() -> None:
    resp_bv: dict[str, Any] = {"BackupVaultList": [{"BackupVaultName": "v1", "NumberOfRecoveryPoints": 5}]}
    sums_bv = to_backup_vault_summaries(resp_bv)
    assert sums_bv[0].vault_name == "v1"

    resp_bp: dict[str, Any] = {"BackupPlansList": [{"BackupPlanId": "id1", "BackupPlanName": "p1"}]}
    sums_bp = to_backup_plan_summaries(resp_bp)
    assert sums_bp[0].plan_name == "p1"

    resp_rp: dict[str, Any] = {
        "RecoveryPoints": [{"RecoveryPointArn": "arn1", "BackupVaultName": "v1", "Status": "COMPLETED"}]
    }
    sums_rp = to_recovery_point_summaries(resp_rp)
    assert sums_rp[0].recovery_point_arn == "arn1"

    resp_bj: dict[str, Any] = {"BackupJobs": [{"BackupJobId": "j1", "State": "COMPLETED", "RecoveryPointArn": "arn1"}]}
    sums_bj = to_backup_job_summaries(resp_bj)
    assert sums_bj[0].job_id == "j1"

    sums_rpj = to_recovery_point_by_job_summaries(resp_bj)
    assert sums_rpj[0].recovery_point_arn == "arn1"

    resp_rj: dict[str, Any] = {"RestoreJobs": [{"RestoreJobId": "rj1", "Status": "COMPLETED"}]}
    sums_rj = to_restore_job_summaries(resp_rj)
    assert sums_rj[0].job_id == "rj1"
