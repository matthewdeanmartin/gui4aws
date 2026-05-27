"""ECS action definitions."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.ecs.views import (
    to_cluster_summaries,
    to_service_summaries,
    to_task_definition_summaries,
    to_task_summaries,
)

__all__ = [
    "ALL_ACTIONS",
    "CREATE_CLUSTER",
    "CREATE_SERVICE",
    "DELETE_CLUSTER",
    "DELETE_SERVICE",
    "DEREGISTER_TASK_DEFINITION",
    "DESCRIBE_CLUSTERS",
    "DESCRIBE_SERVICES",
    "DESCRIBE_TASKS",
    "DESCRIBE_TASK_DEFINITION",
    "LIST_CLUSTERS",
    "LIST_DESCRIBE_SERVICES",
    "LIST_SERVICES",
    "LIST_TASKS",
    "LIST_TASK_DEFINITIONS",
    "REGISTER_TASK_DEFINITION",
    "RUN_TASK",
    "STOP_TASK",
    "UPDATE_SERVICE",
]


def create_service_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Map UI inputs to boto3 create_service parameters."""
    params: dict[str, Any] = {
        "cluster": inputs["cluster"],
        "serviceName": inputs["service_name"],
        "taskDefinition": inputs["task_definition"],
        "desiredCount": int(inputs.get("desired_count") or "1"),
    }
    launch_type = inputs.get("launch_type", "FARGATE")
    if launch_type:
        params["launchType"] = launch_type
    return params


def create_service_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map UI inputs to AWS CLI create-service arguments."""
    args = [
        "--cluster",
        inputs["cluster"],
        "--service-name",
        inputs["service_name"],
        "--task-definition",
        inputs["task_definition"],
        "--desired-count",
        inputs.get("desired_count") or "1",
    ]
    if inputs.get("launch_type"):
        args += ["--launch-type", inputs["launch_type"]]
    return args


def register_task_def_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Map UI inputs to boto3 register_task_definition parameters."""
    import json

    raw = inputs.get("task_definition_json", "{}")
    try:
        doc = json.loads(raw)
        if not isinstance(doc, dict):
            return {}
        return cast(dict[str, Any], doc)
    except Exception:  # pylint: disable=broad-exception-caught
        return {}


def register_task_def_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map UI inputs to AWS CLI register-task-definition arguments."""
    return ["--cli-input-json", inputs.get("task_definition_json", "{}")]


def run_task_boto3_params(inputs: Mapping[str, str]) -> dict[str, Any]:
    """Map UI inputs to boto3 run_task parameters."""
    params: dict[str, Any] = {"taskDefinition": inputs["task_definition"]}
    if inputs.get("cluster"):
        params["cluster"] = inputs["cluster"]
    launch_type = inputs.get("launch_type", "FARGATE")
    if launch_type:
        params["launchType"] = launch_type
    count = inputs.get("count")
    if count:
        params["count"] = int(count)
    return params


def run_task_cli_args(inputs: Mapping[str, str]) -> list[str]:
    """Map UI inputs to AWS CLI run-task arguments."""
    args = ["--task-definition", inputs["task_definition"]]
    if inputs.get("cluster"):
        args += ["--cluster", inputs["cluster"]]
    if inputs.get("launch_type"):
        args += ["--launch-type", inputs["launch_type"]]
    if inputs.get("count"):
        args += ["--count", inputs["count"]]
    return args


# ── Clusters ─────────────────────────────────────────────────────────────────

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
        columns=("cluster_name", "status", "running_tasks", "pending_tasks", "active_services", "arn"),
        title="ECS Clusters",
    ),
    iam_permissions=("ecs:DescribeClusters",),
    description="Describe one or more ECS clusters by name or ARN.",
    view=to_cluster_summaries,
)


CREATE_CLUSTER = ActionDefinition(
    action_id="ecs.create_cluster",
    display_name="Create cluster",
    service_id="ecs",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(InputField(name="cluster_name", label="Cluster name", required=True),),
    cli_template=CliTemplate(
        service="ecs",
        command="create-cluster",
        arg_map={"cluster_name": "cluster-name"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="create_cluster",
        param_map={"cluster_name": "clusterName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create cluster result"),
    iam_permissions=("ecs:CreateCluster",),
    description="Create a new ECS cluster.",
    cache_refresh_nav_ids=("clusters",),
)


DELETE_CLUSTER = ActionDefinition(
    action_id="ecs.delete_cluster",
    display_name="Delete cluster",
    service_id="ecs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="cluster", label="Cluster name or ARN", required=True),),
    cli_template=CliTemplate(
        service="ecs",
        command="delete-cluster",
        arg_map={"cluster": "cluster"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="delete_cluster",
        param_map={"cluster": "cluster"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete cluster result"),
    iam_permissions=("ecs:DeleteCluster",),
    description="Delete an empty ECS cluster (all services and tasks must be stopped first).",
    cache_refresh_nav_ids=("clusters",),
)


# ── Services ──────────────────────────────────────────────────────────────────

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


def _list_and_describe_services(client: Any, inputs: Mapping[str, str]) -> dict[str, Any]:
    """List all services in a cluster, then describe them for full status/counts."""
    params: dict[str, Any] = {}
    if inputs.get("cluster"):
        params["cluster"] = inputs["cluster"]
    arns: list[str] = []
    paginator = client.get_paginator("list_services")
    for page in paginator.paginate(**params):
        arns.extend(page.get("serviceArns", []))
    if not arns:
        return {"services": []}
    # describe_services accepts at most 10 per call.
    described: list[Any] = []
    for i in range(0, len(arns), 10):
        chunk = arns[i : i + 10]
        resp = client.describe_services(cluster=inputs.get("cluster", "default"), services=chunk)
        described.extend(resp.get("services", []))
    return {"services": described}


LIST_DESCRIBE_SERVICES = ActionDefinition(
    action_id="ecs.list_describe_services",
    display_name="List services (with status)",
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
    boto3_template=Boto3Template(service="ecs", operation="list_services", param_map={}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("service_name", "status", "desired_count", "running_count", "pending_count", "launch_type"),
        title="ECS Services",
    ),
    iam_permissions=("ecs:ListServices", "ecs:DescribeServices"),
    description="List ECS services in a cluster with full status (list + describe).",
    view=to_service_summaries,
    boto3_execute_fn=_list_and_describe_services,
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
        columns=(
            "service_name",
            "status",
            "desired_count",
            "running_count",
            "pending_count",
            "launch_type",
            "task_definition",
        ),
        title="ECS Services",
    ),
    iam_permissions=("ecs:DescribeServices",),
    description="Describe specific ECS services (cluster + service names required).",
    view=to_service_summaries,
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
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Update service result"),
    iam_permissions=("ecs:UpdateService",),
    description="Update an ECS service — change desired count, task definition, or force a new deployment.",
    cache_refresh_nav_ids=("clusters", "services", "tasks"),
)


CREATE_SERVICE = ActionDefinition(
    action_id="ecs.create_service",
    display_name="Create service",
    service_id="ecs",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="cluster", label="Cluster name or ARN", required=True),
        InputField(name="service_name", label="Service name", required=True),
        InputField(name="task_definition", label="Task definition (family:revision)", required=True),
        InputField(name="desired_count", label="Desired count", kind="int", default="1"),
        InputField(
            name="launch_type",
            label="Launch type",
            kind="choice",
            choices=("FARGATE", "EC2", "EXTERNAL"),
            default="FARGATE",
        ),
    ),
    cli_template=CliTemplate(service="ecs", command="create-service"),
    boto3_template=Boto3Template(service="ecs", operation="create_service"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create service result"),
    iam_permissions=("ecs:CreateService",),
    description=(
        "Create an ECS service. Note: full network configuration (VPC, subnets, security groups, "
        "load balancer) is not exposed here — use the CLI or console for production services."
    ),
    cache_refresh_nav_ids=("clusters", "services"),
    cli_args_builder=create_service_cli_args,
    boto3_params_builder=create_service_boto3_params,
)


DELETE_SERVICE = ActionDefinition(
    action_id="ecs.delete_service",
    display_name="Delete service",
    service_id="ecs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="cluster", label="Cluster name or ARN", required=True),
        InputField(name="service", label="Service name or ARN", required=True),
        InputField(
            name="force",
            label="Force delete (scale to 0 first)",
            kind="bool",
            default="false",
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="delete-service",
        arg_map={"cluster": "cluster", "service": "service", "force": "force"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="delete_service",
        param_map={"cluster": "cluster", "service": "service", "force": "force"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete service result"),
    iam_permissions=("ecs:DeleteService",),
    description="Delete an ECS service. Use force=true to scale to 0 automatically.",
    cache_refresh_nav_ids=("clusters", "services"),
)


# ── Tasks ─────────────────────────────────────────────────────────────────────

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
        columns=("task_id", "cluster_name", "last_status", "desired_status", "launch_type", "task_definition"),
        title="ECS Tasks",
    ),
    iam_permissions=("ecs:DescribeTasks",),
    description="Describe one or more ECS tasks by ARN or ID.",
    view=to_task_summaries,
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


RUN_TASK = ActionDefinition(
    action_id="ecs.run_task",
    display_name="Run task",
    service_id="ecs",
    risk_level=RiskLevel.COST_AFFECTING,
    input_fields=(
        InputField(name="cluster", label="Cluster name or ARN", required=False),
        InputField(name="task_definition", label="Task definition (family:revision)", required=True),
        InputField(
            name="launch_type",
            label="Launch type",
            kind="choice",
            choices=("FARGATE", "EC2", "EXTERNAL"),
            default="FARGATE",
        ),
        InputField(name="count", label="Count", kind="int", default="1"),
    ),
    cli_template=CliTemplate(service="ecs", command="run-task"),
    boto3_template=Boto3Template(service="ecs", operation="run_task"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Run task result"),
    iam_permissions=("ecs:RunTask",),
    description=(
        "Run a one-off ECS task. Note: full network configuration (VPC, subnets, security groups) "
        "is not exposed here — use the CLI or console for production tasks."
    ),
    cache_refresh_nav_ids=("clusters", "tasks"),
    cli_args_builder=run_task_cli_args,
    boto3_params_builder=run_task_boto3_params,
)


# ── Task Definitions ──────────────────────────────────────────────────────────

LIST_TASK_DEFINITIONS = ActionDefinition(
    action_id="ecs.list_task_definitions",
    display_name="List task definitions",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="family_prefix",
            label="Family prefix (optional filter)",
            required=False,
        ),
        InputField(
            name="status",
            label="Status",
            kind="choice",
            choices=("", "ACTIVE", "INACTIVE"),
            required=False,
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="list-task-definitions",
        arg_map={"family_prefix": "family-prefix", "status": "status"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="list_task_definitions",
        param_map={"family_prefix": "familyPrefix", "status": "status"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("task_definition_arn", "family", "revision", "status"),
        title="ECS Task Definitions",
    ),
    iam_permissions=("ecs:ListTaskDefinitions",),
    description="List ECS task definition ARNs, optionally filtered by family prefix or status.",
    view=to_task_definition_summaries,
)


DESCRIBE_TASK_DEFINITION = ActionDefinition(
    action_id="ecs.describe_task_definition",
    display_name="Describe task definition",
    service_id="ecs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="task_definition",
            label="Task definition (family or family:revision)",
            required=True,
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="describe-task-definition",
        arg_map={"task_definition": "task-definition"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="describe_task_definition",
        param_map={"task_definition": "taskDefinition"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("task_definition_arn", "family", "revision", "status"),
        title="Task Definition Detail",
    ),
    iam_permissions=("ecs:DescribeTaskDefinition",),
    description="Describe a specific ECS task definition revision.",
    view=to_task_definition_summaries,
)


REGISTER_TASK_DEFINITION = ActionDefinition(
    action_id="ecs.register_task_definition",
    display_name="Register task definition",
    service_id="ecs",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(
            name="task_definition_json",
            label="Task definition JSON",
            kind="multiline",
            required=True,
            help_text=(
                "Full task definition JSON (family, containerDefinitions, etc.). "
                "See AWS docs for the complete schema."
            ),
        ),
    ),
    cli_template=CliTemplate(service="ecs", command="register-task-definition"),
    boto3_template=Boto3Template(service="ecs", operation="register_task_definition"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Register task definition result"),
    iam_permissions=("ecs:RegisterTaskDefinition",),
    description="Register a new ECS task definition from JSON.",
    cache_refresh_nav_ids=("task_definitions",),
    cli_args_builder=register_task_def_cli_args,
    boto3_params_builder=register_task_def_boto3_params,
)


DEREGISTER_TASK_DEFINITION = ActionDefinition(
    action_id="ecs.deregister_task_definition",
    display_name="Deregister task definition",
    service_id="ecs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="task_definition",
            label="Task definition (family:revision)",
            required=True,
            help_text="Must include revision number, e.g. my-task:3",
        ),
    ),
    cli_template=CliTemplate(
        service="ecs",
        command="deregister-task-definition",
        arg_map={"task_definition": "task-definition"},
    ),
    boto3_template=Boto3Template(
        service="ecs",
        operation="deregister_task_definition",
        param_map={"task_definition": "taskDefinition"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Deregister result"),
    iam_permissions=("ecs:DeregisterTaskDefinition",),
    description="Deregister (mark INACTIVE) a task definition revision.",
    cache_refresh_nav_ids=("task_definitions",),
)


ALL_ACTIONS = (
    LIST_CLUSTERS,
    DESCRIBE_CLUSTERS,
    CREATE_CLUSTER,
    DELETE_CLUSTER,
    LIST_SERVICES,
    LIST_DESCRIBE_SERVICES,
    DESCRIBE_SERVICES,
    UPDATE_SERVICE,
    CREATE_SERVICE,
    DELETE_SERVICE,
    LIST_TASKS,
    DESCRIBE_TASKS,
    STOP_TASK,
    RUN_TASK,
    LIST_TASK_DEFINITIONS,
    DESCRIBE_TASK_DEFINITION,
    REGISTER_TASK_DEFINITION,
    DEREGISTER_TASK_DEFINITION,
)
