"""ServerManagerMixin: moto/robotocore server management methods for MainWindow."""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any

from gui4aws.execution.endpoint_config import EndpointMode


class ServerManagerMixin:
    """Mixin providing moto and robotocore server management methods.

    Expects ``self`` to have the following attributes (supplied by MainWindow):
    ``moto_manager``, ``robotocore_manager``, ``toolbar``, ``status_bar``,
    ``robotocore_panel``, ``results_queue``, ``context``.
    """

    # These are declared as Any so type checkers don't complain about
    # attributes being undefined in the mixin; MainWindow provides them.
    moto_manager: Any
    robotocore_manager: Any
    toolbar: Any
    status_bar: Any
    robotocore_panel: Any
    results_queue: Any
    context: Any
    # Provided by MainWindow; redraws panels after a toolbar/context change.
    on_toolbar_changed: Callable[[], None]

    # ── Demo resource seeding ─────────────────────────────────────────────────

    def seed_demo_resources(self) -> None:
        """Seed Moto or Robotocore with dummy resources for demonstration."""
        from tkinter import messagebox

        from gui4aws.demo_resources import seed_demo_resources

        # Guard: refuse to seed on live AWS without an explicit double-confirmation.
        if self.context.endpoint_config.mode is EndpointMode.AWS:
            confirmed = messagebox.askyesno(
                "WARNING: Connected to live AWS",
                "You are NOT using a local emulator — this will create REAL billable "
                "resources in your live AWS account.\n\n"
                "Start Moto or Robotocore first, then seed demo resources.\n\n"
                "Proceed on live AWS anyway?",
                icon="warning",
            )
            if not confirmed:
                return

        endpoint_url = self.context.endpoint_config.resolved_url()
        is_robotocore = self.robotocore_manager.running
        backend = "robotocore" if is_robotocore else ("moto" if self.moto_manager.running else "aws")
        self.status_bar.set_status(f"Seeding demo resources via {backend}…")

        def worker() -> None:
            try:
                report = seed_demo_resources(
                    region_name=self.context.region_name,
                    endpoint_url=endpoint_url,
                    profile_name=self.context.profile_name,
                    is_robotocore=is_robotocore,
                )
                self.results_queue.put(("demo_ok", None, report))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("demo_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    # ── Moto ─────────────────────────────────────────────────────────────────

    def restart_moto(self) -> None:
        """Restart the Moto server in the background."""
        self.status_bar.set_status("Restarting moto server…")

        def restart_worker() -> None:
            try:
                self.moto_manager.restart(timeout=15.0)
                self.results_queue.put(("moto_started", None, self.moto_manager.endpoint_url))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("moto_error", None, str(exc)))

        threading.Thread(target=restart_worker, daemon=True).start()

    def reset_moto_state(self) -> None:
        """POST /moto-api/reset to wipe all moto state without restarting the server."""
        if not self.moto_manager.running:
            self.status_bar.set_status("Moto is not running")
            return
        self.status_bar.set_status("Resetting moto state…")

        def worker() -> None:
            try:
                self.moto_manager.reset_state()
                self.results_queue.put(("moto_state_reset", None, None))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("moto_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def open_moto_dashboard(self) -> None:
        """Open Moto's dashboard in the default browser."""
        if not self.moto_manager.running:
            self.status_bar.set_status("Moto is not running")
            return
        import webbrowser

        webbrowser.open(self.moto_manager.dashboard_url)
        self.status_bar.set_status("Opened Moto dashboard")

    def on_moto_toggle(self, start: bool) -> None:
        """Start or stop the Moto server based on the toolbar toggle state."""
        if start:
            self.status_bar.set_status("Starting moto server…")

            def start_worker() -> None:
                try:
                    self.moto_manager.start(timeout=15.0)
                    self.results_queue.put(("moto_started", None, self.moto_manager.endpoint_url))
                except Exception as exc:  # pylint: disable=broad-exception-caught
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
        """Toggle the Robotocore server state.

        Called by the toolbar button. ``currently_running`` is the manager
        state *before* the click, so we invert it to decide the action.
        """
        if currently_running:
            self.robotocore_stop()
        else:
            self.robotocore_start()

    def robotocore_start(self) -> None:
        """Start the Robotocore server in a background thread."""
        if self.robotocore_panel.use_moto:
            self.robotocore_start_moto_mode()
            return
        custom_url = self.toolbar.endpoint_url_var.get().strip() or None
        self.status_bar.set_status("Starting robotocore…")
        self.robotocore_panel.set_status("Starting…")

        def worker() -> None:
            try:
                self.robotocore_manager.start(endpoint_url=custom_url)
                self.results_queue.put(("robotocore_started", None, self.robotocore_manager.endpoint_url))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def robotocore_stop(self) -> None:
        """Stop the Robotocore server in a background thread."""
        self.status_bar.set_status("Stopping robotocore…")

        def worker() -> None:
            try:
                self.robotocore_manager.stop()
                self.results_queue.put(("robotocore_stopped", None, None))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def robotocore_restart(self) -> None:
        """Restart the Robotocore server in a background thread."""
        self.status_bar.set_status("Restarting robotocore…")
        self.robotocore_panel.set_status("Restarting…")

        def worker() -> None:
            try:
                self.robotocore_manager.restart()
                self.results_queue.put(("robotocore_started", None, self.robotocore_manager.endpoint_url))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def robotocore_pull(self) -> None:
        """Pull the latest Robotocore Docker image in a background thread."""
        self.status_bar.set_status("Pulling robotocore Docker image…")
        self.robotocore_panel.set_status("Pulling image…")

        def worker() -> None:
            try:
                self.robotocore_manager.pull()
                self.results_queue.put(("robotocore_pulled", None, None))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def robotocore_reset_state(self) -> None:
        """POST /_localstack/state/reset to wipe robotocore state without restarting."""
        if not self.robotocore_manager.running:
            self.status_bar.set_status("Robotocore is not running")
            return
        self.status_bar.set_status("Resetting robotocore state…")

        def worker() -> None:
            try:
                self.robotocore_manager.reset_state()
                self.results_queue.put(("robotocore_state_reset", None, None))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("robotocore_error", None, str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def robotocore_use_moto_changed(self, use_moto: bool) -> None:
        """Update endpoint mode when the 'Use Moto instead' checkbox flips.

        If robotocore is running, this switches between routing through
        LocalStack/Robotocore and routing through the Moto dev server.
        """
        if not self.robotocore_manager.running:
            return
        if use_moto:
            self.robotocore_start_moto_mode()
        else:
            url = self.robotocore_manager.endpoint_url
            self.context.set_endpoint(EndpointMode.ROBOTOCORE, url)
            self.toolbar.endpoint_mode_var.set(EndpointMode.ROBOTOCORE.value)
            self.toolbar.endpoint_url_var.set(url)
            self.on_toolbar_changed()

    def robotocore_start_moto_mode(self) -> None:
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
