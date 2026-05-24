"""Seed demo CloudWatch alarms, log groups, and CloudFormation stacks."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import DEMO_DESC_TAG_KEY, tags

logger = logging.getLogger(__name__)


def seed_cloudwatch(cloudwatch: Any, logs: Any) -> dict[str, list[str]]:
    """Seed CloudWatch alarms and Log Groups for monitoring visibility.

    Sets up alarms for common resource metrics (CPU, storage) and log groups with
    retention policies to demonstrate observability features in the GUI.
    """
    created: dict[str, list[str]] = {"cloudwatch_alarms": [], "log_groups": []}

    alarms = [
        {
            "AlarmName": "demo-high-cpu-alarm",
            "AlarmDescription": "Demo alarm: triggers when EC2 CPU exceeds 80%",
            "MetricName": "CPUUtilization",
            "Namespace": "AWS/EC2",
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 2,
            "Threshold": 80.0,
            "ComparisonOperator": "GreaterThanOrEqualToThreshold",
        },
        {
            "AlarmName": "demo-low-free-storage-alarm",
            "AlarmDescription": "Demo alarm: triggers when RDS free storage drops below 1 GB",
            "MetricName": "FreeStorageSpace",
            "Namespace": "AWS/RDS",
            "Statistic": "Average",
            "Period": 300,
            "EvaluationPeriods": 1,
            "Threshold": 1073741824.0,
            "ComparisonOperator": "LessThanThreshold",
        },
    ]

    for alarm_spec in alarms:
        alarm_name = str(alarm_spec["AlarmName"])
        try:
            cloudwatch.put_metric_alarm(**alarm_spec)
            logger.info("created CloudWatch alarm %s", alarm_name)
            created["cloudwatch_alarms"].append(alarm_name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped CloudWatch alarm %s: %s", alarm_name, exc)

    log_groups = [
        ("/demo/app/api", 30, "Demo log group for API service"),
        ("/demo/app/worker", 14, "Demo log group for background workers"),
        ("/demo/app/audit", 90, "Demo log group for audit trail"),
    ]

    for log_group_name, retention_days, description in log_groups:
        try:
            logs.create_log_group(
                logGroupName=log_group_name,
                tags={
                    "gui4aws:demo": "true",
                    "Name": log_group_name,
                    DEMO_DESC_TAG_KEY: description,
                },
            )
            logger.info("created log group %s", log_group_name)
            created["log_groups"].append(log_group_name)
            try:
                logs.put_retention_policy(
                    logGroupName=log_group_name,
                    retentionInDays=retention_days,
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped retention policy for %s: %s", log_group_name, exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped log group %s: %s", log_group_name, exc)

    return created


def seed_cloudformation(cfn: Any) -> dict[str, list[str]]:
    """Seed CloudFormation stacks with sample templates.

    Creates infrastructure and application stacks to show how the GUI visualizes
    stack resources, status, and configuration.
    """
    import json

    created: dict[str, list[str]] = {"cloudformation_stacks": []}

    stacks = [
        (
            "demo-infra-stack",
            "Demo infrastructure stack — VPC and networking resources",
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "Demo infrastructure stack",
                "Resources": {
                    "DemoBucket": {"Type": "AWS::S3::Bucket"},
                },
            },
        ),
        (
            "demo-app-stack",
            "Demo application stack — Lambda and SQS resources",
            {
                "AWSTemplateFormatVersion": "2010-09-09",
                "Description": "Demo application stack",
                "Resources": {
                    "DemoQueue": {"Type": "AWS::SQS::Queue"},
                },
            },
        ),
    ]

    for stack_name, description, template in stacks:
        try:
            cfn.create_stack(
                StackName=stack_name,
                TemplateBody=json.dumps(template),
                Tags=tags(
                    {"Key": "Name", "Value": stack_name},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": description},
                ),
            )
            logger.info("created CloudFormation stack %s", stack_name)
            created["cloudformation_stacks"].append(stack_name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped CloudFormation stack %s: %s", stack_name, exc)

    return created
