"""SQL Runner dialog: run queries against Aurora MySQL/PostgreSQL clusters."""

from __future__ import annotations

import contextlib
import csv
import io
import logging
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, messagebox, ttk
from typing import Any

from gui4aws.sql_runner.connection import (
    ConnectionInfo,
    execute_query,
    list_aws_secret_sources,
    list_keyring_sources,
    load_from_aws_secret,
    load_from_keyring,
)

__all__ = ["SqlRunnerDialog"]

logger = logging.getLogger(__name__)

_DEFAULT_LIMIT = 500


def _size_and_center(win: tk.Toplevel) -> None:
    win.update_idletasks()
    root = win.winfo_toplevel() if win.master is None else win.master.winfo_toplevel()
    rw, rh = root.winfo_width(), root.winfo_height()
    if rw < 100:
        rw = win.winfo_screenwidth()
    if rh < 100:
        rh = win.winfo_screenheight()
    w, h = int(rw * 0.82), int(rh * 0.82)
    x = max(0, (win.winfo_screenwidth() - w) // 2)
    y = max(0, (win.winfo_screenheight() - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


class _ResultTable(ttk.Frame):
    """Scrollable Treeview that shows query results."""

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(self, show="headings", selectmode="browse")
        self._vsb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._hsb = ttk.Scrollbar(self, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=self._vsb.set, xscrollcommand=self._hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._hsb.grid(row=1, column=0, sticky="ew")

        self._columns: list[str] = []
        self._rows: list[tuple[Any, ...]] = []

    def show(self, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
        self._columns = columns
        self._rows = rows
        self._tree.delete(*self._tree.get_children())
        self._tree["columns"] = columns
        for col in columns:
            self._tree.heading(col, text=col)
            self._tree.column(col, width=120, minwidth=60, stretch=True)
        for row in rows:
            self._tree.insert("", "end", values=[str(v) for v in row])

    def clear(self) -> None:
        self._columns = []
        self._rows = []
        self._tree["columns"] = ()
        self._tree.delete(*self._tree.get_children())

    def export_csv(self) -> None:
        if not self._columns:
            messagebox.showinfo("No results", "Run a query first.", parent=self)
            return
        path = filedialog.asksaveasfilename(
            parent=self,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Save query results",
        )
        if not path:
            return
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(self._columns)
        writer.writerows(self._rows)
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write(buf.getvalue())
        messagebox.showinfo("Saved", f"Results saved to:\n{path}", parent=self)


class SqlRunnerDialog(tk.Toplevel):
    """Query dialog for an Aurora cluster.

    The user picks a connection string from keyring or AWS Secrets Manager, writes
    SQL, and runs it.  Results appear in a scrollable table (max *limit* rows) or
    can be exported to CSV.

    Pass ``cluster_identifier`` and ``cluster_engine`` to pre-filter the source list.
    Pass ``boto3_session`` to also search AWS Secrets Manager.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        cluster_identifier: str = "",
        cluster_engine: str = "",
        boto3_session: Any = None,
    ) -> None:
        super().__init__(parent)
        self._cluster_id = cluster_identifier
        self._cluster_engine = cluster_engine
        self._boto3_session = boto3_session
        self._conn_info: ConnectionInfo | None = None
        self._running = False

        self.title(f"SQL Runner — {cluster_identifier}" if cluster_identifier else "SQL Runner")
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self.destroy)
        self.bind("<Escape>", lambda _e: self.destroy())

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Main vertical split: top = controls + query, bottom = results
        paned = ttk.PanedWindow(self, orient="vertical")
        paned.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 0))

        # ── Top pane ─────────────────────────────────────────────────────────
        top = ttk.Frame(paned)
        top.grid_columnconfigure(1, weight=1)
        paned.add(top, weight=1)

        # Source picker
        src_lf = ttk.LabelFrame(top, text="Connection source")
        src_lf.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 2))
        src_lf.grid_columnconfigure(1, weight=1)

        ttk.Label(src_lf, text="Source type:").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        self._source_type = tk.StringVar(value="keyring")
        rb_frame = ttk.Frame(src_lf)
        rb_frame.grid(row=0, column=1, sticky="w")
        ttk.Radiobutton(
            rb_frame, text="Keyring", variable=self._source_type, value="keyring", command=self._on_source_type_change
        ).pack(side="left", padx=4)
        ttk.Radiobutton(
            rb_frame,
            text="AWS Secrets Manager",
            variable=self._source_type,
            value="aws",
            command=self._on_source_type_change,
        ).pack(side="left", padx=4)

        ttk.Label(src_lf, text="Secret / key:").grid(row=1, column=0, sticky="w", padx=6, pady=2)
        self._source_var = tk.StringVar()
        self._source_combo = ttk.Combobox(src_lf, textvariable=self._source_var, state="readonly", width=55)
        self._source_combo.grid(row=1, column=1, sticky="ew", padx=6, pady=2)

        btn_row = ttk.Frame(src_lf)
        btn_row.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(0, 4))
        ttk.Button(btn_row, text="Refresh list", command=self._refresh_sources).pack(side="left", padx=4)
        ttk.Button(btn_row, text="Test connection", command=self._test_connection).pack(side="left", padx=4)
        self._conn_status = ttk.Label(btn_row, text="", foreground="gray")
        self._conn_status.pack(side="left", padx=8)

        # Query area
        q_lf = ttk.LabelFrame(top, text="SQL query")
        q_lf.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=4, pady=2)
        q_lf.grid_columnconfigure(0, weight=1)
        q_lf.grid_rowconfigure(0, weight=1)
        top.grid_rowconfigure(1, weight=1)

        self._query_text = tk.Text(q_lf, height=6, wrap="none", font=("Courier", 10))
        q_vsb = ttk.Scrollbar(q_lf, orient="vertical", command=self._query_text.yview)
        q_hsb = ttk.Scrollbar(q_lf, orient="horizontal", command=self._query_text.xview)
        self._query_text.configure(yscrollcommand=q_vsb.set, xscrollcommand=q_hsb.set)
        self._query_text.grid(row=0, column=0, sticky="nsew")
        q_vsb.grid(row=0, column=1, sticky="ns")
        q_hsb.grid(row=1, column=0, sticky="ew")
        self._query_text.insert("1.0", "SELECT 1")

        # Options / run bar
        opt_bar = ttk.Frame(top)
        opt_bar.grid(row=2, column=0, columnspan=2, sticky="ew", padx=4, pady=4)

        ttk.Label(opt_bar, text="Row limit:").pack(side="left", padx=(4, 2))
        self._limit_var = tk.StringVar(value=str(_DEFAULT_LIMIT))
        ttk.Spinbox(opt_bar, textvariable=self._limit_var, from_=1, to=50000, width=7).pack(side="left", padx=(0, 12))

        self._run_btn = ttk.Button(opt_bar, text="Run query  [Ctrl+Enter]", command=self._run_query)
        self._run_btn.pack(side="left", padx=4)
        self.bind("<Control-Return>", lambda _e: self._run_query())

        ttk.Button(opt_bar, text="Clear", command=self._clear_query).pack(side="left", padx=4)
        ttk.Button(opt_bar, text="Export CSV", command=lambda: self._result_table.export_csv()).pack(
            side="right", padx=4
        )
        ttk.Button(opt_bar, text="Close", command=self.destroy).pack(side="right", padx=4)

        # Status label
        self._status_var = tk.StringVar(value="Pick a connection source, then run a query.")
        ttk.Label(opt_bar, textvariable=self._status_var, foreground="gray").pack(side="left", padx=8)

        # ── Bottom pane: results ──────────────────────────────────────────────
        results_lf = ttk.LabelFrame(paned, text="Results")
        results_lf.grid_columnconfigure(0, weight=1)
        results_lf.grid_rowconfigure(0, weight=1)
        paned.add(results_lf, weight=3)

        self._result_table = _ResultTable(results_lf)
        self._result_table.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)

        _size_and_center(self)
        # Kick off initial source list population
        self.after(100, self._refresh_sources)

    # ── Source picker ─────────────────────────────────────────────────────────

    def _on_source_type_change(self) -> None:
        self._refresh_sources()

    def _refresh_sources(self) -> None:
        self._conn_status.configure(text="Scanning…", foreground="gray")
        self.update_idletasks()

        source_type = self._source_type.get()
        if source_type == "keyring":
            names = list_keyring_sources()
        else:
            if self._boto3_session is None:
                self._conn_status.configure(text="No AWS session available.", foreground="red")
                self._source_combo["values"] = []
                return
            names = list_aws_secret_sources(self._boto3_session)

        if not names:
            self._conn_status.configure(text="No matching secrets found.", foreground="gray")
            self._source_combo["values"] = []
            self._source_var.set("")
            return

        self._source_combo["values"] = names
        # Preselect if cluster_identifier appears in a name
        best = next(
            (n for n in names if self._cluster_id and self._cluster_id in n),
            names[0],
        )
        self._source_var.set(best)
        count = len(names)
        self._conn_status.configure(
            text=f"{count} source{'s' if count != 1 else ''} found.",
            foreground="gray",
        )

    def _load_connection(self) -> ConnectionInfo | None:
        source_type = self._source_type.get()
        key = self._source_var.get().strip()
        if not key:
            messagebox.showwarning("No source", "Select a connection source first.", parent=self)
            return None
        if source_type == "keyring":
            info = load_from_keyring(key)
        else:
            if self._boto3_session is None:
                messagebox.showerror("No session", "AWS session not available.", parent=self)
                return None
            info = load_from_aws_secret(self._boto3_session, key)
        if info is None:
            messagebox.showerror("Load failed", f"Could not load connection info from:\n{key}", parent=self)
        return info

    def _test_connection(self) -> None:
        info = self._load_connection()
        if info is None:
            return
        self._conn_status.configure(text="Connecting…", foreground="gray")
        self.update_idletasks()
        try:
            execute_query(info, "SELECT 1", limit=1)
            self._conn_info = info
            self._conn_status.configure(text=f"Connected to {info.host} ({info.engine})", foreground="green")
        except ImportError as exc:
            self._conn_status.configure(text="Driver missing", foreground="red")
            messagebox.showerror("Driver not installed", str(exc), parent=self)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            self._conn_status.configure(text="Connection failed", foreground="red")
            messagebox.showerror("Connection failed", str(exc), parent=self)

    # ── Query execution ───────────────────────────────────────────────────────

    def _clear_query(self) -> None:
        self._query_text.delete("1.0", "end")
        self._result_table.clear()
        self._status_var.set("Query cleared.")

    def _run_query(self) -> None:
        if self._running:
            return
        sql = self._query_text.get("1.0", "end").strip()
        if not sql:
            self._status_var.set("Enter a SQL query first.")
            return

        # Load connection if not already tested
        if self._conn_info is None:
            info = self._load_connection()
            if info is None:
                return
            self._conn_info = info

        try:
            limit = int(self._limit_var.get())
        except ValueError:
            limit = _DEFAULT_LIMIT

        self._running = True
        self._run_btn.configure(state="disabled")
        self._status_var.set("Running…")
        self._result_table.clear()
        self.update_idletasks()

        captured_info = self._conn_info
        captured_sql = sql
        captured_limit = limit

        def marshal(callback: Callable[[], None]) -> None:
            # The dialog may be destroyed mid-query; marshalling back to a dead Tk root
            # raises TclError/RuntimeError. Swallow it so the daemon thread exits cleanly.
            with contextlib.suppress(tk.TclError, RuntimeError):
                self.after(0, callback)

        def worker() -> None:
            try:
                cols, rows = execute_query(captured_info, captured_sql, captured_limit)
                marshal(lambda: self._on_success(cols, rows, captured_limit))
            except ImportError as exc:
                msg = str(exc)
                marshal(lambda: self._on_driver_error(msg))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                msg = str(exc)
                marshal(lambda: self._on_error(msg))

        threading.Thread(target=worker, daemon=True).start()

    def _on_success(self, columns: list[str], rows: list[tuple[Any, ...]], limit: int) -> None:
        self._running = False
        self._run_btn.configure(state="normal")
        self._result_table.show(columns, rows)
        truncated = len(rows) >= limit
        suffix = f"  (limited to {limit} rows — export or increase limit to see more)" if truncated else ""
        self._status_var.set(f"{len(rows)} row{'s' if len(rows) != 1 else ''} returned.{suffix}")

    def _on_error(self, message: str) -> None:
        self._running = False
        self._run_btn.configure(state="normal")
        self._status_var.set("Query failed.")
        messagebox.showerror("Query error", message, parent=self)

    def _on_driver_error(self, message: str) -> None:
        self._running = False
        self._run_btn.configure(state="normal")
        self._status_var.set("Driver not installed.")
        messagebox.showerror("Driver not installed", message, parent=self)


def open_sql_runner(
    parent: tk.Misc,
    *,
    cluster_identifier: str = "",
    cluster_engine: str = "",
    boto3_session: Any = None,
) -> SqlRunnerDialog:
    """Create and return a SqlRunnerDialog (non-blocking)."""
    return SqlRunnerDialog(
        parent,
        cluster_identifier=cluster_identifier,
        cluster_engine=cluster_engine,
        boto3_session=boto3_session,
    )
