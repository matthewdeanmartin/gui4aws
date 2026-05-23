"""Cache warming helpers on MainWindow."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.gui.main_window import MainWindow
from gui4aws.services.ecs.actions import LIST_CLUSTERS, LIST_SERVICES, LIST_TASKS, UPDATE_SERVICE
from gui4aws.services.ecs.service import SERVICE as ECS_SERVICE
from gui4aws.services.service_registry import ServiceRegistry


@dataclass
class _FakeQueue:
    jobs: list[Any] = field(default_factory=list)
    cleared: int = 0

    def submit(self, fn: Any, is_current: Any, description: str = "job") -> None:
        del is_current, description
        self.jobs.append(fn)

    def clear_pending(self) -> int:
        removed = len(self.jobs)
        self.jobs.clear()
        self.cleared += removed
        return removed

    def snapshot(self) -> dict[str, Any]:
        return {
            "pending_jobs": len(self.jobs),
            "current_job": None,
            "submitted_jobs": len(self.jobs),
            "started_jobs": 0,
            "completed_jobs": 0,
            "dropped_jobs": 0,
            "failed_jobs": 0,
            "recent_events": ["12:00:00 queued cache warm ecs.services"],
        }


@dataclass
class _FakePanel:
    values: dict[str, str]
    row: Any = None

    def filter_values(self) -> dict[str, str]:
        return dict(self.values)

    def current_row(self) -> Any:
        return self.row


@dataclass
class _FakeContext:
    registry: ServiceRegistry
    invalidations: list[str | None] = field(default_factory=list)
    calls: list[tuple[str, dict[str, str]]] = field(default_factory=list)
    mode: str = "boto3"
    profile_name: str | None = None
    region_name: str = "us-east-1"
    endpoint_config: Any = None
    action_cache: Any = None

    def invalidate_read_cache(self, service_id: str | None = None) -> None:
        self.invalidations.append(service_id)

    def execute(self, action: Any, inputs: dict[str, str]) -> Boto3Result:
        captured_inputs = dict(inputs)
        self.calls.append((action.action_id, captured_inputs))
        response: dict[str, Any]
        if action.action_id == LIST_CLUSTERS.action_id:
            response = {"clusterArns": ["arn:aws:ecs:us-east-1:123456789012:cluster/demo-cluster"]}
        elif action.action_id == LIST_SERVICES.action_id:
            response = {"serviceArns": ["arn:aws:ecs:us-east-1:123456789012:service/demo-cluster/demo-service"]}
        elif action.action_id == LIST_TASKS.action_id:
            response = {"taskArns": []}
        else:
            response = {"ok": True}
        return Boto3Result(
            service=action.service_id,
            operation=action.boto3_template.operation,
            region="us-east-1",
            duration_seconds=0.1,
            request_params=captured_inputs,
            response=response,
        )


def test_write_refresh_warms_target_nav_caches() -> None:
    """ECS writes invalidate cached reads and prewarm affected navs."""
    window = object.__new__(MainWindow)
    window.context = _FakeContext(ServiceRegistry((ECS_SERVICE,)))
    window.main_panel = _FakePanel({})
    window._current_service_id = "ecs"
    window._action_queue = _FakeQueue()

    window._schedule_cache_refreshes_for_action(UPDATE_SERVICE)

    for job in list(window._action_queue.jobs):
        job()

    assert window.context.invalidations == ["ecs"]
    assert (LIST_CLUSTERS.action_id, {}) in window.context.calls
    assert (LIST_SERVICES.action_id, {"cluster": "demo-cluster"}) in window.context.calls
    assert (LIST_TASKS.action_id, {"cluster": "demo-cluster"}) in window.context.calls


def test_refresh_visible_data_after_write_reloads_current_nav() -> None:
    """Successful writes affecting the selected nav trigger a visible refresh."""
    window = object.__new__(MainWindow)
    window._current_service_id = "ecs"
    window._current_nav = type("_Nav", (), {"item_id": "services"})()
    window.main_panel = _FakePanel({"cluster": "demo-cluster"})
    refreshed: list[dict[str, str]] = []
    window._refresh_current_nav = lambda values: refreshed.append(dict(values))

    window._refresh_visible_data_after_write(UPDATE_SERVICE)

    assert refreshed == [{"cluster": "demo-cluster"}]


def test_clear_request_queue_drains_pending_and_ready_work() -> None:
    """Clearing the request queue removes pending jobs and ready results."""
    import queue

    window = object.__new__(MainWindow)
    window._action_queue = _FakeQueue(jobs=[object(), object()])
    window.results_queue = queue.Queue()
    window.results_queue.put(("ok", None, None))
    window.results_queue.put(("ok", None, None))
    window.status_bar = _FakeStatusBar()
    window.moto_output_panel = _FakeDiagnosticText()
    window.robotocore_panel = _FakeRobotocorePanel()
    window.queue_panel = _FakeSnapshotPanel()
    window.cache_panel = _FakeSnapshotPanel()
    window.moto_manager = _FakeMotoManager()
    window.robotocore_manager = _FakeRobotocoreManager()
    window.context = _FakeContext(
        ServiceRegistry((ECS_SERVICE,)),
        endpoint_config=_FakeEndpointConfig(),
        action_cache=_FakeActionCache(),
    )
    window._nav_generation = 1
    window._current_service_id = "ecs"
    window._current_nav = type("_Nav", (), {"item_id": "services"})()

    window.clear_request_queue()

    assert window._action_queue.cleared == 2
    assert window.results_queue.qsize() == 0
    assert window.status_bar.status == "Cleared queue (2 pending, 2 ready)"


def test_clear_selected_cache_entry_removes_only_current_selection() -> None:
    """Clearing one cache entry delegates to the action cache with the selected row."""
    window = object.__new__(MainWindow)
    window.context = _FakeContext(
        ServiceRegistry((ECS_SERVICE,)),
        endpoint_config=_FakeEndpointConfig(),
        action_cache=_MutableFakeActionCache(),
    )
    window.cache_panel = _FakeCachePanel(
        {
            "service_id": "ecs",
            "action_id": "ecs.list_services",
            "mode": "boto3",
            "inputs": {"cluster": "demo-cluster"},
        }
    )
    window.status_bar = _FakeStatusBar()
    window.moto_output_panel = _FakeDiagnosticText()
    window.robotocore_panel = _FakeRobotocorePanel()
    window.queue_panel = _FakeSnapshotPanel()
    window._action_queue = _FakeQueue()
    window.results_queue = _QueueWithSize(0)
    window._nav_generation = 2
    window._current_service_id = "ecs"
    window._current_nav = type("_Nav", (), {"item_id": "services"})()
    window.moto_manager = _FakeMotoManager()
    window.robotocore_manager = _FakeRobotocoreManager()

    window.clear_selected_cache_entry()

    assert window.context.action_cache.removed == [("ecs", "ecs.list_services", "boto3", {"cluster": "demo-cluster"})]
    assert window.status_bar.status == "Cleared cache entry"


def test_open_moto_dashboard_uses_dashboard_endpoint(monkeypatch: Any) -> None:
    """The Moto dashboard button opens /moto-api/ when Moto is running."""
    opened: list[str] = []
    monkeypatch.setattr("webbrowser.open", lambda url: opened.append(url))

    window = object.__new__(MainWindow)
    window.moto_manager = _FakeMotoManager()
    window.status_bar = _FakeStatusBar()

    window.open_moto_dashboard()

    assert opened == ["http://127.0.0.1:5001/moto-api/"]
    assert window.status_bar.status == "Opened Moto dashboard"


def test_diagnostic_snapshots_include_live_state() -> None:
    """Diagnostic helpers expose live Moto, queue, and cache state."""
    window = object.__new__(MainWindow)
    window.results_queue = _QueueWithSize(2)
    window._nav_generation = 7
    window._current_service_id = "ecs"
    window._current_nav = type("_Nav", (), {"item_id": "services"})()
    window._action_queue = _FakeQueue()
    window.moto_manager = _FakeMotoManager()
    window.context = _FakeContext(
        ServiceRegistry((ECS_SERVICE,)),
        endpoint_config=_FakeEndpointConfig(),
        action_cache=_FakeActionCache(),
    )

    moto_text = window._render_moto_output()
    queue_snapshot = window._queue_diagnostics_snapshot()
    cache_snapshot = window._cache_diagnostics_snapshot()

    assert "Running: True" in moto_text
    assert "GET /moto-api/" in moto_text
    assert queue_snapshot["pending_jobs"] == 0
    assert queue_snapshot["result_queue_depth"] == 2
    assert queue_snapshot["current_nav"] == "services"
    assert cache_snapshot["size"] == 1
    assert cache_snapshot["entries"][0]["action_id"] == "ecs.list_services"
    assert cache_snapshot["endpoint"] == "http://127.0.0.1:5001"


@dataclass
class _QueueWithSize:
    size: int

    def qsize(self) -> int:
        return self.size


class _FakeMotoManager:
    running = True
    dashboard_url = "http://127.0.0.1:5001/moto-api/"

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": True,
            "port": 5001,
            "endpoint_url": "http://127.0.0.1:5001",
            "output_line_count": 2,
            "recent_output": ["127.0.0.1 - - [23/May/2026 07:00:00] GET /moto-api/ 200 -"],
        }


class _FakeRobotocoreManager:
    running = False
    endpoint_url = "http://localhost:4566"

    def snapshot(self) -> dict[str, Any]:
        return {
            "running": False,
            "endpoint_url": "http://localhost:4566",
            "container_name": "gui4aws-robotocore",
            "output_line_count": 0,
            "recent_output": [],
        }


class _FakeRobotocorePanel:
    def set_text(self, text: str) -> None:
        del text

    def set_status(self, text: str) -> None:
        del text

    def set_running(self, running: bool) -> None:
        del running


class _FakeEndpointConfig:
    def resolved_url(self) -> str:
        return "http://127.0.0.1:5001"


class _FakeActionCache:
    def snapshot(self) -> dict[str, Any]:
        return {
            "ttl_seconds": 1800,
            "size": 1,
            "stats": {
                "hits": 2,
                "misses": 1,
                "puts": 1,
                "service_invalidations": 0,
                "entry_invalidations": 0,
                "clears": 0,
                "expired": 0,
            },
            "entries": [
                {
                    "action_id": "ecs.list_services",
                    "service_id": "ecs",
                    "mode": "boto3",
                    "inputs": {"cluster": "demo-cluster"},
                }
            ],
            "recent_events": ["12:00:00 PUT ecs.list_services [ecs]"],
        }


@dataclass
class _FakeStatusBar:
    status: str = ""

    def set_status(self, status: str) -> None:
        self.status = status


class _FakeDiagnosticText:
    def set_text(self, text: str) -> None:
        del text


class _FakeSnapshotPanel:
    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        del snapshot


@dataclass
class _FakeCachePanel:
    entry: dict[str, Any] | None

    def selected_entry(self) -> dict[str, Any] | None:
        return self.entry

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        del snapshot


@dataclass
class _MutableFakeActionCache(_FakeActionCache):
    removed: list[tuple[str, str, str, dict[str, str]]] = field(default_factory=list)

    def invalidate_entry(
        self,
        *,
        service_id: str,
        action_id: str,
        mode: str,
        inputs: dict[str, str],
    ) -> bool:
        self.removed.append((service_id, action_id, mode, dict(inputs)))
        return True
