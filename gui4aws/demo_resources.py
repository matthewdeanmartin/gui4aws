"""Seed demo AWS resources so the GUI has something to browse immediately.

All resources are tagged with ``gui4aws:demo = true`` and given descriptive names so
users can immediately distinguish demo data from real infrastructure.

This module only writes resources; it never deletes. Call :func:`seed_demo_resources`
with a boto3 session (or endpoint_url for moto server mode) to create the assets.
"""

from __future__ import annotations

import logging
from typing import Any

__all__ = ["seed_demo_resources"]

logger = logging.getLogger(__name__)

DEMO_TAG = {"Key": "gui4aws:demo", "Value": "true"}
DEMO_DESC_TAG_KEY = "Description"


def _tags(*extra: dict[str, str]) -> list[dict[str, str]]:
    return [DEMO_TAG, *extra]


def seed_demo_resources(
    *,
    region_name: str = "us-east-1",
    endpoint_url: str | None = None,
    profile_name: str | None = None,
    is_robotocore: bool = False,
) -> dict[str, list[str]]:
    """Create demo resources and return a report of what was created.

    ``is_robotocore`` controls whether richer demo data (backup jobs, restore jobs,
    ECS services with tasks, etc.) is seeded.  Robotocore has broader API coverage
    than Moto for these resource types.

    Returns a dict mapping resource type to list of identifiers.
    """
    import boto3

    session: Any
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
    else:
        session = boto3.Session(region_name=region_name)

    def client(service: str) -> Any:
        if endpoint_url:
            return session.client(service, endpoint_url=endpoint_url)
        return session.client(service)

    created: dict[str, list[str]] = {}

    rds_client = client("rds")
    created.update(_seed_aurora(rds_client))
    created.update(_seed_backup(client("backup"), rds_client, extended=is_robotocore))
    created.update(_seed_networking(client("ec2"), client("elbv2")))
    created.update(_seed_ecs(client("ecs"), extended=is_robotocore))
    created.update(_seed_secrets(client("secretsmanager")))
    created.update(_seed_ssm(client("ssm")))
    created.update(_seed_kms(client("kms")))
    created.update(_seed_s3(client("s3")))
    created.update(_seed_sqs(client("sqs")))
    created.update(_seed_lambda(client("lambda"), client("iam")))
    created.update(_seed_cloudwatch(client("cloudwatch"), client("logs")))
    created.update(_seed_cloudformation(client("cloudformation")))
    created.update(_seed_sns(client("sns")))
    created.update(_seed_ses(client("ses")))
    created.update(_seed_iam_extras(client("iam")))

    return created


def _seed_aurora(rds: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"aurora_clusters": [], "aurora_instances": [], "aurora_snapshots": []}

    clusters = [
        {
            "DBClusterIdentifier": "demo-aurora-mysql-prod",
            "Engine": "aurora-mysql",
            "MasterUsername": "admin",
            "MasterUserPassword": "DemoPass123!",
            "Tags": _tags(
                {"Key": "Name", "Value": "demo-aurora-mysql-prod"},
                {"Key": DEMO_DESC_TAG_KEY, "Value": "Demo Aurora MySQL cluster (production-like)"},
            ),
        },
        {
            "DBClusterIdentifier": "demo-aurora-pg-analytics",
            "Engine": "aurora-postgresql",
            "MasterUsername": "postgres",
            "MasterUserPassword": "DemoPass123!",
            "Tags": _tags(
                {"Key": "Name", "Value": "demo-aurora-pg-analytics"},
                {"Key": DEMO_DESC_TAG_KEY, "Value": "Demo Aurora PostgreSQL cluster (analytics)"},
            ),
        },
    ]

    for spec in clusters:
        cluster_id = str(spec["DBClusterIdentifier"])
        engine = str(spec["Engine"])
        try:
            rds.create_db_cluster(**spec)
            logger.info("created Aurora cluster %s", cluster_id)
            created["aurora_clusters"].append(cluster_id)
        except Exception as exc:
            logger.warning("skipped cluster %s: %s", cluster_id, exc)
            continue

        instance_id = f"{cluster_id}-instance-1"
        try:
            rds.create_db_instance(
                DBInstanceIdentifier=instance_id,
                DBInstanceClass="db.t3.medium",
                Engine=engine,
                DBClusterIdentifier=cluster_id,
                Tags=_tags(
                    {"Key": "Name", "Value": instance_id},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": f"Demo instance for {cluster_id}"},
                ),
            )
            logger.info("created Aurora instance %s", instance_id)
            created["aurora_instances"].append(instance_id)
        except Exception as exc:
            logger.warning("skipped instance %s: %s", instance_id, exc)

    if created["aurora_clusters"]:
        source = created["aurora_clusters"][0]
        snap_id = f"{source}-demo-snapshot"
        try:
            rds.create_db_cluster_snapshot(
                DBClusterIdentifier=source,
                DBClusterSnapshotIdentifier=snap_id,
                Tags=_tags(
                    {"Key": "Name", "Value": snap_id},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": "Demo snapshot — safe to restore"},
                ),
            )
            logger.info("created Aurora snapshot %s", snap_id)
            created["aurora_snapshots"].append(snap_id)
        except Exception as exc:
            logger.warning("skipped snapshot %s: %s", snap_id, exc)

    return created


def _seed_networking(ec2: Any, elbv2: Any) -> dict[str, list[str]]:
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
                    "Tags": _tags({"Key": "Name", "Value": "demo-vpc"}),
                }
            ],
        )
        vpc_id = resp["Vpc"]["VpcId"]
        logger.info("created VPC %s", vpc_id)
        created["vpcs"].append(vpc_id)
    except Exception as exc:
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
                            "Tags": _tags({"Key": "Name", "Value": name}),
                        }
                    ],
                )
                subnet_id = resp["Subnet"]["SubnetId"]
                subnet_ids.append(subnet_id)
                logger.info("created subnet %s", subnet_id)
                created["subnets"].append(subnet_id)
            except Exception as exc:
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
                        "Tags": _tags({"Key": "Name", "Value": "demo-sg"}),
                    }
                ],
            )
            sg_id = resp["GroupId"]
            logger.info("created security group %s", sg_id)
            created["security_groups"].append(sg_id)
        except Exception as exc:
            logger.warning("skipped security group: %s", exc)

    alb_arn: str | None = None
    if subnet_ids:
        try:
            resp = elbv2.create_load_balancer(
                Name="demo-alb",
                Subnets=subnet_ids,
                SecurityGroups=[sg_id] if sg_id else [],
                Scheme="internet-facing",
                Type="application",
                Tags=_tags({"Key": "Name", "Value": "demo-alb"}),
            )
            alb_arn = resp["LoadBalancers"][0]["LoadBalancerArn"]
            logger.info("created ALB %s", alb_arn)
            created["load_balancers"].append(alb_arn)
        except Exception as exc:
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
                Tags=_tags({"Key": "Name", "Value": "demo-tg"}),
            )
            tg_arn = resp["TargetGroups"][0]["TargetGroupArn"]
            logger.info("created target group %s", tg_arn)
            created["target_groups"].append(tg_arn)
        except Exception as exc:
            logger.warning("skipped target group: %s", exc)

    return created


def _seed_ecs(ecs: Any, *, extended: bool = False) -> dict[str, list[str]]:
    """Seed ECS resources.

    ``extended=True`` seeds task definitions, services, and tasks — requires
    robotocore (Moto's ECS write path is limited).
    """
    created: dict[str, list[str]] = {
        "ecs_clusters": [],
        "ecs_task_definitions": [],
        "ecs_services": [],
        "ecs_tasks": [],
    }

    cluster_name = "demo-cluster"
    try:
        ecs.create_cluster(
            clusterName=cluster_name,
            tags=[
                {"key": "gui4aws:demo", "value": "true"},
                {"key": "Name", "value": cluster_name},
                {"key": "Description", "value": "Demo ECS cluster for gui4aws"},
            ],
        )
        logger.info("created ECS cluster %s", cluster_name)
        created["ecs_clusters"].append(cluster_name)
    except Exception as exc:
        logger.warning("skipped ECS cluster %s: %s", cluster_name, exc)

    if not extended:
        return created

    # Register task definitions for robotocore
    task_defs = [
        {
            "family": "demo-web",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [
                {
                    "name": "web",
                    "image": "nginx:latest",
                    "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
                    "essential": True,
                }
            ],
        },
        {
            "family": "demo-worker",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [
                {
                    "name": "worker",
                    "image": "busybox:latest",
                    "command": ["sleep", "3600"],
                    "essential": True,
                }
            ],
        },
    ]

    registered_families: list[str] = []
    for td in task_defs:
        try:
            resp = ecs.register_task_definition(**td)
            td_arn = resp["taskDefinition"]["taskDefinitionArn"]
            family = str(td["family"])
            logger.info("registered task definition %s", td_arn)
            created["ecs_task_definitions"].append(td_arn)
            registered_families.append(family)
        except Exception as exc:
            logger.warning("skipped task definition %s: %s", td["family"], exc)

    # Create services in the demo cluster
    if registered_families and created["ecs_clusters"]:
        services = [
            {
                "cluster": cluster_name,
                "serviceName": "demo-web-svc",
                "taskDefinition": "demo-web",
                "desiredCount": 2,
                "launchType": "FARGATE",
            },
            {
                "cluster": cluster_name,
                "serviceName": "demo-worker-svc",
                "taskDefinition": "demo-worker",
                "desiredCount": 1,
                "launchType": "FARGATE",
            },
        ]
        for svc in services:
            service_name = str(svc["serviceName"])
            try:
                ecs.create_service(**svc)
                logger.info("created ECS service %s", service_name)
                created["ecs_services"].append(service_name)
            except Exception as exc:
                logger.warning("skipped ECS service %s: %s", service_name, exc)

    return created


def _seed_secrets(sm: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"secrets": []}

    secrets = [
        ("demo/db-password", "Demo database password", '{"username":"admin","password":"DemoPass123!"}'),
        ("demo/api-key", "Demo API key", "demo-api-key-abc123"),
    ]

    for name, description, value in secrets:
        try:
            sm.create_secret(
                Name=name,
                Description=description,
                SecretString=value,
                Tags=_tags({"Key": "Name", "Value": name}),
            )
            logger.info("created secret %s", name)
            created["secrets"].append(name)
        except Exception as exc:
            logger.warning("skipped secret %s: %s", name, exc)

    return created


def _seed_ssm(ssm: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"ssm_parameters": []}

    params = [
        ("/demo/app/db-host", "String", "demo-aurora-mysql-prod.cluster-xyz.us-east-1.rds.amazonaws.com"),
        ("/demo/app/db-port", "String", "3306"),
        ("/demo/app/log-level", "String", "INFO"),
        ("/demo/app/feature-flags", "String", '{"new_ui":true,"dark_mode":false}'),
    ]

    for name, ptype, value in params:
        try:
            ssm.put_parameter(
                Name=name,
                Value=value,
                Type=ptype,
                Description=f"Demo parameter: {name}",
                Tags=_tags({"Key": "Name", "Value": name}),
            )
            logger.info("created SSM parameter %s", name)
            created["ssm_parameters"].append(name)
        except Exception as exc:
            logger.warning("skipped SSM parameter %s: %s", name, exc)

    return created


def _seed_backup(backup: Any, rds: Any | None = None, *, extended: bool = False) -> dict[str, list[str]]:
    """Seed Backup resources.

    ``extended=True`` seeds additional backup plans and on-demand backup jobs
    that create recovery points — requires robotocore.
    """
    created: dict[str, list[str]] = {
        "backup_vaults": [],
        "backup_plans": [],
        "backup_selections": [],
        "backup_jobs": [],
        "recovery_points": [],
    }

    vaults = [
        ("demo-daily-vault", "Demo vault for daily backups"),
        ("demo-weekly-vault", "Demo vault for weekly backups"),
        ("demo-monthly-vault", "Demo vault for monthly backups"),
    ]

    for vault_name, description in vaults:
        try:
            backup.create_backup_vault(
                BackupVaultName=vault_name,
                BackupVaultTags={
                    "gui4aws:demo": "true",
                    "Name": vault_name,
                    DEMO_DESC_TAG_KEY: description,
                },
            )
            logger.info("created backup vault %s", vault_name)
            created["backup_vaults"].append(vault_name)
        except Exception as exc:
            logger.warning("skipped vault %s: %s", vault_name, exc)

    # Backup plans with different schedules
    plans = [
        (
            "demo-daily-plan",
            "demo-daily-vault",
            "daily-rule",
            "cron(0 5 ? * * *)",
            60,
            180,
            "Demo daily backup plan — backs up every day at 5 AM UTC",
        ),
        (
            "demo-weekly-plan",
            "demo-weekly-vault",
            "weekly-rule",
            "cron(0 5 ? * 1 *)",
            60,
            360,
            "Demo weekly backup plan — backs up every Monday at 5 AM UTC",
        ),
    ]

    if extended:
        plans.append(
            (
                "demo-monthly-plan",
                "demo-monthly-vault",
                "monthly-rule",
                "cron(0 5 1 * ? *)",
                120,
                720,
                "Demo monthly backup plan — backs up on the 1st of each month",
            )
        )

    for plan_name, vault_name, rule_name, schedule, start_window, completion_window, description in plans:
        if vault_name not in created["backup_vaults"]:
            continue
        try:
            resp = backup.create_backup_plan(
                BackupPlan={
                    "BackupPlanName": plan_name,
                    "Rules": [
                        {
                            "RuleName": rule_name,
                            "TargetBackupVaultName": vault_name,
                            "ScheduleExpression": schedule,
                            "StartWindowMinutes": start_window,
                            "CompletionWindowMinutes": completion_window,
                        }
                    ],
                },
                BackupPlanTags={
                    "gui4aws:demo": "true",
                    "Name": plan_name,
                    DEMO_DESC_TAG_KEY: description,
                },
            )
            plan_id = resp.get("BackupPlanId", plan_name)
            logger.info("created backup plan %s (id=%s)", plan_name, plan_id)
            created["backup_plans"].append(plan_id)

            # Add a selection to each plan targeting the demo tag
            try:
                backup.create_backup_selection(
                    BackupPlanId=plan_id,
                    BackupSelection={
                        "SelectionName": f"{plan_name}-selection",
                        "IamRoleArn": "arn:aws:iam::123456789012:role/DemoBackupRole",
                        "ListOfTags": [
                            {
                                "ConditionType": "STRINGEQUALS",
                                "ConditionKey": "gui4aws:demo",
                                "ConditionValue": "true",
                            }
                        ],
                    },
                )
                logger.info("created backup selection for plan %s", plan_name)
                created["backup_selections"].append(f"{plan_name}-selection")
            except Exception as exc:
                logger.warning("skipped backup selection for %s: %s", plan_name, exc)

        except Exception as exc:
            logger.warning("skipped backup plan %s: %s", plan_name, exc)

    if extended and rds is not None and created["backup_vaults"]:
        _seed_backup_jobs(backup, rds, created)

    return created


def _seed_backup_jobs(backup: Any, rds: Any, created: dict[str, list[str]]) -> None:
    """Create on-demand backup jobs for demo clusters so recovery points exist."""
    try:
        clusters = rds.describe_db_clusters().get("DBClusters", [])
    except Exception as exc:
        logger.warning("could not list RDS clusters for backup seeding: %s", exc)
        return

    vault_name = created["backup_vaults"][0] if created["backup_vaults"] else "demo-daily-vault"
    demo_role = "arn:aws:iam::123456789012:role/DemoBackupRole"

    for cluster in clusters[:2]:
        cluster_arn = cluster.get("DBClusterArn", "")
        cluster_id = cluster.get("DBClusterIdentifier", "")
        if not cluster_arn:
            continue
        try:
            resp = backup.start_backup_job(
                BackupVaultName=vault_name,
                ResourceArn=cluster_arn,
                IamRoleArn=demo_role,
            )
            job_id = resp.get("BackupJobId", "")
            rp_arn = resp.get("RecoveryPointArn", "")
            logger.info("started backup job %s for cluster %s -> recovery point %s", job_id, cluster_id, rp_arn)
            created["backup_jobs"].append(job_id)
            if rp_arn:
                created["recovery_points"].append(rp_arn)
        except Exception as exc:
            logger.warning("skipped backup job for cluster %s: %s", cluster_id, exc)


def _seed_kms(kms: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"kms_keys": [], "kms_aliases": []}

    key_specs = [
        ("Demo symmetric encryption key for application data", "ENCRYPT_DECRYPT", "SYMMETRIC_DEFAULT"),
        ("Demo asymmetric signing key for JWT tokens", "SIGN_VERIFY", "RSA_2048"),
    ]

    aliases = ["alias/demo-app-key", "alias/demo-jwt-signing-key"]

    for (description, key_usage, key_spec), alias_name in zip(key_specs, aliases, strict=True):
        try:
            resp = kms.create_key(
                Description=description,
                KeyUsage=key_usage,
                KeySpec=key_spec,
                Tags=[
                    {"TagKey": "gui4aws:demo", "TagValue": "true"},
                    {"TagKey": "Name", "TagValue": alias_name.replace("alias/", "")},
                ],
            )
            key_id = resp["KeyMetadata"]["KeyId"]
            logger.info("created KMS key %s (%s)", key_id, description)
            created["kms_keys"].append(key_id)

            try:
                kms.create_alias(AliasName=alias_name, TargetKeyId=key_id)
                logger.info("created KMS alias %s -> %s", alias_name, key_id)
                created["kms_aliases"].append(alias_name)
            except Exception as exc:
                logger.warning("skipped KMS alias %s: %s", alias_name, exc)

        except Exception as exc:
            logger.warning("skipped KMS key (%s): %s", description, exc)

    return created


def _seed_s3(s3: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"s3_buckets": []}

    buckets = [
        "demo-gui4aws-assets",
        "demo-gui4aws-logs",
        "demo-gui4aws-backups",
    ]

    for bucket_name in buckets:
        try:
            # us-east-1 does not accept a LocationConstraint
            s3.create_bucket(Bucket=bucket_name)
            logger.info("created S3 bucket %s", bucket_name)
            created["s3_buckets"].append(bucket_name)
            try:
                s3.put_bucket_tagging(
                    Bucket=bucket_name,
                    Tagging={
                        "TagSet": _tags(
                            {"Key": "Name", "Value": bucket_name},
                            {"Key": DEMO_DESC_TAG_KEY, "Value": f"Demo bucket: {bucket_name}"},
                        )
                    },
                )
            except Exception as exc:
                logger.warning("skipped tagging bucket %s: %s", bucket_name, exc)
        except Exception as exc:
            logger.warning("skipped S3 bucket %s: %s", bucket_name, exc)

    return created


def _seed_sqs(sqs: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"sqs_queues": []}

    queues = [
        ("demo-orders-queue", "Demo queue for order processing events"),
        ("demo-notifications-queue", "Demo queue for notification dispatch"),
        ("demo-dead-letter-queue", "Demo dead-letter queue for failed messages"),
    ]

    for queue_name, description in queues:
        try:
            resp = sqs.create_queue(
                QueueName=queue_name,
                tags={
                    "gui4aws:demo": "true",
                    "Name": queue_name,
                    DEMO_DESC_TAG_KEY: description,
                },
            )
            queue_url = resp.get("QueueUrl", queue_name)
            logger.info("created SQS queue %s", queue_name)
            created["sqs_queues"].append(queue_url)
        except Exception as exc:
            logger.warning("skipped SQS queue %s: %s", queue_name, exc)

    return created


def _make_lambda_zip() -> bytes:
    """Create a minimal in-memory deployment zip containing a handler module."""
    import io
    import zipfile

    handler_code = (
        "def handler(event, context):\n" '    return {"statusCode": 200, "body": "Hello from gui4aws demo"}\n'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handler.py", handler_code)
    return buf.getvalue()


def _seed_lambda(lambda_client: Any, iam: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"lambda_functions": []}

    zip_bytes = _make_lambda_zip()

    # Moto validates that the role actually exists in IAM, so create it first.
    demo_role_arn = "arn:aws:iam::123456789012:role/DemoLambdaRole"
    try:
        import json

        resp = iam.create_role(
            RoleName="DemoLambdaRole",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            Description="Demo IAM role for gui4aws Lambda functions",
        )
        demo_role_arn = resp["Role"]["Arn"]
        logger.info("created IAM role DemoLambdaRole: %s", demo_role_arn)
    except Exception as exc:
        logger.warning("could not create IAM role DemoLambdaRole: %s", exc)

    functions = [
        (
            "demo-order-processor",
            "python3.11",
            "handler.handler",
            "Demo Lambda: processes orders from SQS",
        ),
        (
            "demo-notification-sender",
            "python3.11",
            "handler.handler",
            "Demo Lambda: sends email/SMS notifications",
        ),
    ]

    for function_name, runtime, handler, description in functions:
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime=runtime,
                Role=demo_role_arn,
                Handler=handler,
                Code={"ZipFile": zip_bytes},
                Description=description,
                Timeout=30,
                MemorySize=128,
                Tags={
                    "gui4aws:demo": "true",
                    "Name": function_name,
                },
            )
            logger.info("created Lambda function %s", function_name)
            created["lambda_functions"].append(function_name)
        except Exception as exc:
            logger.warning("skipped Lambda function %s: %s", function_name, exc)

    return created


def _seed_cloudwatch(cloudwatch: Any, logs: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"cloudwatch_alarms": [], "log_groups": []}

    # Seed metric alarms
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
        except Exception as exc:
            logger.warning("skipped CloudWatch alarm %s: %s", alarm_name, exc)

    # Seed log groups
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
            except Exception as exc:
                logger.warning("skipped retention policy for %s: %s", log_group_name, exc)
        except Exception as exc:
            logger.warning("skipped log group %s: %s", log_group_name, exc)

    return created


def _seed_cloudformation(cfn: Any) -> dict[str, list[str]]:
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
                Tags=_tags(
                    {"Key": "Name", "Value": stack_name},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": description},
                ),
            )
            logger.info("created CloudFormation stack %s", stack_name)
            created["cloudformation_stacks"].append(stack_name)
        except Exception as exc:
            logger.warning("skipped CloudFormation stack %s: %s", stack_name, exc)

    return created


def _seed_sns(sns: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"sns_topics": []}
    topics = [
        ("demo-order-events", "Demo SNS topic for order lifecycle events"),
        ("demo-alerts", "Demo SNS topic for application alerts"),
    ]
    for topic_name, description in topics:
        try:
            resp = sns.create_topic(
                Name=topic_name,
                Tags=[
                    {"Key": "gui4aws:demo", "Value": "true"},
                    {"Key": "Name", "Value": topic_name},
                    {"Key": "Description", "Value": description},
                ],
            )
            topic_arn = resp.get("TopicArn", topic_name)
            logger.info("created SNS topic %s", topic_name)
            created["sns_topics"].append(topic_arn)
        except Exception as exc:
            logger.warning("skipped SNS topic %s: %s", topic_name, exc)
    return created


def _seed_ses(ses: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"ses_identities": []}
    identities = [
        "demo@example.com",
        "noreply@demo.example.com",
    ]
    for email in identities:
        try:
            ses.verify_email_identity(EmailAddress=email)
            logger.info("verified SES email identity %s", email)
            created["ses_identities"].append(email)
        except Exception as exc:
            logger.warning("skipped SES identity %s: %s", email, exc)
    return created


def _seed_iam_extras(iam: Any) -> dict[str, list[str]]:
    """Seed additional IAM resources (users, groups, policies) beyond the Lambda role."""
    import json

    created: dict[str, list[str]] = {"iam_users": [], "iam_groups": [], "iam_policies": []}

    # Groups
    groups = [
        ("demo-developers", "/demo/"),
        ("demo-operators", "/demo/"),
        ("demo-readonly", "/demo/"),
    ]
    for group_name, path in groups:
        try:
            iam.create_group(GroupName=group_name, Path=path)
            logger.info("created IAM group %s", group_name)
            created["iam_groups"].append(group_name)
        except Exception as exc:
            logger.warning("skipped IAM group %s: %s", group_name, exc)

    # Users
    users = [
        ("demo-alice", "/demo/", "demo-developers"),
        ("demo-bob", "/demo/", "demo-operators"),
        ("demo-charlie", "/demo/", "demo-readonly"),
    ]
    for user_name, path, group_name in users:
        try:
            iam.create_user(UserName=user_name, Path=path, Tags=_tags({"Key": "Name", "Value": user_name}))
            logger.info("created IAM user %s", user_name)
            created["iam_users"].append(user_name)
        except Exception as exc:
            logger.warning("skipped IAM user %s: %s", user_name, exc)
        if group_name in created["iam_groups"]:
            try:
                iam.add_user_to_group(GroupName=group_name, UserName=user_name)
            except Exception as exc:
                logger.warning("skipped adding %s to %s: %s", user_name, group_name, exc)

    # Customer-managed policy
    policy_doc = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Action": ["s3:GetObject", "s3:ListBucket"],
                "Resource": ["arn:aws:s3:::demo-gui4aws-assets", "arn:aws:s3:::demo-gui4aws-assets/*"],
            }
        ],
    }
    try:
        resp = iam.create_policy(
            PolicyName="demo-s3-readonly-policy",
            Path="/demo/",
            PolicyDocument=json.dumps(policy_doc),
            Description="Demo policy: read-only access to demo S3 bucket",
        )
        policy_arn = resp["Policy"]["Arn"]
        logger.info("created IAM policy demo-s3-readonly-policy: %s", policy_arn)
        created["iam_policies"].append(policy_arn)
    except Exception as exc:
        logger.warning("skipped IAM policy demo-s3-readonly-policy: %s", exc)

    return created
