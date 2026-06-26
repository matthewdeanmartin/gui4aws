"""Seed demo AWS resources so the GUI has something to browse immediately.

All resources are tagged with ``gui4aws:demo = true`` and given descriptive names so
users can immediately distinguish demo data from real infrastructure.

This package only writes resources; it never deletes.

**Safety:** demo data must never land on real AWS. :func:`seed_demo_resources`
requires a :class:`~gui4aws.demo_resources.verification.VerifiedEmulator` proof
token, which is only obtainable by probing an endpoint and positively confirming
it is a Moto or Robotocore emulator (see ``verification.py``). There is no code
path that writes demo resources to an unverified target.
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
from gui4aws.demo_resources.verification import (
    EmulatorVerificationError,
    VerifiedEmulator,
    verify_emulator,
)

__all__ = [
    "EmulatorVerificationError",
    "VerifiedEmulator",
    "seed_demo_resources",
    "verify_emulator",
]

logger = logging.getLogger(__name__)


def seed_demo_resources(
    emulator: VerifiedEmulator,
    *,
    region_name: str = "us-east-1",
    profile_name: str | None = None,
) -> dict[str, list[str]]:
    """Create demo resources against a **verified** local emulator.

    Args:
        emulator: Proof that the target endpoint was confirmed to be Moto or
            Robotocore. Obtain via
            :func:`~gui4aws.demo_resources.verification.verify_emulator`.
        region_name: AWS region to create resources in.
        profile_name: Optional AWS profile (credentials are irrelevant against an
            emulator, but kept for session parity).

    Returns:
        A dict mapping resource type to the list of identifiers created.

    Richer demo data (backup jobs, restore jobs, ECS services with tasks, etc.)
    is seeded for Robotocore, which has broader API coverage than Moto.
    """
    import boto3

    endpoint_url = emulator.endpoint_url
    session: Any
    if profile_name:
        session = boto3.Session(profile_name=profile_name, region_name=region_name)
    else:
        session = boto3.Session(region_name=region_name)

    def client(service: str) -> Any:
        return session.client(service, endpoint_url=endpoint_url)

    return _seed_with_client_factory(client, is_robotocore=emulator.is_robotocore)


def _seed_with_client_factory(
    client: Any,
    *,
    is_robotocore: bool,
) -> dict[str, list[str]]:
    """Run every seeder using *client* (a ``service -> boto3 client`` factory).

    Split out from :func:`seed_demo_resources` so tests using the in-process
    ``moto.mock_aws`` patcher (which has no HTTP endpoint to verify) can seed
    directly without bypassing the verification guard on the public path.
    """
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
