"""ActionDialog: single popup covering form, live scripts, and result output."""

from __future__ import annotations

import json
import logging
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from gui4aws.gui.action_form import ActionForm
from gui4aws.gui.review_dialog import needs_review, warning_banner
from gui4aws.models import ActionDefinition

__all__ = ["ActionDialog"]

logger = logging.getLogger(__name__)


def _size_and_center(win: tk.Toplevel) -> None:
    """Size the dialog to 80% of its parent root window and center it on screen."""
    win.update_idletasks()
    root = win.winfo_toplevel() if win.master is None else win.master.winfo_toplevel()
    rw = root.winfo_width()
    rh = root.winfo_height()
    if rw < 100:
        rw = win.winfo_screenwidth()
    if rh < 100:
        rh = win.winfo_screenheight()
    w = int(rw * 0.80)
    h = int(rh * 0.80)
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


class ActionDialog(tk.Toplevel):
    """Single-popup dialog: form → live script preview → result panel.

    Layout uses a vertical PanedWindow so the result panel grows with the window:
      Top pane  — scrollable form + scripts
      Bottom pane — result text (grows to fill remaining space)

    Keyboard shortcuts:
      Enter  — Run (when form is focused)
      Escape — Cancel / close
    """

    def __init__(
        self,
        parent: tk.Misc,
        action: ActionDefinition,
        *,
        prefill: dict[str, str] | None = None,
        on_run: Callable[[ActionDefinition, dict[str, str]], None] | None = None,
        on_generate_scripts: Callable[[ActionDefinition, dict[str, str]], tuple[str, str]] | None = None,
    ) -> None:
        super().__init__(parent)
        self.action = action
        self.on_run = on_run
        self._on_generate_scripts = on_generate_scripts
        self._running = False

        self.title(action.display_name)
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.bind("<Escape>", lambda _e: self._on_cancel())

        # Root grid: paned area grows, then status bar and button bar are fixed.
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ── Vertical PanedWindow: top=form+scripts, bottom=result ─────────────
        paned = ttk.PanedWindow(self, orient="vertical")
        paned.grid(row=0, column=0, sticky="nsew", padx=4, pady=(4, 0))

        # ── Top pane: scrollable form area ────────────────────────────────────
        top_canvas_frame = ttk.Frame(paned)
        top_canvas_frame.grid_columnconfigure(0, weight=1)
        top_canvas_frame.grid_rowconfigure(0, weight=1)

        canvas = tk.Canvas(top_canvas_frame, highlightthickness=0, borderwidth=0)
        canvas.grid(row=0, column=0, sticky="nsew")
        top_scroll = ttk.Scrollbar(top_canvas_frame, orient="vertical", command=canvas.yview)
        top_scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(yscrollcommand=top_scroll.set)

        form_container = ttk.Frame(canvas)
        form_container.grid_columnconfigure(0, weight=1)
        _win_id = canvas.create_window((0, 0), window=form_container, anchor="nw")

        def _sync_scroll(_e: Any) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _stretch(_e: Any) -> None:
            canvas.itemconfigure(_win_id, width=_e.width)

        form_container.bind("<Configure>", _sync_scroll)
        canvas.bind("<Configure>", _stretch)

        paned.add(top_canvas_frame, weight=1)

        form_row = 0

        # Risk banner
        banner = warning_banner(action)
        if banner:
            ttk.Label(
                form_container,
                text=banner,
                foreground="#a04000",
                wraplength=680,
                justify="left",
            ).grid(row=form_row, column=0, sticky="ew", padx=12, pady=(8, 0))
            form_row += 1

        # Form
        self.form = ActionForm(form_container, action, prefill=prefill, on_change=self._refresh_scripts)
        self.form.grid(row=form_row, column=0, sticky="nsew", padx=8, pady=4)
        form_row += 1

        # Description
        if action.description:
            ttk.Label(
                form_container,
                text=action.description,
                wraplength=680,
                foreground="gray",
                justify="left",
            ).grid(row=form_row, column=0, sticky="ew", padx=12, pady=(0, 4))
            form_row += 1

        # Live script preview (for non-read-only actions)
        self._cli_text: tk.Text | None = None
        self._python_text: tk.Text | None = None
        if needs_review(action):
            script_frame = ttk.LabelFrame(form_container, text="Generated scripts")
            script_frame.grid(row=form_row, column=0, sticky="nsew", padx=8, pady=4)
            script_frame.grid_columnconfigure(0, weight=1)
            script_frame.grid_columnconfigure(1, weight=1)
            form_container.grid_rowconfigure(form_row, weight=1)

            cli_lf = ttk.LabelFrame(script_frame, text="AWS CLI")
            cli_lf.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
            cli_lf.grid_columnconfigure(0, weight=1)
            cli_lf.grid_rowconfigure(0, weight=1)
            self._cli_text = tk.Text(cli_lf, height=8, width=48, wrap="none", font=("Courier", 9))
            self._cli_text.configure(state="disabled")
            cli_scroll = ttk.Scrollbar(cli_lf, orient="vertical", command=self._cli_text.yview)
            self._cli_text.configure(yscrollcommand=cli_scroll.set)
            self._cli_text.grid(row=0, column=0, sticky="nsew")
            cli_scroll.grid(row=0, column=1, sticky="ns")

            py_lf = ttk.LabelFrame(script_frame, text="Python (boto3)")
            py_lf.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
            py_lf.grid_columnconfigure(0, weight=1)
            py_lf.grid_rowconfigure(0, weight=1)
            self._python_text = tk.Text(py_lf, height=8, width=48, wrap="none", font=("Courier", 9))
            self._python_text.configure(state="disabled")
            py_scroll = ttk.Scrollbar(py_lf, orient="vertical", command=self._python_text.yview)
            self._python_text.configure(yscrollcommand=py_scroll.set)
            self._python_text.grid(row=0, column=0, sticky="nsew")
            py_scroll.grid(row=0, column=1, sticky="ns")

            copy_bar = ttk.Frame(script_frame)
            copy_bar.grid(row=1, column=0, columnspan=2, sticky="e", padx=4, pady=2)
            ttk.Button(copy_bar, text="Copy CLI", command=self._copy_cli).grid(row=0, column=0, padx=2)
            ttk.Button(copy_bar, text="Copy Python", command=self._copy_python).grid(row=0, column=1, padx=2)

            form_row += 1
            self._refresh_scripts()

        # ── Bottom pane: result — fills remaining dialog height ───────────────
        result_lf = ttk.LabelFrame(paned, text="Result")
        result_lf.grid_columnconfigure(0, weight=1)
        result_lf.grid_rowconfigure(0, weight=1)

        self.result_text = tk.Text(result_lf, wrap="word", font=("Courier", 9))
        self.result_text.configure(state="disabled")
        result_scroll = ttk.Scrollbar(result_lf, orient="vertical", command=self.result_text.yview)
        result_hscroll = ttk.Scrollbar(result_lf, orient="horizontal", command=self.result_text.xview)
        self.result_text.configure(yscrollcommand=result_scroll.set, xscrollcommand=result_hscroll.set)
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scroll.grid(row=0, column=1, sticky="ns")
        result_hscroll.grid(row=1, column=0, sticky="ew")

        paned.add(result_lf, weight=2)

        # ── Status label ──────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Fill in the form and click Run.")
        ttk.Label(self, textvariable=self.status_var, foreground="gray").grid(
            row=1, column=0, sticky="w", padx=12, pady=(4, 2)
        )

        # ── Button bar ────────────────────────────────────────────────────────
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=2, column=0, sticky="e", padx=8, pady=8)

        self._cancel_btn = ttk.Button(btn_frame, text="Cancel  [Esc]", command=self._on_cancel)
        self._cancel_btn.grid(row=0, column=0, padx=4)

        verb = "Run" if not needs_review(action) else "Review & Run"
        self._run_btn = ttk.Button(btn_frame, text=f"{verb}  [Enter]", command=self._on_run)
        self._run_btn.grid(row=0, column=1, padx=4)
        self.bind("<Return>", lambda _e: self._on_run())

        self._close_btn = ttk.Button(btn_frame, text="Close", command=self.destroy, state="disabled")
        self._close_btn.grid(row=0, column=2, padx=4)

        _size_and_center(self)

    # ── Script helpers ───────────────────────────────────────────────────────

    def _refresh_scripts(self) -> None:
        if self._on_generate_scripts is None or self._cli_text is None:
            return
        try:
            cli, python = self._on_generate_scripts(self.action, self.form.values())
        except Exception:
            return
        self._set_text(self._cli_text, cli)
        if self._python_text is not None:
            self._set_text(self._python_text, python)

    @staticmethod
    def _set_text(widget: tk.Text, content: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", content)
        widget.configure(state="disabled")

    def _copy_cli(self) -> None:
        if self._cli_text is not None:
            self.clipboard_clear()
            self.clipboard_append(self._cli_text.get("1.0", "end").strip())

    def _copy_python(self) -> None:
        if self._python_text is not None:
            self.clipboard_clear()
            self.clipboard_append(self._python_text.get("1.0", "end").strip())

    # ── Button actions ───────────────────────────────────────────────────────

    def _on_run(self) -> None:
        if self._running:
            return
        errors = self.form.validate()
        if errors:
            self.status_var.set("Required: " + "; ".join(errors))
            return
        self._running = True
        self._run_btn.configure(state="disabled")
        self.status_var.set("Running…")
        self._set_result_text("(waiting for result…)")
        if self.on_run is not None:
            self.on_run(self.action, self.form.values())

    def _on_cancel(self) -> None:
        self.destroy()

    # ── External API (called by MainWindow) ──────────────────────────────────

    def set_status(self, text: str) -> None:
        """Update the status label and enable the Close button once done."""
        self.status_var.set(text)
        if self._running:
            self._running = False
            self._run_btn.configure(state="normal")
            self._close_btn.configure(state="normal")

    def set_result(self, raw: Any) -> None:
        """Display raw result data in the result panel."""
        try:
            text = json.dumps(raw, indent=2, default=str)
        except TypeError:
            text = repr(raw)
        self._set_result_text(text)

    def _set_result_text(self, text: str) -> None:
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")
