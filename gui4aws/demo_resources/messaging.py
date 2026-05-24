"""Seed demo SNS topics and SES verified identities."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def seed_sns(sns: Any) -> dict[str, list[str]]:
    """Seed SNS topics for notification workflows.

    Creates topics for events and alerts to illustrate how the GUI displays
    pub/sub infrastructure.
    """
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped SNS topic %s: %s", topic_name, exc)
    return created


def seed_ses(ses: Any) -> dict[str, list[str]]:
    """Seed SES verified email identities.

    Creates sample identities to demonstrate how the GUI visualizes email
    sending configurations.
    """
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped SES identity %s: %s", email, exc)
    return created
