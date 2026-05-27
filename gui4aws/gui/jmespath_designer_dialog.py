"""JMESPath Query Designer: interactive query builder with history and save/load.

Layout:
  [Query bar]  expression entry + Run + Clear + Recent dropdown
  [Saved bar]  name entry + Save + Load + Delete
  [Main panes] Data tree  |  Builder buttons  |  Result tree
  [Help panel] tabbed JMESPath quick-reference
  [Footer]     Close
"""

from __future__ import annotations

import json
import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

__all__ = ["JmespathDesignerDialog"]

logger = logging.getLogger(__name__)

_MAX_RECENT = 30


# ── Persistence ───────────────────────────────────────────────────────────────

def _queries_path() -> Path:
    from gui4aws.config import config_path
    return config_path().parent / "jmespath_queries.json"


def _load_saved() -> dict[str, str]:
    p = _queries_path()
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_all(queries: dict[str, str]) -> None:
    p = _queries_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(queries, indent=2, sort_keys=True), encoding="utf-8")


# ── Tree helpers (shared with JsonViewerDialog pattern) ───────────────────────

def _insert_node(tree: ttk.Treeview, parent: str, key: str, value: Any) -> None:
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


def _clear_tree(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())


def _populate_tree(tree: ttk.Treeview, data: Any) -> None:
    _clear_tree(tree)
    if isinstance(data, dict):
        for k, v in data.items():
            _insert_node(tree, "", str(k), v)
    elif isinstance(data, list):
        for i, item in enumerate(data):
            _insert_node(tree, "", f"[{i}]", item)
    elif data is None:
        tree.insert("", "end", text="(null)", values=("",))
    else:
        tree.insert("", "end", text="value", values=(str(data),))


# ── Help text ─────────────────────────────────────────────────────────────────

_HELP: dict[str, str] = {
    "Field Access": """\
field_name        Access a top-level field
parent.child      Nested field access
parent.*.child    Wildcard: value of 'child' in every sub-object
@                 Current node (identity)

Examples:
  foo              → data["foo"]
  foo.bar          → data["foo"]["bar"]
  foo.*            → list of all values inside foo
""",
    "Arrays": """\
[*]               All elements of an array (creates a projection)
[0]               First element
[-1]              Last element
[2:5]             Slice — elements at index 2, 3, 4
[::2]             Every 2nd element
[]                Flatten one level of nested arrays

Examples:
  items[*]         → every element in items
  items[0]         → first element
  items[-1]        → last element
  items[1:3]       → second and third elements
  items[].name     → name from each item (flatten + project)
""",
    "Filters": """\
[?field == 'val']     Equality (string values need quotes)
[?field != 'val']     Not-equal
[?field > `0`]        Numeric comparison — use backtick literals
[?field >= `0`]       Greater-or-equal
[?field]              Existence / truthiness
[?!field]             Negation — field is falsy or absent
[?a == 'x' && b]     AND condition
[?a || b]             OR condition

String comparison examples:
  items[?status == 'ACTIVE']
  items[?starts_with(name, 'prod-')]
  items[?contains(tags, 'web')]

Numeric comparison examples:
  items[?size > `100`]
  items[?count >= `1` && count <= `10`]
""",
    "Functions": """\
length(@)             Length of string, array, or object key-count
keys(@)               List of object keys
values(@)             List of object values
type(@)               Type: 'string' | 'number' | 'boolean' | 'array'
                        | 'object' | 'null'
to_string(@)          Convert any value to a string
to_number('3')        Parse string to number
sort(@)               Sort a homogeneous array
reverse(@)            Reverse an array
sort_by(@, &field)    Sort objects by a named field
min_by(@, &field)     Object with minimum field value
max_by(@, &field)     Object with maximum field value
sum(@)                Sum of numeric array
max(@)                Maximum of numeric array
min(@)                Minimum of numeric array
avg(@)                Average of numeric array
join(', ', @)         Join string array with separator
contains(@, 'val')    True if array/string contains value
starts_with(s, 'p')   String prefix test
ends_with(s, 'suf')   String suffix test
merge({}, obj)        Merge two objects

Examples:
  length(items)
  sort_by(items, &name)
  items | length(@)
  join(', ', items[*].name)
""",
    "Pipe & Multi-select": """\
expr | expr2          Pipe — feed result of left into right
{key: field}          Multi-select object: reshape each node
[f1, f2]              Multi-select list: keep only named fields

Examples:
  items | length(@)               count items
  items[*].name | sort(@)         sorted list of names
  items[*].{id: id, n: name}      reshape to id/name pairs
  items[*].[id, name, status]     extract 3 fields as list
  {count: length(items),
   names: items[*].name}          build a summary object
""",
}

# ── Builder button definitions ────────────────────────────────────────────────

_BUILDER: dict[str, list[tuple[str, str]]] = {
    "Navigate": [
        (".", "."),
        ("[*]", "[*]"),
        ("[@]", "[@]"),
        ("@", "@"),
        ("[0]", "[0]"),
        ("[-1]", "[-1]"),
        ("[0:5]", "[0:5]"),
        ("[::2]", "[::2]"),
        ("[]", "[]"),
        ("| ", "| "),
        (".*", ".*"),
    ],
    "Filters": [
        ("[?f == 'v']", "[?field == 'value']"),
        ("[?f != 'v']", "[?field != 'value']"),
        ("[?f > `0`]", "[?field > `0`]"),
        ("[?f >= `0`]", "[?field >= `0`]"),
        ("[?f]", "[?field]"),
        ("[?!f]", "[?!field]"),
        ("[?a && b]", "[?a && b]"),
        ("[?a || b]", "[?a || b]"),
        ("starts_with", "starts_with(field, 'prefix')"),
        ("ends_with", "ends_with(field, 'suffix')"),
        ("contains", "contains(field, 'value')"),
    ],
    "Functions": [
        ("length()", "length(@)"),
        ("keys()", "keys(@)"),
        ("values()", "values(@)"),
        ("type()", "type(@)"),
        ("sort()", "sort(@)"),
        ("reverse()", "reverse(@)"),
        ("sort_by()", "sort_by(@, &field)"),
        ("min_by()", "min_by(@, &field)"),
        ("max_by()", "max_by(@, &field)"),
        ("max()", "max(@)"),
        ("min()", "min(@)"),
        ("avg()", "avg(@)"),
        ("sum()", "sum(@)"),
        ("join()", "join(', ', @)"),
        ("to_string()", "to_string(@)"),
        ("to_number()", "to_number(@)"),
    ],
    "Project": [
        ("{k: v}", "{key: field}"),
        ("[a, b]", "[field1, field2]"),
        ("[*].f", "[*].field"),
        ("[].f", "[].field"),
        ("merge()", "merge(`{}`, @)"),
        ("[*].{}", "[*].{id: id, name: name}"),
    ],
}


# ── Dialog ────────────────────────────────────────────────────────────────────

class JmespathDesignerDialog(tk.Toplevel):
    """Interactive JMESPath query designer with tree preview, builder, and saved queries."""

    def __init__(self, parent: tk.Misc, payload: Any = None, title: str = "JMESPath Query Designer") -> None:
        super().__init__(parent)
        self.title(title)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

        self._payload: Any = payload
        self._recent: list[str] = []
        self._saved: dict[str, str] = _load_saved()
        self._status_var = tk.StringVar(value="Enter a JMESPath expression and click Run.")

        self.grid_columnconfigure(0, weight=1)

        row = 0

        # ── Query bar ─────────────────────────────────────────────────────────
        qbar = ttk.LabelFrame(self, text="Query")
        qbar.grid(row=row, column=0, sticky="ew", padx=8, pady=(8, 2))
        qbar.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(qbar, text="Expression:").grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")
        self._query_var = tk.StringVar()
        self._query_entry = ttk.Entry(qbar, textvariable=self._query_var, font=("Courier", 10))
        self._query_entry.grid(row=0, column=1, sticky="ew", padx=4, pady=4)
        self._query_entry.bind("<Return>", lambda _e: self._run())

        btn_frame = ttk.Frame(qbar)
        btn_frame.grid(row=0, column=2, padx=(4, 8), pady=4)
        ttk.Button(btn_frame, text="Run  [Enter]", command=self._run, width=12).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Clear", command=self._clear_query, width=7).pack(side="left", padx=2)

        ttk.Label(qbar, text="Recent:").grid(row=1, column=0, padx=(8, 4), pady=(0, 4), sticky="w")
        self._recent_var = tk.StringVar()
        self._recent_combo = ttk.Combobox(qbar, textvariable=self._recent_var, state="readonly", width=60)
        self._recent_combo.grid(row=1, column=1, columnspan=2, sticky="ew", padx=(4, 8), pady=(0, 4))
        self._recent_combo.bind("<<ComboboxSelected>>", self._on_select_recent)

        # ── Saved queries bar ─────────────────────────────────────────────────
        sbar = ttk.LabelFrame(self, text="Saved Queries")
        sbar.grid(row=row, column=0, sticky="ew", padx=8, pady=2)
        sbar.grid_columnconfigure(1, weight=1)
        row += 1

        ttk.Label(sbar, text="Name:").grid(row=0, column=0, padx=(8, 4), pady=4, sticky="w")
        self._save_name_var = tk.StringVar()
        ttk.Entry(sbar, textvariable=self._save_name_var, width=30).grid(
            row=0, column=1, sticky="ew", padx=4, pady=4
        )
        saved_btns = ttk.Frame(sbar)
        saved_btns.grid(row=0, column=2, padx=(4, 8), pady=4)
        ttk.Button(saved_btns, text="Save", command=self._save_query, width=7).pack(side="left", padx=2)
        ttk.Button(saved_btns, text="Load…", command=self._load_query, width=7).pack(side="left", padx=2)
        ttk.Button(saved_btns, text="Delete…", command=self._delete_query, width=8).pack(side="left", padx=2)
        ttk.Button(saved_btns, text="Copy", command=self._copy_query, width=7).pack(side="left", padx=2)

        # ── Status bar ────────────────────────────────────────────────────────
        status_lbl = ttk.Label(self, textvariable=self._status_var, foreground="#555")
        status_lbl.grid(row=row, column=0, sticky="ew", padx=12, pady=(2, 0))
        self._status_label = status_lbl
        row += 1

        # ── Main paned area ───────────────────────────────────────────────────
        main_pw = ttk.PanedWindow(self, orient="horizontal")
        main_pw.grid(row=row, column=0, sticky="nsew", padx=8, pady=4)
        self.grid_rowconfigure(row, weight=1)
        row += 1

        # Left: input data tree
        data_frame = ttk.LabelFrame(main_pw, text="Input Data")
        data_frame.grid_columnconfigure(0, weight=1)
        data_frame.grid_rowconfigure(0, weight=1)
        self._data_tree, _ = self._make_tree(data_frame)
        main_pw.add(data_frame, weight=3)

        # Middle: builder
        builder_outer = ttk.LabelFrame(main_pw, text="Query Builder  (click to insert at cursor)")
        main_pw.add(builder_outer, weight=2)
        self._build_builder(builder_outer)

        # Right: result tree
        result_frame = ttk.LabelFrame(main_pw, text="Result")
        result_frame.grid_columnconfigure(0, weight=1)
        result_frame.grid_rowconfigure(0, weight=1)
        self._result_tree, _ = self._make_tree(result_frame)
        main_pw.add(result_frame, weight=3)

        # ── Help panel ────────────────────────────────────────────────────────
        help_outer = ttk.LabelFrame(self, text="JMESPath Reference")
        help_outer.grid(row=row, column=0, sticky="nsew", padx=8, pady=(0, 4))
        self.grid_rowconfigure(row, weight=1)
        row += 1
        self._build_help(help_outer)

        # ── Footer ────────────────────────────────────────────────────────────
        footer = ttk.Frame(self)
        footer.grid(row=row, column=0, sticky="e", padx=8, pady=6)
        ttk.Button(footer, text="Close  [Esc]", command=self.destroy).pack()

        # ── Populate initial data ─────────────────────────────────────────────
        if payload is not None:
            self._set_payload(payload)

        self._size_and_center()
        self._query_entry.focus_set()

    # ── Tree factory ─────────────────────────────────────────────────────────

    def _make_tree(self, parent: tk.Misc) -> tuple[ttk.Treeview, ttk.Frame]:
        frame = ttk.Frame(parent)
        frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=("value",), selectmode="browse")
        tree.heading("#0", text="Key", anchor="w")
        tree.heading("value", text="Value", anchor="w")
        tree.column("#0", width=180, stretch=True)
        tree.column("value", width=260, stretch=True)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        return tree, frame

    # ── Builder ───────────────────────────────────────────────────────────────

    def _build_builder(self, parent: tk.Misc) -> None:
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=4, pady=4)

        for tab_name, buttons in _BUILDER.items():
            tab = ttk.Frame(nb)
            nb.add(tab, text=tab_name)
            col = 0
            row = 0
            for label, snippet in buttons:
                btn = ttk.Button(
                    tab,
                    text=label,
                    width=13,
                    command=lambda s=snippet: self._insert_snippet(s),
                )
                btn.grid(row=row, column=col, padx=2, pady=2, sticky="ew")
                col += 1
                if col >= 2:
                    col = 0
                    row += 1

    # ── Help panel ────────────────────────────────────────────────────────────

    def _build_help(self, parent: tk.Misc) -> None:
        nb = ttk.Notebook(parent)
        nb.pack(fill="both", expand=True, padx=4, pady=(0, 4))

        for topic, text in _HELP.items():
            frame = ttk.Frame(nb)
            nb.add(frame, text=topic)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            txt = tk.Text(
                frame,
                wrap="none",
                height=6,
                font=("Courier", 9),
                background="#f8f8f8",
                relief="flat",
            )
            vsb = ttk.Scrollbar(frame, orient="vertical", command=txt.yview)
            txt.configure(yscrollcommand=vsb.set)
            txt.insert("1.0", text.strip())
            txt.configure(state="disabled")
            txt.grid(row=0, column=0, sticky="nsew", padx=(4, 0), pady=4)
            vsb.grid(row=0, column=1, sticky="ns", pady=4)

    # ── Snippet insertion ─────────────────────────────────────────────────────

    def _insert_snippet(self, snippet: str) -> None:
        """Insert snippet at cursor position in the query entry."""
        try:
            pos = self._query_entry.index(tk.INSERT)
            current = self._query_var.get()
            new_val = current[:pos] + snippet + current[pos:]
            self._query_var.set(new_val)
            self._query_entry.icursor(pos + len(snippet))
        except Exception:
            self._query_var.set(self._query_var.get() + snippet)
        self._query_entry.focus_set()

    # ── Data loading ──────────────────────────────────────────────────────────

    def _set_payload(self, payload: Any) -> None:
        self._payload = payload
        if isinstance(payload, str):
            try:
                self._payload = json.loads(payload)
            except (json.JSONDecodeError, TypeError):
                pass
        _populate_tree(self._data_tree, self._payload)

    # ── Query execution ───────────────────────────────────────────────────────

    def _run(self) -> None:
        expr = self._query_var.get().strip()
        if not expr:
            self._status("No expression — enter a JMESPath query and press Run.", ok=False)
            return
        if self._payload is None:
            self._status("No data loaded — open the designer from the output panel.", ok=False)
            return
        try:
            import jmespath  # transitive dep of boto3

            result = jmespath.compile(expr).search(self._payload)
            _populate_tree(self._result_tree, result)
            self._add_recent(expr)
            count = _result_count(result)
            self._status(f"OK — {count}", ok=True)
        except jmespath.exceptions.JMESPathError as exc:
            _clear_tree(self._result_tree)
            self._status(f"Error: {exc}", ok=False)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            _clear_tree(self._result_tree)
            self._status(f"Unexpected error: {exc}", ok=False)

    def _clear_query(self) -> None:
        self._query_var.set("")
        _clear_tree(self._result_tree)
        self._status("Expression cleared.")
        self._query_entry.focus_set()

    def _status(self, msg: str, ok: bool | None = None) -> None:
        self._status_var.set(msg)
        if ok is True:
            self._status_label.configure(foreground="#267326")
        elif ok is False:
            self._status_label.configure(foreground="#993333")
        else:
            self._status_label.configure(foreground="#555")

    # ── Recent ────────────────────────────────────────────────────────────────

    def _add_recent(self, expr: str) -> None:
        if expr in self._recent:
            self._recent.remove(expr)
        self._recent.insert(0, expr)
        if len(self._recent) > _MAX_RECENT:
            self._recent.pop()
        self._recent_combo["values"] = self._recent

    def _on_select_recent(self, _event: object = None) -> None:
        expr = self._recent_var.get()
        if expr:
            self._query_var.set(expr)
            self._query_entry.focus_set()

    # ── Save / load / delete ──────────────────────────────────────────────────

    def _save_query(self) -> None:
        name = self._save_name_var.get().strip()
        expr = self._query_var.get().strip()
        if not name:
            messagebox.showwarning("Save Query", "Enter a name before saving.", parent=self)
            return
        if not expr:
            messagebox.showwarning("Save Query", "The expression is empty.", parent=self)
            return
        if name in self._saved and not messagebox.askyesno(
            "Overwrite?", f"'{name}' already exists. Overwrite?", parent=self
        ):
            return
        self._saved[name] = expr
        _save_all(self._saved)
        self._status(f"Saved '{name}'.", ok=True)

    def _load_query(self) -> None:
        if not self._saved:
            messagebox.showinfo("Load Query", "No saved queries yet.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("Load Saved Query")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        lf = ttk.LabelFrame(win, text="Saved Queries")
        lf.pack(fill="both", expand=True, padx=8, pady=8)

        lb = tk.Listbox(lf, width=50, height=12, selectmode="single")
        lb.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        sb = ttk.Scrollbar(lf, command=lb.yview)
        sb.pack(side="left", fill="y", pady=4)
        lb.configure(yscrollcommand=sb.set)

        names = sorted(self._saved)
        for n in names:
            lb.insert("end", n)

        preview_var = tk.StringVar()
        ttk.Label(win, text="Expression:").pack(anchor="w", padx=8)
        prev_entry = ttk.Entry(win, textvariable=preview_var, state="readonly", width=60)
        prev_entry.pack(fill="x", padx=8, pady=(0, 4))

        def on_select(_e: object = None) -> None:
            sel = lb.curselection()
            if sel:
                preview_var.set(self._saved[names[sel[0]]])

        lb.bind("<<ListboxSelect>>", on_select)

        def do_load() -> None:
            sel = lb.curselection()
            if not sel:
                return
            chosen_name = names[sel[0]]
            self._query_var.set(self._saved[chosen_name])
            self._save_name_var.set(chosen_name)
            win.destroy()
            self._status(f"Loaded '{chosen_name}'.")
            self._query_entry.focus_set()

        lb.bind("<Double-Button-1>", lambda _e: do_load())

        btn_row = ttk.Frame(win)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Load", command=do_load, width=10).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Cancel", command=win.destroy, width=10).pack(side="left", padx=2)

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _delete_query(self) -> None:
        if not self._saved:
            messagebox.showinfo("Delete Query", "No saved queries.", parent=self)
            return
        win = tk.Toplevel(self)
        win.title("Delete Saved Query")
        win.resizable(False, False)
        win.transient(self)
        win.grab_set()

        lf = ttk.LabelFrame(win, text="Saved Queries")
        lf.pack(fill="both", expand=True, padx=8, pady=8)
        lb = tk.Listbox(lf, width=50, height=12, selectmode="single")
        lb.pack(side="left", fill="both", expand=True, padx=(4, 0), pady=4)
        sb = ttk.Scrollbar(lf, command=lb.yview)
        sb.pack(side="left", fill="y", pady=4)
        lb.configure(yscrollcommand=sb.set)
        names = sorted(self._saved)
        for n in names:
            lb.insert("end", n)

        def do_delete() -> None:
            sel = lb.curselection()
            if not sel:
                return
            chosen = names[sel[0]]
            if messagebox.askyesno("Confirm Delete", f"Delete '{chosen}'?", parent=win):
                del self._saved[chosen]
                _save_all(self._saved)
                win.destroy()
                self._status(f"Deleted '{chosen}'.")

        btn_row = ttk.Frame(win)
        btn_row.pack(fill="x", padx=8, pady=(0, 8))
        ttk.Button(btn_row, text="Delete", command=do_delete, width=10).pack(side="left", padx=2)
        ttk.Button(btn_row, text="Cancel", command=win.destroy, width=10).pack(side="left", padx=2)

        win.update_idletasks()
        w, h = win.winfo_reqwidth(), win.winfo_reqheight()
        x = self.winfo_x() + (self.winfo_width() - w) // 2
        y = self.winfo_y() + (self.winfo_height() - h) // 2
        win.geometry(f"{w}x{h}+{x}+{y}")

    def _copy_query(self) -> None:
        expr = self._query_var.get().strip()
        if expr:
            self.clipboard_clear()
            self.clipboard_append(expr)
            self._status("Expression copied to clipboard.")

    # ── Window sizing ─────────────────────────────────────────────────────────

    def _size_and_center(self) -> None:
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        w = int(sw * 0.90)
        h = int(sh * 0.90)
        x = max(0, (sw - w) // 2)
        y = max(0, (sh - h) // 2)
        self.geometry(f"{w}x{h}+{x}+{y}")


# ── Helper ────────────────────────────────────────────────────────────────────

def _result_count(result: Any) -> str:
    if result is None:
        return "null result"
    if isinstance(result, list):
        return f"{len(result)} items"
    if isinstance(result, dict):
        return f"object with {len(result)} keys"
    return f"scalar: {result!r}"
