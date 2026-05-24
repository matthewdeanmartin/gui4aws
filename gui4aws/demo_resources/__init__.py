"""Seed demo AWS resources so the GUI has something to browse immediately.

All resources are tagged with ``gui4aws:demo = true`` and given descriptive names so
users can immediately distinguish demo data from real infrastructure.

This package only writes resources; it never deletes. Call :func:`seed_demo_resources`
with a boto3 session (or endpoint_url for moto server mode) to create the assets.
"""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources.aurora import seed_aurora
from gui4aws.demo_resources.backup import seed_backup
from gui4aws.demo_resources.compute import seed_lambda
from gui4aws.demo_resources.ecs import seed_ecs
from gui4aws.demo_resources.iam_resources import seed_iam_extras
from gui4aws.demo_resources.kms import seed_kms
from gui4aws.demo_resources.messaging import seed_ses, seed_sns
from gui4aws.demo_resources.monitoring import seed_cloudformation, seed_cloudwatch
from gui4aws.demo_resources.networking import seed_networking
from gui4aws.demo_resources.secrets import seed_secrets, seed_ssm
from gui4aws.demo_resources.storage import seed_s3, seed_sqs

__all__ = ["seed_demo_resources"]

logger = logging.getLogger(__name__)


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
    created.update(seed_aurora(rds_client))
    created.update(seed_backup(client("backup"), rds_client, extended=is_robotocore))
    created.update(seed_networking(client("ec2"), client("elbv2")))
    created.update(seed_ecs(client("ecs"), extended=is_robotocore))
    created.update(seed_secrets(client("secretsmanager")))
    created.update(seed_ssm(client("ssm")))
    created.update(seed_kms(client("kms")))
    created.update(seed_s3(client("s3")))
    created.update(seed_sqs(client("sqs")))
    created.update(seed_lambda(client("lambda"), client("iam")))
    created.update(seed_cloudwatch(client("cloudwatch"), client("logs")))
    created.update(seed_cloudformation(client("cloudformation")))
    created.update(seed_sns(client("sns")))
    created.update(seed_ses(client("ses")))
    created.update(seed_iam_extras(client("iam")))

    return created
