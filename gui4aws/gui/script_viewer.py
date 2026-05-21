"""Read-only viewer for generated CLI/Python scripts."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

__all__ = ["ScriptViewer"]


class ScriptViewer(ttk.Frame):
    """Two side-by-side text widgets: CLI on the left, Python on the right."""

    def __init__(self, parent: tk.Misc, **kwargs: Any) -> None:
        super().__init__(parent, **kwargs)

        cli_frame = ttk.LabelFrame(self, text="AWS CLI")
        cli_frame.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self.cli_text = tk.Text(cli_frame, wrap="none", height=14, width=60)
        self.cli_text.grid(row=0, column=0, sticky="nsew")
        ttk.Button(cli_frame, text="Copy", command=self.copy_cli).grid(row=1, column=0, sticky="e", padx=4, pady=2)
        cli_frame.grid_rowconfigure(0, weight=1)
        cli_frame.grid_columnconfigure(0, weight=1)

        python_frame = ttk.LabelFrame(self, text="Python (boto3)")
        python_frame.grid(row=0, column=1, sticky="nsew", padx=4, pady=4)
        self.python_text = tk.Text(python_frame, wrap="none", height=14, width=60)
        self.python_text.grid(row=0, column=0, sticky="nsew")
        ttk.Button(python_frame, text="Copy", command=self.copy_python).grid(row=1, column=0, sticky="e", padx=4, pady=2)
        python_frame.grid_rowconfigure(0, weight=1)
        python_frame.grid_columnconfigure(0, weight=1)

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

    def set_scripts(self, cli: str, python: str) -> None:
        """Replace the displayed CLI and Python scripts."""
        self.cli_text.delete("1.0", "end")
        self.cli_text.insert("1.0", cli)
        self.python_text.delete("1.0", "end")
        self.python_text.insert("1.0", python)

    def copy_cli(self) -> None:
        """Copy the CLI script to the system clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self.cli_text.get("1.0", "end-1c"))

    def copy_python(self) -> None:
        """Copy the Python script to the system clipboard."""
        self.clipboard_clear()
        self.clipboard_append(self.python_text.get("1.0", "end-1c"))
