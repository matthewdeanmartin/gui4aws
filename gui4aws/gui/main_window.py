"""MainWindow: composes toolbar + sidebar + main panel + status bar."""

from __future__ import annotations

import dataclasses
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from typing import Any

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.gui.action_dialog import ActionDialog
from gui4aws.gui.main_panel import MainPanel
from gui4aws.gui.review_dialog import ReviewDecision, ReviewDialog, needs_review
from gui4aws.gui.sidebar import Sidebar, SidebarSelection
from gui4aws.gui.status_bar import StatusBar
from gui4aws.gui.toolbar import Toolbar
from gui4aws.models import ActionDefinition, RowAction
from gui4aws.moto_server import MotoServerManager

__all__ = ["MainWindow", "create_main_window"]

logger = logging.getLogger(__name__)


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
        self.root.geometry("1400x900")

        self.results_queue: queue.Queue[Any] = queue.Queue()
        self.moto_manager = MotoServerManager()
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
        )
        self.toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        self.sidebar = Sidebar(self.root, context.registry, on_select=self.on_sidebar_select)
        self.sidebar.grid(row=1, column=0, sticky="nsw")

        self.main_panel = MainPanel(self.root)
        self.main_panel.grid(row=1, column=1, sticky="nsew")

        self.status_bar = StatusBar(self.root, context)
        self.status_bar.grid(row=2, column=0, columnspan=2, sticky="ew")

        self.root.grid_columnconfigure(1, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        self.current_action: ActionDefinition | None = None
        self.current_inputs: dict[str, str] = {}
        self.root.after(50, self.poll_queue)

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
                "Start Moto first (toolbar button), then select Demo → Seed demo resources.",
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

    # ── Toolbar ───────────────────────────────────────────────────────────────

    def on_toolbar_changed(self) -> None:
        self.status_bar.refresh_context()

    # ── Sidebar navigation ────────────────────────────────────────────────────

    def on_sidebar_select(self, selection: SidebarSelection) -> None:
        """Clear the panel, wire row-action buttons, and run the list action."""
        try:
            service = self.context.registry.get(selection.service_id)
        except KeyError:
            return
        if selection.item_id is None:
            return
        nav = next((item for item in service.navigation_items if item.item_id == selection.item_id), None)
        if nav is None:
            return

        self.main_panel.clear_for_navigation()

        if nav.default_action_id is None:
            return

        try:
            action = service.action(nav.default_action_id)
        except KeyError:
            return

        if nav.row_actions:
            self.main_panel.set_row_actions(
                nav.row_actions,
                on_row_action=lambda ra, row: self._on_row_action(service.service_id, ra, row),
            )

        self.run_action(action, inputs={})

    def _on_row_action(self, service_id: str, row_action: RowAction, row: Any) -> None:
        """Open an ActionDialog pre-filled from the selected row."""
        try:
            service = self.context.registry.get(service_id)
            action = service.action(row_action.action_id)
        except KeyError:
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

    # ── ActionDialog ──────────────────────────────────────────────────────────

    def open_action_dialog(self, action: ActionDefinition, prefill: dict[str, str]) -> None:
        """Open (or raise) an ActionDialog for the given action."""
        dialog = ActionDialog(
            self.root,
            action,
            prefill=prefill,
            on_submit=self._dialog_submit,
        )
        self.active_dialog = dialog

    def _dialog_submit(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Called when the user clicks Run/Review in the ActionDialog."""
        cli = generate_cli_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        self.main_panel.show_scripts(cli, python)

        if not needs_review(action):
            self.run_action(action, inputs)
            return

        def on_resolved(decision: ReviewDecision) -> None:
            if decision.confirmed:
                self.run_action(action, inputs)

        dialog = ReviewDialog(self.root, action, cli, python, on_resolved=on_resolved)
        dialog.show_modal()

    # ── Action execution ──────────────────────────────────────────────────────

    def run_action(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        """Execute an action in a worker thread."""
        self.current_action = action
        self.current_inputs = dict(inputs)
        cli = generate_cli_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        self.main_panel.show_scripts(cli, python)
        self.status_bar.set_status("Loading")
        self.status_bar.set_last_action(action.action_id)
        threading.Thread(target=self._worker, args=(action, inputs), daemon=True).start()

    def _worker(self, action: ActionDefinition, inputs: dict[str, str]) -> None:
        try:
            result = self.context.execute(action, inputs)
        except Exception as exc:
            logger.exception("action %s failed", action.action_id)
            self.results_queue.put(("error", action, str(exc)))
            return
        self.results_queue.put(("ok", action, result))

    # ── Queue polling ─────────────────────────────────────────────────────────

    def poll_queue(self) -> None:
        while True:
            try:
                kind, action, payload = self.results_queue.get_nowait()
            except queue.Empty:
                break
            self.dispatch_result(kind, action, payload)
        self.root.after(50, self.poll_queue)

    def dispatch_result(self, kind: str, action: ActionDefinition | None, payload: Any) -> None:
        if kind == "moto_started":
            endpoint_url: str = payload
            self.context.set_endpoint(EndpointMode.MOTO, endpoint_url)
            self.toolbar.endpoint_mode_var.set(EndpointMode.MOTO.value)
            self.toolbar.endpoint_url_var.set(endpoint_url)
            self.status_bar.set_status(f"Moto running at {endpoint_url}")
            self.on_toolbar_changed()
            return
        if kind == "moto_error":
            self.status_bar.set_status("Moto start failed")
            messagebox.showerror("Moto server error", f"Could not start moto server:\n{payload}")
            self.toolbar.moto_running = False
            self.toolbar.moto_btn.configure(text="Start Moto")
            return
        if kind == "demo_ok":
            report: dict[str, list[str]] = payload
            lines = [
                f"{rtype}: {', '.join(ids) if ids else '(none)'}"
                for rtype, ids in report.items()
            ]
            self.status_bar.set_status("Demo resources seeded")
            messagebox.showinfo("Demo resources seeded", "\n".join(lines) or "Nothing was created.")
            return
        if kind == "demo_error":
            self.status_bar.set_status("Demo seed failed")
            messagebox.showerror("Demo seed error", f"Failed to seed demo resources:\n{payload}")
            return
        if action is None:
            return

        self.record_history(action, kind, payload)

        if kind == "error":
            self.status_bar.set_status("Error")
            self.main_panel.show_output(f"Error: {payload}", payload)
            if self.active_dialog and self.active_dialog.winfo_exists():
                self.active_dialog.set_status(f"Error: {payload}")
            return

        if hasattr(payload, "exception_class"):
            self.status_bar.set_status("Error")
            message = getattr(payload, "message", None) or getattr(payload, "reason", "failed")
            self.main_panel.show_output(f"{action.action_id} failed: {message}", payload)
            if self.active_dialog and self.active_dialog.winfo_exists():
                self.active_dialog.set_status(f"Failed: {message}")
            return

        self.status_bar.set_status("Ready")

        # Update dialog status if it's still open.
        if self.active_dialog and self.active_dialog.winfo_exists():
            self.active_dialog.set_status("Done.")

        view = action.view
        raw_response: Any = getattr(payload, "response", None) or getattr(payload, "parsed_json", None)
        if view is not None and raw_response is not None:
            try:
                rows = view(raw_response)
            except Exception as exc:
                logger.exception("view function failed for %s", action.action_id)
                self.main_panel.show_output(f"View failed: {exc}", raw_response)
                return
            columns = list(action.result_view.columns) or (list(vars(rows[0]).keys()) if rows else [])
            self.main_panel.show_table(rows, columns)
            self.main_panel.show_output(f"{len(rows)} item(s)", raw_response)
            return

        self.main_panel.show_output(f"{action.action_id} ok", raw_response)

    def record_history(self, action: ActionDefinition, kind: str, payload: Any) -> None:
        from datetime import datetime, timezone
        from gui4aws.execution.action_history import ActionHistoryEntry

        inputs = dict(self.current_inputs)
        cli = generate_cli_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        python = generate_python_script(
            action, inputs,
            profile_name=self.context.profile_name,
            region_name=self.context.region_name,
            endpoint_config=self.context.endpoint_config,
        )
        is_failure = kind == "error" or hasattr(payload, "exception_class")
        error_message: str | None = None
        duration = float(getattr(payload, "duration_seconds", 0.0) or 0.0)
        if is_failure:
            error_message = (
                getattr(payload, "message", None)
                or getattr(payload, "reason", None)
                or str(payload)
            )
        self.context.history.add(ActionHistoryEntry(
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
        ))

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
