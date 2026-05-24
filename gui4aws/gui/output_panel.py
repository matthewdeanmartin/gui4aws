"""Output panel: copyable text area showing the last action result or error."""

from __future__ import annotations

import json
import tkinter as tk
from tkinter import ttk
from typing import Any

__all__ = ["OutputPanel"]


class OutputPanel(ttk.LabelFrame):
    """Copyable text view of the last action's result with a raw-JSON toggle."""

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, text="Output", **kwargs)

        btn_bar = ttk.Frame(self)
        btn_bar.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 0))
        ttk.Button(btn_bar, text="Copy", command=self.copy_text).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="View raw JSON", command=self.toggle_raw).pack(side="left", padx=2)

        self.text = tk.Text(self, height=8, wrap="word", font=("Courier", 9))
        self.text.grid(row=1, column=0, sticky="nsew", padx=4, pady=4)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scroll.grid(row=1, column=1, sticky="ns", pady=4)
        self.text.configure(yscrollcommand=scroll.set)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.raw_visible = False
        self.raw_payload: Any = None
        self.summary_text: str = ""

    def set_result(self, summary: str, raw_payload: Any) -> None:
        """Show a success result — summary in text area, raw available via toggle."""
        self.summary_text = summary
        self.raw_payload = raw_payload
        self.raw_visible = False
        self.render()

    def set_error(self, message: str) -> None:
        """Show an error message in the text area so it is copyable."""
        self.summary_text = message
        self.raw_payload = None
        self.raw_visible = False
        self.render()

    def toggle_raw(self) -> None:
        """Switch between summary text and raw JSON."""
        self.raw_visible = not self.raw_visible
        self.render()

    def copy_text(self) -> None:
        content = self.text.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)

    def render(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        if self.raw_visible and self.raw_payload is not None:
            try:
                self.text.insert("1.0", json.dumps(self.raw_payload, indent=2, default=str))
            except TypeError:
                self.text.insert("1.0", repr(self.raw_payload))
        else:
            self.text.insert("1.0", self.summary_text)
        self.text.configure(state="disabled")
