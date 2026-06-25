"""Global toolbar: mode / profile / region / endpoint selectors + moto/robotocore toggles."""

# pylint: disable=too-many-ancestors

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk
from typing import Any

from gui4aws.app import AWS_PARTITIONS, AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.execution.execution_mode import ExecutionMode

__all__ = ["Toolbar"]


class Toolbar(ttk.Frame):
    """Always-visible bar with mode, profile, region, partition, endpoint pickers and moto/robotocore toggles."""

    def __init__(
        self,
        parent: tk.Misc,
        context: AppContext,
        *,
        profiles: Sequence[str] = (),
        regions: Sequence[str] = (),
        on_change: Callable[[], None] | None = None,
        on_moto_toggle: Callable[[bool], None] | None = None,
        on_robotocore_toggle: Callable[[bool], None] | None = None,
        on_clear_cache: Callable[[], None] | None = None,
        on_partition_changed: Callable[[str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.context = context
        self.on_change = on_change or (lambda: None)
        self.on_moto_toggle = on_moto_toggle or (lambda running: None)
        self.on_robotocore_toggle = on_robotocore_toggle or (lambda running: None)
        self.on_clear_cache = on_clear_cache or (lambda: None)
        self.on_partition_changed_cb = on_partition_changed or (lambda partition: None)
        self.moto_running = False
        self.robotocore_running = False

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

        self.endpoint_mode_var = tk.StringVar(value=str(context.endpoint_config.mode))
        ttk.Label(self, text="Endpoint:").grid(row=0, column=col, padx=(16, 4))
        col += 1
        endpoint_combo = ttk.Combobox(
            self,
            textvariable=self.endpoint_mode_var,
            values=[m.value for m in EndpointMode],
            state="readonly",
            width=10,
        )
        endpoint_combo.grid(row=0, column=col, padx=4)
        endpoint_combo.bind("<<ComboboxSelected>>", self.on_endpoint_mode_changed)
        col += 1

        self.endpoint_url_var = tk.StringVar(value=context.endpoint_config.endpoint_url or "")
        url_entry = ttk.Entry(self, textvariable=self.endpoint_url_var, width=26)
        url_entry.grid(row=0, column=col, padx=4)
        url_entry.bind("<FocusOut>", self.on_endpoint_url_changed)
        col += 1

        self.moto_btn = ttk.Button(self, text="Start Moto", command=self.toggle_moto, width=12)
        self.moto_btn.grid(row=0, column=col, padx=(16, 4), pady=4)
        col += 1

        self.robotocore_btn = ttk.Button(self, text="Start Robotocore", command=self.toggle_robotocore, width=17)
        self.robotocore_btn.grid(row=0, column=col, padx=(4, 4), pady=4)
        col += 1

        clear_cache_btn = ttk.Button(self, text="Clear Cache", command=self.on_clear_cache, width=11)
        clear_cache_btn.grid(row=0, column=col, padx=(4, 8), pady=4)

    def on_mode_changed(self, event: object = None) -> None:
        """Push the mode selector value into AppContext."""
        del event
        self.context.set_mode(ExecutionMode(self.mode_var.get()))
        self.on_change()

    def on_profile_changed(self, event: object = None) -> None:
        """Push the profile selector value into AppContext."""
        del event
        value = self.profile_var.get().strip()
        if value in ("(none)", ""):
            self.context.set_profile(None)
            self.profile_var.set("(none)")
        else:
            self.context.set_profile(value)
        self.on_change()

    def set_profile(self, profile_name: str | None) -> None:
        """Update the profile selector from external code (e.g. when moto starts)."""
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

    def on_endpoint_mode_changed(self, event: object = None) -> None:
        """Push the endpoint mode selector value into AppContext."""
        del event
        mode = EndpointMode(self.endpoint_mode_var.get())
        url = self.endpoint_url_var.get().strip() or None
        self.context.set_endpoint(mode, url)
        self.on_change()

    def on_endpoint_url_changed(self, event: object = None) -> None:
        """Push the endpoint URL value into AppContext."""
        del event
        mode = EndpointMode(self.endpoint_mode_var.get())
        url = self.endpoint_url_var.get().strip() or None
        if mode is EndpointMode.CUSTOM and url is None:
            return
        self.context.set_endpoint(mode, url)
        self.on_change()

    def toggle_moto(self) -> None:
        """Start or stop the moto server and update the button label."""
        self.moto_running = not self.moto_running
        if self.moto_running:
            self.moto_btn.configure(text="Stop Moto")
        else:
            self.moto_btn.configure(text="Start Moto")
        self.on_moto_toggle(self.moto_running)

    def toggle_robotocore(self) -> None:
        """Start or stop robotocore.

        The button label is NOT flipped here — it is updated only when the
        result arrives via dispatch_result, so a failed or slow start cannot
        leave the button in the wrong state.
        """
        self.on_robotocore_toggle(self.robotocore_running)
