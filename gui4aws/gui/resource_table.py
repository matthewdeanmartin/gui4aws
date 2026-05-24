"""ttk.Treeview wrapper for sortable resource lists."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from functools import partial
from tkinter import ttk
from typing import Any

__all__ = ["ResourceTable"]


class ResourceTable(ttk.Frame):
    """A sortable table built on ttk.Treeview.

    Rows are added via ``set_rows``, which takes a list of objects and an attribute list. The
    table reads ``getattr(obj, column)`` for each column.

    Selecting a row calls ``on_select(row_object)`` if provided.

    Rows with a truthy ``deleted`` attribute are displayed greyed-out using the
    ``deleted`` Treeview tag so users can see them without confusing them for
    active resources.
    """

    def __init__(
        self,
        parent: tk.Misc,
        columns: Sequence[str],
        on_select: Callable[[Any], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.columns = tuple(columns)
        self.on_select = on_select
        self._rows: list[Any] = []

        self.tree = ttk.Treeview(self, columns=self.columns, show="headings", height=10)
        for column in self.columns:
            self.tree.heading(
                column,
                text=column,
                command=partial(self.sort_by, column, False),
            )
            self.tree.column(column, anchor="w", width=160, stretch=True)

        # Style for deleted / pending-deletion rows: dimmed foreground.
        self.tree.tag_configure("deleted", foreground="#999999")

        scroll_y = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll_y.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def set_rows(self, rows: Sequence[Any]) -> None:
        """Replace all rows and auto-select the first one."""
        self._rows = list(rows)
        for child in self.tree.get_children():
            self.tree.delete(child)
        for idx, row in enumerate(rows):
            values = tuple(format_cell(getattr(row, column, "")) for column in self.columns)
            tags = ("deleted",) if getattr(row, "deleted", False) else ()
            self.tree.insert("", "end", iid=str(idx), values=values, tags=tags)
        if self._rows:
            self.tree.selection_set("0")
            self.tree.focus("0")
            if self.on_select is not None:
                self.on_select(self._rows[0])

    def set_selected_index(self, index: int) -> None:
        """Select an existing row by index and fire the selection callback."""
        if index < 0 or index >= len(self._rows):
            return
        iid = str(index)
        self.tree.selection_set(iid)
        self.tree.focus(iid)
        if self.on_select is not None:
            self.on_select(self._rows[index])

    def _on_tree_select(self, event: object = None) -> None:
        del event
        if self.on_select is None:
            return
        selected = self.tree.selection()
        if not selected:
            return
        try:
            idx = int(selected[0])
            row = self._rows[idx]
        except (ValueError, IndexError):
            return
        self.on_select(row)

    def sort_by(self, column: str, descending: bool) -> None:
        """Sort the rows by the given column."""
        data = [(self.tree.set(item, column), item) for item in self.tree.get_children("")]
        data.sort(reverse=descending)
        for index, (_, item) in enumerate(data):
            self.tree.move(item, "", index)
        self.tree.heading(column, command=partial(self.sort_by, column, not descending))


def format_cell(value: Any) -> str:
    """Render a Python value as a table cell string."""
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)
