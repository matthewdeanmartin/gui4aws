"""ServiceDefinition for ECS."""

from __future__ import annotations

from gui4aws.models import (
    EagerChoiceSource,
    InputField,
    NavigationItem,
    RowAction,
    ServiceDefinition,
    SubAction,
)
from gui4aws.services.ecs.actions import (
    ALL_ACTIONS,
    CREATE_CLUSTER,
    CREATE_SERVICE,
    DELETE_CLUSTER,
    DELETE_SERVICE,
    DEREGISTER_TASK_DEFINITION,
    DESCRIBE_TASK_DEFINITION,
    DESCRIBE_TASKS,
    LIST_CLUSTERS,
    LIST_SERVICES,
    LIST_TASK_DEFINITIONS,
    LIST_TASKS,
    RUN_TASK,
    STOP_TASK,
    UPDATE_SERVICE,
)

__all__ = ["SERVICE"]


_CLUSTERS_SOURCE = EagerChoiceSource(
    action_id=LIST_CLUSTERS.action_id,
    jmespath="clusterArns[]",
)


SERVICE = ServiceDefinition(
    service_id="ecs",
    display_name="ECS",
    boto3_service_name="ecs",
    cli_service_name="ecs",
    navigation_items=(
        # ── Clusters ──────────────────────────────────────────────────────────
        NavigationItem(
            item_id="clusters",
            display_name="Clusters",
            default_action_id=LIST_CLUSTERS.action_id,
            sub_action=SubAction(
                action_id=LIST_SERVICES.action_id,
                panel_label="Services in cluster",
                prefill={"cluster": "cluster_name"},
                columns=("service_name", "status", "desired_count", "running_count", "launch_type"),
            ),
            row_actions=(
                RowAction(
                    action_id=CREATE_CLUSTER.action_id,
                    button_label="Create Cluster",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_CLUSTER.action_id,
                    button_label="Delete Cluster",
                    prefill={"cluster": "cluster_name"},
                ),
            ),
        ),
        # ── Services ──────────────────────────────────────────────────────────
        NavigationItem(
            item_id="services",
            display_name="Services",
            default_action_id=LIST_SERVICES.action_id,
            filter_fields=(
                InputField(
                    name="cluster",
                    label="Cluster",
                    kind="choice",
                    required=True,
                    help_text="Pick a cluster to list its services.",
                ),
            ),
            eager_choices={"cluster": _CLUSTERS_SOURCE},
            row_actions=(
                RowAction(
                    action_id=UPDATE_SERVICE.action_id,
                    button_label="Update Service",
                    prefill={"service": "service_name", "cluster": "cluster_name"},
                ),
                RowAction(
                    action_id=CREATE_SERVICE.action_id,
                    button_label="Create Service",
                    prefill={"cluster": "cluster_name"},
                ),
                RowAction(
                    action_id=DELETE_SERVICE.action_id,
                    button_label="Delete Service",
                    prefill={"service": "service_name", "cluster": "cluster_name"},
                ),
            ),
        ),
        # ── Tasks ─────────────────────────────────────────────────────────────
        NavigationItem(
            item_id="tasks",
            display_name="Tasks",
            default_action_id=LIST_TASKS.action_id,
            filter_fields=(
                InputField(
                    name="cluster",
                    label="Cluster",
                    kind="choice",
                    required=True,
                ),
                InputField(
                    name="service_name",
                    label="Service",
                    kind="choice",
                    required=False,
                    help_text="Optional — leave blank to list all tasks in the cluster.",
                ),
            ),
            eager_choices={
                "cluster": _CLUSTERS_SOURCE,
                "service_name": EagerChoiceSource(
                    action_id=LIST_SERVICES.action_id,
                    jmespath="serviceArns[]",
                    depends_on={"cluster": "cluster"},
                ),
            },
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_TASKS.action_id,
                    button_label="Describe Task",
                    prefill={"tasks": "arn", "cluster": "cluster_name"},
                ),
                RowAction(
                    action_id=RUN_TASK.action_id,
                    button_label="Run Task",
                    prefill={"cluster": "cluster_name", "task_definition": "task_definition"},
                ),
                RowAction(
                    action_id=STOP_TASK.action_id,
                    button_label="Stop Task",
                    prefill={"task": "arn", "cluster": "cluster_name"},
                ),
            ),
        ),
        # ── Task Definitions ──────────────────────────────────────────────────
        NavigationItem(
            item_id="task_definitions",
            display_name="Task Definitions",
            default_action_id=LIST_TASK_DEFINITIONS.action_id,
            filter_fields=(
                InputField(
                    name="family_prefix",
                    label="Family prefix",
                    required=False,
                    help_text="Optional filter by task family prefix.",
                ),
                InputField(
                    name="status",
                    label="Status",
                    kind="choice",
                    choices=("", "ACTIVE", "INACTIVE"),
                    required=False,
                ),
            ),
            row_actions=(
                RowAction(
                    action_id=DESCRIBE_TASK_DEFINITION.action_id,
                    button_label="Describe",
                    prefill={"task_definition": "task_definition_arn"},
                ),
                RowAction(
                    action_id=DEREGISTER_TASK_DEFINITION.action_id,
                    button_label="Deregister",
                    prefill={"task_definition": "task_definition_arn"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
