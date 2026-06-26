"""Global toolbar: mode / profile / region / **target** selectors.

The **Target** selector (AWS / Moto / Robotocore / Custom) is the single source
of truth for where AWS calls go. Selecting a target is also the start/stop
gesture for the emulators — there are no separate Start/Stop buttons, so Moto and
Robotocore can never both be active at once. See ``spec/mutually_exclusive.md``.
"""

# pylint: disable=too-many-ancestors

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from typing import Any

from gui4aws.app import AWS_PARTITIONS, AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode

__all__ = ["Toolbar"]

# Value shown in the (disabled) Profile box when a target makes credentials moot.
_PROFILE_NA = "(emulator — n/a)"


class Toolbar(ttk.Frame):
    """Always-visible bar with mode, profile, region, partition, and Target pickers."""

    def __init__(
        self,
        parent: tk.Misc,
        context: AppContext,
        *,
        profiles: Sequence[str] = (),
        regions: Sequence[str] = (),
        on_change: Callable[[], None] | None = None,
        on_target_changed: Callable[[EndpointMode], None] | None = None,
        on_clear_cache: Callable[[], None] | None = None,
        on_partition_changed: Callable[[str], None] | None = None,
        on_network_settings: Callable[[], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.context = context
        self.on_change = on_change or (lambda: None)
        self.on_target_changed_cb = on_target_changed or (lambda mode: None)
        self.on_clear_cache = on_clear_cache or (lambda: None)
        self.on_partition_changed_cb = on_partition_changed or (lambda partition: None)
        self.on_network_settings = on_network_settings or (lambda: None)
        # Running flags, mirrored from the managers so apply_target_state() can
        # decide whether the URL box should display a live emulator URL.
        self.moto_running = False
        self.robotocore_running = False
        # Remembers the last real profile so it can be restored when returning to AWS.
        self._saved_profile = context.profile_name or "(none)"

        col = 0

        self.mode_var = tk.StringVar(value=str(context.mode))
        ttk.Label(self, text="Mode:").grid(row=0, column=col, padx=(8, 4), pady=4)
        col += 1
        mode_combo = ttk.Combobox(
            self,
            textvariable=self.mode_var,
            values=[ExecutionMode.AWS_CLI.value, ExecutionMode.BOTO3.value],
            state="readonly",
            width=10,
        )
        mode_combo.grid(row=0, column=col, padx=4, pady=4)
        mode_combo.bind("<<ComboboxSelected>>", self.on_mode_changed)
        col += 1

        # ── Target selector — the single source of truth for the endpoint ─────
        self.target_var = tk.StringVar()
        ttk.Label(self, text="Target:").grid(row=0, column=col, padx=(16, 4))
        col += 1
        self._target_modes = [EndpointMode.AWS, EndpointMode.MOTO, EndpointMode.ROBOTOCORE, EndpointMode.CUSTOM]
        self.target_combo = ttk.Combobox(
            self,
            textvariable=self.target_var,
            values=[m.display_label for m in self._target_modes],
            state="readonly",
            width=11,
        )
        self.target_combo.current(self._target_index(context.endpoint_config.mode))
        self.target_combo.grid(row=0, column=col, padx=4)
        self.target_combo.bind("<<ComboboxSelected>>", self.on_target_selected)
        col += 1

        self.profile_var = tk.StringVar(value=context.profile_name or "(none)")
        ttk.Label(self, text="Profile:").grid(row=0, column=col, padx=(16, 4))
        col += 1
        profile_values = ["(none)", *list(profiles)]
        self.profile_combo = ttk.Combobox(self, textvariable=self.profile_var, values=profile_values, width=18)
        self.profile_combo.grid(row=0, column=col, padx=4)
        self.profile_combo.bind("<<ComboboxSelected>>", self.on_profile_changed)
        self.profile_combo.bind("<FocusOut>", self.on_profile_changed)
        col += 1

        # ── Partition / Region compound group ────────────────────────────────
        pr_frame = ttk.Frame(self)
        pr_frame.grid(row=0, column=col, padx=(16, 4), pady=4)
        col += 1

        self.partition_var = tk.StringVar(value=context.partition)
        partition_labels = [f"{pid} ({info[1]})" for pid, info in AWS_PARTITIONS.items()]
        self.partition_ids = list(AWS_PARTITIONS.keys())
        partition_combo = ttk.Combobox(
            pr_frame,
            textvariable=self.partition_var,
            values=partition_labels,
            state="readonly",
            width=16,
        )
        idx = self.partition_ids.index(context.partition) if context.partition in self.partition_ids else 0
        partition_combo.current(idx)
        partition_combo.grid(row=0, column=0, padx=(0, 2))
        partition_combo.bind("<<ComboboxSelected>>", self.on_partition_changed)
        self.partition_combo = partition_combo

        ttk.Label(pr_frame, text="/").grid(row=0, column=1, padx=2)

        self.region_var = tk.StringVar(value=context.region_name)
        self.region_combo = ttk.Combobox(pr_frame, textvariable=self.region_var, values=list(regions), width=16)
        self.region_combo.grid(row=0, column=2, padx=(2, 0))
        self.region_combo.bind("<<ComboboxSelected>>", self.on_region_changed)
        self.region_combo.bind("<FocusOut>", self.on_region_changed)

        # Endpoint URL — editable only for Custom; read-only display otherwise.
        ttk.Label(self, text="URL:").grid(row=0, column=col, padx=(16, 4))
        col += 1
        self.endpoint_url_var = tk.StringVar(value=context.endpoint_config.endpoint_url or "")
        self.url_entry = ttk.Entry(self, textvariable=self.endpoint_url_var, width=26)
        self.url_entry.grid(row=0, column=col, padx=4)
        self.url_entry.bind("<FocusOut>", self.on_endpoint_url_changed)
        self.url_entry.bind("<Return>", self.on_endpoint_url_changed)
        col += 1

        clear_cache_btn = ttk.Button(self, text="Clear Cache", command=self.on_clear_cache, width=11)
        clear_cache_btn.grid(row=0, column=col, padx=(16, 4), pady=4)
        col += 1

        # Proxy / TLS settings — for users behind a corporate proxy or a
        # TLS-inspecting firewall whose cert must be trusted.
        self.network_btn = ttk.Button(self, text="🌐 Network…", command=self.on_network_settings, width=12)
        self.network_btn.grid(row=0, column=col, padx=(4, 8), pady=4)

        # ``endpoint_mode_var`` mirrors the resolved endpoint mode for the rest
        # of the app (dispatch_result, diagnostics) which reads/writes it.
        self.endpoint_mode_var = tk.StringVar(value=context.endpoint_config.mode.value)

        self._refresh_network_button()
        self.apply_target_state()

    # ── Target selector ───────────────────────────────────────────────────────

    def _target_index(self, mode: EndpointMode) -> int:
        return self._target_modes.index(mode) if mode in self._target_modes else 0

    def selected_target(self) -> EndpointMode:
        """Return the EndpointMode currently chosen in the Target combobox."""
        idx = self.target_combo.current()
        if 0 <= idx < len(self._target_modes):
            return self._target_modes[idx]
        return EndpointMode.AWS

    def on_target_selected(self, event: object = None) -> None:
        """Hand a Target change to MainWindow, which orchestrates start/stop."""
        del event
        self.on_target_changed_cb(self.selected_target())

    def set_target(self, mode: EndpointMode) -> None:
        """Set the Target combobox + mirror var without firing the change callback."""
        self.target_combo.current(self._target_index(mode))
        self.endpoint_mode_var.set(mode.value)
        self.apply_target_state()

    def set_transition_busy(self, busy: bool) -> None:
        """Disable the Target selector while an emulator start/stop is in flight."""
        with contextlib.suppress(tk.TclError):
            self.target_combo.configure(state="disabled" if busy else "readonly")

    def apply_target_state(self) -> None:
        """Enable/disable Profile + URL widgets to match the active target.

        This is the heart of the mutual-exclusion UX: the Profile field only
        matters on live AWS, and the URL field is only editable for Custom.
        """
        mode = self.context.endpoint_config.mode
        # ── Profile: enabled only on AWS ──────────────────────────────────────
        if mode is EndpointMode.AWS:
            self.profile_combo.configure(state="normal")
            if self.profile_var.get() == _PROFILE_NA:
                self.profile_var.set(self._saved_profile)
        else:
            if self.profile_var.get() != _PROFILE_NA:
                self._saved_profile = self.profile_var.get()
            self.profile_var.set(_PROFILE_NA)
            self.profile_combo.configure(state="disabled")

        # ── URL: editable only for Custom; read-only display for emulators ────
        if mode is EndpointMode.CUSTOM:
            self.url_entry.configure(state="normal")
        else:
            # Show the live emulator URL (if running) read-only; blank for AWS.
            running = (mode is EndpointMode.MOTO and self.moto_running) or (
                mode is EndpointMode.ROBOTOCORE and self.robotocore_running
            )
            if not running and mode is EndpointMode.AWS:
                self.endpoint_url_var.set("")
            self.url_entry.configure(state="readonly")

    def on_mode_changed(self, event: object = None) -> None:
        """Push the mode selector value into AppContext."""
        del event
        self.context.set_mode(ExecutionMode(self.mode_var.get()))
        self.on_change()

    def on_profile_changed(self, event: object = None) -> None:
        """Push the profile selector value into AppContext (ignored unless AWS)."""
        del event
        if self.context.endpoint_config.mode is not EndpointMode.AWS:
            return
        value = self.profile_var.get().strip()
        if value in ("(none)", "", _PROFILE_NA):
            self.context.set_profile(None)
            self.profile_var.set("(none)")
        else:
            self.context.set_profile(value)
        self._saved_profile = self.profile_var.get()
        self.on_change()

    def set_profile(self, profile_name: str | None) -> None:
        """Update the profile selector from external code (e.g. when moto starts)."""
        self._saved_profile = profile_name or "(none)"
        if self.context.endpoint_config.mode is EndpointMode.AWS:
            self.profile_var.set(profile_name or "(none)")
        self.context.set_profile(profile_name)

    def on_region_changed(self, event: object = None) -> None:
        """Push the region selector value into AppContext."""
        del event
        value = self.region_var.get().strip()
        if value:
            self.context.set_region(value)
            self.on_change()

    def on_partition_changed(self, event: object = None) -> None:
        """Push the partition selector value into AppContext and refresh the region list."""
        del event
        current_idx = self.partition_combo.current()
        if current_idx < 0 or current_idx >= len(self.partition_ids):
            return
        partition = self.partition_ids[current_idx]
        self.context.set_partition(partition)
        self.on_partition_changed_cb(partition)
        self.on_change()

    def update_regions(self, regions: list[str]) -> None:
        """Replace the region combobox choices (called after partition change)."""
        self.region_combo.configure(values=regions)
        if regions and self.region_var.get() not in regions:
            self.region_var.set(regions[0])
            self.context.set_region(regions[0])

    def on_endpoint_url_changed(self, event: object = None) -> None:
        """Push a Custom endpoint URL value into AppContext."""
        del event
        if self.selected_target() is not EndpointMode.CUSTOM:
            return
        url = self.endpoint_url_var.get().strip() or None
        if url is None:
            return
        self.context.set_endpoint(EndpointMode.CUSTOM, url)
        self.endpoint_mode_var.set(EndpointMode.CUSTOM.value)
        self.on_change()

    def _refresh_network_button(self) -> None:
        """Bold the Network button when non-default proxy/TLS settings are active."""
        active = not self.context.network_config.is_default()
        with contextlib.suppress(tk.TclError):
            self.network_btn.configure(text="🌐 Network *" if active else "🌐 Network…")
