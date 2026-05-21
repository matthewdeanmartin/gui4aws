"""Dynamic form built from list[InputField]."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Any

from gui4aws.models import ActionDefinition

__all__ = ["ActionForm"]


class ActionForm(ttk.Frame):
    """Renders an ActionDefinition's input_fields into entry widgets.

    ``prefill`` maps InputField.name → initial string value, overriding field defaults.
    This is used by ActionDialog when a row-action button supplies context from the
    selected resource.
    """

    def __init__(
        self,
        parent: tk.Misc,
        action: ActionDefinition,
        *,
        prefill: dict[str, str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.action = action
        self.variables: dict[str, tk.StringVar] = {}
        effective_prefill = prefill or {}

        ttk.Label(self, text=action.display_name, font=("TkDefaultFont", 10, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", padx=8, pady=(8, 4)
        )

        for row_index, field in enumerate(action.input_fields, start=1):
            ttk.Label(self, text=field.label + (" *" if field.required else "")).grid(
                row=row_index, column=0, sticky="w", padx=8, pady=2
            )
            initial = effective_prefill.get(field.name, field.default or "")
            var = tk.StringVar(value=initial)
            self.variables[field.name] = var
            if field.kind == "choice" and field.choices:
                widget: tk.Widget = ttk.Combobox(
                    self, textvariable=var, values=list(field.choices), state="readonly"
                )
            elif field.kind == "bool":
                widget = ttk.Combobox(self, textvariable=var, values=["true", "false"], state="readonly")
            elif field.kind == "multiline":
                widget = tk.Text(self, height=4, width=40)
            else:
                widget = ttk.Entry(self, textvariable=var, width=40)
            widget.grid(row=row_index, column=1, sticky="ew", padx=8, pady=2)
            if field.help_text:
                ttk.Label(self, text=field.help_text, foreground="gray").grid(
                    row=row_index, column=2, sticky="w", padx=8
                )

        self.grid_columnconfigure(1, weight=1)

    def values(self) -> dict[str, str]:
        """Snapshot of current input values."""
        return {name: var.get() for name, var in self.variables.items()}

    def validate(self) -> list[str]:
        """Return a list of human-readable validation errors (empty if valid)."""
        errors: list[str] = []
        values = self.values()
        for field in self.action.input_fields:
            if field.required and not values.get(field.name, "").strip():
                errors.append(f"{field.label} is required")
        return errors
