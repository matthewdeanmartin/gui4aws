"""Script Editor panel: accumulates bash CLI script from user actions."""

from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import filedialog, ttk
from typing import Any

from gui4aws.models import ActionDefinition, RiskLevel

__all__ = ["ScriptEditorPanel"]


@dataclass
class ScriptEntry:
    """One recorded action entry in the script editor history."""

    action_id: str
    display_name: str
    risk_level: RiskLevel
    cli_script: str


class ScriptEditorPanel(ttk.Frame):  # pylint: disable=too-many-ancestors
    """IDE-like panel that accumulates CLI bash script from user actions.

    Left sidebar: checkboxes controlling which risk-level actions to include.
    Right area: read-only monospace view of the accumulated script.
    Bottom bar: Copy All, Save..., Clear History.

    Read-Only (list/describe) actions are excluded by default because 90 % of
    API calls are just populating the GUI; the user probably only wants the
    writes in a saved script.
    """

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self._entries: list[ScriptEntry] = []

        # ── Left sidebar ──────────────────────────────────────────────────────
        sidebar = ttk.Frame(self, width=190)
        sidebar.grid(row=0, column=0, sticky="nsw", padx=(4, 0), pady=4)
        sidebar.grid_propagate(False)

        ttk.Label(sidebar, text="Include in script:", font=("", 9, "bold")).pack(anchor="w", padx=8, pady=(10, 4))

        self._include_vars: dict[RiskLevel, tk.BooleanVar] = {}
        _level_labels = [
            (RiskLevel.READ_ONLY, "Read-Only (lists)", False),
            (RiskLevel.SAFE_WRITE, "Safe Writes", True),
            (RiskLevel.COST_AFFECTING, "Cost-Affecting", True),
            (RiskLevel.DESTRUCTIVE, "Destructive", True),
        ]
        for level, label, default in _level_labels:
            var = tk.BooleanVar(value=default)
            self._include_vars[level] = var
            ttk.Checkbutton(
                sidebar,
                text=label,
                variable=var,
                command=self._rebuild_script,
            ).pack(anchor="w", padx=12, pady=2)

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=8, pady=8)

        self._count_label = ttk.Label(sidebar, text="0 / 0 actions", foreground="gray")
        self._count_label.pack(anchor="w", padx=10)

        ttk.Separator(sidebar, orient="horizontal").pack(fill="x", padx=8, pady=8)

        ttk.Button(sidebar, text="Select All", command=self._select_all).pack(fill="x", padx=8, pady=2)
        ttk.Button(sidebar, text="Deselect All", command=self._deselect_all).pack(fill="x", padx=8, pady=2)

        # ── Right script area ─────────────────────────────────────────────────
        right = ttk.Frame(self)
        right.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(0, weight=1)

        self._text = tk.Text(
            right,
            wrap="none",
            font=("Courier", 10),
            bg="#1e1e1e",
            fg="#d4d4d4",
            insertbackground="white",
            state="disabled",
        )
        v_scroll = ttk.Scrollbar(right, orient="vertical", command=self._text.yview)
        h_scroll = ttk.Scrollbar(right, orient="horizontal", command=self._text.xview)
        self._text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        self._text.grid(row=0, column=0, sticky="nsew")
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll.grid(row=1, column=0, sticky="ew")

        # ── Bottom button bar ─────────────────────────────────────────────────
        btn_bar = ttk.Frame(self)
        btn_bar.grid(row=1, column=0, columnspan=2, sticky="ew", padx=4, pady=(0, 4))
        ttk.Button(btn_bar, text="Copy All", command=self._copy_all).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Save...", command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_bar, text="Clear History", command=self._clear).pack(side="left", padx=4)

        self._rebuild_script()

    def append_action(self, action: ActionDefinition, cli_script: str) -> None:
        """Add an action to the history and rebuild the displayed script."""
        self._entries.append(
            ScriptEntry(
                action_id=action.action_id,
                display_name=action.display_name,
                risk_level=action.risk_level,
                cli_script=cli_script,
            )
        )
        self._rebuild_script()

    def get_script(self) -> str:
        """Return the current script text as shown."""
        return self._text.get("1.0", "end")

    # ── Internal ─────────────────────────────────────────────────────────────

    def _rebuild_script(self) -> None:
        included = [e for e in self._entries if self._include_vars[e.risk_level].get()]
        lines: list[str] = [
            "#!/usr/bin/env bash",
            "set -euo pipefail",
            "",
            "# Generated by gui4aws",
            "",
        ]
        for entry in included:
            body = _strip_script_header(entry.cli_script).strip()
            if body:
                lines.append(f"# {entry.display_name}")
                lines.append(body)
                lines.append("")

        content = "\n".join(lines)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
        self._text.configure(state="disabled")
        self._count_label.configure(text=f"{len(included)} / {len(self._entries)} actions")

    def _copy_all(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.get_script())

    def _save(self) -> None:
        path = filedialog.asksaveasfilename(
            defaultextension=".sh",
            filetypes=[("Bash script", "*.sh"), ("All files", "*.*")],
            title="Save script",
        )
        if not path:
            return
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(self.get_script())

    def _clear(self) -> None:
        self._entries.clear()
        self._rebuild_script()

    def _select_all(self) -> None:
        for var in self._include_vars.values():
            var.set(True)
        self._rebuild_script()

    def _deselect_all(self) -> None:
        for var in self._include_vars.values():
            var.set(False)
        self._rebuild_script()


def _strip_script_header(script: str) -> str:
    """Remove the shebang / set -euo pipefail header so scripts can be concatenated."""
    lines = script.splitlines()
    out: list[str] = []
    skip_blank = False
    for line in lines:
        if line.startswith("#!/") or line.strip() == "set -euo pipefail":
            skip_blank = True
            continue
        if skip_blank and line.strip() == "":
            skip_blank = False
            continue
        skip_blank = False
        out.append(line)
    return "\n".join(out)
