"""Seed demo Secrets Manager and SSM Parameter Store resources."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import tags

logger = logging.getLogger(__name__)


def seed_secrets(sm: Any) -> dict[str, list[str]]:
    """Seed demo secrets in AWS Secrets Manager.

    Populates common secret types like database credentials and API keys to demonstrate
    secret management and metadata viewing capabilities.
    """
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
                Tags=tags({"Key": "Name", "Value": name}),
            )
            logger.info("created secret %s", name)
            created["secrets"].append(name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped secret %s: %s", name, exc)

    return created


def seed_ssm(ssm: Any) -> dict[str, list[str]]:
    """Seed demo parameters in SSM Parameter Store.

    Creates various parameter types including application config and feature flags
    to showcase parameter exploration.
    """
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
                Tags=tags({"Key": "Name", "Value": name}),
            )
            logger.info("created SSM parameter %s", name)
            created["ssm_parameters"].append(name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped SSM parameter %s: %s", name, exc)

    return created
