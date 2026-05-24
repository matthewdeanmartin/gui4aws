"""Seed demo IAM users, groups, and managed policies."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import tags

logger = logging.getLogger(__name__)


def seed_iam_extras(iam: Any) -> dict[str, list[str]]:
    """Seed additional IAM resources including users, groups, and managed policies.

    Sets up a small hierarchy of users and groups with specific managed policies
    to showcase identity management and permission visualization in the GUI.
    """
    import json

    created: dict[str, list[str]] = {"iam_users": [], "iam_groups": [], "iam_policies": []}

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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped IAM group %s: %s", group_name, exc)

    users = [
        ("demo-alice", "/demo/", "demo-developers"),
        ("demo-bob", "/demo/", "demo-operators"),
        ("demo-charlie", "/demo/", "demo-readonly"),
    ]
    for user_name, path, group_name in users:
        try:
            iam.create_user(UserName=user_name, Path=path, Tags=tags({"Key": "Name", "Value": user_name}))
            logger.info("created IAM user %s", user_name)
            created["iam_users"].append(user_name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped IAM user %s: %s", user_name, exc)
        if group_name in created["iam_groups"]:
            try:
                iam.add_user_to_group(GroupName=group_name, UserName=user_name)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped adding %s to %s: %s", user_name, group_name, exc)

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
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("skipped IAM policy demo-s3-readonly-policy: %s", exc)

    return created
