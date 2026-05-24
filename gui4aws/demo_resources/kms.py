"""Seed demo KMS keys and aliases."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def seed_kms(kms: Any) -> dict[str, list[str]]:
    """Seed KMS keys and aliases for cryptographic operations.

    Creates both symmetric and asymmetric keys with descriptive aliases to demonstrate
    how the GUI handles encryption keys and their metadata.
    """
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
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped KMS alias %s: %s", alias_name, exc)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped KMS key (%s): %s", description, exc)

    return created
