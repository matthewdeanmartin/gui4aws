"""Output panel: shows a result summary plus a "view raw JSON" button."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

__all__ = ["OutputPanel"]


class OutputPanel(ttk.Frame):
    """Text view of the last action's result with a raw-JSON toggle."""

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.summary_var = tk.StringVar(value="(no action run yet)")
        ttk.Label(self, textvariable=self.summary_var, anchor="w").grid(row=0, column=0, sticky="ew", padx=8, pady=4)
        button_frame = ttk.Frame(self)
        button_frame.grid(row=0, column=1, sticky="e")
        ttk.Button(button_frame, text="View raw JSON", command=self.toggle_raw).grid(row=0, column=0, padx=4)

        self.text = tk.Text(self, height=12, wrap="word")
        self.text.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=8, pady=4)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.raw_visible = False
        self._raw_payload: Any = None
        self._summary_payload: str = ""

    def set_result(self, summary: str, raw_payload: Any) -> None:
        """Replace the displayed result."""
        self.summary_var.set(summary)
        self._summary_payload = summary
        self._raw_payload = raw_payload
        self.raw_visible = False
        self.render()

    def toggle_raw(self) -> None:
        """Switch between summary text and raw JSON."""
        self.raw_visible = not self.raw_visible
        self.render()

    def render(self) -> None:
        """Render the current text buffer."""
        self.text.delete("1.0", "end")
        if self.raw_visible and self._raw_payload is not None:
            try:
                self.text.insert("1.0", json.dumps(self._raw_payload, indent=2, default=str))
            except TypeError:
                self.text.insert("1.0", repr(self._raw_payload))
        else:
            self.text.insert("1.0", self._summary_payload)
