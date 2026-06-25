"""Full-screen JSON viewer dialog with a tree widget for AWS API responses.

AWS responses follow a predictable shape:
  - Top-level 'ResponseMetadata' key  → structured label panel at top
  - Everything else                   → auto-expanded ttk.Treeview below

When 'ResponseMetadata' is absent the entire payload goes into the tree.
"""

from __future__ import annotations

import contextlib
import json
import tkinter as tk
from tkinter import ttk
from typing import Any

__all__ = ["JsonViewerDialog"]

_METADATA_KEY = "ResponseMetadata"

# Keys we render as individual labelled rows in the metadata panel.
_KNOWN_META_KEYS = ("HTTPStatusCode", "RequestId", "HostId", "RetryAttempts")


def _insert_node(tree: ttk.Treeview, parent: str, key: str, value: Any) -> None:
    """Recursively insert a JSON value into the treeview."""
    if isinstance(value, dict):
        node = tree.insert(parent, "end", text=key, values=("",), open=True)
        for k, v in value.items():
            _insert_node(tree, node, str(k), v)
    elif isinstance(value, list):
        node = tree.insert(parent, "end", text=f"{key}  [{len(value)}]", values=("",), open=True)
        for i, item in enumerate(value):
            _insert_node(tree, node, f"[{i}]", item)
    else:
        display = str(value) if not isinstance(value, str) else value
        tree.insert(parent, "end", text=key, values=(display,))


def _collapse_all(tree: ttk.Treeview, node: str = "") -> None:
    """Recursively close every node in the treeview."""
    for child in tree.get_children(node):
        _collapse_all(tree, child)
        tree.item(child, open=False)


def _expand_all(tree: ttk.Treeview, node: str = "") -> None:
    """Recursively open every node in the treeview."""
    tree.item(node, open=True)
    for child in tree.get_children(node):
        _expand_all(tree, child)


def _build_metadata_panel(parent: tk.Misc, metadata: dict[str, Any]) -> None:
    """Populate the metadata LabelFrame with structured widgets.

    Known scalar keys → Label + readonly Entry.
    HTTPHeaders → single wide Combobox with "key: value" entries.
    Remaining unknown keys → Label + readonly Entry.

    StringVars are stored on the parent widget to prevent GC blanking entries.
    """
    lf = parent
    lf.grid_columnconfigure(1, weight=1)
    # Anchor all StringVars on the widget so they survive past this function's scope.
    anchored_vars: list[tk.StringVar] = []
    lf._vars = anchored_vars  # type: ignore[attr-defined]  # pylint: disable=protected-access

    row = 0

    # ── Well-known scalar keys ────────────────────────────────────────────────
    for key in _KNOWN_META_KEYS:
        if key not in metadata:
            continue
        ttk.Label(lf, text=f"{key}:", anchor="e").grid(row=row, column=0, sticky="e", padx=(8, 4), pady=2)
        var = tk.StringVar(value=str(metadata[key]))
        anchored_vars.append(var)
        entry = ttk.Entry(lf, textvariable=var, state="readonly", width=60)
        entry.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=2)
        row += 1

    # ── HTTPHeaders — single wide "key: value" combobox ──────────────────────
    headers: dict[str, str] = metadata.get("HTTPHeaders", {})
    if headers:
        ttk.Label(lf, text="HTTPHeaders:", anchor="e").grid(row=row, column=0, sticky="e", padx=(8, 4), pady=2)
        # Each entry shows "header-name: value" so scanning is instant.
        header_items = [f"{k}: {v}" for k, v in sorted(headers.items())]
        combo = ttk.Combobox(lf, values=header_items, state="readonly")
        combo.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=2)
        if header_items:
            combo.current(0)
        row += 1

    # ── Unexpected / unknown keys ─────────────────────────────────────────────
    known = set(_KNOWN_META_KEYS) | {"HTTPHeaders"}
    for key, value in metadata.items():
        if key in known:
            continue
        ttk.Label(lf, text=f"{key}:", anchor="e").grid(row=row, column=0, sticky="e", padx=(8, 4), pady=2)
        raw_val = str(value) if not isinstance(value, (dict, list)) else json.dumps(value, default=str)
        var2 = tk.StringVar(value=raw_val)
        anchored_vars.append(var2)
        entry2 = ttk.Entry(lf, textvariable=var2, state="readonly", width=60)
        entry2.grid(row=row, column=1, sticky="ew", padx=(0, 8), pady=2)
        row += 1


class JsonViewerDialog(tk.Toplevel):
    """Full-screen popup that renders an AWS JSON response as an interactive tree.

    Layout:
      [Response Metadata panel]   ← structured labels; only when key present
      [Expand / Collapse / Copy]
      [Data Treeview]
      [Close button]
    """

    def __init__(self, parent: tk.Misc, payload: Any, title: str = "JSON Viewer") -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Normalise payload ────────────────────────────────────────────────
        if isinstance(payload, str):
            with contextlib.suppress(json.JSONDecodeError, TypeError):
                payload = json.loads(payload)

        metadata: dict[str, Any] | None = None
        data: Any = payload

        if isinstance(payload, dict) and _METADATA_KEY in payload:
            metadata = payload[_METADATA_KEY]
            data = {k: v for k, v in payload.items() if k != _METADATA_KEY}

        # ── Metadata panel ───────────────────────────────────────────────────
        if metadata is not None:
            meta_lf = ttk.LabelFrame(self, text="Response Metadata")
            meta_lf.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 4))
            _build_metadata_panel(meta_lf, metadata)
            row += 1

        # ── Tree toolbar ─────────────────────────────────────────────────────
        toolbar = ttk.Frame(self)
        toolbar.grid(row=row, column=0, sticky="ew", padx=8, pady=(4, 2))
        row += 1

        ttk.Button(toolbar, text="Expand All", command=lambda: _expand_all(self.tree)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Collapse All", command=lambda: _collapse_all(self.tree)).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Copy JSON", command=self._copy_json).pack(side="left", padx=2)

        # ── Treeview ─────────────────────────────────────────────────────────
        tree_frame = ttk.LabelFrame(self, text="Data")
        tree_frame.grid(row=row, column=0, sticky="nsew", padx=8, pady=(0, 4))
        tree_frame.grid_columnconfigure(0, weight=1)
        tree_frame.grid_rowconfigure(0, weight=1)
        self.grid_rowconfigure(row, weight=1)
        row += 1

        self.tree = ttk.Treeview(tree_frame, columns=("value",), selectmode="browse")
        self.tree.heading("#0", text="Key", anchor="w")
        self.tree.heading("value", text="Value", anchor="w")
        self.tree.column("#0", width=280, stretch=True)
        self.tree.column("value", width=520, stretch=True)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ── Populate tree (open=True in _insert_node means auto-expanded) ────
        self._raw_data = data
        if isinstance(data, dict):
            for k, v in data.items():
                _insert_node(self.tree, "", str(k), v)
        elif isinstance(data, list):
            for i, item in enumerate(data):
                _insert_node(self.tree, "", f"[{i}]", item)
        else:
            self.tree.insert("", "end", text="value", values=(str(data),))

        # ── Close button ─────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=row, column=0, sticky="e", padx=8, pady=8)
        ttk.Button(btn_frame, text="Close  [Esc]", command=self.destroy).pack()

        self._size_and_center()

    def _copy_json(self) -> None:
        """Copy the data payload (without metadata) as formatted JSON to the clipboard."""
        try:
            text = json.dumps(self._raw_data, indent=2, default=str)
        except TypeError:
            text = repr(self._raw_data)
        self.clipboard_clear()
        self.clipboard_append(text)

    def _size_and_center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = int(sw * 0.85)
        h = int(sh * 0.85)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")
