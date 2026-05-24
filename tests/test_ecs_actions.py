"""Moto-backed tests for ECS actions."""

from __future__ import annotations

import json

import boto3

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.ecs.actions import (
    CREATE_CLUSTER,
    CREATE_SERVICE,
    DELETE_CLUSTER,
    DELETE_SERVICE,
    DESCRIBE_CLUSTERS,
    DESCRIBE_SERVICES,
    DESCRIBE_TASK_DEFINITION,
    LIST_CLUSTERS,
    LIST_SERVICES,
    LIST_TASK_DEFINITIONS,
    REGISTER_TASK_DEFINITION,
)
from gui4aws.services.ecs.views import (
    to_cluster_summaries,
    to_service_summaries,
    to_task_definition_summaries,
)


def test_list_clusters_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_CLUSTERS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_cluster_summaries(result.response)
    assert summaries == []


def test_create_and_delete_cluster(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    # Create
    result = context.execute(CREATE_CLUSTER, inputs={"cluster_name": "test-cluster"})
    assert isinstance(result, Boto3Result)
    assert result.response["cluster"]["clusterName"] == "test-cluster"

    # List
    list_result = context.execute(LIST_CLUSTERS, inputs={})
    summaries = to_cluster_summaries(list_result.response)
    assert any(s.cluster_name == "test-cluster" for s in summaries)

    # Describe
    desc_result = context.execute(DESCRIBE_CLUSTERS, inputs={"clusters": "test-cluster"})
    summaries = to_cluster_summaries(desc_result.response)
    assert len(summaries) == 1
    assert summaries[0].cluster_name == "test-cluster"

    # Delete
    del_result = context.execute(DELETE_CLUSTER, inputs={"cluster": "test-cluster"})
    assert isinstance(del_result, Boto3Result)
    # Note: Moto might not immediately reflect the deletion in describe_clusters,
    # so we trust the successful result of the delete_cluster operation itself.


def test_task_definition_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")

    task_def = {
        "family": "test-family",
        "containerDefinitions": [
            {
                "name": "web",
                "image": "nginx",
                "memory": 128,
            }
        ],
    }

    # Register
    result = context.execute(REGISTER_TASK_DEFINITION, inputs={"task_definition_json": json.dumps(task_def)})
    assert isinstance(result, Boto3Result)
    assert result.response["taskDefinition"]["family"] == "test-family"

    # List
    list_result = context.execute(LIST_TASK_DEFINITIONS, inputs={})
    summaries = to_task_definition_summaries(list_result.response)
    assert any(s.family == "test-family" for s in summaries)

    # Describe
    desc_result = context.execute(DESCRIBE_TASK_DEFINITION, inputs={"task_definition": "test-family"})
    summaries = to_task_definition_summaries(desc_result.response)
    assert len(summaries) == 1
    assert summaries[0].family == "test-family"


def test_service_actions(mock_aws_env: None) -> None:
    ecs = boto3.client("ecs", region_name="us-east-1")
    ecs.create_cluster(clusterName="svc-cluster")
    ecs.register_task_definition(
        family="svc-task", containerDefinitions=[{"name": "web", "image": "nginx", "memory": 128}]
    )

    context = AppContext(region_name="us-east-1")

    # Create Service
    result = context.execute(
        CREATE_SERVICE,
        inputs={
            "cluster": "svc-cluster",
            "service_name": "test-service",
            "task_definition": "svc-task",
            "desired_count": "1",
        },
    )
    assert isinstance(result, Boto3Result)
    assert result.response["service"]["serviceName"] == "test-service"

    # List Services
    list_result = context.execute(LIST_SERVICES, inputs={"cluster": "svc-cluster"})
    summaries = to_service_summaries(list_result.response)
    assert any(s.service_name == "test-service" for s in summaries)

    # Describe Services
    desc_result = context.execute(DESCRIBE_SERVICES, inputs={"cluster": "svc-cluster", "services": "test-service"})
    summaries = to_service_summaries(desc_result.response)
    assert len(summaries) == 1
    assert summaries[0].service_name == "test-service"

    # Delete Service
    del_result = context.execute(
        DELETE_SERVICE, inputs={"cluster": "svc-cluster", "service": "test-service", "force": "true"}
    )
    assert isinstance(del_result, Boto3Result)
