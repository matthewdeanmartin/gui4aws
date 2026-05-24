"""Seed demo S3 buckets and SQS queues."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import DEMO_DESC_TAG_KEY, tags

logger = logging.getLogger(__name__)


def seed_s3(s3: Any) -> dict[str, list[str]]:
    """Seed demo S3 buckets for various storage use cases.

    Sets up buckets for assets, logs, and backups to illustrate bucket listing,
    tagging, and resource discovery features.
    """
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
                        "TagSet": tags(
                            {"Key": "Name", "Value": bucket_name},
                            {"Key": DEMO_DESC_TAG_KEY, "Value": f"Demo bucket: {bucket_name}"},
                        )
                    },
                )
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped tagging bucket %s: %s", bucket_name, exc)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped S3 bucket %s: %s", bucket_name, exc)

    return created


def seed_sqs(sqs: Any) -> dict[str, list[str]]:
    """Seed SQS queues for message processing scenarios.

    Creates standard and dead-letter queues to showcase how the GUI displays
    messaging infrastructure and its associated metadata.
    """
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped SQS queue %s: %s", queue_name, exc)

    return created
