"""Typed-text confirmation dialog for destructive actions.

Used in phase 6, built now so the matching logic can be unit-tested. The user must type the
exact ``expected_text`` (case-sensitive, whitespace-trimmed) before the Confirm button enables.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable
from dataclasses import dataclass, field
from tkinter import ttk

__all__ = ["TypedConfirmation", "TypedConfirmationDialog", "matches"]


def matches(expected: str, typed: str) -> bool:
    """Whitespace-trimmed, case-sensitive equality."""
    return expected.strip() == typed.strip() and bool(expected.strip())


@dataclass
class TypedConfirmation:
    """Headless state for a typed-confirmation dialog.

    Attributes:
        expected_text: The string the user must type (e.g. the cluster identifier).
        typed_text: What the user has typed so far.
        confirmed: True once :meth:`confirm` is called while the typed text matches.
        cancelled: True if the user cancels.
    """

    expected_text: str
    typed_text: str = ""
    confirmed: bool = field(default=False)
    cancelled: bool = field(default=False)

    def set_typed(self, value: str) -> None:
        """Record the user's current typed input."""
        if self.is_resolved():
            return
        self.typed_text = value

    def can_confirm(self) -> bool:
        """True iff the typed text matches the expected text exactly."""
        return matches(self.expected_text, self.typed_text)

    def confirm(self) -> bool:
        """Confirm if and only if ``can_confirm``. Returns the new ``confirmed`` value."""
        if self.is_resolved():
            return self.confirmed
        if self.can_confirm():
            self.confirmed = True
        return self.confirmed

    def cancel(self) -> None:
        """Mark the dialog as cancelled."""
        if self.confirmed:
            return
        self.cancelled = True

    def is_resolved(self) -> bool:
        """True once the user has either confirmed or cancelled."""
        return self.confirmed or self.cancelled


class TypedConfirmationDialog:
    """A Toplevel dialog that wraps :class:`TypedConfirmation`."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        title: str,
        prompt: str,
        expected_text: str,
        on_resolved: Callable[[TypedConfirmation], None] | None = None,
    ) -> None:
        self.confirmation = TypedConfirmation(expected_text=expected_text)
        self.on_resolved = on_resolved

        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.transient(parent.winfo_toplevel())
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        ttk.Label(self.window, text=prompt, wraplength=520).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(12, 4)
        )
        ttk.Label(self.window, text=f"Type to confirm:  {expected_text}", foreground="#a04000").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 4)
        )

        self.text_var = tk.StringVar(value="")
        entry = ttk.Entry(self.window, textvariable=self.text_var, width=40)
        entry.grid(row=2, column=0, columnspan=2, sticky="ew", padx=12, pady=4)
        self.text_var.trace_add("write", self.on_text_changed)

        button_frame = ttk.Frame(self.window)
        button_frame.grid(row=3, column=0, columnspan=2, sticky="e", padx=12, pady=12)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).grid(row=0, column=0, padx=4)
        self.confirm_button = ttk.Button(
            button_frame, text="Confirm", command=self.confirm, state="disabled"
        )
        self.confirm_button.grid(row=0, column=1, padx=4)

        self.window.grid_columnconfigure(0, weight=1)

    def on_text_changed(self, *_args: object) -> None:
        """Update internal state and button enable/disable on every keystroke."""
        self.confirmation.set_typed(self.text_var.get())
        new_state = "normal" if self.confirmation.can_confirm() else "disabled"
        self.confirm_button.configure(state=new_state)

    def confirm(self) -> None:
        """Handle the Confirm button click."""
        self.confirmation.confirm()
        self.resolve()

    def cancel(self) -> None:
        """Handle Cancel / window close."""
        self.confirmation.cancel()
        self.resolve()

    def resolve(self) -> None:
        """Notify the caller and destroy the window."""
        if self.on_resolved is not None:
            self.on_resolved(self.confirmation)
        with contextlib.suppress(tk.TclError):
            self.window.destroy()

    def show_modal(self) -> TypedConfirmation:
        """Block until the user resolves the dialog."""
        self.window.grab_set()
        self.window.wait_window()
        return self.confirmation
