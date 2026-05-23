"""Shared data models for gui4aws.

These dataclasses describe services, actions, and resources without referring to tkinter or
boto3. They are the contract between service modules, the execution layer, and the GUI.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

__all__ = [
    "ActionDefinition",
    "Boto3ParamsBuilder",
    "Boto3Template",
    "CliArgsBuilder",
    "CliTemplate",
    "EagerChoiceSource",
    "InputField",
    "NavigationItem",
    "ResourceSummary",
    "ResultViewDefinition",
    "ResultViewKind",
    "RiskLevel",
    "RowAction",
    "ServiceDefinition",
    "SubAction",
]


class RiskLevel(StrEnum):
    """How dangerous an action is. Used to gate confirmation flows."""

    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    COST_AFFECTING = "cost_affecting"
    DESTRUCTIVE = "destructive"


@dataclass(frozen=True)
class InputField:
    """One field in an action form.

    Attributes:
        name: Parameter name as used by boto3 (PascalCase) and rendered as a label.
        label: Human-friendly label.
        kind: One of "string", "int", "bool", "choice", "multiline", "arn".
        required: Whether the field must be filled.
        default: Default value (string form). None means no default.
        choices: For kind == "choice", the allowed values.
        help_text: Short hint shown beside the field.
    """

    name: str
    label: str
    kind: str = "string"
    required: bool = False
    default: str | None = None
    choices: tuple[str, ...] = ()
    help_text: str = ""


@dataclass(frozen=True)
class CliTemplate:
    """How an action renders as an `aws` CLI invocation.

    Attributes:
        service: The CLI service name, e.g. "rds", "backup".
        command: The subcommand, e.g. "describe-db-clusters".
        arg_map: Mapping from InputField.name -> CLI flag name (without the leading `--`).
                 Fields not in arg_map are omitted from the CLI line.
    """

    service: str
    command: str
    arg_map: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Boto3Template:
    """How an action renders as a boto3 client call.

    Attributes:
        service: boto3 service name, e.g. "rds", "backup".
        operation: snake_case operation name, e.g. "describe_db_clusters".
        param_map: Mapping from InputField.name -> boto3 parameter name (PascalCase).
                   Fields not in param_map are omitted from the call.
    """

    service: str
    operation: str
    param_map: Mapping[str, str] = field(default_factory=dict)


class ResultViewKind(StrEnum):
    """How the main panel should render the action result."""

    TABLE = "table"
    TREE = "tree"
    TEXT = "text"
    RAW_JSON = "raw_json"
    NONE = "none"


@dataclass(frozen=True)
class ResultViewDefinition:
    """How to render the result of an action in the main panel.

    Attributes:
        kind: ResultViewKind.
        columns: For kind == TABLE, ordered column names. Each column name corresponds to a
                 field on the normalized summary dataclass returned by the action's view.
        title: Title shown above the view.
    """

    kind: ResultViewKind
    columns: tuple[str, ...] = ()
    title: str = ""


# A view function takes a raw boto3 response (or parsed JSON from the CLI) and returns a list
# of normalized summary dataclasses. The dataclass type is service-specific.
ViewFunction = Callable[[Mapping[str, Any]], list[Any]]
CliArgsBuilder = Callable[[Mapping[str, str]], list[str]]
Boto3ParamsBuilder = Callable[[Mapping[str, str]], dict[str, Any]]


@dataclass(frozen=True)
class ActionDefinition:
    """A single operation the user can perform."""

    action_id: str
    display_name: str
    service_id: str
    risk_level: RiskLevel
    input_fields: tuple[InputField, ...]
    cli_template: CliTemplate
    boto3_template: Boto3Template
    result_view: ResultViewDefinition
    iam_permissions: tuple[str, ...] = ()
    description: str = ""
    cache_refresh_nav_ids: tuple[str, ...] = ()
    # View function is intentionally not part of __eq__/repr — keep it on a side channel.
    view: ViewFunction | None = field(default=None, compare=False, repr=False)
    cli_args_builder: CliArgsBuilder | None = field(default=None, compare=False, repr=False)
    boto3_params_builder: Boto3ParamsBuilder | None = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class RowAction:
    """A button shown below the detail panel when a row is selected.

    Attributes:
        action_id: The ActionDefinition to open in the ActionDialog.
        button_label: Short label for the button, e.g. "Create Snapshot".
        prefill: Mapping from InputField.name → attribute name on the selected row object.
                 When the dialog opens, these fields are pre-populated from the row.
    """

    action_id: str
    button_label: str
    prefill: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class SubAction:
    """A secondary read-only action run when a row is selected, shown in the sub-panel.

    Attributes:
        action_id: The ActionDefinition to run (must be READ_ONLY).
        panel_label: Title for the sub-panel (e.g. "Instances").
        prefill: Mapping from InputField.name → attribute name on the selected row object.
        columns: Column names to display in the sub-table.
        row_actions: Buttons shown for the currently selected sub-row.
    """

    action_id: str
    panel_label: str
    prefill: Mapping[str, str] = field(default_factory=dict)
    columns: tuple[str, ...] = ()
    row_actions: tuple[RowAction, ...] = ()


@dataclass(frozen=True)
class EagerChoiceSource:
    """Populate a filter field's choices from another action's response.

    Attributes:
        action_id: Read-only action to run when the nav item is opened (and again
                   whenever any field in ``depends_on`` changes value).
        jmespath: JMESPath expression that returns a list of strings (the choices).
                  Evaluated against the raw boto3 response.
        depends_on: Map of filter-field-name → action-input-name. When the named
                    filter field has a non-empty value, its value is passed to
                    the source action as that input. The fetch is deferred until
                    every depended-on field has a value, and re-fired whenever
                    any of them changes. Leave empty for an independent source
                    that loads once at nav-open time.
    """

    action_id: str
    jmespath: str
    depends_on: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class NavigationItem:
    """One sidebar entry under a service.

    Clicking a sidebar entry always runs ``default_action_id`` (a read-only list/describe).
    Write actions are never triggered by sidebar clicks — they appear as buttons in the
    row-action bar below the detail panel.

    Attributes:
        item_id: Stable identifier within the service.
        display_name: Label shown in the sidebar.
        default_action_id: The read-only action to auto-run when this item is clicked.
        row_actions: Buttons shown below the detail panel when a row is selected.
        sub_action: Optional secondary action run on row-select to populate the sub-panel.
        filter_fields: Input fields shown in the filter bar above the resource table.
                       Their values are passed to ``default_action_id`` on Refresh.
        eager_choices: Per-field-name source of dropdown choices, fetched once on open.
                       Keys are filter_field names; values are EagerChoiceSource specs.
    """

    item_id: str
    display_name: str
    default_action_id: str | None = None
    row_actions: tuple[RowAction, ...] = ()
    sub_action: SubAction | None = None
    filter_fields: tuple[InputField, ...] = ()
    eager_choices: Mapping[str, EagerChoiceSource] = field(default_factory=dict)


@dataclass(frozen=True)
class ServiceDefinition:
    """Top-level service: sidebar group + actions."""

    service_id: str
    display_name: str
    boto3_service_name: str
    cli_service_name: str
    navigation_items: tuple[NavigationItem, ...]
    actions: tuple[ActionDefinition, ...]

    def action(self, action_id: str) -> ActionDefinition:
        """Return the action with the given id."""
        for candidate in self.actions:
            if candidate.action_id == action_id:
                return candidate
        raise KeyError(f"No action {action_id!r} in service {self.service_id!r}")


@dataclass(frozen=True)
class ResourceSummary:
    """Generic normalized summary used when a service has nothing more specific."""

    service_id: str
    resource_type: str
    identifier: str
    arn: str | None
    status: str | None
    region: str
    account_id: str | None
    display_name: str
