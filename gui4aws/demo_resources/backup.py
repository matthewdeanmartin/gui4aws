"""Seed demo AWS Backup vaults, plans, selections, and jobs."""

from __future__ import annotations

import logging
from typing import Any

from gui4aws.demo_resources._common import DEMO_DESC_TAG_KEY

logger = logging.getLogger(__name__)


def seed_backup(backup: Any, rds: Any | None = None, *, extended: bool = False) -> dict[str, list[str]]:
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped vault %s: %s", vault_name, exc)

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
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped backup selection for %s: %s", plan_name, exc)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped backup plan %s: %s", plan_name, exc)

    if extended and rds is not None and created["backup_vaults"]:
        _seed_backup_jobs(backup, rds, created)

    return created


def _seed_backup_jobs(backup: Any, rds: Any, created: dict[str, list[str]]) -> None:
    """Create on-demand backup jobs for demo clusters so recovery points exist."""
    try:
        clusters = rds.describe_db_clusters().get("DBClusters", [])
    except Exception as exc:  # pylint: disable=broad-exception-caught
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
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped backup job for cluster %s: %s", cluster_id, exc)
