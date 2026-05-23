"""ECS action definitions."""

from __future__ import annotations

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.ecs.views import to_cluster_summaries, to_service_summaries, to_task_summaries

__all__ = [
    "ALL_ACTIONS",
    "DESCRIBE_CLUSTERS",
    "DESCRIBE_SERVICES",
    "DESCRIBE_TASKS",
    "LIST_CLUSTERS",
    "LIST_SERVICES",
    "LIST_TASKS",
    "STOP_TASK",
    "UPDATE_SERVICE",
]


LIST_CLUSTERS = ActionDefinition(
    action_id="ecs.list_clusters",
    display_name="List clusters",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="ecs", command="list-clusters", arg_map={}),
    boto3_template=Boto3Template(service="ecs", operation="list_clusters", param_map={}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("cluster_name", "status", "running_tasks", "pending_tasks", "active_services"),
        title="ECS Clusters",
    ),
    iam_permissions=("ecs:ListClusters",),
    description="List ECS clusters in the current region.",
    view=to_cluster_summaries,
)


DESCRIBE_CLUSTERS = ActionDefinition(
    action_id="ecs.describe_clusters",
    display_name="Describe clusters",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="clusters",
            label="Cluster names or ARNs (comma-sep)",
            kind="list",
            required=False,
            help_text="Leave blank to describe all clusters.",
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="describe-clusters",
        arg_map={"clusters": "clusters"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="describe_clusters",
        param_map={"clusters": "clusters"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("cluster_name", "status", "running_tasks", "pending_tasks", "active_services"),
        title="ECS Clusters",
    ),
    iam_permissions=("ecs:DescribeClusters",),
    description="Describe one or more ECS clusters by name or ARN.",
    view=to_cluster_summaries,
)


LIST_SERVICES = ActionDefinition(
    action_id="ecs.list_services",
    display_name="List services",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster",
            label="Cluster name or ARN",
            required=False,
            help_text="Leave blank for the default cluster.",
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="list-services",
        arg_map={"cluster": "cluster"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="list_services",
        param_map={"cluster": "cluster"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("service_name", "status", "desired_count", "running_count", "pending_count", "launch_type"),
        title="ECS Services",
    ),
    iam_permissions=("ecs:ListServices",),
    description="List ECS services in a cluster.",
    view=to_service_summaries,
)


DESCRIBE_SERVICES = ActionDefinition(
    action_id="ecs.describe_services",
    display_name="Describe services",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster",
            label="Cluster name or ARN",
            required=True,
        ),
        InputField(
            name="services",
            label="Service names or ARNs (comma-sep)",
            kind="list",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="describe-services",
        arg_map={"cluster": "cluster", "services": "services"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="describe_services",
        param_map={"cluster": "cluster", "services": "services"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("service_name", "status", "desired_count", "running_count", "pending_count", "launch_type"),
        title="ECS Services",
    ),
    iam_permissions=("ecs:DescribeServices",),
    description="Describe specific ECS services (cluster + service names required).",
    view=to_service_summaries,
)


LIST_TASKS = ActionDefinition(
    action_id="ecs.list_tasks",
    display_name="List tasks",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster",
            label="Cluster name or ARN",
            required=False,
            help_text="Leave blank for the default cluster.",
        ),
        InputField(
            name="service_name",
            label="Service name (optional filter)",
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="list-tasks",
        arg_map={"cluster": "cluster", "service_name": "service-name"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="list_tasks",
        param_map={"cluster": "cluster", "service_name": "serviceName"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("task_id", "cluster_name", "last_status", "desired_status", "launch_type"),
        title="ECS Tasks",
    ),
    iam_permissions=("ecs:ListTasks",),
    description="List tasks in a cluster or service.",
    view=to_task_summaries,
)


DESCRIBE_TASKS = ActionDefinition(
    action_id="ecs.describe_tasks",
    display_name="Describe tasks",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="cluster",
            label="Cluster name or ARN",
            required=False,
        ),
        InputField(
            name="tasks",
            label="Task ARNs or IDs (comma-sep)",
            kind="list",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="describe-tasks",
        arg_map={"cluster": "cluster", "tasks": "tasks"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="describe_tasks",
        param_map={"cluster": "cluster", "tasks": "tasks"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("task_id", "cluster_name", "last_status", "desired_status", "launch_type"),
        title="ECS Tasks",
    ),
    iam_permissions=("ecs:DescribeTasks",),
    description="Describe one or more ECS tasks by ARN or ID.",
    view=to_task_summaries,
)


UPDATE_SERVICE = ActionDefinition(
    action_id="ecs.update_service",
    display_name="Update service",
    service_id="ecs",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="cluster", label="Cluster name or ARN", required=True),
        InputField(name="service", label="Service name or ARN", required=True),
        InputField(name="desired_count", label="Desired count", kind="int", required=False),
        InputField(name="task_definition", label="Task definition (optional)", required=False),
        InputField(
            name="force_new_deployment",
            label="Force new deployment",
            kind="bool",
            required=False,
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="update-service",
        arg_map={
            "cluster": "cluster",
            "service": "service",
            "desired_count": "desired-count",
            "task_definition": "task-definition",
            "force_new_deployment": "force-new-deployment",
        },
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="update_service",
        param_map={
            "cluster": "cluster",
            "service": "service",
            "desired_count": "desiredCount",
            "task_definition": "taskDefinition",
            "force_new_deployment": "forceNewDeployment",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Update result"),
    iam_permissions=("ecs:UpdateService",),
    description="Update an ECS service — change desired count, task definition, or force a new deployment.",
    cache_refresh_nav_ids=("clusters", "services", "tasks"),
)


STOP_TASK = ActionDefinition(
    action_id="ecs.stop_task",
    display_name="Stop task",
    service_id="ecs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="cluster", label="Cluster name or ARN", required=False),
        InputField(name="task", label="Task ARN or ID", required=True),
        InputField(name="reason", label="Reason", required=False, default="Stopped via gui4aws"),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="stop-task",
        arg_map={"cluster": "cluster", "task": "task", "reason": "reason"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="stop_task",
        param_map={"cluster": "cluster", "task": "task", "reason": "reason"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Stop task result"),
    iam_permissions=("ecs:StopTask",),
    description="Stop a running ECS task.",
    cache_refresh_nav_ids=("clusters", "services", "tasks"),
)


ALL_ACTIONS = (
    LIST_CLUSTERS,
    DESCRIBE_CLUSTERS,
    LIST_SERVICES,
    DESCRIBE_SERVICES,
    LIST_TASKS,
    DESCRIBE_TASKS,
    UPDATE_SERVICE,
    STOP_TASK,
)
