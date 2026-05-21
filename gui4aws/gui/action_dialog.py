"""ActionDialog: a Toplevel window containing a form, review, and execution result."""

from __future__ import annotations

import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from gui4aws.gui.action_form import ActionForm
from gui4aws.gui.review_dialog import needs_review, warning_banner
from gui4aws.models import ActionDefinition

__all__ = ["ActionDialog"]

logger = logging.getLogger(__name__)


class ActionDialog(tk.Toplevel):
    """Self-contained dialog for filling out, reviewing, and submitting an action.

    The caller supplies an ``on_submit`` callback that receives ``(action, inputs)`` — the
    dialog itself does not execute the action. The callback is responsible for running the
    action and may close the dialog or leave it open for feedback.

    Pre-fill values can be passed via ``prefill`` to seed specific fields from the currently
    selected row.
    """

    def __init__(
        self,
        parent: tk.Misc,
        action: ActionDefinition,
        *,
        prefill: dict[str, str] | None = None,
        on_submit: Callable[[ActionDefinition, dict[str, str]], None] | None = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.on_submit = on_submit
        self.title(action.display_name)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ── Risk banner ──────────────────────────────────────────────────────
        banner = warning_banner(action)
        if banner:
            ttk.Label(
                self,
                text=banner,
                foreground="#a04000",
                wraplength=560,
                justify="left",
            ).grid(row=0, column=0, sticky="ew", padx=12, pady=(8, 0))

        # ── Form ─────────────────────────────────────────────────────────────
        self.form = ActionForm(self, action, prefill=prefill)
        self.form.grid(row=1, column=0, sticky="nsew", padx=8, pady=4)

        # ── Description ──────────────────────────────────────────────────────
        if action.description:
            ttk.Label(self, text=action.description, wraplength=560, foreground="gray", justify="left").grid(
                row=2, column=0, sticky="ew", padx=12, pady=(0, 4)
            )

        # ── Buttons ──────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, sticky="e", padx=8, pady=8)

        verb = "Run" if not needs_review(action) else "Review & Run"
        ttk.Button(btn_frame, text=verb, command=self._on_submit).grid(row=0, column=1, padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).grid(row=0, column=0, padx=4)

        # ── Status label (updated by MainWindow after submit) ────────────────
        self.status_var = tk.StringVar(value="")
        ttk.Label(self, textvariable=self.status_var, foreground="gray").grid(
            row=4, column=0, sticky="w", padx=12, pady=(0, 4)
        )

        self.update_idletasks()
        self.geometry("")  # let tk size to content

    def _on_submit(self) -> None:
        errors = self.form.validate()
        if errors:
            self.status_var.set("Required: " + "; ".join(errors))
            return
        self.status_var.set("Running…")
        if self.on_submit is not None:
            self.on_submit(self.action, self.form.values())

    def set_status(self, text: str) -> None:
        """Update the in-dialog status label (called by MainWindow on completion)."""
        self.status_var.set(text)
