"""Key-value grid for displaying the fields of a selected resource row."""

# pylint: disable=too-many-ancestors

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

__all__ = ["DetailTree"]


class DetailTree(ttk.Frame):
    """Flat two-column grid: Field | Value.

    Data is a flat dict (from dataclasses.asdict). Nested dicts/lists are serialised
    to a compact string so every field stays on one visible row — no expand/collapse needed.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        """Initialize the detail tree with Field and Value columns."""
        super().__init__(parent, **kwargs)
        cols = ("field", "value")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("field", text="Field")
        self.tree.heading("value", text="Value")
        self.tree.column("field", width=200, anchor="w", stretch=False)
        self.tree.column("value", width=500, anchor="w", stretch=True)
        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

    def set_data(self, data: Any) -> None:
        """Replace contents with a flat or nested mapping."""
        for child in self.tree.get_children():
            self.tree.delete(child)
        if not data:
            return
        if isinstance(data, dict):
            for key, value in data.items():
                self.tree.insert("", "end", values=(str(key), fmt(value)))
        else:
            self.tree.insert("", "end", values=("value", fmt(data)))


# pylint: disable=too-many-return-statements
def fmt(value: Any) -> str:
    """Render any value as a compact single-line string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, dict):
        if not value:
            return "{}"
        parts = [f"{k}: {fmt(v)}" for k, v in value.items()]
        return "{ " + ",  ".join(parts) + " }"
    if isinstance(value, (list, tuple)):
        if not value:
            return "[]"
        return "[" + ",  ".join(fmt(item) for item in value) + "]"
    return str(value)
