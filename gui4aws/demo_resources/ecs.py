"""Seed demo ECS clusters, task definitions, and services."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def seed_ecs(ecs: Any, *, extended: bool = False) -> dict[str, list[str]]:
    """Seed ECS resources.

    ``extended=True`` seeds task definitions and services — requires
    robotocore (Moto's ECS write path is limited).
    """
    created: dict[str, list[str]] = {
        "ecs_clusters": [],
        "ecs_task_definitions": [],
        "ecs_services": [],
        "ecs_tasks": [],
    }

    cluster_name = "demo-cluster"
    try:
        ecs.create_cluster(
            clusterName=cluster_name,
            tags=[
                {"key": "gui4aws:demo", "value": "true"},
                {"key": "Name", "value": cluster_name},
                {"key": "Description", "value": "Demo ECS cluster for gui4aws"},
            ],
        )
        logger.info("created ECS cluster %s", cluster_name)
        created["ecs_clusters"].append(cluster_name)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("skipped ECS cluster %s: %s", cluster_name, exc)

    if not extended:
        return created

    task_defs = [
        {
            "family": "demo-web",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [
                {
                    "name": "web",
                    "image": "nginx:latest",
                    "portMappings": [{"containerPort": 80, "protocol": "tcp"}],
                    "essential": True,
                }
            ],
        },
        {
            "family": "demo-worker",
            "networkMode": "awsvpc",
            "requiresCompatibilities": ["FARGATE"],
            "cpu": "256",
            "memory": "512",
            "containerDefinitions": [
                {
                    "name": "worker",
                    "image": "busybox:latest",
                    "command": ["sleep", "3600"],
                    "essential": True,
                }
            ],
        },
    ]

    registered_families: list[str] = []
    for td in task_defs:
        try:
            resp = ecs.register_task_definition(**td)
            td_arn = resp["taskDefinition"]["taskDefinitionArn"]
            family = str(td["family"])
            logger.info("registered task definition %s", td_arn)
            created["ecs_task_definitions"].append(td_arn)
            registered_families.append(family)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped task definition %s: %s", td["family"], exc)

    if registered_families and created["ecs_clusters"]:
        services = [
            {
                "cluster": cluster_name,
                "serviceName": "demo-web-svc",
                "taskDefinition": "demo-web",
                "desiredCount": 2,
                "launchType": "FARGATE",
            },
            {
                "cluster": cluster_name,
                "serviceName": "demo-worker-svc",
                "taskDefinition": "demo-worker",
                "desiredCount": 1,
                "launchType": "FARGATE",
            },
        ]
        for svc in services:
            service_name = str(svc["serviceName"])
            try:
                ecs.create_service(**svc)
                logger.info("created ECS service %s", service_name)
                created["ecs_services"].append(service_name)
            except Exception as exc:  # pylint: disable=broad-exception-caught
                logger.warning("skipped ECS service %s: %s", service_name, exc)

    return created
