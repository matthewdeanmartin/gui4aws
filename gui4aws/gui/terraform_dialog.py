"""TerraformDialog: stub — not yet implemented.

Placeholder so the service wiring exists before the full implementation.
The CDK launcher (cdk_dialog.py) serves as the reference pattern.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

__all__ = ["TerraformDialog"]


def size_and_center(win: tk.Toplevel) -> None:
    """Size the window to 90% of the screen and center it."""
    win.update_idletasks()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    w = int(sw * 0.90)
    h = int(sh * 0.90)
    x = max(0, (sw - w) // 2)
    y = max(0, (sh - h) // 2)
    win.geometry(f"{w}x{h}+{x}+{y}")


class TerraformDialog(tk.Toplevel):
    """Terraform launcher — not yet implemented.

    When implemented, this will follow the same pattern as CdkDialog:
      - Left sidebar: subcommand buttons (init / plan / apply / destroy / …)
      - Center: cwd picker + option form + output pane
      - Right: terraform <subcommand> --help
    """

    def __init__(self, parent: tk.Misc) -> None:
        super().__init__(parent)
        self.title("Terraform Launcher (not yet implemented)")
        self.resizable(True, True)
        self.transient(parent.winfo_toplevel())
        self.bind("<Escape>", lambda _e: self.destroy())

        size_and_center(self)

        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame,
            text="Terraform Launcher",
            font=("", 16, "bold"),
            anchor="center",
        ).pack(pady=(60, 8))

        ttk.Label(
            frame,
            text="Not yet implemented.\n\nThis dialog will support: init, validate, plan, apply, destroy, output, and more.\nSee cdk_dialog.py for the reference pattern.",
            font=("", 11),
            anchor="center",
            justify="center",
            foreground="gray",
        ).pack(pady=8)

        ttk.Button(frame, text="Close", command=self.destroy).pack(pady=24)
