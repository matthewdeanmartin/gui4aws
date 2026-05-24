"""Panels for runtime diagnostics."""

from __future__ import annotations

import json
import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk
from typing import Any

__all__ = ["CacheDiagnosticsPanel", "DiagnosticPanel", "QueueDiagnosticsPanel", "RobotocorePanel"]


class DiagnosticPanel(ttk.Frame):
    """Read-only text area with copy support."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        actions: tuple[tuple[str, Any], ...] = (),
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.last_text = ""

        button_bar = ttk.Frame(self)
        button_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ttk.Button(button_bar, text="Copy", command=self.copy).pack(side="left", padx=2)
        for label, callback in actions:
            ttk.Button(button_bar, text=label, command=callback).pack(side="left", padx=2)

        self.text = tk.Text(self, wrap="none", font=("Courier", 9))
        self.text.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)

        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scroll_y.grid(row=1, column=1, sticky="ns", pady=4)
        self.text.configure(yscrollcommand=scroll_y.set)
        self.text.configure(state="disabled")

    def set_text(self, text: str) -> None:
        """Replace the panel contents, preserving scroll position when possible."""
        if text == self.last_text:
            return
        yview = self.text.yview()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")
        if self.last_text and yview[1] < 1.0:
            self.text.yview_moveto(yview[0])
        elif text:
            self.text.yview_moveto(1.0)
        self.last_text = text

    def copy(self) -> None:
        """Copy the visible text content of the diagnostic panel to the system clipboard.

        Strips leading and trailing whitespace to ensure a clean copy.
        """
        content = self.text.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)


class QueueDiagnosticsPanel(ttk.Frame):
    """Widget-based queue diagnostics."""

    STAT_FIELDS = (
        ("pending_jobs", "Pending jobs"),
        ("current_job", "Current job"),
        ("submitted_jobs", "Submitted"),
        ("started_jobs", "Started"),
        ("completed_jobs", "Completed"),
        ("dropped_jobs", "Dropped"),
        ("failed_jobs", "Failed"),
        ("result_queue_depth", "Result queue depth"),
        ("current_nav_generation", "Nav generation"),
        ("current_service", "Current service"),
        ("current_nav", "Current nav"),
    )

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_clear: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.last_snapshot: dict[str, Any] | None = None

        stats_frame = ttk.LabelFrame(self, text="Queue State")
        stats_frame.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        stats_frame.grid_columnconfigure(1, weight=1)
        if on_clear is not None:
            ttk.Button(stats_frame, text="Clear Queue", command=on_clear).grid(
                row=0, column=2, rowspan=2, sticky="e", padx=4, pady=4
            )
        self.vars: dict[str, tk.StringVar] = {}
        for row, (key, label) in enumerate(self.STAT_FIELDS):
            ttk.Label(stats_frame, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=4, pady=2)
            var = tk.StringVar(value="")
            self.vars[key] = var
            ttk.Label(stats_frame, textvariable=var).grid(row=row, column=1, sticky="w", padx=4, pady=2)

        events_frame = ttk.LabelFrame(self, text="Recent Events")
        events_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        events_frame.grid_columnconfigure(0, weight=1)
        events_frame.grid_rowconfigure(0, weight=1)
        self.events = tk.Listbox(events_frame)
        self.events.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        events_scroll = ttk.Scrollbar(events_frame, orient="vertical", command=self.events.yview)
        events_scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.events.configure(yscrollcommand=events_scroll.set)

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Refresh the queue panel if the data changed."""
        if snapshot == self.last_snapshot:
            return
        for key, _ in self.STAT_FIELDS:
            value = snapshot.get(key)
            if key == "current_job":
                display = "(idle)" if not value else str(value)
            elif value is None or value == "":
                display = "(none)"
            else:
                display = str(value)
            self.vars[key].set(display)
        replace_listbox(self.events, snapshot.get("recent_events", ()))
        self.last_snapshot = dict(snapshot)


class CacheDiagnosticsPanel(ttk.Frame):
    """Widget-based cache diagnostics."""

    SUMMARY_FIELDS = (
        ("mode", "Mode"),
        ("profile", "Profile"),
        ("region", "Region"),
        ("endpoint", "Endpoint"),
        ("ttl_seconds", "TTL seconds"),
        ("size", "Entries"),
    )

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_clear_selected: Any | None = None,
        on_clear_all: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.grid_rowconfigure(2, weight=2)
        self.grid_rowconfigure(3, weight=1)
        self.last_snapshot: dict[str, Any] | None = None
        self.entry_lookup: dict[str, dict[str, Any]] = {}

        summary = ttk.LabelFrame(self, text="Context")
        summary.grid(row=0, column=0, sticky="ew", padx=4, pady=4)
        summary.grid_columnconfigure(1, weight=1)
        self.summary_vars: dict[str, tk.StringVar] = {}
        for row, (key, label) in enumerate(self.SUMMARY_FIELDS):
            ttk.Label(summary, text=f"{label}:").grid(row=row, column=0, sticky="w", padx=4, pady=2)
            var = tk.StringVar(value="")
            self.summary_vars[key] = var
            ttk.Label(summary, textvariable=var).grid(row=row, column=1, sticky="w", padx=4, pady=2)

        stats_frame = ttk.LabelFrame(self, text="Stats")
        stats_frame.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        stats_frame.grid_columnconfigure(0, weight=1)
        stats_frame.grid_rowconfigure(0, weight=1)
        self.stats_tree = ttk.Treeview(stats_frame, columns=("metric", "value"), show="headings", height=6)
        self.stats_tree.heading("metric", text="Metric")
        self.stats_tree.heading("value", text="Value")
        self.stats_tree.column("metric", anchor="w", width=180, stretch=True)
        self.stats_tree.column("value", anchor="w", width=120, stretch=True)
        self.stats_tree.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        stats_scroll = ttk.Scrollbar(stats_frame, orient="vertical", command=self.stats_tree.yview)
        stats_scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.stats_tree.configure(yscrollcommand=stats_scroll.set)

        entries_frame = ttk.LabelFrame(self, text="Entries")
        entries_frame.grid(row=2, column=0, sticky="nsew", padx=4, pady=(0, 4))
        entries_frame.grid_columnconfigure(0, weight=1)
        entries_frame.grid_rowconfigure(0, weight=1)
        button_bar = ttk.Frame(entries_frame)
        button_bar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        if on_clear_selected is not None:
            ttk.Button(button_bar, text="Clear Selected", command=on_clear_selected).pack(side="left", padx=2)
        if on_clear_all is not None:
            ttk.Button(button_bar, text="Clear All", command=on_clear_all).pack(side="left", padx=2)
        self.entries_tree = ttk.Treeview(
            entries_frame,
            columns=("service", "action", "mode", "inputs"),
            show="headings",
            height=8,
        )
        for key, label, width in (
            ("service", "Service", 120),
            ("action", "Action", 240),
            ("mode", "Mode", 90),
            ("inputs", "Inputs", 420),
        ):
            self.entries_tree.heading(key, text=label)
            self.entries_tree.column(key, anchor="w", width=width, stretch=True)
        self.entries_tree.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        entries_scroll = ttk.Scrollbar(entries_frame, orient="vertical", command=self.entries_tree.yview)
        entries_scroll.grid(row=1, column=1, sticky="ns", pady=4)
        self.entries_tree.configure(yscrollcommand=entries_scroll.set)

        events_frame = ttk.LabelFrame(self, text="Recent Events")
        events_frame.grid(row=3, column=0, sticky="nsew", padx=4, pady=(0, 4))
        events_frame.grid_columnconfigure(0, weight=1)
        events_frame.grid_rowconfigure(0, weight=1)
        self.events = tk.Listbox(events_frame)
        self.events.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        events_scroll = ttk.Scrollbar(events_frame, orient="vertical", command=self.events.yview)
        events_scroll.grid(row=0, column=1, sticky="ns", pady=4)
        self.events.configure(yscrollcommand=events_scroll.set)

    def set_snapshot(self, snapshot: dict[str, Any]) -> None:
        """Refresh the cache panel if the data changed."""
        if snapshot == self.last_snapshot:
            return
        for key, _ in self.SUMMARY_FIELDS:
            self.summary_vars[key].set(str(snapshot.get(key, "")))
        stats_rows = [(name, str(value)) for name, value in snapshot.get("stats", {}).items()]
        replace_tree(self.stats_tree, stats_rows)
        entry_rows = [
            (
                entry["service_id"],
                entry["action_id"],
                entry["mode"],
                json.dumps(entry["inputs"], sort_keys=True),
            )
            for entry in snapshot.get("entries", ())
        ]
        replace_tree(self.entries_tree, entry_rows)
        self.entry_lookup = {str(index): entry for index, entry in enumerate(snapshot.get("entries", ()))}
        replace_listbox(self.events, snapshot.get("recent_events", ()))
        self.last_snapshot = dict(snapshot)

    def selected_entry(self) -> dict[str, Any] | None:
        """Return the currently selected cache entry, if any."""
        selected = self.entries_tree.selection()
        if not selected:
            return None
        return self.entry_lookup.get(selected[0])


class RobotocorePanel(ttk.Frame):
    """Dedicated panel for robotocore: controls, "use moto" toggle, and live log."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_start: Any | None = None,
        on_stop: Any | None = None,
        on_restart: Any | None = None,
        on_reset: Any | None = None,
        on_pull: Any | None = None,
        on_use_moto_changed: Any | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        self.last_text = ""

        # ── Button bar ────────────────────────────────────────────────────────
        controls = ttk.Frame(self)
        controls.grid(row=0, column=0, sticky="ew", padx=4, pady=4)

        self.start_btn = ttk.Button(controls, text="Start Robotocore", width=18, command=on_start or (lambda: None))
        self.start_btn.pack(side="left", padx=2)

        self.stop_btn = ttk.Button(controls, text="Stop", width=8, command=on_stop or (lambda: None))
        self.stop_btn.pack(side="left", padx=2)

        self.restart_btn = ttk.Button(controls, text="Restart", width=10, command=on_restart or (lambda: None))
        self.restart_btn.pack(side="left", padx=2)

        self.reset_btn = ttk.Button(controls, text="Reset State", width=12, command=on_reset or (lambda: None))
        self.reset_btn.pack(side="left", padx=2)

        self.pull_btn = ttk.Button(controls, text="Pull Docker Image", width=16, command=on_pull or (lambda: None))
        self.pull_btn.pack(side="left", padx=(16, 2))

        ttk.Button(controls, text="Copy Log", width=10, command=self.copy).pack(side="left", padx=(16, 2))

        # ── "Use Moto instead" checkbox ───────────────────────────────────────
        self.use_moto_var = tk.BooleanVar(value=False)
        cb = ttk.Checkbutton(
            controls,
            text="Use Moto instead",
            variable=self.use_moto_var,
            command=self.on_use_moto_changed,
        )
        cb.pack(side="right", padx=(16, 4))
        self.on_use_moto_changed_cb = on_use_moto_changed

        # ── Status label ──────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Not running")
        ttk.Label(controls, textvariable=self.status_var, foreground="gray").pack(side="right", padx=(4, 16))

        # ── Log text area ─────────────────────────────────────────────────────
        self.text = tk.Text(self, wrap="none", font=("Courier", 9))
        self.text.grid(row=1, column=0, sticky="nsew", padx=4, pady=(0, 4))
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scroll_y.grid(row=1, column=1, sticky="ns", pady=(0, 4))
        self.text.configure(yscrollcommand=scroll_y.set, state="disabled")

    def set_text(self, text: str) -> None:
        """Replace log panel contents."""
        if text == self.last_text:
            return
        yview = self.text.yview()
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", text)
        self.text.configure(state="disabled")
        if self.last_text and yview[1] < 1.0:
            self.text.yview_moveto(yview[0])
        elif text:
            self.text.yview_moveto(1.0)
        self.last_text = text

    def set_status(self, text: str) -> None:
        """Update the human-readable status message for the robotocore container."""
        self.status_var.set(text)

    def set_running(self, running: bool) -> None:
        """Update button states and status label to reflect the container's running state."""
        if running:
            self.start_btn.configure(state="disabled")
            self.stop_btn.configure(state="normal")
            self.restart_btn.configure(state="normal")
            self.reset_btn.configure(state="normal")
            self.status_var.set("Running")
        else:
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.restart_btn.configure(state="disabled")
            self.reset_btn.configure(state="disabled")
            self.status_var.set("Not running")

    @property
    def use_moto(self) -> bool:
        """Return True if the 'Use Moto instead' checkbox is currently checked."""
        return self.use_moto_var.get()

    def on_use_moto_changed(self) -> None:
        """Handle toggle events for the 'Use Moto instead' checkbox."""
        if self.on_use_moto_changed_cb:
            self.on_use_moto_changed_cb(self.use_moto_var.get())

    def copy(self) -> None:
        """Copy the robotocore log content to the system clipboard."""
        content = self.text.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)


def replace_listbox(widget: tk.Listbox, items: Any) -> None:
    """Update a Listbox with new items while minimizing flicker and preserving scroll position.

    Only performs the update if the content has actually changed.
    """
    new_items = [str(item) for item in items] or ["(none)"]
    current = list(widget.get(0, "end"))
    if current == new_items:
        return
    yview = widget.yview()
    widget.delete(0, "end")
    for item in new_items:
        widget.insert("end", item)
    if current and yview[1] < 1.0:
        widget.yview_moveto(yview[0])


def replace_tree(widget: ttk.Treeview, rows: Sequence[tuple[Any, ...]]) -> None:
    """Update a Treeview with new rows while minimizing flicker and preserving scroll position.

    Only performs the update if the content has actually changed.
    """
    current = [tuple(widget.item(item, "values")) for item in widget.get_children("")]
    new_rows: Sequence[tuple[Any, ...]]
    if rows:
        new_rows = rows
    elif len(widget["columns"]) == 2:
        new_rows = [("(none)", "")]
    else:
        new_rows = [("(none)", "", "", "")]
    if current == list(new_rows):
        return
    yview = widget.yview()
    for item in widget.get_children(""):
        widget.delete(item)
    for index, row in enumerate(new_rows):
        widget.insert("", "end", iid=str(index), values=row)
    if current and yview[1] < 1.0:
        widget.yview_moveto(yview[0])
