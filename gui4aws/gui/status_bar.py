"""Bottom status bar."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from gui4aws.app import AppContext

__all__ = ["StatusBar"]


class StatusBar(ttk.Frame):
    """Shows status, last operation, duration, and current context."""

    def __init__(self, parent: tk.Misc, context: AppContext, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.context = context
        self.status_var = tk.StringVar(value="Ready")
        self.last_action_var = tk.StringVar(value="—")
        self.context_var = tk.StringVar(value=self.context_text())

        ttk.Label(self, textvariable=self.status_var, width=12).grid(row=0, column=0, padx=8, pady=2)
        ttk.Separator(self, orient="vertical").grid(row=0, column=1, sticky="ns", padx=4)
        ttk.Label(self, text="Last action:").grid(row=0, column=2)
        ttk.Label(self, textvariable=self.last_action_var).grid(row=0, column=3, padx=4)
        ttk.Separator(self, orient="vertical").grid(row=0, column=4, sticky="ns", padx=4)
        ttk.Label(self, textvariable=self.context_var).grid(row=0, column=5, padx=8)

    def set_status(self, status: str) -> None:
        """Update the leftmost status label."""
        self.status_var.set(status)

    def set_last_action(self, summary: str) -> None:
        """Update the last-action label."""
        self.last_action_var.set(summary)

    def refresh_context(self) -> None:
        """Refresh the right-hand context summary."""
        self.context_var.set(self.context_text())

    def context_text(self) -> str:
        """Generate a human-readable summary of the current application context."""
        ctx = self.context
        return (
            f"mode={ctx.mode}  profile={ctx.profile_name or '(env)'}  "
            f"region={ctx.region_name}  endpoint={ctx.endpoint_config.mode}"
        )
