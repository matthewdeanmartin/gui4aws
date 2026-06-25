"""Review dialog for safe_write / cost_affecting actions.

The dialog shows the generated AWS CLI + Python and asks for explicit confirmation. For
cost-affecting actions, a warning banner is shown above the scripts.

The decision logic lives in :class:`ReviewDecision` so it can be unit-tested without spinning
up a Tk root. The widget class wraps that logic in a ``Toplevel``.
"""

from __future__ import annotations

import contextlib
import tkinter as tk
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from tkinter import ttk
from typing import Any

from gui4aws.models import ActionDefinition, RiskLevel

__all__ = [
    "ReviewDecision",
    "ReviewDialog",
    "confirmation_text_for",
    "needs_review",
    "needs_typed_confirmation",
    "warning_banner",
]


def needs_review(action: ActionDefinition) -> bool:
    """Return True if the action requires a review screen before executing.

    READ_ONLY actions skip review (the GUI runs them inline on sidebar selection). All other
    risk levels require the user to read the generated script first.
    """
    return action.risk_level is not RiskLevel.READ_ONLY


def needs_typed_confirmation(action: ActionDefinition) -> bool:
    """Return True if the action requires the user to type a confirmation token.

    Only DESTRUCTIVE actions (deletes/terminates) demand typed confirmation; lighter writes
    are gated by the review screen alone.
    """
    return action.risk_level is RiskLevel.DESTRUCTIVE


def confirmation_text_for(action: ActionDefinition, inputs: Mapping[str, str]) -> str:
    """Pick the token the user must type to confirm a destructive action.

    Uses the value of the first required input field (the resource identifier in every
    destructive action — e.g. the cluster/instance/key name). Falls back to the action's
    display name when no required field has a value, so the gate can never be bypassed by
    matching an empty string.
    """
    for field in action.input_fields:
        if field.required:
            value = str(inputs.get(field.name, "")).strip()
            if value:
                return value
    return action.display_name


def warning_banner(action: ActionDefinition) -> str | None:
    """Return the warning message for the dialog header, or None."""
    if action.risk_level is RiskLevel.COST_AFFECTING:
        return "This action may create billable resources. Review the generated script before " "confirming."
    if action.risk_level is RiskLevel.DESTRUCTIVE:
        return "This action is destructive. Type the exact confirmation text to proceed."
    return None


@dataclass
class ReviewDecision:
    """Headless decision state for a review dialog.

    Attributes:
        action: The action being reviewed.
        confirmed: True once the user clicks Confirm.
        cancelled: True if the user closes / cancels the dialog.
    """

    action: ActionDefinition
    confirmed: bool = False
    cancelled: bool = False

    def confirm(self) -> None:
        """Mark the dialog as confirmed."""
        if self.cancelled:
            return
        self.confirmed = True

    def cancel(self) -> None:
        """Mark the dialog as cancelled."""
        if self.confirmed:
            return
        self.cancelled = True

    def is_resolved(self) -> bool:
        """True once the user has either confirmed or cancelled."""
        return self.confirmed or self.cancelled


class ReviewDialog:
    """A Toplevel dialog that wraps :class:`ReviewDecision`.

    Usage:
        decision = ReviewDialog(parent, action, cli_text, python_text).show_modal()
        if decision.confirmed: ...
    """

    def __init__(
        self,
        parent: tk.Misc,
        action: ActionDefinition,
        cli_text: str,
        python_text: str,
        *,
        on_resolved: Callable[[ReviewDecision], None] | None = None,
    ) -> None:
        self.action = action
        self.decision = ReviewDecision(action=action)
        self.on_resolved = on_resolved

        self.window = tk.Toplevel(parent)
        self.window.title(f"Review — {action.display_name}")
        self.window.transient(parent.winfo_toplevel())
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        ttk.Label(
            self.window,
            text=f"{action.display_name}  ({action.risk_level.value})",
            font=("TkDefaultFont", 11, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4))

        banner = warning_banner(action)
        if banner:
            ttk.Label(self.window, text=banner, foreground="#a04000", wraplength=720).grid(
                row=1, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 4)
            )

        if action.description:
            ttk.Label(self.window, text=action.description, wraplength=720).grid(
                row=2, column=0, columnspan=2, sticky="w", padx=8, pady=(0, 8)
            )

        cli_frame = ttk.LabelFrame(self.window, text="AWS CLI")
        cli_frame.grid(row=3, column=0, sticky="nsew", padx=8, pady=4)
        cli_text_widget = tk.Text(cli_frame, height=10, width=60, wrap="none")
        cli_text_widget.insert("1.0", cli_text)
        cli_text_widget.configure(state="disabled")
        cli_text_widget.grid(row=0, column=0, sticky="nsew")

        python_frame = ttk.LabelFrame(self.window, text="Python (boto3)")
        python_frame.grid(row=3, column=1, sticky="nsew", padx=8, pady=4)
        python_text_widget = tk.Text(python_frame, height=10, width=60, wrap="none")
        python_text_widget.insert("1.0", python_text)
        python_text_widget.configure(state="disabled")
        python_text_widget.grid(row=0, column=0, sticky="nsew")

        button_frame = ttk.Frame(self.window)
        button_frame.grid(row=4, column=0, columnspan=2, sticky="e", padx=8, pady=8)
        ttk.Button(button_frame, text="Cancel", command=self.cancel).grid(row=0, column=0, padx=4)
        ttk.Button(button_frame, text="Confirm", command=self.confirm).grid(row=0, column=1, padx=4)

        self.window.grid_columnconfigure(0, weight=1)
        self.window.grid_columnconfigure(1, weight=1)
        self.window.grid_rowconfigure(3, weight=1)

    def confirm(self) -> None:
        """Handle the Confirm button."""
        self.decision.confirm()
        self.resolve()

    def cancel(self) -> None:
        """Handle the Cancel button (or window close)."""
        self.decision.cancel()
        self.resolve()

    def resolve(self) -> None:
        """Notify the caller and destroy the window."""
        if self.on_resolved is not None:
            self.on_resolved(self.decision)
        with contextlib.suppress(tk.TclError):
            self.window.destroy()

    def show_modal(self) -> ReviewDecision:
        """Block until the user resolves the dialog."""
        self.window.grab_set()
        self.window.wait_window()
        return self.decision

    def ignored_widget_state(self) -> Any:  # pragma: no cover - placeholder for future tests
        """Reserved for future tests that need to introspect Tk state."""
        return None
