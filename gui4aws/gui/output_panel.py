"""Output panel: history dropdown + copyable text area showing action results."""

# pylint: disable=too-many-ancestors

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from gui4aws.gui.json_viewer_dialog import JsonViewerDialog
from gui4aws.gui.jmespath_designer_dialog import JmespathDesignerDialog

__all__ = ["OutputPanel"]

_MAX_HISTORY = 20


class OutputPanel(ttk.LabelFrame):
    """Output panel with a recent-results dropdown and JSON viewer button.

    Each call to set_result() adds an entry to the history dropdown.
    The dropdown label is: "<action summary>  |  <cli command>".
    Selecting an entry updates the summary text and the active raw payload.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, text="Output", **kwargs)

        # ── History dropdown ─────────────────────────────────────────────────
        combo_frame = ttk.Frame(self)
        combo_frame.grid(row=0, column=0, columnspan=2, sticky="ew", padx=4, pady=(4, 0))
        combo_frame.grid_columnconfigure(1, weight=1)

        ttk.Label(combo_frame, text="Recent:").grid(row=0, column=0, padx=(0, 4))

        self._history_var = tk.StringVar()
        self._combo = ttk.Combobox(
            combo_frame,
            textvariable=self._history_var,
            state="readonly",
            postcommand=self._on_combo_open,
        )
        self._combo.grid(row=0, column=1, sticky="ew")
        self._combo.bind("<<ComboboxSelected>>", self._on_select)

        # ── Button bar ───────────────────────────────────────────────────────
        btn_bar = ttk.Frame(self)
        btn_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(2, 0))
        ttk.Button(btn_bar, text="Copy", command=self.copy_text).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="View raw JSON", command=self.open_json_viewer).pack(side="left", padx=2)
        ttk.Button(btn_bar, text="JMESPath Designer", command=self.open_jmespath_designer).pack(side="left", padx=2)

        # ── Summary text area ────────────────────────────────────────────────
        self.text = tk.Text(self, height=5, wrap="word", font=("Courier", 9))
        self.text.grid(row=2, column=0, sticky="nsew", padx=4, pady=4)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scroll.grid(row=2, column=1, sticky="ns", pady=4)
        self.text.configure(yscrollcommand=scroll.set)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ── Internal state ───────────────────────────────────────────────────
        # Each entry: (label, summary_text, raw_payload)
        self._history: list[tuple[str, str, Any]] = []
        self._active_index: int = -1

    # ── Public API ───────────────────────────────────────────────────────────

    def set_result(self, summary: str, raw_payload: Any, cli: str = "") -> None:
        """Add a result to history and display it. Skips blank nav-clear calls."""
        if not summary and raw_payload is None and not cli:
            return
        label = _make_label(summary, cli)
        entry = (label, summary, raw_payload)
        self._history.insert(0, entry)
        if len(self._history) > _MAX_HISTORY:
            self._history.pop()
        self._active_index = 0
        self._refresh_combo()
        self._render_active()

    def set_error(self, message: str) -> None:
        """Show an error — added to history without a raw payload."""
        self.set_result(message, None, cli="")

    def open_json_viewer(self) -> None:
        """Open the full-screen JSON tree viewer for the active result."""
        raw = self._active_raw()
        if raw is None:
            return
        JsonViewerDialog(self, raw, title="Raw JSON Viewer")

    def open_jmespath_designer(self) -> None:
        """Open the JMESPath Query Designer pre-loaded with the active result payload."""
        raw = self._active_raw()
        JmespathDesignerDialog(self, payload=raw, title="JMESPath Query Designer")

    def copy_text(self) -> None:
        """Copy the visible summary text to the clipboard."""
        content = self.text.get("1.0", "end").strip()
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _active_raw(self) -> Any:
        if 0 <= self._active_index < len(self._history):
            return self._history[self._active_index][2]
        return None

    def _refresh_combo(self) -> None:
        labels = [e[0] for e in self._history]
        self._combo["values"] = labels
        if self._history:
            self._combo.current(0)

    def _render_active(self) -> None:
        if 0 <= self._active_index < len(self._history):
            summary = self._history[self._active_index][1]
        else:
            summary = ""
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("1.0", summary)
        self.text.configure(state="disabled")

    def _on_select(self, _event: Any = None) -> None:
        idx = self._combo.current()
        if idx >= 0:
            self._active_index = idx
            self._render_active()

    def _on_combo_open(self) -> None:
        # Ensure the dropdown is wide enough to show full labels without truncation.
        if not self._history:
            return
        longest = max(len(e[0]) for e in self._history)
        # Rough char-width → pixel estimate; font is typically ~7px per char.
        needed = max(longest * 7, self._combo.winfo_width())
        self._combo.configure(width=needed // 7)


def _extract_aws_command(cli_script: str) -> str:
    """Pull the bare `aws ...` invocation out of a generated bash script.

    The script looks like:
        #!/usr/bin/env bash
        set -euo pipefail

        # List clusters
        aws ecs list-clusters \\
          --region us-east-1 \\
          --profile default

    We skip shebang / set / blank / comment lines, then join the `aws` lines
    (stripping continuation backslashes) into a single space-separated string.
    """
    aws_lines: list[str] = []
    in_aws = False
    for raw_line in cli_script.splitlines():
        line = raw_line.strip()
        if not in_aws:
            if line.startswith("aws "):
                in_aws = True
            else:
                continue  # skip shebang, set, blank, comment lines
        # Strip trailing backslash continuation marker.
        if line.endswith("\\"):
            line = line[:-1].rstrip()
        aws_lines.append(line)
        # A line without a trailing backslash ends the command.
        if not raw_line.rstrip().endswith("\\"):
            break
    return " ".join(" ".join(aws_lines).split())


def _make_label(summary: str, cli: str) -> str:
    """Build the dropdown label: summary  |  aws command."""
    summary_part = " ".join(summary.split())
    if not cli:
        return summary_part
    aws_cmd = _extract_aws_command(cli)
    if not aws_cmd:
        return summary_part
    # Keep the combined label under ~220 chars so the dropdown stays readable.
    max_cmd = max(40, 220 - len(summary_part) - 5)
    if len(aws_cmd) > max_cmd:
        aws_cmd = aws_cmd[:max_cmd] + "…"
    return f"{summary_part}  |  {aws_cmd}"
