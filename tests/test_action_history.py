"""ActionHistory add/export tests."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from gui4aws.execution.action_history import ActionHistory, ActionHistoryEntry
from gui4aws.execution.execution_mode import ExecutionMode


def make_entry(action_id: str = "aurora.describe_db_clusters") -> ActionHistoryEntry:
    """Build a synthetic entry."""
    return ActionHistoryEntry(
        timestamp=datetime(2026, 5, 20, 12, 0, tzinfo=timezone.utc),
        service_id="aurora",
        action_id=action_id,
        mode=ExecutionMode.BOTO3,
        profile_name="default",
        region_name="us-east-1",
        endpoint_url=None,
        inputs={},
        cli_script="#!/usr/bin/env bash\nset -euo pipefail\naws rds describe-db-clusters --region us-east-1\n",
        python_script=(
            'import boto3\n\n\ndef main() -> None:\n'
            '    session = boto3.Session(region_name="us-east-1")\n'
            '    client = session.client("rds")\n'
            "    response = client.describe_db_clusters()\n"
            "    print(response)\n\n\n"
            'if __name__ == "__main__":\n    main()\n'
        ),
        status="success",
        duration_seconds=0.123,
    )


def test_history_add_and_latest() -> None:
    """``add`` appends and ``latest`` returns the most recent."""
    history = ActionHistory()
    history.add(make_entry("a"))
    history.add(make_entry("b"))
    latest = history.latest()
    assert latest is not None
    assert latest.action_id == "b"


def test_history_trims_to_max_entries() -> None:
    """Adding past max_entries drops the oldest."""
    history = ActionHistory(max_entries=2)
    history.add(make_entry("a"))
    history.add(make_entry("b"))
    history.add(make_entry("c"))
    assert [entry.action_id for entry in history.entries] == ["b", "c"]


def test_history_export_bash_has_no_double_shebang() -> None:
    """Aggregating two entries produces exactly one shebang."""
    history = ActionHistory()
    history.add(make_entry("a"))
    history.add(make_entry("b"))
    text = history.export_bash()
    assert text.count("#!/usr/bin/env bash") == 1
    assert text.count("aws rds describe-db-clusters") == 2


def test_history_export_python_has_step_functions() -> None:
    """Aggregating produces step_1, step_2, ..."""
    history = ActionHistory()
    history.add(make_entry("a"))
    history.add(make_entry("b"))
    text = history.export_python()
    assert "def step_1()" in text
    assert "def step_2()" in text
    assert "step_1()" in text
    assert "step_2()" in text


def test_history_export_json_roundtrips() -> None:
    """Exported JSON is parseable."""
    history = ActionHistory()
    history.add(make_entry("a"))
    parsed = json.loads(history.export_json())
    assert isinstance(parsed, list)
    assert parsed[0]["action_id"] == "a"
