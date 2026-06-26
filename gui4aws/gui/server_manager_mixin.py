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

    def demo_seeding_allowed(self) -> bool:
        """True only when the active endpoint is a manager-owned Moto/Robotocore.

        This is the UI-level gate: the Demo menu item is enabled only when this
        returns True. Custom endpoints (even a moto the user started themselves)
        are intentionally excluded — demo seeding is never offered on anything we
        did not start, and never on real AWS.
        """
        mode = self.context.endpoint_config.mode
        resolved = self.context.endpoint_config.resolved_url()
        if mode is EndpointMode.MOTO and self.moto_manager.running:
            return bool(resolved == self.moto_manager.endpoint_url)
        if mode is EndpointMode.ROBOTOCORE and self.robotocore_manager.running:
            return bool(resolved == self.robotocore_manager.endpoint_url)
        return False

    def seed_demo_resources(self) -> None:
        """Seed our running Moto or Robotocore with demonstration resources.

        Two independent guards keep demo data off real AWS:

        1. ``demo_seeding_allowed`` — the endpoint must match a manager we
           started (also enforced by hiding the menu item otherwise).
        2. ``verify_emulator`` (inside the worker) — the endpoint is *probed*
           for a Moto/Robotocore signature before anything is written.
        """
        from gui4aws.demo_resources import seed_demo_resources, verify_emulator

        if not self.demo_seeding_allowed():
            self.status_bar.set_status("Start Moto or Robotocore first to seed demo resources")
            return

        endpoint_url = self.context.endpoint_config.resolved_url()
        self.status_bar.set_status("Verifying emulator before seeding…")

        def worker() -> None:
            try:
                # Positive confirmation that we are talking to a local emulator.
                emulator = verify_emulator(endpoint_url)
                report = seed_demo_resources(
                    emulator,
                    region_name=self.context.region_name,
                    profile_name=self.context.profile_name,
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
        """Start the Moto server (async).

        Invoked by the Target selector when the user picks Moto. Stopping is
        handled by ``MainWindow`` when switching away from the Moto target, so
        this only needs to cover the start path; ``start=False`` is a no-op kept
        for back-compatibility.
        """
        if not start:
            return
        self.status_bar.set_status("Starting moto server…")

        def start_worker() -> None:
            try:
                self.moto_manager.start(timeout=15.0)
                self.results_queue.put(("moto_started", None, self.moto_manager.endpoint_url))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                self.results_queue.put(("moto_error", None, str(exc)))

        threading.Thread(target=start_worker, daemon=True).start()

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
