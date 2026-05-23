"""MainWindow: composes toolbar + sidebar + main panel + status bar."""

from __future__ import annotations

import dataclasses
import logging
import queue
import threading
import time
import tkinter as tk
from collections import deque
from tkinter import messagebox, ttk
from typing import Any

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.gui.action_dialog import ActionDialog
from gui4aws.gui.diagnostic_panel import CacheDiagnosticsPanel, DiagnosticPanel, QueueDiagnosticsPanel, RobotocorePanel
from gui4aws.gui.main_panel import MainPanel
from gui4aws.gui.sidebar import Sidebar, SidebarSelection
from gui4aws.gui.status_bar import StatusBar
from gui4aws.gui.toolbar import Toolbar
from gui4aws.models import ActionDefinition, EagerChoiceSource, RiskLevel, RowAction
from gui4aws.moto_server import MotoServerManager
from gui4aws.robotocore_server import RobotocoreManager

__all__ = ["MainWindow", "create_main_window"]

logger = logging.getLogger(__name__)


class SerialWorker:
    """A single background thread that runs jobs FIFO, skipping stale ones.

    ``submit(fn, is_current)`` queues ``fn``. When the worker dequeues a job,
    it first calls ``is_current()`` — if False, the job is dropped without
    being run. This lets rapid nav switches enqueue many jobs while ensuring
    only the ones still relevant when the worker gets to them actually hit
    moto.

    Why serial and not a pool: moto's dev server is single-threaded, so
    parallelism doesn't help and 100+ in-flight HTTP requests pile up faster
    than moto can serve them, freezing the UI.
    """

    def __init__(self) -> None:
        self._queue: queue.Queue[Any] = queue.Queue()
        self._closed = False
        self._lock = threading.RLock()
        self._current_description: str | None = None
        self._submitted_jobs = 0
        self._started_jobs = 0
        self._completed_jobs = 0
        self._dropped_jobs = 0
        self._failed_jobs = 0
        self._recent_events: deque[str] = deque(maxlen=100)
        self._thread = threading.Thread(target=self._loop, name="action-worker", daemon=True)
        self._thread.start()

    def submit(self, fn: Any, is_current: Any, description: str = "job") -> None:
        """Queue ``fn`` for serial execution.

        ``is_current`` is a 0-arg callable returning bool, checked just before
        dispatch. If it returns False, the job is dropped.
        """
        if self._closed:
            return
        with self._lock:
            self._submitted_jobs += 1
            self._record_event(f"queued {description}")
        self._queue.put((fn, is_current, description))

    def close(self) -> None:
        self._closed = True
        # Wake the loop so it can notice.
        self._queue.put((None, None, "shutdown"))

    def clear_pending(self) -> int:
        """Drop queued jobs that have not started yet."""
        removed = 0
        drained: list[tuple[Any, Any, str]] = []
        while True:
            try:
                job = self._queue.get_nowait()
            except queue.Empty:
                break
            if job[2] == "shutdown":
                drained.append(job)
                continue
            removed += 1
        for job in drained:
            self._queue.put(job)
        if removed:
            with self._lock:
                self._dropped_jobs += removed
                self._record_event(f"cleared pending count={removed}")
        return removed

    def _loop(self) -> None:
        while True:
            fn, is_current, description = self._queue.get()
            if self._closed:
                return
            if is_current is not None:
                try:
                    if not is_current():
                        with self._lock:
                            self._dropped_jobs += 1
                            self._record_event(f"dropped stale {description}")
                        continue
                except Exception:
                    logger.exception("worker is_current check raised — dropping job")
                    with self._lock:
                        self._dropped_jobs += 1
                        self._record_event(f"dropped error-check {description}")
                    continue
            with self._lock:
                self._started_jobs += 1
                self._current_description = description
                self._record_event(f"started {description}")
            try:
                fn()
            except Exception:
                logger.exception("worker job raised")
                with self._lock:
                    self._failed_jobs += 1
                    self._record_event(f"failed {description}")
            else:
                with self._lock:
                    self._completed_jobs += 1
                    self._record_event(f"completed {description}")
            finally:
                with self._lock:
                    self._current_description = None

    def snapshot(self) -> dict[str, Any]:
        """Return queue state for diagnostics."""
        with self._lock:
            return {
                "pending_jobs": self._queue.qsize(),
                "current_job": self._current_description,
                "submitted_jobs": self._submitted_jobs,
                "started_jobs": self._started_jobs,
                "completed_jobs": self._completed_jobs,
                "dropped_jobs": self._dropped_jobs,
                "failed_jobs": self._failed_jobs,
                "recent_events": list(self._recent_events),
            }

    def _record_event(self, message: str) -> None:
        stamp = time.strftime("%H:%M:%S")
        self._recent_events.append(f"{stamp} {message}")


class MainWindow:
    """The application's top-level window."""

    def __init__(
        self,
        context: AppContext,
        *,
        root: tk.Tk | None = None,
        profiles: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> None:
        self.context = context
        self.root = root or tk.Tk()
        self.root.title("gui4aws — AWS Think Console")
        self.root.state("zoomed")  # maximise on Windows; harmless on other platforms

        self.results_queue: queue.Queue[Any] = queue.Queue()
        self.moto_manager = MotoServerManager()
        self.robotocore_manager = RobotocoreManager()
        # Track the last opened ActionDialog so we can update its status label.
        self.active_dialog: ActionDialog | None = None

        self._build_menu()

        self.toolbar = Toolbar(
            self.root,
            context,
            profiles=profiles or [],
            regions=regions or [],
            on_change=self.on_toolbar_changed,
            on_moto_toggle=self.on_moto_toggle,
            on_robotocore_toggle=self.on_robotocore_toggle,
        )
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.sidebar = Sidebar(self.root, context.registry, on_select=self.on_sidebar_select)
        self.sidebar.grid(row=1, column=0, sticky="nsw")

        self.content_tabs = ttk.Notebook(self.root)
        self.content_tabs.grid(row=1, column=1, sticky="nsew")

        self.main_panel = MainPanel(self.content_tabs)
        self.moto_output_panel = DiagnosticPanel(
            self.content_tabs,
            actions=(
                ("Restart Moto", self.restart_moto),
                ("Open Dashboard", self.open_moto_dashboard),
            ),
        )
        self.robotocore_panel = RobotocorePanel(
            self.content_tabs,
            on_start=self._robotocore_start,
            on_stop=self._robotocore_stop,
            on_restart=self._robotocore_restart,
            on_pull=self._robotocore_pull,
            on_use_moto_changed=self._robotocore_use_moto_changed,
        )
        self.queue_panel = QueueDiagnosticsPanel(self.content_tabs, on_clear=self.clear_request_queue)
        self.cache_panel = CacheDiagnosticsPanel(
            self.content_tabs,
            on_clear_selected=self.clear_selected_cache_entry,
            on_clear_all=self.clear_all_cache_entries,
        )
        self.content_tabs.add(self.main_panel, text="Browser")
        self.content_tabs.add(self.moto_output_panel, text="Moto Output")
        self.content_tabs.add(self.robotocore_panel, text="Robotocore")
        self.content_tabs.add(self.queue_panel, text="Request Queue")
        self.content_tabs.add(self.cache_panel, text="Cache")

        self.status_bar = StatusBar(self.root, context)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self.current_action: ActionDefinition | None = None
        self.current_inputs: dict[str, str] = {}
        self._current_sub_action: Any = None  # SubAction | None
        self._current_service_id: str | None = None
        self._current_nav: Any = None  # NavigationItem | None
        # Monotonic nav-transition counter — bumped every time the user switches
        # nav item OR triggers a refresh. Workers capture the generation they
        # were launched in; results from older generations are dropped without
        # touching the loading overlay so we don't get a stuck overlay race.
        self._nav_generation: int = 0
        # Serialise default-action / eager-choice / sub-action workers through
        # a single background thread. Rapid arrow-key bouncing previously
        # spawned a daemon thread per nav, all blocked waiting for moto's
        # single-threaded dev server — pile-ups of 100+ threads stalled every
        # panel. Now we run one HTTP call at a time and skip jobs whose nav
        # generation is no longer current at dispatch time.
        self._action_queue = SerialWorker()
        self.root.after(50, self.poll_queue)
        self.root.after(1000, self.refresh_diagnostics)

    # ── Menu ─────────────────────────────────────────────────────────────────

    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)
        self.root.configure(menu=menubar)

        demo_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Demo", menu=demo_menu)
        demo_menu.add_command(label="Seed demo resources", command=self.seed_demo_resources)
        demo_menu.add_separator()
        demo_menu.add_command(
            label="About demo resources",
            command=lambda: messagebox.showinfo(
                "Demo resources",
                "Seeding creates Aurora clusters, snapshots, and AWS Backup vaults tagged with\n"
                "'gui4aws:demo = true' so you can explore the GUI without real AWS access.\n\n"
                "Start Moto (toolbar button) or connect Robotocore, then select Demo → Seed demo resources.",
            ),
        )

        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self._open_docs)
        help_menu.add_separator()
        help_menu.add_command(label="About gui4aws", command=self._show_about)

    def _open_docs(self) -> None:
        import webbrowser

        webbrowser.open("https://gui4aws.readthedocs.io/en/latest/")

    def _show_about(self) -> None:
        import sys

        import boto3
        import botocore

        from gui4aws.__about__ import __description__, __license__, __version__

        try:
            import moto

            moto_ver = moto.__version__
        except ImportError:
            moto_ver = "not installed"
        rc_status = (
            f"connected ({self.robotocore_manager.endpoint_url})"
            if self.robotocore_manager.connected
            else "not connected"
        )
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
        messagebox.showinfo("About gui4aws", "\n".join(lines))

    # ── Moto ─────────────────────────────────────────────────────────────────

    def seed_demo_resources(self) -> None:
        from gui4aws.demo_resources import seed_demo_resources

        endpoint_url = self.context.endpoint_config.resolved_url()
        self.status_bar.set_status("Seeding demo resources…")

        def worker() -> None:
            try:
                report = seed_demo_resources(
                    region_name=self.context.region_name,
                    endpoint_url=endpoint_url,
                    profile_name=self.context.profile_name,
                )
                self.results_queue.put(("demo_ok", None, report))
            except Exception as exc:
                self.results_queue.put(("demo_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def restart_moto(self) -> None:
        """Restart the Moto server in the background."""
        self.status_bar.set_status("Restarting moto server…")

        def restart_worker() -> None:
            try:
                self.moto_manager.restart(timeout=15.0)
                self.results_queue.put(("moto_started", None, self.moto_manager.endpoint_url))
            except Exception as exc:
                self.results_queue.put(("moto_error", None, str(exc)))

        threading.Thread(target=restart_worker, daemon=True).start()

    def open_moto_dashboard(self) -> None:
        """Open Moto's dashboard in the default browser."""
        if not self.moto_manager.running:
            self.status_bar.set_status("Moto is not running")
            return
        import webbrowser

        webbrowser.open(self.moto_manager.dashboard_url)
        self.status_bar.set_status("Opened Moto dashboard")

    def on_moto_toggle(self, start: bool) -> None:
        if start:
            self.status_bar.set_status("Starting moto server…")

            def start_worker() -> None:
                try:
                    self.moto_manager.start(timeout=15.0)
                    self.results_queue.put(("moto_started", None, self.moto_manager.endpoint_url))
                except Exception as exc:
                    self.results_queue.put(("moto_error", None, str(exc)))

            threading.Thread(target=start_worker, daemon=True).start()
        else:
            self.moto_manager.stop()
            self.context.set_endpoint(EndpointMode.AWS)
            self.toolbar.endpoint_mode_var.set(EndpointMode.AWS.value)
            self.toolbar.endpoint_url_var.set("")
            self.status_bar.set_status("Moto stopped")
            self.on_toolbar_changed()

    # ── Robotocore ────────────────────────────────────────────────────────────

    def on_robotocore_toggle(self, currently_running: bool) -> None:
        """Called by the toolbar button.  ``currently_running`` is the manager
        state *before* the click, so we invert it to decide the action."""
        if currently_running:
            self._robotocore_stop()
        else:
            self._robotocore_start()

    def _robotocore_start(self) -> None:
        if self.robotocore_panel.use_moto:
            self._robotocore_start_moto_mode()
            return
        custom_url = self.toolbar.endpoint_url_var.get().strip() or None
        self.status_bar.set_status("Starting robotocore…")
        self.robotocore_panel.set_status("Starting…")

        def worker() -> None:
            try:
                self.robotocore_manager.start(endpoint_url=custom_url)
                self.results_queue.put(("robotocore_started", None, self.robotocore_manager.endpoint_url))
            except Exception as exc:
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _robotocore_stop(self) -> None:
        self.status_bar.set_status("Stopping robotocore…")

        def worker() -> None:
            try:
                self.robotocore_manager.stop()
                self.results_queue.put(("robotocore_stopped", None, None))
            except Exception as exc:
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _robotocore_restart(self) -> None:
        self.status_bar.set_status("Restarting robotocore…")
        self.robotocore_panel.set_status("Restarting…")

        def worker() -> None:
            try:
                self.robotocore_manager.restart()
                self.results_queue.put(("robotocore_started", None, self.robotocore_manager.endpoint_url))
            except Exception as exc:
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _robotocore_pull(self) -> None:
        self.status_bar.set_status("Pulling robotocore Docker image…")
        self.robotocore_panel.set_status("Pulling image…")

        def worker() -> None:
            try:
                self.robotocore_manager.pull()
                self.results_queue.put(("robotocore_pulled", None, None))
            except Exception as exc:
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _robotocore_use_moto_changed(self, use_moto: bool) -> None:
        """When the checkbox flips, switch endpoint mode if robotocore is running."""
        if not self.robotocore_manager.running:
            return
        if use_moto:
            self._robotocore_start_moto_mode()
        else:
            # Switch back to robotocore endpoint.
            url = self.robotocore_manager.endpoint_url
            self.context.set_endpoint(EndpointMode.ROBOTOCORE, url)
            self.toolbar.endpoint_mode_var.set(EndpointMode.ROBOTOCORE.value)
            self.toolbar.endpoint_url_var.set(url)
            self.on_toolbar_changed()

    def _robotocore_start_moto_mode(self) -> None:
        """Point endpoint at a running moto server instead of robotocore."""
        if not self.moto_manager.running:
            self.status_bar.set_status("Start Moto first, then enable 'Use Moto instead'")
            return
        url = self.moto_manager.endpoint_url
        self.context.set_endpoint(EndpointMode.MOTO, url)
        self.toolbar.endpoint_mode_var.set(EndpointMode.MOTO.value)
        self.toolbar.endpoint_url_var.set(url)
        self.status_bar.set_status(f"Routing via Moto at {url}")
        self.on_toolbar_changed()

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def on_toolbar_changed(self) -> None:
        self.status_bar.refresh_context()

    def _refresh_diagnostics_now(self) -> None:
        """Refresh diagnostic widgets immediately without scheduling timers."""
        self.moto_output_panel.set_text(self._render_moto_output())
        self.robotocore_panel.set_text(self._render_robotocore_output())
        self.queue_panel.set_snapshot(self._queue_diagnostics_snapshot())
        self.cache_panel.set_snapshot(self._cache_diagnostics_snapshot())

    def clear_request_queue(self) -> None:
        """Drop pending work from the request and result queues."""
        removed_jobs = self._action_queue.clear_pending()
        removed_results = 0
        while True:
            try:
                self.results_queue.get_nowait()
            except queue.Empty:
                break
            removed_results += 1
        self.status_bar.set_status(f"Cleared queue ({removed_jobs} pending, {removed_results} ready)")
        self._refresh_diagnostics_now()

    def clear_selected_cache_entry(self) -> None:
        """Remove the selected cache entry from diagnostics."""
        entry = self.cache_panel.selected_entry()
        if entry is None:
            self.status_bar.set_status("Pick a cache entry first")
            return
        removed = self.context.action_cache.invalidate_entry(
            service_id=str(entry["service_id"]),
            action_id=str(entry["action_id"]),
            mode=str(entry["mode"]),
            inputs={str(name): str(value) for name, value in entry["inputs"].items()},
        )
        self.status_bar.set_status("Cleared cache entry" if removed else "Cache entry was already gone")
        self._refresh_diagnostics_now()

    def clear_all_cache_entries(self) -> None:
        """Remove all cached read results."""
        self.context.invalidate_read_cache()
        self.status_bar.set_status("Cleared cache")
        self._refresh_diagnostics_now()

    # ── Sidebar navigation ────────────────────────────────────────────────────

    def on_sidebar_select(self, selection: SidebarSelection) -> None:
        """Clear the panel, wire row-action buttons, and run the list action.

        Selecting a service-row (item_id is None) still bumps the generation
        so a worker that's still in flight for the previously-selected child
        nav gets its result dropped on arrival.
        """
        # Bump generation unconditionally on every sidebar selection,
        # including transitions to a service-row (item_id=None). Any in-flight
        # worker from the previous nav is now stale.
        self._nav_generation += 1

        try:
            service = self.context.registry.get(selection.service_id)
        except KeyError:
            logger.warning("sidebar selected unknown service %r", selection.service_id)
            return
        if selection.item_id is None:
            # Service-row selection — nothing to load, but we already bumped
            # the generation above so stale results from the prior nav drop.
            return
        nav = next((item for item in service.navigation_items if item.item_id == selection.item_id), None)
        if nav is None:
            logger.warning(
                "sidebar selected unknown nav item %r in service %r", selection.item_id, selection.service_id
            )
            return

        self.main_panel.clear_for_navigation()

        self._current_sub_action = nav.sub_action
        self._current_service_id = service.service_id
        self._current_nav = nav

        # Configure the filter bar for this nav (always — empty fields if none).
        self.main_panel.configure_filter_bar(
            nav.filter_fields,
            on_refresh=lambda values, _nav=nav: self._refresh_current_nav(values),
        )
        # Wire dependent-field watchers so that picking e.g. a cluster refires
        # the eager fetch for service_name.
        self.main_panel.set_filter_field_change_handler(self._on_filter_field_changed)

        if nav.row_actions or nav.sub_action:
            self.main_panel.set_row_actions(
                nav.row_actions,
                on_row_action=lambda ra, row: self._on_row_action(service.service_id, ra, row),
                on_row_select=self._on_sub_action_row_select if nav.sub_action else None,
            )
        else:
            self.main_panel.set_row_actions((), None)
        self.main_panel.set_sub_row_actions(
            nav.sub_action.row_actions if nav.sub_action else (),
            (lambda ra, row: self._on_sub_row_action(service.service_id, ra, row)) if nav.sub_action else None,
        )

        # Kick off any eager-choice fetches so dropdowns get populated.
        # Only fields without a depends_on are loaded here; dependent ones
        # are fired when their dependency picks up a value.
        self._dispatch_eager_choices(service, nav, only_independent=True)

        if nav.default_action_id is None:
            return

        try:
            action = service.action(nav.default_action_id)
        except KeyError:
            logger.warning("nav item %r has unknown default_action_id %r", nav.item_id, nav.default_action_id)
            return

        # If any required filter field is empty, skip the initial run — the
        # eager-choice load (or the user) will trigger the first refresh.
        inputs = self.main_panel.filter_values()
        if self._missing_required(nav, inputs):
            self.status_bar.set_status("Pick a value above and click Refresh")
            return

        self.run_action(action, inputs=inputs)

    def _refresh_current_nav(self, values: dict[str, str]) -> None:
        """Re-run the current nav's default action with the filter-bar values."""
        nav = getattr(self, "_current_nav", None)
        service_id = self._current_service_id
        if nav is None or service_id is None or nav.default_action_id is None:
            return
        if self._missing_required(nav, values):
            self.status_bar.set_status("Fill in the required filter fields above")
            return
        try:
            service = self.context.registry.get(service_id)
            action = service.action(nav.default_action_id)
        except KeyError:
            return
        # Treat a refresh as a new generation too — any previously in-flight
        # default-action worker is now stale.
        self._nav_generation += 1
        self.run_action(action, inputs=values)

    def _on_filter_field_changed(self, field_name: str, value: str) -> None:
        """Called by FilterBar when any (non-client-filter) field's value changes.

        Refires eager-choice fetches whose ``depends_on`` references this field.
        """
        nav = getattr(self, "_current_nav", None)
        service_id = self._current_service_id
        if nav is None or service_id is None or not nav.eager_choices:
            return
        try:
            service = self.context.registry.get(service_id)
        except KeyError:
            return
        for fname, source in nav.eager_choices.items():
            if not getattr(source, "depends_on", None):
                continue
            if field_name not in source.depends_on:
                continue
            if not value.strip():
                # Dependency cleared — wipe the dependent dropdown.
                self.main_panel.set_filter_choices(fname, [])
                continue
            self._launch_eager_fetch(service, fname, source)

    def _missing_required(self, nav: Any, values: dict[str, str]) -> bool:
        return any(fld.required and not values.get(fld.name, "").strip() for fld in nav.filter_fields)

    def _dispatch_eager_choices(self, service: Any, nav: Any, *, only_independent: bool) -> None:
        """For each (field_name → EagerChoiceSource), fetch the source action
        in a worker thread and populate the dropdown when it returns.

        If ``only_independent`` is True, skip sources with non-empty
        ``depends_on`` — those are fired by _on_filter_field_changed once
        their dependency picks up a value.
        """
        if not nav.eager_choices:
            return
        for field_name, source in nav.eager_choices.items():
            if only_independent and getattr(source, "depends_on", None):
                continue
            self._launch_eager_fetch(service, field_name, source)

    def _launch_eager_fetch(self, service: Any, field_name: str, source: Any) -> None:
        """Start one eager-choice worker tagged with the current generation."""
        try:
            src_action = service.action(source.action_id)
        except KeyError:
            logger.warning(
                "eager_choice for %r references unknown action %r",
                field_name,
                source.action_id,
            )
            return

        # Gather input values for the source action from dependent filter fields.
        inputs: dict[str, str] = {}
        depends_on = getattr(source, "depends_on", None) or {}
        if depends_on:
            current_values = self.main_panel.filter_values()
            for filter_field, source_param in depends_on.items():
                v = current_values.get(filter_field, "").strip()
                if not v:
                    # Dependency unset — bail; the dropdown stays empty.
                    return
                inputs[source_param] = v

        generation = self._nav_generation

        def worker() -> None:
            try:
                result = self.context.execute(src_action, inputs)
            except Exception as exc:
                logger.warning("eager_choice fetch failed for %s: %s", field_name, exc)
                return
            raw = getattr(result, "response", None) or getattr(result, "parsed_json", None)
            if raw is None:
                return
            try:
                choices = self._extract_choices_from_raw(source.jmespath, raw)
            except Exception as exc:
                logger.warning("eager_choice JMESPath failed for %s: %s", field_name, exc)
                return
            self.results_queue.put(("choices", field_name, choices, generation))

        # Route through the same single-worker queue as default actions, so
        # rapid nav switching can't pile up parallel eager fetches. Stale
        # generations skipped at dispatch time.
        self._action_queue.submit(
            worker,
            lambda gen=generation: gen == self._nav_generation,
            f"choices {field_name}",
        )

    def _extract_choices_from_raw(self, jmespath_expression: str, raw: Any) -> list[str]:
        import jmespath  # type: ignore[import-untyped]

        choices_raw = jmespath.compile(jmespath_expression).search(raw) or []
        choices: list[str] = []
        for value in choices_raw:
            text = str(value)
            if "/" in text and text.startswith("arn:"):
                text = text.split("/")[-1]
            if text:
                choices.append(text)
        return choices

    def _seed_filter_values(self, nav: Any, current_values: dict[str, str]) -> dict[str, str]:
        values = {field.name: field.default for field in nav.filter_fields if field.default is not None}
        for name, value in current_values.items():
            if value:
                values[name] = value
        return values

    def _source_inputs_from_values(
        self,
        source: EagerChoiceSource,
        values: dict[str, str],
    ) -> dict[str, str] | None:
        inputs: dict[str, str] = {}
        depends_on = source.depends_on or {}
        for filter_field, source_param in depends_on.items():
            value = values.get(filter_field, "").strip()
            if not value:
                return None
            inputs[source_param] = value
        return inputs

    def _resolve_required_filter_value(
        self,
        service: Any,
        nav: Any,
        field_name: str,
        values: dict[str, str],
        resolving: set[str],
    ) -> str | None:
        source = nav.eager_choices.get(field_name)
        if source is None or field_name in resolving:
            return None
        resolving.add(field_name)
        try:
            for dependency_field in source.depends_on:
                if values.get(dependency_field, "").strip():
                    continue
                dependency_value = self._resolve_required_filter_value(
                    service,
                    nav,
                    dependency_field,
                    values,
                    resolving,
                )
                if dependency_value is None:
                    return None
                values[dependency_field] = dependency_value
            source_inputs = self._source_inputs_from_values(source, values)
            if source_inputs is None:
                return None
            src_action = service.action(source.action_id)
            result = self.context.execute(src_action, source_inputs)
            raw = getattr(result, "response", None) or getattr(result, "parsed_json", None)
            if raw is None:
                return None
            choices = self._extract_choices_from_raw(source.jmespath, raw)
            if not choices:
                return None
            return choices[0]
        finally:
            resolving.discard(field_name)

    def _resolved_filter_values(
        self,
        service: Any,
        nav: Any,
        current_values: dict[str, str],
    ) -> dict[str, str] | None:
        values = self._seed_filter_values(nav, current_values)
        resolving: set[str] = set()
        for field in nav.filter_fields:
            if values.get(field.name, "").strip():
                continue
            if not field.required:
                continue
            resolved = self._resolve_required_filter_value(service, nav, field.name, values, resolving)
            if resolved is None:
                return None
            values[field.name] = resolved
        return values

    def _nav_action_inputs(self, nav: Any, values: dict[str, str]) -> dict[str, str]:
        return {field.name: values[field.name] for field in nav.filter_fields if values.get(field.name, "").strip()}

    def _submit_nav_cache_warm(
        self,
        service: Any,
        nav: Any,
        current_values: dict[str, str],
    ) -> None:
        if nav.default_action_id is None:
            return
        try:
            default_action = service.action(nav.default_action_id)
        except KeyError:
            logger.warning("cache warm skipped unknown nav action %r", nav.default_action_id)
            return
        captured_values = dict(current_values)

        def warm_nav() -> None:
            values = self._resolved_filter_values(service, nav, captured_values)
            if values is None:
                return
            for source in nav.eager_choices.values():
                try:
                    source_action = service.action(source.action_id)
                except KeyError:
                    logger.warning("cache warm skipped unknown eager action %r", source.action_id)
                    continue
                source_inputs = self._source_inputs_from_values(source, values)
                if source_inputs is None:
                    continue
                self.context.execute(source_action, source_inputs)
            self.context.execute(default_action, self._nav_action_inputs(nav, values))

        self._action_queue.submit(warm_nav, lambda: True, f"cache warm {service.service_id}.{nav.item_id}")

    def _schedule_cache_refreshes_for_action(self, action: ActionDefinition) -> None:
        self.context.invalidate_read_cache(action.service_id)
        if not action.cache_refresh_nav_ids:
            return
        try:
            service = self.context.registry.get(action.service_id)
        except KeyError:
            logger.warning("cache refresh skipped unknown service %r", action.service_id)
            return
        current_values = self.main_panel.filter_values() if self._current_service_id == action.service_id else {}
        target_nav_ids = set(action.cache_refresh_nav_ids)
        for nav in service.navigation_items:
            if nav.item_id in target_nav_ids:
                self._submit_nav_cache_warm(service, nav, current_values)

    def _refresh_visible_data_after_write(self, action: ActionDefinition) -> None:
        """Reload the visible grid after a successful write affecting the current nav."""
        nav = getattr(self, "_current_nav", None)
        if nav is None or self._current_service_id != action.service_id:
            return
        if nav.item_id not in set(action.cache_refresh_nav_ids):
            return
        self._refresh_current_nav(self.main_panel.filter_values())

    def _schedule_demo_cache_seed(self) -> None:
        self.context.invalidate_read_cache()
        for service in self.context.registry:
            for nav in service.navigation_items:
                self._submit_nav_cache_warm(service, nav, {})

    def _on_sub_action_row_select(self, row: Any) -> None:
        """Fire the sub_action when a row is selected and show results in the sub-panel."""
        import dataclasses as _dc

        sub = self._current_sub_action
        if sub is None or self._current_service_id is None:
            return
        try:
            service = self.context.registry.get(self._current_service_id)
            action = service.action(sub.action_id)
        except KeyError:
            logger.warning("sub-action %r not found in service %r", sub.action_id, self._current_service_id)
            return
        inputs: dict[str, str] = {}
        for field_name, attr_name in sub.prefill.items():
            value = None
            if _dc.is_dataclass(row) and not isinstance(row, type):
                value = getattr(row, attr_name, None)
            elif hasattr(row, attr_name):
                value = getattr(row, attr_name)
            if value is not None:
                inputs[field_name] = str(value)

        def sub_worker() -> None:
            try:
                result = self.context.execute(action, inputs)
            except Exception as exc:
                self.results_queue.put(("sub_error", sub, str(exc), generation))
                return
            self.results_queue.put(("sub_ok", sub, (result, dict(inputs)), generation))

        # Same serialised queue as default actions and eager fetches; capture
        # the generation so a sub-action enqueued before a nav-switch doesn't
        # run after the user has moved on.
        generation = self._nav_generation
        self._action_queue.submit(
            sub_worker,
            lambda gen=generation: gen == self._nav_generation,
            f"sub-action {action.action_id}",
        )

    def _on_row_action(self, service_id: str, row_action: RowAction, row: Any) -> None:
        """Open an ActionDialog pre-filled from the selected row."""
        try:
            service = self.context.registry.get(service_id)
            action = service.action(row_action.action_id)
        except KeyError:
            logger.warning("row action %r references unknown action in service %r", row_action.action_id, service_id)
            return
        prefill: dict[str, str] = {}
        if row is not None:
            for field_name, attr_name in row_action.prefill.items():
                value = None
                if dataclasses.is_dataclass(row) and not isinstance(row, type):
                    value = getattr(row, attr_name, None)
                elif hasattr(row, attr_name):
                    value = getattr(row, attr_name)
                if value is not None:
                    prefill[field_name] = str(value)
        self.open_action_dialog(action, prefill=prefill)

    def _on_sub_row_action(self, service_id: str, row_action: RowAction, row: Any) -> None:
        """Open an ActionDialog for the currently selected sub-row."""
        self._on_row_action(service_id, row_action, row)

    @staticmethod
    def _filter_rows_by_inputs(rows: list[Any], inputs: dict[str, str]) -> list[Any]:
        """Apply any exact-match filters whose input names also exist on the row objects."""
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

    # ── ActionDialog ──────────────────────────────────────────────────────────

    def open_action_dialog(self, action: ActionDefinition, prefill: dict[str, str]) -> None:
        """Open a combined ActionDialog for the given action."""
        dialog = ActionDialog(
            self.root,
            action,
            prefill=prefill,
            on_run=self._dialog_run,
            on_generate_scripts=self._generate_scripts,
        )
        self.active_dialog = dialog

    def _generate_scripts(self, action: ActionDefinition, inputs: dict[str, str]) -> tuple[str, str]:
        cli = generate_cli_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        return cli, python

    def _dialog_run(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Called when the user clicks Run in the combined ActionDialog."""
        cli, python = self._generate_scripts(action, inputs)
        self.main_panel.show_scripts(cli, python)
        self.run_action(action, inputs)

    # ── Action execution ──────────────────────────────────────────────────────

    def run_action(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Execute an action via the single-worker queue.

        Rapid nav switching just replaces the pending job — at most one HTTP
        call is in flight at any time.
        """
        self.current_action = action
        self.current_inputs = dict(inputs)
        cli = generate_cli_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        self.main_panel.show_scripts(cli, python)
        self.status_bar.set_status("Loading")
        self.status_bar.set_last_action(action.action_id)
        generation = self._nav_generation
        # Capture inputs/action in the closure so the worker has its own copy.
        captured_inputs = dict(inputs)

        def job() -> None:
            try:
                result = self.context.execute(action, captured_inputs)
            except Exception as exc:
                logger.exception("action %s failed", action.action_id)
                self.results_queue.put(("error", action, str(exc), generation))
                return
            self.results_queue.put(("ok", action, result, generation))

        self._action_queue.submit(
            job,
            lambda gen=generation: gen == self._nav_generation,
            f"action {action.action_id}",
        )

    # ── Queue polling ─────────────────────────────────────────────────────────

    def poll_queue(self) -> None:
        try:
            while True:
                try:
                    message = self.results_queue.get_nowait()
                except queue.Empty:
                    break
                # Messages may be 3-tuples (legacy: moto/demo/sub) or 4-tuples
                # (action/choices: includes generation). Normalise to 4-tuple.
                if len(message) == 3:
                    kind, action, payload = message
                    generation = None
                else:
                    kind, action, payload, generation = message
                try:
                    self.dispatch_result(kind, action, payload, generation)
                except Exception:
                    # One bad dispatch must NOT stop the poll loop — if it did,
                    # every panel would freeze until the user restarted the app.
                    logger.exception(
                        "dispatch_result raised for kind=%r action=%r — continuing",
                        kind,
                        getattr(action, "action_id", action),
                    )
        finally:
            # Always reschedule, even if our own loop body raised somehow.
            self.root.after(50, self.poll_queue)

    def refresh_diagnostics(self) -> None:
        """Refresh the diagnostic tabs from live runtime state."""
        try:
            self.moto_output_panel.set_text(self._render_moto_output())
            self.robotocore_panel.set_text(self._render_robotocore_output())
            self.queue_panel.set_snapshot(self._queue_diagnostics_snapshot())
            self.cache_panel.set_snapshot(self._cache_diagnostics_snapshot())
        finally:
            self.root.after(1000, self.refresh_diagnostics)

    def _render_moto_output(self) -> str:
        snapshot = self.moto_manager.snapshot()
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

    def _render_robotocore_output(self) -> str:
        snapshot = self.robotocore_manager.snapshot()
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

    def _queue_diagnostics_snapshot(self) -> dict[str, Any]:
        snapshot = self._action_queue.snapshot()
        snapshot["result_queue_depth"] = self.results_queue.qsize()
        snapshot["current_nav_generation"] = self._nav_generation
        snapshot["current_service"] = self._current_service_id
        snapshot["current_nav"] = getattr(self._current_nav, "item_id", None)
        return snapshot

    def _cache_diagnostics_snapshot(self) -> dict[str, Any]:
        snapshot = self.context.action_cache.snapshot()
        snapshot["mode"] = str(self.context.mode)
        snapshot["profile"] = self.context.profile_name or "(environment)"
        snapshot["region"] = self.context.region_name
        snapshot["endpoint"] = self.context.endpoint_config.resolved_url() or "(aws)"
        return snapshot

    def dispatch_result(
        self,
        kind: str,
        action: ActionDefinition | None,
        payload: Any,
        generation: int | None = None,
    ) -> None:
        # Drop results from a stale nav generation — the user moved on and
        # touching the panel for them would corrupt the current view.
        # Default-action and sub-panel results update the current browser view,
        # so they participate in the generation check. Moto/demo/choice results
        # are either global or targeted to named widgets.
        if (
            kind in ("ok", "error", "sub_ok", "sub_error")
            and generation is not None
            and generation != self._nav_generation
        ):
            # Stale result for an older selection/refresh; ignore it.
            return
        if kind == "moto_started":
            endpoint_url: str = payload
            self.context.set_endpoint(EndpointMode.MOTO, endpoint_url)
            self.toolbar.endpoint_mode_var.set(EndpointMode.MOTO.value)
            self.toolbar.endpoint_url_var.set(endpoint_url)
            self.toolbar.moto_running = True
            self.toolbar.moto_btn.configure(text="Stop Moto")
            self.status_bar.set_status(f"Moto running at {endpoint_url}")
            self.on_toolbar_changed()
            return
        if kind == "moto_error":
            self.status_bar.set_status("Moto start failed")
            messagebox.showerror("Moto server error", f"Could not start moto server:\n{payload}")
            self.toolbar.moto_running = False
            self.toolbar.moto_btn.configure(text="Start Moto")
            return
        if kind == "robotocore_started":
            rc_url: str = payload
            self.context.set_endpoint(EndpointMode.ROBOTOCORE, rc_url)
            self.toolbar.endpoint_mode_var.set(EndpointMode.ROBOTOCORE.value)
            self.toolbar.endpoint_url_var.set(rc_url)
            self.toolbar.robotocore_running = True
            self.toolbar.robotocore_btn.configure(text="Stop Robotocore")
            self.robotocore_panel.set_running(True)
            self.status_bar.set_status(f"Robotocore running at {rc_url}")
            self.on_toolbar_changed()
            return
        if kind == "robotocore_stopped":
            self.context.set_endpoint(EndpointMode.AWS)
            self.toolbar.endpoint_mode_var.set(EndpointMode.AWS.value)
            self.toolbar.endpoint_url_var.set("")
            self.toolbar.robotocore_running = False
            self.toolbar.robotocore_btn.configure(text="Start Robotocore")
            self.robotocore_panel.set_running(False)
            self.status_bar.set_status("Robotocore stopped")
            self.on_toolbar_changed()
            return
        if kind == "robotocore_pulled":
            self.status_bar.set_status("Robotocore image pull complete")
            self.robotocore_panel.set_status("Image up to date")
            return
        if kind == "robotocore_error":
            self.status_bar.set_status("Robotocore error")
            messagebox.showerror("Robotocore error", str(payload))
            self.toolbar.robotocore_running = False
            self.toolbar.robotocore_btn.configure(text="Start Robotocore")
            self.robotocore_panel.set_running(False)
            return
        if kind == "demo_ok":
            report: dict[str, list[str]] = payload
            lines = [f"{rtype}: {', '.join(ids) if ids else '(none)'}" for rtype, ids in report.items()]
            self.status_bar.set_status("Demo resources seeded")
            self._schedule_demo_cache_seed()
            messagebox.showinfo("Demo resources seeded", "\n".join(lines) or "Nothing was created.")
            return
        if kind == "demo_error":
            self.status_bar.set_status("Demo seed failed")
            messagebox.showerror("Demo seed error", f"Failed to seed demo resources:\n{payload}")
            return
        if kind == "sub_ok":
            sub = action  # reusing the action slot for SubAction
            result, sub_inputs = payload
            raw = getattr(result, "response", None) or getattr(result, "parsed_json", None)
            if raw is not None:
                from gui4aws.models import SubAction as _SubAction

                if isinstance(sub, _SubAction):
                    try:
                        service = self.context.registry.get(self._current_service_id or "")
                        act = service.action(sub.action_id)
                        if act.view is not None:
                            rows = act.view(raw)
                            rows = self._filter_rows_by_inputs(rows, sub_inputs)
                            self.main_panel.show_sub_table(sub.panel_label, rows, list(sub.columns))
                    except Exception:
                        logger.exception("sub-panel view failed for %s", getattr(sub, "action_id", sub))
            return

        if kind == "sub_error":
            logger.warning("sub-panel fetch failed: %s", payload)
            return

        if kind == "choices":
            # action slot carries the field name here.
            field_name = str(action)
            # Auto-select only for *required* fields — for optional ones, blank
            # is a meaningful value (e.g. ECS Tasks' service_name = "all
            # services") and we shouldn't override it.
            auto_select = True
            nav = getattr(self, "_current_nav", None)
            if nav is not None:
                for fld in nav.filter_fields:
                    if fld.name == field_name and not fld.required:
                        auto_select = False
                        break
            self.main_panel.set_filter_choices(field_name, list(payload), auto_select=auto_select)
            return

        if action is None:
            return

        self.record_history(action, kind, payload)

        if kind == "error":
            self.status_bar.set_status("Error")
            self.main_panel.output_panel.set_error(str(payload))
            if self.active_dialog and self.active_dialog.winfo_exists():
                self.active_dialog.set_status(f"Error: {payload}")
                self.active_dialog.set_result({"error": str(payload)})
            return

        if hasattr(payload, "exception_class"):
            self.status_bar.set_status("Error")
            message = getattr(payload, "message", None) or getattr(payload, "reason", "failed")
            error_code = getattr(payload, "aws_error_code", None)
            full_message = f"{error_code}: {message}" if error_code else message
            logger.error("action %s failed: %s", action.action_id, full_message)
            self.main_panel.output_panel.set_error(full_message)
            if self.active_dialog and self.active_dialog.winfo_exists():
                self.active_dialog.set_status(f"Failed: {full_message}")
                self.active_dialog.set_result({"error": full_message})
            return

        self.status_bar.set_status("Ready")

        view = action.view
        raw_response: Any = getattr(payload, "response", None) or getattr(payload, "parsed_json", None)

        # Update dialog status and show result if it's still open.
        if self.active_dialog and self.active_dialog.winfo_exists():
            self.active_dialog.set_status("Done.")
            if raw_response is not None:
                self.active_dialog.set_result(raw_response)

        if action.risk_level is not RiskLevel.READ_ONLY:
            self._schedule_cache_refreshes_for_action(action)
            self._refresh_visible_data_after_write(action)

        if view is not None and raw_response is not None:
            try:
                rows = view(raw_response)
            except Exception as exc:
                logger.exception("view function failed for %s", action.action_id)
                self.main_panel.output_panel.set_error(f"View failed: {exc}")
                return
            columns = list(action.result_view.columns) or (list(vars(rows[0]).keys()) if rows else [])
            self.main_panel.show_table(rows, columns)
            count = len(rows)
            self.main_panel.show_output(f"{count} {'item' if count == 1 else 'items'}", raw_response)
            return

        self.main_panel.show_output(f"{action.action_id} ok", raw_response)

    def record_history(self, action: ActionDefinition, kind: str, payload: Any) -> None:
        from datetime import datetime, timezone

        from gui4aws.execution.action_history import ActionHistoryEntry

        inputs = dict(self.current_inputs)
        cli = generate_cli_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        is_failure = kind == "error" or hasattr(payload, "exception_class")
        error_message: str | None = None
        duration = float(getattr(payload, "duration_seconds", 0.0) or 0.0)
        if is_failure:
            error_message = getattr(payload, "message", None) or getattr(payload, "reason", None) or str(payload)
        self.context.history.add(
            ActionHistoryEntry(
                timestamp=datetime.now(timezone.utc),
                service_id=action.service_id,
                action_id=action.action_id,
                mode=self.context.mode,
                profile_name=self.context.profile_name,
                region_name=self.context.region_name,
                endpoint_url=self.context.endpoint_config.resolved_url(),
                inputs=inputs,
                cli_script=cli,
                python_script=python,
                status="failure" if is_failure else "success",
                duration_seconds=duration,
                error_message=error_message,
            )
        )

    def run(self) -> None:
        self.root.mainloop()


def create_main_window(
    context: AppContext,
    *,
    profiles: list[str] | None = None,
    regions: list[str] | None = None,
) -> MainWindow:
    """Factory that builds a MainWindow without entering mainloop."""
    return MainWindow(context, profiles=profiles, regions=regions)
