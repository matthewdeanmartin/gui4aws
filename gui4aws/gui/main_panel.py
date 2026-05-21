"""Main panel: resource table + detail grid + row-action buttons on top; output on bottom."""

from __future__ import annotations

import dataclasses
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from gui4aws.gui.detail_tree import DetailTree
from gui4aws.gui.output_panel import OutputPanel
from gui4aws.gui.resource_table import ResourceTable
from gui4aws.models import ActionDefinition, RowAction

__all__ = ["MainPanel", "ScriptDialog"]


class ScriptDialog(tk.Toplevel):
    """Popup window showing generated CLI and Python scripts."""

    def __init__(self, parent: tk.Misc, cli: str, python: str) -> None:
        super().__init__(parent)
        self.title("Generated Scripts")
        self.geometry("900x500")
        self.resizable(True, True)

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        cli_frame = ttk.Frame(nb)
        nb.add(cli_frame, text="AWS CLI")
        cli_text = tk.Text(cli_frame, wrap="none", font=("Courier", 10))
        cli_text.insert("1.0", cli)
        cli_text.configure(state="disabled")
        cli_scroll = ttk.Scrollbar(cli_frame, orient="vertical", command=cli_text.yview)
        cli_text.configure(yscrollcommand=cli_scroll.set)
        cli_text.pack(side="left", fill="both", expand=True)
        cli_scroll.pack(side="right", fill="y")

        py_frame = ttk.Frame(nb)
        nb.add(py_frame, text="Python (boto3)")
        py_text = tk.Text(py_frame, wrap="none", font=("Courier", 10))
        py_text.insert("1.0", python)
        py_text.configure(state="disabled")
        py_scroll = ttk.Scrollbar(py_frame, orient="vertical", command=py_text.yview)
        py_text.configure(yscrollcommand=py_scroll.set)
        py_text.pack(side="left", fill="both", expand=True)
        py_scroll.pack(side="right", fill="y")

        btn_bar = ttk.Frame(self)
        btn_bar.pack(fill="x", padx=4, pady=4)
        ttk.Button(btn_bar, text="Copy CLI", command=lambda: _copy(self, cli)).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Copy Python", command=lambda: _copy(self, python)).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Close", command=self.destroy).pack(side="right", padx=8)


def _copy(widget: tk.Misc, text: str) -> None:
    widget.clipboard_clear()
    widget.clipboard_append(text)


class MainPanel(ttk.Frame):
    """Main content area.

    Layout (outer vertical PanedWindow):
      Top pane (vertical PanedWindow):
        ├─ Resource table  (list of rows)
        ├─ Detail grid     (fields of selected row)
        └─ Row-action bar  (contextual buttons for selected row)
      Bottom pane:
        └─ Output panel    (result summary + raw JSON toggle)

    Action forms open in a separate ActionDialog Toplevel window.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        outer = ttk.PanedWindow(self, orient="vertical")
        outer.grid(row=0, column=0, sticky="nsew")

        # ── Top pane ─────────────────────────────────────────────────────────
        top_frame = ttk.Frame(outer)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_rowconfigure(0, weight=2)
        top_frame.grid_rowconfigure(1, weight=1)

        self.resource_table = ResourceTable(
            top_frame, columns=("identifier", "status"), on_select=self._on_row_select
        )
        self.resource_table.grid(row=0, column=0, sticky="nsew")

        detail_frame = ttk.LabelFrame(top_frame, text="Detail")
        detail_frame.grid(row=1, column=0, sticky="nsew", padx=2, pady=2)
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_tree = DetailTree(detail_frame)
        self.detail_tree.grid(row=0, column=0, sticky="nsew")

        # Row-action button bar — populated by set_row_actions()
        self.row_action_bar = ttk.Frame(top_frame)
        self.row_action_bar.grid(row=2, column=0, sticky="ew", padx=4, pady=4)
        self._row_action_label = ttk.Label(self.row_action_bar, text="", foreground="gray")
        self._row_action_label.pack(side="left", padx=4)

        outer.add(top_frame, weight=3)

        # ── Bottom pane ───────────────────────────────────────────────────────
        bottom_frame = ttk.Frame(outer)
        bottom_frame.grid_columnconfigure(0, weight=1)
        bottom_frame.grid_rowconfigure(0, weight=1)

        self.output_panel = OutputPanel(bottom_frame)
        self.output_panel.grid(row=0, column=0, sticky="nsew")

        btn_bar = ttk.Frame(bottom_frame)
        btn_bar.grid(row=1, column=0, sticky="e", padx=4, pady=2)
        self._scripts_cli = ""
        self._scripts_python = ""
        ttk.Button(btn_bar, text="Show Scripts", command=self._open_script_dialog).pack(side="right", padx=4)

        outer.add(bottom_frame, weight=1)

        # State
        self._current_rows: list[Any] = []
        self._current_row: Any = None
        self._on_row_action: Callable[[RowAction, Any], None] | None = None
        self._current_row_actions: tuple[RowAction, ...] = ()

    # ── Public API ───────────────────────────────────────────────────────────

    def clear_for_navigation(self) -> None:
        """Reset everything for a fresh navigation."""
        self.resource_table.set_rows([])
        self.detail_tree.set_data({})
        self.output_panel.set_result("", None)
        self._scripts_cli = ""
        self._scripts_python = ""
        self._current_row = None
        self.set_row_actions((), None)

    def show_table(self, rows: list[Any], columns: list[str]) -> None:
        """Replace the resource table with new rows and columns."""
        if tuple(columns) != self.resource_table.columns:
            old = self.resource_table
            old.grid_remove()
            old.destroy()
            self.resource_table = ResourceTable(
                old.master, columns=columns, on_select=self._on_row_select
            )
            self.resource_table.grid(row=0, column=0, sticky="nsew")
        self._current_rows = list(rows)
        self.resource_table.set_rows(rows)
        self.detail_tree.set_data({})

    def show_output(self, summary: str, raw: Any) -> None:
        """Show an output summary in the output panel."""
        self.output_panel.set_result(summary, raw)

    def show_scripts(self, cli: str, python: str) -> None:
        """Store the latest generated scripts (opened on demand via Show Scripts)."""
        self._scripts_cli = cli
        self._scripts_python = python

    def set_row_actions(
        self,
        row_actions: tuple[RowAction, ...],
        on_row_action: Callable[[RowAction, Any], None] | None,
    ) -> None:
        """Rebuild the row-action button bar for the current navigation item."""
        self._current_row_actions = row_actions
        self._on_row_action = on_row_action
        for child in self.row_action_bar.winfo_children():
            child.destroy()
        if not row_actions:
            return
        self._row_action_label = ttk.Label(self.row_action_bar, text="Actions:", foreground="gray")
        self._row_action_label.pack(side="left", padx=(4, 8))
        for ra in row_actions:
            ttk.Button(
                self.row_action_bar,
                text=ra.button_label,
                command=lambda _ra=ra: self._fire_row_action(_ra),
            ).pack(side="left", padx=2)

    # ── Internal helpers ─────────────────────────────────────────────────────

    def _on_row_select(self, row: Any) -> None:
        """Populate the detail grid when a table row is selected."""
        self._current_row = row
        if dataclasses.is_dataclass(row) and not isinstance(row, type):
            data = dataclasses.asdict(row)
        elif hasattr(row, "__dict__"):
            data = vars(row)
        else:
            data = {"value": str(row)}
        self.detail_tree.set_data(data)

    def _fire_row_action(self, row_action: RowAction) -> None:
        if self._on_row_action is not None:
            self._on_row_action(row_action, self._current_row)

    def _open_script_dialog(self) -> None:
        if not self._scripts_cli and not self._scripts_python:
            return
        ScriptDialog(self, self._scripts_cli, self._scripts_python)
