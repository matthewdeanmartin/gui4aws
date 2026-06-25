"""Pure helper functions extracted from MainWindow to reduce module size."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from gui4aws.models import EagerChoiceSource

if TYPE_CHECKING:
    from gui4aws.app import AppContext
    from gui4aws.models import ActionDefinition

logger = logging.getLogger(__name__)


def extract_choices_from_raw(jmespath_expression: str, raw: Any) -> list[str]:
    """Extract a list of strings from a raw API response using JMESPath."""
    import jmespath

    choices_raw = jmespath.compile(jmespath_expression).search(raw) or []
    choices: list[str] = []
    for value in choices_raw:
        text = str(value)
        if "/" in text and text.startswith("arn:"):
            text = text.rsplit("/", maxsplit=1)[-1]
        if text:
            choices.append(text)
    return choices


def seed_filter_values(nav: Any, current_values: dict[str, str]) -> dict[str, str]:
    """Combine default field values with current filter-bar values."""
    values = {field.name: field.default for field in nav.filter_fields if field.default is not None}
    for name, value in current_values.items():
        if value:
            values[name] = value
    return values


def source_inputs_from_values(
    source: EagerChoiceSource,
    values: dict[str, str],
) -> dict[str, str] | None:
    """Map filter field values to source action input parameters.

    Returns None if any required dependency field is missing a value.
    """
    inputs: dict[str, str] = {}
    depends_on = source.depends_on or {}
    for filter_field, source_param in depends_on.items():
        value = values.get(filter_field, "").strip()
        if not value:
            return None
        inputs[source_param] = value
    return inputs


def nav_action_inputs(nav: Any, values: dict[str, str]) -> dict[str, str]:
    """Extract inputs for the default nav action from resolved filter values."""
    return {field.name: values[field.name] for field in nav.filter_fields if values.get(field.name, "").strip()}


def filter_rows_by_inputs(rows: list[Any], inputs: dict[str, str]) -> list[Any]:
    """Apply exact-match filters whose input names also exist as row attributes."""
    filtered = list(rows)
    for field_name, expected in inputs.items():
        if not filtered:
            break
        if not any(hasattr(row, field_name) for row in filtered):
            continue
        filtered = [
            row
            for row in filtered
            if getattr(row, field_name, None) is not None and str(getattr(row, field_name)) == expected
        ]
    return filtered


def resolve_required_filter_value(
    service: Any,
    nav: Any,
    field_name: str,
    values: dict[str, str],
    resolving: set[str],
    *,
    execute: Callable[[Any, dict[str, str]], Any],
) -> str | None:
    """Recursively resolve a required filter field by fetching its first available choice."""
    source = nav.eager_choices.get(field_name)
    if source is None or field_name in resolving:
        return None
    resolving.add(field_name)
    try:
        for dependency_field in source.depends_on:
            if values.get(dependency_field, "").strip():
                continue
            dependency_value = resolve_required_filter_value(
                service, nav, dependency_field, values, resolving, execute=execute
            )
            if dependency_value is None:
                return None
            values[dependency_field] = dependency_value
        source_inputs = source_inputs_from_values(source, values)
        if source_inputs is None:
            return None
        src_action = service.action(source.action_id)
        result = execute(src_action, source_inputs)
        raw = getattr(result, "response", None) or getattr(result, "parsed_json", None)
        if raw is None:
            return None
        choices = extract_choices_from_raw(source.jmespath, raw)
        if not choices:
            return None
        return choices[0]
    finally:
        resolving.discard(field_name)


def resolved_filter_values(
    service: Any,
    nav: Any,
    current_values: dict[str, str],
    *,
    execute: Callable[[Any, dict[str, str]], Any],
) -> dict[str, str] | None:
    """Try to fill all required filter fields by fetching choices from the API."""
    values = seed_filter_values(nav, current_values)
    resolving: set[str] = set()
    for field in nav.filter_fields:
        if values.get(field.name, "").strip():
            continue
        if not field.required:
            continue
        resolved = resolve_required_filter_value(service, nav, field.name, values, resolving, execute=execute)
        if resolved is None:
            return None
        values[field.name] = resolved
    return values


def render_moto_output(snapshot: dict[str, Any]) -> str:
    """Format a Moto server snapshot dict into a human-readable status string."""
    lines = [
        f"Running: {snapshot['running']}",
        f"Endpoint: {snapshot['endpoint_url'] or '(not started)'}",
        f"Port: {snapshot['port'] or '(none)'}",
        f"Captured lines: {snapshot['output_line_count']}",
        "",
        "Recent output:",
    ]
    recent_output = snapshot["recent_output"]
    if recent_output:
        lines.extend(recent_output)
    else:
        lines.append("(no output yet)")
    return "\n".join(lines)


def render_robotocore_output(snapshot: dict[str, Any]) -> str:
    """Format a Robotocore snapshot dict into a human-readable status string."""
    lines = [
        f"Running: {snapshot['running']}",
        f"Endpoint: {snapshot['endpoint_url']}",
        f"Container: {snapshot['container_name']}",
        f"Captured lines: {snapshot['output_line_count']}",
    ]
    if not snapshot["running"]:
        lines.append(
            "Tip: if the container is still starting after a timeout, "
            "click Start Robotocore again — it will probe the endpoint "
            "and reconnect automatically."
        )
    lines += ["", "Recent output:"]
    recent_output = snapshot["recent_output"]
    if recent_output:
        lines.extend(recent_output)
    else:
        lines.append("(no output yet — click Start Robotocore or Pull Docker Image first)")
    return "\n".join(lines)


def record_history(
    action: ActionDefinition,
    kind: str,
    payload: Any,
    *,
    context: AppContext,
    current_inputs: dict[str, str],
) -> None:
    """Add an execution entry to the persistent action history."""
    from datetime import datetime, timezone

    from gui4aws.execution.action_history import ActionHistoryEntry
    from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
    from gui4aws.models import redact_secrets

    inputs = dict(current_inputs)
    # The generators redact secrets internally; the stored ``inputs`` snapshot must be
    # redacted too so passwords never land in history JSON / diagnostics.
    redacted_inputs = redact_secrets(inputs, action.secret_field_names())
    cli = generate_cli_script(
        action,
        inputs,
        profile_name=context.profile_name,
        region_name=context.region_name,
        endpoint_config=context.endpoint_config,
    )
    python = generate_python_script(
        action,
        inputs,
        profile_name=context.profile_name,
        region_name=context.region_name,
        endpoint_config=context.endpoint_config,
    )
    is_failure = kind == "error" or hasattr(payload, "exception_class")
    error_message: str | None = None
    duration = float(getattr(payload, "duration_seconds", 0.0) or 0.0)
    if is_failure:
        error_message = getattr(payload, "message", None) or getattr(payload, "reason", None) or str(payload)
    context.history.add(
        ActionHistoryEntry(
            timestamp=datetime.now(timezone.utc),
            service_id=action.service_id,
            action_id=action.action_id,
            mode=context.mode,
            profile_name=context.profile_name,
            region_name=context.region_name,
            endpoint_url=context.endpoint_config.resolved_url(),
            inputs=redacted_inputs,
            cli_script=cli,
            python_script=python,
            status="failure" if is_failure else "success",
            duration_seconds=duration,
            error_message=error_message,
        )
    )


def build_about_text(robotocore_running: bool, robotocore_endpoint_url: str) -> str:
    """Compose the 'About gui4aws' dialog body text."""
    import sys

    import boto3
    import botocore

    from gui4aws.__about__ import __description__, __license__, __version__

    try:
        import moto

        moto_ver = moto.__version__
    except ImportError:
        moto_ver = "not installed"

    rc_status = f"connected ({robotocore_endpoint_url})" if robotocore_running else "not connected"

    lines = [
        f"gui4aws  {__version__}",
        f"{__description__}",
        "",
        f"License: {__license__}",
        f"Python:  {sys.version.split()[0]}",
        "",
        "Runtime dependencies:",
        f"  boto3      {boto3.__version__}",
        f"  botocore   {botocore.__version__}",
        "",
        "Dev/test dependencies:",
        f"  moto       {moto_ver}",
        "",
        "Local emulators:",
        f"  robotocore {rc_status}",
        "",
        "Repository: https://github.com/matthewdeanmartin/gui4aws",
        "Docs:       https://gui4aws.readthedocs.io/en/latest/",
    ]
    return "\n".join(lines)
