"""Seed demo Aurora clusters, instances, and snapshots."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import DEMO_DESC_TAG_KEY, tags

logger = logging.getLogger(__name__)


def seed_aurora(rds: Any) -> dict[str, list[str]]:
    """Seed demo Aurora clusters, instances, and snapshots.

    Creates both MySQL and PostgreSQL clusters with associated instances and a sample
    snapshot to demonstrate RDS resource browsing and management in the GUI.
    """
    created: dict[str, list[str]] = {"aurora_clusters": [], "aurora_instances": [], "aurora_snapshots": []}

    clusters = [
        {
            "DBClusterIdentifier": "demo-aurora-mysql-prod",
            "Engine": "aurora-mysql",
            "MasterUsername": "admin",
            "MasterUserPassword": "DemoPass123!",
            "Tags": tags(
                {"Key": "Name", "Value": "demo-aurora-mysql-prod"},
                {"Key": DEMO_DESC_TAG_KEY, "Value": "Demo Aurora MySQL cluster (production-like)"},
            ),
        },
        {
            "DBClusterIdentifier": "demo-aurora-pg-analytics",
            "Engine": "aurora-postgresql",
            "MasterUsername": "postgres",
            "MasterUserPassword": "DemoPass123!",
            "Tags": tags(
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped cluster %s: %s", cluster_id, exc)
            continue

        instance_id = f"{cluster_id}-instance-1"
        try:
            rds.create_db_instance(
                DBInstanceIdentifier=instance_id,
                DBInstanceClass="db.t3.medium",
                Engine=engine,
                DBClusterIdentifier=cluster_id,
                Tags=tags(
                    {"Key": "Name", "Value": instance_id},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": f"Demo instance for {cluster_id}"},
                ),
            )
            logger.info("created Aurora instance %s", instance_id)
            created["aurora_instances"].append(instance_id)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped instance %s: %s", instance_id, exc)

    if created["aurora_clusters"]:
        source = created["aurora_clusters"][0]
        snap_id = f"{source}-demo-snapshot"
        try:
            rds.create_db_cluster_snapshot(
                DBClusterIdentifier=source,
                DBClusterSnapshotIdentifier=snap_id,
                Tags=tags(
                    {"Key": "Name", "Value": snap_id},
                    {"Key": DEMO_DESC_TAG_KEY, "Value": "Demo snapshot — safe to restore"},
                ),
            )
            logger.info("created Aurora snapshot %s", snap_id)
            created["aurora_snapshots"].append(snap_id)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped snapshot %s: %s", snap_id, exc)

    return created
