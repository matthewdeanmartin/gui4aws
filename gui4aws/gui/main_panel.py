"""Main panel: resource table + detail grid + contextual action bars; output on bottom."""

from __future__ import annotations

import dataclasses
import logging
import tkinter as tk
from collections.abc import Callable, Iterable
from functools import partial
from tkinter import ttk
from typing import Any

from gui4aws.gui.detail_tree import DetailTree
from gui4aws.gui.filter_bar import FilterBar
from gui4aws.gui.output_panel import OutputPanel
from gui4aws.gui.resource_table import ResourceTable
from gui4aws.models import InputField, RowAction

__all__ = ["MainPanel", "ScriptDialog"]

logger = logging.getLogger(__name__)


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
        ├─ Row-action bar  (contextual buttons for the selected root row)
        └─ Sub-table panel (e.g. cluster member instances + sub-row actions)
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
        # Rows: 0 filter bar, 1 resource table, 2 detail, 3 row-action bar, 4 sub-table
        top_frame = ttk.Frame(outer)
        top_frame.grid_columnconfigure(0, weight=1)
        top_frame.grid_rowconfigure(1, weight=2)
        top_frame.grid_rowconfigure(2, weight=1)

        # Filter bar — wired by MainWindow via configure_filter_bar().
        self.filter_bar = FilterBar(top_frame)
        self.filter_bar.grid(row=0, column=0, sticky="ew", padx=2, pady=(2, 0))

        self.resource_table = ResourceTable(top_frame, columns=("identifier", "status"), on_select=self._on_row_select)
        self.resource_table.grid(row=1, column=0, sticky="nsew")

        detail_frame = ttk.LabelFrame(top_frame, text="Detail")
        detail_frame.grid(row=2, column=0, sticky="nsew", padx=2, pady=2)
        detail_frame.grid_columnconfigure(0, weight=1)
        detail_frame.grid_rowconfigure(0, weight=1)
        self.detail_tree = DetailTree(detail_frame)
        self.detail_tree.grid(row=0, column=0, sticky="nsew")

        # Row-action button bar — populated by set_row_actions()
        self.row_action_bar = ttk.Frame(top_frame)
        self.row_action_bar.grid(row=3, column=0, sticky="ew", padx=4, pady=4)
        self._row_action_label = ttk.Label(self.row_action_bar, text="", foreground="gray")
        self._row_action_label.pack(side="left", padx=4)

        # Sub-table panel (e.g. cluster → instances) — hidden until populated.
        self._sub_frame = ttk.LabelFrame(top_frame, text="Instances")
        self._sub_frame.grid_columnconfigure(0, weight=1)
        self._sub_frame.grid_rowconfigure(0, weight=1)
        self._sub_tree = ttk.Treeview(self._sub_frame, show="headings", height=4)
        self._sub_scroll = ttk.Scrollbar(self._sub_frame, orient="vertical", command=self._sub_tree.yview)
        self._sub_tree.configure(yscrollcommand=self._sub_scroll.set)
        self._sub_tree.grid(row=0, column=0, sticky="nsew")
        self._sub_scroll.grid(row=0, column=1, sticky="ns")
        self._sub_tree.bind("<<TreeviewSelect>>", self._on_sub_table_select)
        self.sub_row_action_bar = ttk.Frame(self._sub_frame)
        self.sub_row_action_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))
        # Hidden by default; show_sub_table / clear_sub_table toggle visibility.
        self._sub_visible = False
        self._sub_grid_row = 4

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
        self._current_columns: list[str] = []
        self._current_row: Any = None
        self._current_client_filter: str = ""
        self._on_row_action: Callable[[RowAction, Any], None] | None = None
        self._on_sub_row_select: Callable[[Any], None] | None = None
        self._current_row_actions: tuple[RowAction, ...] = ()
        self._sub_rows: list[Any] = []
        self._current_sub_row: Any = None
        self._sub_row_actions: tuple[RowAction, ...] = ()
        self._on_sub_row_action: Callable[[RowAction, Any], None] | None = None

    # ── Public API ───────────────────────────────────────────────────────────

    def clear_for_navigation(self) -> None:
        """Reset everything for a fresh navigation."""
        self.resource_table.set_rows([])
        self.detail_tree.set_data({})
        self.output_panel.set_result("", None)
        self._scripts_cli = ""
        self._scripts_python = ""
        self._current_row = None
        self._current_rows = []
        self._current_client_filter = ""
        self.set_row_actions((), None)
        self.clear_sub_table()

    def configure_filter_bar(
        self,
        fields: Iterable[InputField],
        *,
        on_refresh: Callable[[dict[str, str]], None] | None = None,
        prefill: dict[str, str] | None = None,
    ) -> None:
        """Set up the filter bar for the active navigation item.

        Sets ``on_refresh`` and ``on_client_filter``. The per-field change
        handler is set separately via ``set_filter_field_change_handler``.
        """
        self.filter_bar.set_fields(fields, prefill)
        self.filter_bar._on_refresh = (lambda: on_refresh(self.filter_bar.values())) if on_refresh else None
        self.filter_bar._on_client_filter = self._on_client_filter_changed

    def set_filter_field_change_handler(self, handler: Callable[[str, str], None] | None) -> None:
        """Register a callback fired whenever any (non-client) filter field changes."""
        self.filter_bar._on_field_change = handler

    def set_filter_choices(self, field_name: str, choices: list[str], *, auto_select: bool = True) -> None:
        """Populate an eager-dropdown field on the filter bar."""
        self.filter_bar.set_choices(field_name, choices, auto_select=auto_select)

    def filter_values(self) -> dict[str, str]:
        """Current values from the filter bar (for the controller to use on refresh)."""
        return self.filter_bar.values()

    def current_row(self) -> Any:
        """Return the currently selected root row."""
        return self._current_row

    def current_sub_row(self) -> Any:
        """Return the currently selected sub-table row."""
        return self._current_sub_row

    def show_sub_table(self, label: str, rows: list[Any], columns: list[str]) -> None:
        """Populate and show the sub-table panel (e.g. instances for a cluster)."""
        self._sub_frame.configure(text=label)
        previous_key = _row_identity(self._current_sub_row)
        self._sub_rows = list(rows)
        self._current_sub_row = None
        self._sub_tree.configure(columns=columns)
        for col in columns:
            self._sub_tree.heading(col, text=col)
            self._sub_tree.column(col, anchor="w", width=140, stretch=True)
        for child in self._sub_tree.get_children():
            self._sub_tree.delete(child)
        for idx, row in enumerate(rows):
            from gui4aws.gui.resource_table import format_cell

            values = tuple(format_cell(getattr(row, col, "")) for col in columns)
            self._sub_tree.insert("", "end", iid=str(idx), values=values)
        if self._sub_rows:
            selected_index = _find_row_index_by_identity(self._sub_rows, previous_key)
            iid = str(selected_index)
            self._sub_tree.selection_set(iid)
            self._sub_tree.focus(iid)
            self._current_sub_row = self._sub_rows[selected_index]
        if not self._sub_visible:
            self._sub_frame.grid(row=self._sub_grid_row, column=0, sticky="nsew", padx=2, pady=2)
            self._sub_visible = True

    def clear_sub_table(self) -> None:
        """Hide and empty the sub-table panel."""
        if self._sub_visible:
            self._sub_frame.grid_remove()
            self._sub_visible = False
        for child in self._sub_tree.get_children():
            self._sub_tree.delete(child)
        self._sub_rows = []
        self._current_sub_row = None
        self.set_sub_row_actions((), None)

    def show_table(self, rows: list[Any], columns: list[str]) -> None:
        """Replace the resource table with new rows and columns."""
        previous_key = _row_identity(self._current_row)
        if tuple(columns) != self.resource_table.columns:
            old = self.resource_table
            old.grid_remove()
            old.destroy()
            self.resource_table = ResourceTable(old.master, columns=columns, on_select=self._on_row_select)
            self.resource_table.grid(row=1, column=0, sticky="nsew")
        self._current_rows = list(rows)
        self._current_columns = list(columns)
        # Apply any active client-side JMESPath filter immediately.
        visible = self._apply_client_filter(self._current_client_filter)
        self.resource_table.set_rows(visible)
        selected_index = _find_row_index_by_identity(visible, previous_key)
        if visible and selected_index != 0:
            self.resource_table.set_selected_index(selected_index)
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
        on_row_select: Callable[[Any], None] | None = None,
    ) -> None:
        """Rebuild the row-action button bar for the current navigation item."""
        self._current_row_actions = row_actions
        self._on_row_action = on_row_action
        self._on_sub_row_select = on_row_select
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
                command=partial(self._fire_row_action, ra),
            ).pack(side="left", padx=2)

    def set_sub_row_actions(
        self,
        row_actions: tuple[RowAction, ...],
        on_row_action: Callable[[RowAction, Any], None] | None,
    ) -> None:
        """Rebuild the sub-row action button bar for the current sub-table."""
        self._sub_row_actions = row_actions
        self._on_sub_row_action = on_row_action
        for child in self.sub_row_action_bar.winfo_children():
            child.destroy()
        if not row_actions:
            return
        ttk.Label(self.sub_row_action_bar, text="Selected item actions:", foreground="gray").pack(
            side="left",
            padx=(4, 8),
        )
        for ra in row_actions:
            ttk.Button(
                self.sub_row_action_bar,
                text=ra.button_label,
                command=partial(self._fire_sub_row_action, ra),
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
        if self._on_sub_row_select is not None:
            self._on_sub_row_select(row)

    def _fire_row_action(self, row_action: RowAction) -> None:
        if self._on_row_action is not None:
            self._on_row_action(row_action, self._current_row)

    def _on_sub_table_select(self, event: object = None) -> None:
        del event
        selected = self._sub_tree.selection()
        if not selected:
            self._current_sub_row = None
            return
        try:
            idx = int(selected[0])
            self._current_sub_row = self._sub_rows[idx]
        except (ValueError, IndexError):
            self._current_sub_row = None

    def _fire_sub_row_action(self, row_action: RowAction) -> None:
        if self._on_sub_row_action is not None:
            self._on_sub_row_action(row_action, self._current_sub_row)

    def _open_script_dialog(self) -> None:
        if not self._scripts_cli and not self._scripts_python:
            return
        ScriptDialog(self, self._scripts_cli, self._scripts_python)

    # ── Client-side row filtering ────────────────────────────────────────────

    def _on_client_filter_changed(self, expression: str) -> None:
        self._current_client_filter = expression
        visible = self._apply_client_filter(expression)
        self.resource_table.set_rows(visible)

    def _apply_client_filter(self, expression: str) -> list[Any]:
        """Return the subset of current rows matching ``expression``.

        Empty expression → all rows.
        A bare word (no JMESPath-y characters) is treated as a case-insensitive
        substring filter against every visible column. A full JMESPath expression
        is applied to each row's dict form; rows where it returns a truthy value
        are kept.
        """
        if not expression or not self._current_rows:
            return list(self._current_rows)
        # Heuristic: if the user typed a plain word, do a substring match — most
        # users will reach for the filter to type "prod" or a partial name, not
        # to write a JMESPath. Reserve JMESPath for expressions with operators.
        jmespath_chars = set("=<>!&|()[].`?")
        if not any(ch in expression for ch in jmespath_chars):
            needle = expression.lower()
            return [row for row in self._current_rows if _row_substring_match(row, self._current_columns, needle)]
        try:
            import jmespath  # transitive dep of boto3

            compiled = jmespath.compile(expression)
        except Exception as exc:
            logger.debug("invalid JMESPath %r: %s", expression, exc)
            return list(self._current_rows)
        kept: list[Any] = []
        for row in self._current_rows:
            data = _row_to_dict(row)
            try:
                if compiled.search(data):
                    kept.append(row)
            except Exception as exc:
                logger.debug("JMESPath eval failed on row: %s", exc)
                kept.append(row)
        return kept


def _row_to_dict(row: Any) -> dict[str, Any]:
    if dataclasses.is_dataclass(row) and not isinstance(row, type):
        return dataclasses.asdict(row)
    if hasattr(row, "__dict__"):
        return dict(vars(row))
    return {"value": row}


def _row_substring_match(row: Any, columns: list[str], needle: str) -> bool:
    data = _row_to_dict(row)
    for col in columns or data.keys():
        value = data.get(col, "")
        if value is None:
            continue
        if needle in str(value).lower():
            return True
    return False


def _row_identity(row: Any) -> tuple[str, str] | None:
    if row is None:
        return None
    for attr in (
        "cluster_identifier",
        "instance_identifier",
        "snapshot_identifier",
        "identifier",
        "service_name",
        "cluster_name",
        "task_id",
        "name",
        "arn",
    ):
        value = getattr(row, attr, None)
        if value is not None and str(value):
            return (attr, str(value))
    return None


def _find_row_index_by_identity(rows: list[Any], key: tuple[str, str] | None) -> int:
    if key is None:
        return 0
    attr, value = key
    for index, row in enumerate(rows):
        if str(getattr(row, attr, "")) == value:
            return index
    return 0
