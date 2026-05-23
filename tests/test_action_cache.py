"""Read cache behavior."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from gui4aws.app import AppContext
from gui4aws.execution.action_cache import ActionCache
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.models import ActionDefinition, Boto3Template, CliTemplate, ResultViewDefinition, ResultViewKind, RiskLevel

READ_ACTION = ActionDefinition(
    action_id="fake.read",
    display_name="Fake read",
    service_id="fake",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="fake", command="read"),
    boto3_template=Boto3Template(service="fake", operation="read"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON),
)

WRITE_ACTION = ActionDefinition(
    action_id="fake.write",
    display_name="Fake write",
    service_id="fake",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(),
    cli_template=CliTemplate(service="fake", command="write"),
    boto3_template=Boto3Template(service="fake", operation="write"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON),
)


@dataclass
class _FakeExecutor:
    result: Any
    calls: int = 0

    def execute(self, action: ActionDefinition, inputs: dict[str, str]) -> Any:
        del action, inputs
        self.calls += 1
        return self.result


def _result(operation: str) -> Boto3Result:
    return Boto3Result(
        service="fake",
        operation=operation,
        region="us-east-1",
        duration_seconds=0.1,
        request_params={},
        response={"ok": True, "operation": operation},
    )


def test_action_cache_entry_expires() -> None:
    """Expired entries are evicted on read."""
    now = 100.0
    cache = ActionCache(ttl_seconds=30, clock=lambda: now)
    key = cache.build_key(
        READ_ACTION,
        {},
        mode=AppContext().mode,
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=AppContext().endpoint_config,
    )
    cache.put(key, "cached")
    assert cache.get(key) == "cached"

    now = 131.0
    assert cache.get(key) is None


def test_app_context_caches_read_only_results(monkeypatch: Any) -> None:
    """Repeated read-only calls reuse the cached result."""
    context = AppContext(region_name="us-east-1")
    fake_executor = _FakeExecutor(_result("read"))
    monkeypatch.setattr(context, "boto3_executor", lambda: fake_executor)

    first = context.execute(READ_ACTION, {})
    second = context.execute(READ_ACTION, {})

    assert first is second
    assert fake_executor.calls == 1


def test_app_context_does_not_cache_writes(monkeypatch: Any) -> None:
    """Write actions always execute again."""
    context = AppContext(region_name="us-east-1")
    fake_executor = _FakeExecutor(_result("write"))
    monkeypatch.setattr(context, "boto3_executor", lambda: fake_executor)

    context.execute(WRITE_ACTION, {})
    context.execute(WRITE_ACTION, {})

    assert fake_executor.calls == 2


def test_invalidate_read_cache_for_service(monkeypatch: Any) -> None:
    """Invalidating one service drops its cached reads."""
    context = AppContext(region_name="us-east-1")
    fake_executor = _FakeExecutor(_result("read"))
    monkeypatch.setattr(context, "boto3_executor", lambda: fake_executor)

    context.execute(READ_ACTION, {})
    context.invalidate_read_cache("fake")
    context.execute(READ_ACTION, {})

    assert fake_executor.calls == 2


def test_action_cache_snapshot_reports_entries() -> None:
    """Cache snapshots include entries and counters for the diagnostics tab."""
    cache = ActionCache(ttl_seconds=60, clock=lambda: 100.0)
    key = cache.build_key(
        READ_ACTION,
        {"name": "demo"},
        mode=AppContext().mode,
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=AppContext().endpoint_config,
    )
    cache.put(key, _result("read"))

    snapshot = cache.snapshot()

    assert snapshot["size"] == 1
    assert snapshot["stats"]["puts"] == 1
    assert snapshot["entries"][0]["action_id"] == READ_ACTION.action_id
    assert snapshot["entries"][0]["inputs"] == {"name": "demo"}


def test_invalidate_entry_removes_only_selected_cache_entry() -> None:
    """Diagnostics can remove a single cached entry without clearing the rest."""
    cache = ActionCache(ttl_seconds=60, clock=lambda: 100.0)
    first_key = cache.build_key(
        READ_ACTION,
        {"name": "demo"},
        mode=AppContext().mode,
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=AppContext().endpoint_config,
    )
    second_key = cache.build_key(
        READ_ACTION,
        {"name": "other"},
        mode=AppContext().mode,
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=AppContext().endpoint_config,
    )
    cache.put(first_key, _result("read"))
    cache.put(second_key, _result("read"))

    removed = cache.invalidate_entry(
        service_id="fake",
        action_id="fake.read",
        mode="boto3",
        inputs={"name": "demo"},
    )

    snapshot = cache.snapshot()
    assert removed is True
    assert snapshot["size"] == 1
    assert snapshot["stats"]["entry_invalidations"] == 1
    assert snapshot["entries"][0]["inputs"] == {"name": "other"}
