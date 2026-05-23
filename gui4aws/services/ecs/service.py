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
    DESCRIBE_TASKS,
    LIST_CLUSTERS,
    LIST_SERVICES,
    LIST_TASKS,
    STOP_TASK,
    UPDATE_SERVICE,
)

__all__ = ["SERVICE"]


# Eager choice source: list clusters and project their names. ECS list_clusters
# returns {"clusterArns": [...]}, so the JMESPath grabs ARNs and the filter bar
# normalises them to short names.
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
        # Selecting a cluster row shows its services in the sub-panel below,
        # which is how grandchild rows (services, tasks) become reachable
        # without making them top-level sidebar entries.
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
                # service_name depends on cluster — re-fetched whenever the
                # cluster dropdown changes value.
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
                    action_id=STOP_TASK.action_id,
                    button_label="Stop Task",
                    prefill={"task": "arn", "cluster": "cluster_name"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
