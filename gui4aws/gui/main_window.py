"""MainWindow: composes toolbar + sidebar + main panel + status bar."""

# pylint: disable=broad-exception-caught,too-many-lines

from __future__ import annotations

import contextlib
import dataclasses
import logging
import queue
import tkinter as tk
from functools import partial
from tkinter import messagebox, ttk
from typing import Any

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.gui.action_dialog import ActionDialog
from gui4aws.gui.diagnostic_panel import CacheDiagnosticsPanel, DiagnosticPanel, QueueDiagnosticsPanel, RobotocorePanel
from gui4aws.gui.main_panel import MainPanel
from gui4aws.gui.script_editor_panel import ScriptEditorPanel
from gui4aws.gui.server_manager_mixin import ServerManagerMixin
from gui4aws.gui.sidebar import Sidebar, SidebarSelection
from gui4aws.gui.status_bar import StatusBar
from gui4aws.gui.toolbar import Toolbar
from gui4aws.gui.window_helpers import build_about_text as _build_about_text
from gui4aws.gui.window_helpers import extract_choices_from_raw as _extract_choices_from_raw
from gui4aws.gui.window_helpers import filter_rows_by_inputs as _filter_rows_by_inputs
from gui4aws.gui.window_helpers import nav_action_inputs as _nav_action_inputs
from gui4aws.gui.window_helpers import record_history as _record_history
from gui4aws.gui.window_helpers import render_moto_output as _render_moto_output
from gui4aws.gui.window_helpers import render_robotocore_output as _render_robotocore_output
from gui4aws.gui.window_helpers import resolve_required_filter_value as _resolve_required_filter_value
from gui4aws.gui.window_helpers import resolved_filter_values as _resolved_filter_values
from gui4aws.gui.window_helpers import seed_filter_values as _seed_filter_values
from gui4aws.gui.window_helpers import source_inputs_from_values as _source_inputs_from_values
from gui4aws.gui.worker import SerialWorker
from gui4aws.models import ActionDefinition, EagerChoiceSource, RiskLevel, RowAction, SubAction
from gui4aws.moto_server import MotoServerManager
from gui4aws.robotocore_server import RobotocoreManager

__all__ = ["MainWindow", "SerialWorker", "create_main_window"]

logger = logging.getLogger(__name__)


def _maximize_window(root: tk.Tk) -> None:
    """Maximize the window in a cross-platform way."""
    import sys

    if sys.platform.startswith("win"):
        root.state("zoomed")
    else:
        # Linux/macOS: -zoomed attribute (works on most compositing WMs);
        # fall back to filling the screen geometry if the attribute is unsupported.
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")


class MainWindow(ServerManagerMixin):
    """The application's top-level window."""

    def __init__(
        self,
        context: AppContext,
        *,
        root: tk.Tk | None = None,
        profiles: list[str] | None = None,
        regions: list[str] | None = None,
    ) -> None:
        """Initialize the main window and all its sub-panels.

        If ``root`` is not provided, a new ``tk.Tk`` instance is created.
        """
        self.context = context
        self.root = root or tk.Tk()
        self.root.title("gui4aws — AWS Think Console")
        _maximize_window(self.root)

        self.results_queue: queue.Queue[Any] = queue.Queue()
        self.moto_manager = MotoServerManager()
        self.robotocore_manager = RobotocoreManager()
        # Track the last opened ActionDialog so we can update its status label.
        self.active_dialog: ActionDialog | None = None

        self.build_menu()

        self.toolbar = Toolbar(
            self.root,
            context,
            profiles=profiles or [],
            regions=regions or [],
            on_change=self.on_toolbar_changed,
            on_moto_toggle=self.on_moto_toggle,
            on_robotocore_toggle=self.on_robotocore_toggle,
            on_clear_cache=self.clear_all_cache_entries,
            on_partition_changed=self.on_partition_changed,
            on_network_settings=self.open_network_settings,
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
                ("Reset Moto State", self.reset_moto_state),
                ("Open Dashboard", self.open_moto_dashboard),
            ),
        )
        self.robotocore_panel = RobotocorePanel(
            self.content_tabs,
            on_start=self.robotocore_start,
            on_stop=self.robotocore_stop,
            on_restart=self.robotocore_restart,
            on_reset=self.robotocore_reset_state,
            on_pull=self.robotocore_pull,
            on_use_moto_changed=self.robotocore_use_moto_changed,
        )
        self.queue_panel = QueueDiagnosticsPanel(self.content_tabs, on_clear=self.clear_request_queue)
        self.cache_panel = CacheDiagnosticsPanel(
            self.content_tabs,
            on_clear_selected=self.clear_selected_cache_entry,
            on_clear_all=self.clear_all_cache_entries,
        )
        self.script_editor = ScriptEditorPanel(self.content_tabs)
        self.content_tabs.add(self.main_panel, text="Browser")
        self.content_tabs.add(self.script_editor, text="Script Editor")
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
        self.current_sub_action: Any = None
        self.current_service_id: str | None = None
        self.current_nav: Any = None
        # Bumped on every nav switch; workers check this to drop stale results.
        self.nav_generation: int = 0
        # Single worker thread — see SerialWorker docstring for rationale.
        self.action_queue = SerialWorker()
        self.root.after(50, self.poll_queue)
        self.root.after(1000, self.refresh_diagnostics)

        # Pagination state — reset on every nav selection / manual refresh.
        self._page_base_inputs: dict[str, str] = {}
        self._page_tokens: list[str | None] = [None]  # tokens[i] = token used to reach page i
        self._page_idx: int = 0
        self._page_next_token: str | None = None
        self._page_token_input_key: str | None = None  # "NextToken" | "Marker" etc.

    # ── Menu ─────────────────────────────────────────────────────────────────

    def build_menu(self) -> None:
        """Create the top-level menu bar."""
        menubar = tk.Menu(self.root)
        self.root.configure(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Switch to Script Editor", command=self.switch_to_script_editor)
        file_menu.add_command(label="Switch to Browser", command=self.switch_to_browser)
        file_menu.add_command(label="Save Script...", command=self.save_script)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)

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
                "Start Moto (toolbar button) or connect Robotocore, then select Demo → Seed demo resources.\n\n"
                "WARNING: Seeding on live AWS will create real billable resources.",
            ),
        )

        help_menu = tk.Menu(menubar, tearoff=False)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Documentation", command=self.open_docs)
        help_menu.add_separator()
        help_menu.add_command(label="About gui4aws", command=self.show_about)

    def switch_to_script_editor(self) -> None:
        """Bring the Script Editor tab to the front."""
        self.content_tabs.select(self.script_editor)  # type: ignore[no-untyped-call]

    def switch_to_browser(self) -> None:
        """Bring the Browser tab to the front."""
        self.content_tabs.select(self.main_panel)  # type: ignore[no-untyped-call]

    def save_script(self) -> None:
        """Delegate to the Script Editor's save dialog."""
        self.script_editor._save()  # pylint: disable=protected-access

    def open_docs(self) -> None:
        """Open the documentation website in the default browser."""
        import webbrowser

        webbrowser.open("https://gui4aws.readthedocs.io/en/latest/")

    def show_about(self) -> None:
        """Show the 'About' dialog with version and dependency information."""
        text = _build_about_text(
            robotocore_running=self.robotocore_manager.running,
            robotocore_endpoint_url=self.robotocore_manager.endpoint_url,
        )
        messagebox.showinfo("About gui4aws", text)

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def on_toolbar_changed(self) -> None:
        """Refresh the status bar when toolbar settings (profile, region) change."""
        self.status_bar.refresh_context()
        self._save_config()

    def _save_config(self) -> None:
        """Persist the current profile/region/partition + network settings to the config file."""
        try:
            from gui4aws.config import AppConfig, save_config

            net = self.context.network_config
            cfg = AppConfig(
                default_profile=self.context.profile_name or "",
                default_region=self.context.region_name,
                default_partition=self.context.partition,
                network_use_env_proxy=net.use_env_proxy,
                network_http_proxy=net.http_proxy,
                network_https_proxy=net.https_proxy,
                network_no_proxy=net.no_proxy,
                network_ca_bundle_path=net.ca_bundle_path,
                network_client_cert_path=net.client_cert_path,
                network_verify_ssl=net.verify_ssl,
            )
            save_config(cfg)
        except Exception:  # pylint: disable=broad-exception-caught
            logger.debug("config save failed", exc_info=True)

    def on_partition_changed(self, partition: str) -> None:
        """Update the region list when the partition changes."""
        from gui4aws.cli import available_regions

        regions = available_regions(partition=partition)
        self.toolbar.update_regions(regions)

    def open_network_settings(self) -> None:
        """Open the proxy / TLS settings dialog and apply the result on save."""
        from gui4aws.gui.network_settings_dialog import open_network_settings

        open_network_settings(
            self.root,
            self.context.network_config,
            on_apply=self.apply_network_settings,
        )

    def apply_network_settings(self, network_config: Any) -> None:
        """Apply new proxy/TLS settings, persist them, and refresh the toolbar."""
        self.context.set_network_config(network_config)
        self.toolbar._refresh_network_button()  # pylint: disable=protected-access
        self._save_config()
        summary = "default" if network_config.is_default() else "custom proxy/TLS"
        self.status_bar.set_status(f"Network settings applied ({summary}) — cache cleared")

    def refresh_diagnostics_now(self) -> None:
        """Refresh diagnostic widgets immediately without scheduling timers."""
        self.moto_output_panel.set_text(self.render_moto_output())
        self.robotocore_panel.set_text(self.render_robotocore_output())
        self.queue_panel.set_snapshot(self.queue_diagnostics_snapshot())
        self.cache_panel.set_snapshot(self.cache_diagnostics_snapshot())

    def clear_request_queue(self) -> None:
        """Drop pending work from the request and result queues."""
        removed_jobs = self.action_queue.clear_pending()
        removed_results = 0
        while True:
            try:
                self.results_queue.get_nowait()
            except queue.Empty:
                break
            removed_results += 1
        self.status_bar.set_status(f"Cleared queue ({removed_jobs} pending, {removed_results} ready)")
        self.refresh_diagnostics_now()

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
        self.refresh_diagnostics_now()

    def clear_all_cache_entries(self) -> None:
        """Remove all cached read results."""
        self.context.invalidate_read_cache()
        self.status_bar.set_status("Cleared cache")
        self.refresh_diagnostics_now()

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
        self.nav_generation += 1

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
        self._reset_pagination()

        self.current_sub_action = nav.sub_action
        self.current_service_id = service.service_id
        self.current_nav = nav

        # Configure the filter bar for this nav (always — empty fields if none).
        self.main_panel.configure_filter_bar(
            nav.filter_fields,
            on_refresh=self.refresh_current_nav,
        )
        # Wire dependent-field watchers so that picking e.g. a cluster refires
        # the eager fetch for service_name.
        self.main_panel.set_filter_field_change_handler(self.on_filter_field_changed)

        if nav.row_actions or nav.sub_action:
            self.main_panel.set_row_actions(
                nav.row_actions,
                on_row_action=partial(self.on_row_action, service.service_id),
                on_row_select=self.on_sub_action_row_select if nav.sub_action else None,
            )
        else:
            self.main_panel.set_row_actions((), None)
        self.main_panel.set_sub_row_actions(
            nav.sub_action.row_actions if nav.sub_action else (),
            partial(self.on_sub_row_action, service.service_id) if nav.sub_action else None,
        )

        # Kick off any eager-choice fetches so dropdowns get populated.
        # Only fields without a depends_on are loaded here; dependent ones
        # are fired when their dependency picks up a value.
        self.dispatch_eager_choices(service, nav, only_independent=True)

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
        if self.missing_required(nav, inputs):
            self.status_bar.set_status("Pick a value above and click Refresh")
            return

        self.run_action(action, inputs=inputs)

    def refresh_current_nav(self, values: dict[str, str]) -> None:
        """Re-run the current nav's default action with the filter-bar values."""
        nav = getattr(self, "current_nav", None)
        service_id = self.current_service_id
        if nav is None or service_id is None or nav.default_action_id is None:
            return
        if self.missing_required(nav, values):
            self.status_bar.set_status("Fill in the required filter fields above")
            return
        try:
            service = self.context.registry.get(service_id)
            action = service.action(nav.default_action_id)
        except KeyError:
            return
        # Treat a refresh as a new generation too — any previously in-flight
        # default-action worker is now stale.
        self.nav_generation += 1
        self._reset_pagination()
        self.run_action(action, inputs=values)

    def on_filter_field_changed(self, field_name: str, value: str) -> None:
        """Handle value changes in the filter bar.

        Called by FilterBar when any (non-client-filter) field's value changes.
        Refires eager-choice fetches whose ``depends_on`` references this field.
        """
        nav = getattr(self, "current_nav", None)
        service_id = self.current_service_id
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
            self.launch_eager_fetch(service, fname, source)

    def missing_required(self, nav: Any, values: dict[str, str]) -> bool:
        """Check if any required filter fields are missing values."""
        return any(fld.required and not values.get(fld.name, "").strip() for fld in nav.filter_fields)

    def dispatch_eager_choices(self, service: Any, nav: Any, *, only_independent: bool) -> None:
        """Fetch data for dropdowns in the filter bar.

        For each (field_name → EagerChoiceSource), fetch the source action
        in a worker thread and populate the dropdown when it returns.

        If ``only_independent`` is True, skip sources with non-empty
        ``depends_on`` — those are fired by on_filter_field_changed once
        their dependency picks up a value.
        """
        if not nav.eager_choices:
            return
        for field_name, source in nav.eager_choices.items():
            if only_independent and getattr(source, "depends_on", None):
                continue
            self.launch_eager_fetch(service, field_name, source)

    def launch_eager_fetch(self, service: Any, field_name: str, source: Any) -> None:
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

        generation = self.nav_generation

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
                choices = self.extract_choices_from_raw(source.jmespath, raw)
            except Exception as exc:
                logger.warning("eager_choice JMESPath failed for %s: %s", field_name, exc)
                return
            self.results_queue.put(("choices", field_name, choices, generation))

        # Route through the same single-worker queue as default actions, so
        # rapid nav switching can't pile up parallel eager fetches. Stale
        # generations skipped at dispatch time.
        self.action_queue.submit(
            worker,
            lambda gen=generation: gen == self.nav_generation,
            f"choices {field_name}",
        )

    def extract_choices_from_raw(self, jmespath_expression: str, raw: Any) -> list[str]:
        """Extract a list of strings from raw API response using JMESPath."""
        return _extract_choices_from_raw(jmespath_expression, raw)

    def seed_filter_values(self, nav: Any, current_values: dict[str, str]) -> dict[str, str]:
        """Combine default values with current values for filter fields."""
        return _seed_filter_values(nav, current_values)

    def source_inputs_from_values(
        self,
        source: EagerChoiceSource,
        values: dict[str, str],
    ) -> dict[str, str] | None:
        """Map filter field values to source action input parameters."""
        return _source_inputs_from_values(source, values)

    def resolve_required_filter_value(
        self,
        service: Any,
        nav: Any,
        field_name: str,
        values: dict[str, str],
        resolving: set[str],
    ) -> str | None:
        """Recursively resolve a required filter field by fetching its first choice."""
        return _resolve_required_filter_value(service, nav, field_name, values, resolving, execute=self.context.execute)

    def resolved_filter_values(
        self,
        service: Any,
        nav: Any,
        current_values: dict[str, str],
    ) -> dict[str, str] | None:
        """Try to fill all required filter fields by fetching choices."""
        return _resolved_filter_values(service, nav, current_values, execute=self.context.execute)

    def nav_action_inputs(self, nav: Any, values: dict[str, str]) -> dict[str, str]:
        """Extract inputs for the default nav action from resolved filter values."""
        return _nav_action_inputs(nav, values)

    def submit_nav_cache_warm(
        self,
        service: Any,
        nav: Any,
        current_values: dict[str, str],
    ) -> None:
        """Pre-fetch data for a navigation item to warm the cache."""
        if nav.default_action_id is None:
            return
        try:
            default_action = service.action(nav.default_action_id)
        except KeyError:
            logger.warning("cache warm skipped unknown nav action %r", nav.default_action_id)
            return
        captured_values = dict(current_values)

        def warm_nav() -> None:
            values = self.resolved_filter_values(service, nav, captured_values)
            if values is None:
                return
            for source in nav.eager_choices.values():
                try:
                    source_action = service.action(source.action_id)
                except KeyError:
                    logger.warning("cache warm skipped unknown eager action %r", source.action_id)
                    continue
                source_inputs = self.source_inputs_from_values(source, values)
                if source_inputs is None:
                    continue
                self.context.execute(source_action, source_inputs)
            self.context.execute(default_action, self.nav_action_inputs(nav, values))

        self.action_queue.submit(warm_nav, lambda: True, f"cache warm {service.service_id}.{nav.item_id}")

    def schedule_cache_refreshes_for_action(self, action: ActionDefinition) -> None:
        """Invalidate cache and schedule warming for nav items affected by an action."""
        self.context.invalidate_read_cache(action.service_id)
        if not action.cache_refresh_nav_ids:
            return
        try:
            service = self.context.registry.get(action.service_id)
        except KeyError:
            logger.warning("cache refresh skipped unknown service %r", action.service_id)
            return
        current_values = self.main_panel.filter_values() if self.current_service_id == action.service_id else {}
        target_nav_ids = set(action.cache_refresh_nav_ids)
        for nav in service.navigation_items:
            if nav.item_id in target_nav_ids:
                self.submit_nav_cache_warm(service, nav, current_values)

    def refresh_visible_data_after_write(self, action: ActionDefinition) -> None:
        """Reload the visible grid after a successful write affecting the current nav."""
        nav = getattr(self, "current_nav", None)
        if nav is None or self.current_service_id != action.service_id:
            return
        if nav.item_id not in set(action.cache_refresh_nav_ids):
            return
        self.refresh_current_nav(self.main_panel.filter_values())

    def schedule_demo_cache_seed(self) -> None:
        """Warm the cache for all navigation items in all services."""
        self.context.invalidate_read_cache()
        for service in self.context.registry:
            for nav in service.navigation_items:
                self.submit_nav_cache_warm(service, nav, {})

    # ── Pagination ────────────────────────────────────────────────────────────

    def _reset_pagination(self) -> None:
        """Clear all pagination state for the current nav view."""
        self._page_base_inputs = {}
        self._page_tokens = [None]
        self._page_idx = 0
        self._page_next_token = None
        self._page_token_input_key = None
        self.main_panel.clear_pagination()

    def _update_pagination_from_response(self, raw_response: Any) -> None:
        """Detect a next-page token in the response and show/hide the pagination bar."""
        # Guard: if pagination state was never initialized (e.g. in tests that use
        # object.__new__), skip silently rather than crashing.
        if not hasattr(self, "_page_tokens"):
            return

        next_token: str | None = None
        token_input_key: str | None = None
        if isinstance(raw_response, dict):
            for resp_key, inp_key in (
                ("NextToken", "NextToken"),
                ("Marker", "Marker"),
                ("NextMarker", "Marker"),
            ):
                val = raw_response.get(resp_key)
                if val:
                    next_token = str(val)
                    token_input_key = inp_key
                    break

        self._page_next_token = next_token
        if token_input_key:
            self._page_token_input_key = token_input_key

        if not self._page_base_inputs:
            # Snapshot the current inputs (minus any token) as the base for this result set.
            _token_keys = {"NextToken", "Marker", "StartingToken"}
            self._page_base_inputs = {k: v for k, v in self.current_inputs.items() if k not in _token_keys}

        if next_token is not None:
            # Grow the token list if we haven't cached the next-page token yet.
            expected_next = self._page_idx + 1
            if len(self._page_tokens) <= expected_next:
                self._page_tokens.append(next_token)
            self.main_panel.set_pagination(
                has_prev=self._page_idx > 0,
                has_next=True,
                page_num=self._page_idx + 1,
                on_prev=self._on_prev_page,
                on_next=self._on_next_page,
            )
        elif self._page_idx > 0:
            # Last page of a multi-page result set — still show Prev.
            self.main_panel.set_pagination(
                has_prev=True,
                has_next=False,
                page_num=self._page_idx + 1,
                on_prev=self._on_prev_page,
                on_next=None,
            )
        else:
            self.main_panel.clear_pagination()

    def _on_next_page(self) -> None:
        if self._page_next_token is None or self.current_action is None:
            return
        self._page_idx += 1
        token = self._page_tokens[self._page_idx] if self._page_idx < len(self._page_tokens) else self._page_next_token
        inputs = dict(self._page_base_inputs)
        if token and self._page_token_input_key:
            inputs[self._page_token_input_key] = token
        self.nav_generation += 1
        self.run_action(self.current_action, inputs)

    def _on_prev_page(self) -> None:
        if self._page_idx <= 0 or self.current_action is None:
            return
        self._page_idx -= 1
        inputs = dict(self._page_base_inputs)
        token = self._page_tokens[self._page_idx]
        if token and self._page_token_input_key:
            inputs[self._page_token_input_key] = token
        self.nav_generation += 1
        self.run_action(self.current_action, inputs)

    def on_sub_action_row_select(self, row: Any) -> None:
        """Fire the sub_action when a row is selected and show results in the sub-panel."""
        sub = self.current_sub_action
        if sub is None or self.current_service_id is None:
            return
        try:
            service = self.context.registry.get(self.current_service_id)
            action = service.action(sub.action_id)
        except KeyError:
            logger.warning("sub-action %r not found in service %r", sub.action_id, self.current_service_id)
            return
        inputs: dict[str, str] = {}
        for field_name, attr_name in sub.prefill.items():
            value = None
            if dataclasses.is_dataclass(row) and not isinstance(row, type):
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
        generation = self.nav_generation
        self.action_queue.submit(
            sub_worker,
            lambda gen=generation: gen == self.nav_generation,
            f"sub-action {action.action_id}",
        )

    def on_row_action(self, service_id: str, row_action: RowAction, row: Any) -> None:
        """Open an ActionDialog pre-filled from the selected row.

        First applies the row's own attributes (via row_action.prefill), then
        falls back to current filter-bar values for any action fields that are
        still empty. This ensures context fields like 'cluster' are populated
        even when the row itself doesn't carry them (e.g. a service row in a
        cluster-scoped list).

        Sentinel action IDs (``cdk://launch``, ``terraform://launch``) open
        their respective specialist dialogs instead of a generic ActionDialog.
        """
        # ── Sentinel: CDK launcher ────────────────────────────────────────────
        if row_action.action_id == "cdk://launch":
            from gui4aws.gui.cdk_dialog import CdkDialog

            stack_name = str(getattr(row, "name", "") or "") if row is not None else ""
            CdkDialog(self.root, stack_name=stack_name)
            return

        # ── Sentinel: Terraform launcher (stub) ───────────────────────────────
        if row_action.action_id == "terraform://launch":
            from gui4aws.gui.terraform_dialog import TerraformDialog

            TerraformDialog(self.root)
            return

        # ── Sentinel: SQL runner ──────────────────────────────────────────────
        if row_action.action_id == "sql://query":
            from gui4aws.gui.sql_runner_dialog import open_sql_runner

            cluster_id = ""
            cluster_engine = ""
            if row is not None:
                cluster_id = str(getattr(row, "cluster_identifier", "") or "")
                cluster_engine = str(getattr(row, "engine", "") or "")
            try:
                boto3_session = self.context.boto3_executor().build_session()
            except Exception:  # pylint: disable=broad-exception-caught
                boto3_session = None
            open_sql_runner(
                self.root,
                cluster_identifier=cluster_id,
                cluster_engine=cluster_engine,
                boto3_session=boto3_session,
            )
            return

        # Action IDs like "kms.describe_key" reference a different service than the current one.
        target_service_id = service_id
        if "." in row_action.action_id:
            maybe_service_id = row_action.action_id.split(".", 1)[0]
            try:
                self.context.registry.get(maybe_service_id)
                target_service_id = maybe_service_id
            except KeyError:
                pass
        try:
            service = self.context.registry.get(target_service_id)
            action = service.action(row_action.action_id)
        except KeyError:
            logger.warning(
                "row action %r references unknown action in service %r", row_action.action_id, target_service_id
            )
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
        # Back-fill from the active filter bar for any action input field that
        # is still unset. This covers context fields (e.g. "cluster") that live
        # on the filter bar but not on individual service/task row objects.
        filter_values = self.main_panel.filter_values()
        for field in action.input_fields:
            if field.name not in prefill and field.name in filter_values and filter_values[field.name]:
                prefill[field.name] = filter_values[field.name]
        self.open_action_dialog(action, prefill=prefill)

    def on_sub_row_action(self, service_id: str, row_action: RowAction, row: Any) -> None:
        """Open an ActionDialog for the currently selected sub-row."""
        self.on_row_action(service_id, row_action, row)

    @staticmethod
    def filter_rows_by_inputs(rows: list[Any], inputs: dict[str, str]) -> list[Any]:
        """Apply any exact-match filters whose input names also exist on the row objects."""
        return _filter_rows_by_inputs(rows, inputs)

    # ── ActionDialog ──────────────────────────────────────────────────────────

    def open_action_dialog(self, action: ActionDefinition, prefill: dict[str, str]) -> None:
        """Open a combined ActionDialog for the given action."""
        dialog = ActionDialog(
            self.root,
            action,
            prefill=prefill,
            on_run=self.dialog_run,
            on_generate_scripts=self.generate_scripts,
        )
        self.active_dialog = dialog

    def generate_scripts(self, action: ActionDefinition, inputs: dict[str, str]) -> tuple[str, str]:
        """Generate AWS CLI and Boto3 scripts for the given action and inputs."""
        cli = generate_cli_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
            network_config=self.context.network_config,
        )
        python = generate_python_script(
            action,
            inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
            network_config=self.context.network_config,
        )
        return cli, python

    def dialog_run(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Execute an action from the ActionDialog.

        Called when the user clicks Run in the combined ActionDialog.
        """
        cli, python = self.generate_scripts(action, inputs)
        self.main_panel.show_scripts(cli, python)
        self.run_action(action, inputs)

    # ── Action execution ──────────────────────────────────────────────────────

    def run_action(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Execute an action via the single-worker queue.

        Actions with a ``text_generator`` are handled synchronously — no boto3
        call is made; the text is generated immediately from the input values.

        For all other actions, rapid nav switching just replaces the pending
        job — at most one HTTP call is in flight at any time.
        """
        self.current_action = action
        self.current_inputs = dict(inputs)

        # Text-generator actions: produce output purely from inputs, no network call.
        if action.text_generator is not None:
            self.status_bar.set_last_action(action.action_id)
            try:
                generated = action.text_generator(inputs)
            except Exception as exc:
                logger.exception("text_generator failed for %s", action.action_id)
                self.main_panel.output_panel.set_error(f"Text generation failed: {exc}")
                return
            self.main_panel.show_output(generated, None, cli="")
            self.status_bar.set_status("Ready")
            return

        cli, python = self.generate_scripts(action, inputs)
        self.main_panel.show_scripts(cli, python)
        self.status_bar.set_status("Loading")
        self.status_bar.set_last_action(action.action_id)
        generation = self.nav_generation
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

        self.action_queue.submit(
            job,
            lambda gen=generation: gen == self.nav_generation,
            f"action {action.action_id}",
        )

    # ── Queue polling ─────────────────────────────────────────────────────────

    def poll_queue(self) -> None:
        """Periodically check the results queue for background job completion."""
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
            self.moto_output_panel.set_text(self.render_moto_output())
            self.robotocore_panel.set_text(self.render_robotocore_output())
            self.queue_panel.set_snapshot(self.queue_diagnostics_snapshot())
            self.cache_panel.set_snapshot(self.cache_diagnostics_snapshot())
        finally:
            self.root.after(1000, self.refresh_diagnostics)

    def render_moto_output(self) -> str:
        """Format Moto server status and logs for display."""
        return _render_moto_output(self.moto_manager.snapshot())

    def render_robotocore_output(self) -> str:
        """Format Robotocore status and logs for display."""
        return _render_robotocore_output(self.robotocore_manager.snapshot())

    def queue_diagnostics_snapshot(self) -> dict[str, Any]:
        """Gather internal queue and navigation state for diagnostics."""
        snapshot = self.action_queue.snapshot()
        snapshot["result_queue_depth"] = self.results_queue.qsize()
        snapshot["current_nav_generation"] = self.nav_generation
        snapshot["current_service"] = self.current_service_id
        snapshot["current_nav"] = getattr(self.current_nav, "item_id", None)
        return snapshot

    def cache_diagnostics_snapshot(self) -> dict[str, Any]:
        """Gather cache and endpoint state for diagnostics."""
        snapshot: dict[str, Any] = self.context.action_cache.snapshot()
        snapshot["mode"] = str(self.context.mode)
        snapshot["profile"] = self.context.profile_name or "(environment)"
        snapshot["region"] = self.context.region_name
        snapshot["endpoint"] = self.context.endpoint_config.resolved_url() or "(aws)"
        return snapshot

    # pylint: disable=too-many-return-statements
    def dispatch_result(
        self,
        kind: str,
        action: ActionDefinition | SubAction | str | None,
        payload: Any,
        generation: int | None = None,
    ) -> None:
        """Route a background job's result to the appropriate UI update function."""
        # Drop results from a stale nav generation — the user moved on and
        # touching the panel for them would corrupt the current view.
        # Default-action and sub-panel results update the current browser view,
        # so they participate in the generation check. Moto/demo/choice results
        # are either global or targeted to named widgets.
        if (
            kind in ("ok", "error", "sub_ok", "sub_error")
            and generation is not None
            and generation != self.nav_generation
        ):
            # Stale result for an older selection/refresh; ignore it.
            return
        if kind == "moto_started":
            endpoint_url: str = payload
            # Clear profile so live AWS data never mingles with moto data.
            self.toolbar.set_profile(None)
            self.context.set_endpoint(EndpointMode.MOTO, endpoint_url)
            self.context.invalidate_read_cache()
            self.toolbar.endpoint_mode_var.set(EndpointMode.MOTO.value)
            self.toolbar.endpoint_url_var.set(endpoint_url)
            self.toolbar.moto_running = True
            self.toolbar.moto_btn.configure(text="Stop Moto")
            self.status_bar.set_status(f"Moto running at {endpoint_url} — profile cleared")
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
        if kind == "moto_state_reset":
            self.context.invalidate_read_cache()
            self.status_bar.set_status("Moto state reset — cache cleared")
            return
        if kind == "robotocore_state_reset":
            self.context.invalidate_read_cache()
            self.status_bar.set_status("Robotocore state reset — cache cleared")
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
            self.schedule_demo_cache_seed()
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
            if raw is not None and isinstance(sub, SubAction):
                try:
                    service = self.context.registry.get(self.current_service_id or "")
                    act = service.action(sub.action_id)
                    if act.view is not None:
                        rows = act.view(raw)
                        rows = self.filter_rows_by_inputs(rows, sub_inputs)
                        self.main_panel.show_sub_table(sub.panel_label, rows, list(sub.columns))
                except Exception:  # pylint: disable=broad-exception-caught
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
            nav = getattr(self, "current_nav", None)
            if nav is not None:
                for fld in nav.filter_fields:
                    if fld.name == field_name and not fld.required:
                        auto_select = False
                        break
            self.main_panel.set_filter_choices(field_name, list(payload), auto_select=auto_select)
            return

        if action is None:
            return

        if isinstance(action, ActionDefinition):
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
            message = str(getattr(payload, "message", None) or getattr(payload, "reason", "failed"))
            error_code = getattr(payload, "aws_error_code", None)
            full_message = f"{error_code}: {message}" if error_code else message
            act_id = getattr(action, "action_id", str(action))
            logger.error("action %s failed: %s", act_id, full_message)
            self.main_panel.output_panel.set_error(full_message)
            if self.active_dialog and self.active_dialog.winfo_exists():
                self.active_dialog.set_status(f"Failed: {full_message}")
                self.active_dialog.set_result({"error": full_message})
            return

        self.status_bar.set_status("Ready")

        raw_response: Any = getattr(payload, "response", None) or getattr(payload, "parsed_json", None)

        # Update dialog status and show result if it's still open.
        if self.active_dialog and self.active_dialog.winfo_exists():
            self.active_dialog.set_status("Done.")
            if raw_response is not None:
                self.active_dialog.set_result(raw_response)

        if isinstance(action, ActionDefinition):
            # Record every successful action in the Script Editor.
            _cli_for_editor = getattr(self.main_panel, "scripts_cli", "")
            if _cli_for_editor and hasattr(self, "script_editor"):
                self.script_editor.append_action(action, _cli_for_editor)

            view = action.view
            if action.risk_level is not RiskLevel.READ_ONLY:
                self.schedule_cache_refreshes_for_action(action)
                self.refresh_visible_data_after_write(action)
                if action.action_id == "aurora.modify_db_cluster_password":
                    self._save_cluster_password_to_keyring(self.current_inputs)

            if action.text_generator is not None:
                try:
                    generated = action.text_generator(self.current_inputs)
                except Exception as exc:
                    logger.exception("text_generator failed for %s", action.action_id)
                    self.main_panel.output_panel.set_error(f"Text generation failed: {exc}")
                    return
                _cli = getattr(self.main_panel, "scripts_cli", "")
                self.main_panel.show_output(generated, raw_response, cli=_cli)
                return

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
                _cli = getattr(self.main_panel, "scripts_cli", "")
                self.main_panel.show_output(f"{count} {'item' if count == 1 else 'items'}", raw_response, cli=_cli)
                self._update_pagination_from_response(raw_response)
                return

            _cli = getattr(self.main_panel, "scripts_cli", "")
            self.main_panel.show_output(f"{action.action_id} ok", raw_response, cli=_cli)

    def record_history(self, action: ActionDefinition, kind: str, payload: Any) -> None:
        """Add an execution entry to the persistent action history."""
        _record_history(action, kind, payload, context=self.context, current_inputs=self.current_inputs)

    def _save_cluster_password_to_keyring(self, inputs: dict[str, str]) -> None:
        """Persist an Aurora connection string to the OS keyring after a password update."""
        from gui4aws.sql_runner.connection import save_to_keyring

        cluster_id = inputs.get("cluster_identifier", "").strip()
        username = inputs.get("master_username", "").strip()
        password = inputs.get("new_master_password", "").strip()
        host = inputs.get("host", "").strip()
        port_raw = inputs.get("port", "").strip()
        database = inputs.get("database", "").strip()
        if not (cluster_id and username and password):
            return
        engine = inputs.get("engine", "aurora-mysql").strip() or "aurora-mysql"
        conn_dict: dict[str, Any] = {
            "username": username,
            "password": password,
            "host": host or cluster_id,
            "dbClusterIdentifier": cluster_id,
            "engine": engine,
        }
        if port_raw:
            with contextlib.suppress(ValueError):
                conn_dict["port"] = int(port_raw)
        if database:
            conn_dict["dbname"] = database
        try:
            save_to_keyring(cluster_id, conn_dict)
            self.status_bar.set_status(f"Password updated and saved to keyring for {cluster_id}")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("keyring save failed for %s: %s", cluster_id, exc)
            self.status_bar.set_status("Password updated (keyring save failed)")

    def run(self) -> None:
        """Enter the Tkinter main event loop."""
        self.root.mainloop()


def create_main_window(
    context: AppContext,
    *,
    profiles: list[str] | None = None,
    regions: list[str] | None = None,
) -> MainWindow:
    """Factory that builds a MainWindow without entering mainloop."""
    return MainWindow(context, profiles=profiles, regions=regions)
