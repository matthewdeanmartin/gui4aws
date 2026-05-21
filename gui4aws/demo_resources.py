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
) -> dict[str, list[str]]:
    """Create demo resources and return a report of what was created.

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

    created.update(_seed_aurora(client("rds")))
    created.update(_seed_backup(client("backup")))

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
        cluster_id = spec["DBClusterIdentifier"]
        engine = spec["Engine"]
        try:
            rds.create_db_cluster(**spec)
            logger.info("created Aurora cluster %s", cluster_id)
            created["aurora_clusters"].append(cluster_id)
        except Exception as exc:
            logger.warning("skipped cluster %s: %s", cluster_id, exc)
            continue

        # Create one writer instance per cluster so Instances view has data.
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

    # Create a manual snapshot from the first cluster if it was created.
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


def _seed_backup(backup: Any) -> dict[str, list[str]]:
    created: dict[str, list[str]] = {"backup_vaults": [], "backup_plans": []}

    vaults = [
        ("demo-daily-vault", "Demo vault for daily backups"),
        ("demo-weekly-vault", "Demo vault for weekly backups"),
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

    # Seed a backup plan targeting the daily vault.
    if created["backup_vaults"]:
        plan_name = "demo-daily-plan"
        try:
            backup.create_backup_plan(
                BackupPlan={
                    "BackupPlanName": plan_name,
                    "Rules": [
                        {
                            "RuleName": "daily-rule",
                            "TargetBackupVaultName": created["backup_vaults"][0],
                            "ScheduleExpression": "cron(0 5 ? * * *)",
                            "StartWindowMinutes": 60,
                            "CompletionWindowMinutes": 180,
                        }
                    ],
                },
                BackupPlanTags={
                    "gui4aws:demo": "true",
                    "Name": plan_name,
                    DEMO_DESC_TAG_KEY: "Demo daily backup plan",
                },
            )
            logger.info("created backup plan %s", plan_name)
            created["backup_plans"].append(plan_name)
        except Exception as exc:
            logger.warning("skipped backup plan %s: %s", plan_name, exc)

    return created
