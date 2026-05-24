"""Filter bar shown above the resource table.

Hosts:
  * Service-side filter inputs (per ``NavigationItem.filter_fields``) — sent to the
    default action when the user clicks Refresh.
  * A client-side JMESPath expression that filters already-loaded rows in place,
    so large result sets (e.g. 500 clusters) stay browsable without re-calling AWS.

Layout is horizontal — fields flow left-to-right and wrap to a second row if needed.
"""

from __future__ import annotations

import contextlib
import logging
import tkinter as tk
from collections.abc import Callable, Iterable
from tkinter import ttk
from typing import Any

from gui4aws.models import InputField

__all__ = ["FilterBar"]

logger = logging.getLogger(__name__)


class FilterBar(ttk.LabelFrame):
    """A reusable input bar that drives the resource list above it.

    The bar exposes two callbacks:
      * ``on_refresh()`` — fired when the user clicks Refresh, presses Enter in a
        field, or picks a value from an auto-populated dropdown. The caller is
        expected to re-run the default action using ``values()``.
      * ``on_client_filter()`` — fired (debounced) when the JMESPath filter changes.
        The caller is expected to re-render the visible rows using the expression
        from ``client_filter()``.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        on_refresh: Callable[[], None] | None = None,
        on_client_filter: Callable[[str], None] | None = None,
        on_field_change: Callable[[str, str], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, text="Filter", **kwargs)
        self.on_refresh = on_refresh
        self.on_client_filter = on_client_filter
        self.on_field_change = on_field_change

        self.inner = ttk.Frame(self)
        self.inner.grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        self.inner.grid_columnconfigure(99, weight=1)  # absorb trailing space
        self.grid_columnconfigure(0, weight=1)

        # Per-field state — rebuilt every time set_fields() is called.
        self.fields: tuple[InputField, ...] = ()
        self.variables: dict[str, tk.StringVar] = {}
        self.comboboxes: dict[str, ttk.Combobox] = {}
        # Set during render to suppress on_field_change while we're populating
        # initial values from prefill / defaults / auto-select.
        self.suppress_change: bool = False

        # Client-side JMESPath filter — persistent across nav switches if user wants it.
        self.client_var = tk.StringVar()
        self.client_after_id: str | None = None
        self.client_var.trace_add("write", lambda *_: self.on_client_change())

        # Build an empty bar so geometry stays stable.
        self.render([])

    # ── Public API ───────────────────────────────────────────────────────────

    def set_fields(self, fields: Iterable[InputField], values: dict[str, str] | None = None) -> None:
        """Rebuild the bar for a new navigation item."""
        self.fields = tuple(fields)
        # Reset client filter when nav changes — a JMESPath for clusters makes no
        # sense applied to a snapshots table.
        self.client_var.set("")
        self.render(list(self.fields), values or {})

    def values(self) -> dict[str, str]:
        """Snapshot of current field values (excluding the client filter)."""
        return {name: var.get() for name, var in self.variables.items()}

    def client_filter(self) -> str:
        """Current JMESPath expression (may be empty)."""
        return self.client_var.get().strip()

    def set_choices(self, field_name: str, choices: list[str], *, auto_select: bool = True) -> None:
        """Populate a combobox's choice list (used by eager dropdowns).

        If ``auto_select`` is True and the field is currently empty, the first
        choice is selected and a refresh is fired. Callers should set this False
        for optional fields where "blank" is meaningful (e.g. ECS task service
        filter — blank means all services).
        """
        combo = self.comboboxes.get(field_name)
        if combo is None:
            return
        combo.configure(values=choices)
        if not auto_select:
            return
        var = self.variables.get(field_name)
        if var is not None and not var.get() and choices:
            var.set(choices[0])
            # Drive a refresh now that we have a viable cluster name.
            if self.on_refresh is not None:
                self.on_refresh()

    # ── Internal: rendering ──────────────────────────────────────────────────

    def render(self, fields: list[InputField], prefill: dict[str, str] | None = None) -> None:
        """Create and lay out the actual input widgets based on a set of fields.

        Clears any existing widgets and rebuilds the bar, optionally populating
        initial values from prefill data.
        """
        prefill = prefill or {}
        for child in self.inner.winfo_children():
            child.destroy()
        self.variables.clear()
        self.comboboxes.clear()

        self.suppress_change = True
        col = 0
        # Service-side filter fields ──────────────────────────────────────────
        for fld in fields:
            ttk.Label(self.inner, text=fld.label + (" *" if fld.required else "") + ":").grid(
                row=0, column=col, sticky="w", padx=(4, 2), pady=2
            )
            col += 1
            initial = prefill.get(fld.name, fld.default or "")
            var = tk.StringVar(value=initial)
            var.trace_add(
                "write",
                lambda *_a, _name=fld.name, _var=var: self.fire_field_change(_name, _var.get()),
            )
            self.variables[fld.name] = var
            widget: tk.Widget
            if fld.kind == "choice" and fld.choices:
                combo = ttk.Combobox(self.inner, textvariable=var, values=list(fld.choices), width=24)
                combo.bind("<<ComboboxSelected>>", lambda _e: self.fire_refresh())
                self.comboboxes[fld.name] = combo
                widget = combo
            elif fld.kind == "choice":
                # Choices not known yet — eager loader will fill them in.
                combo = ttk.Combobox(self.inner, textvariable=var, values=[], width=24)
                combo.bind("<<ComboboxSelected>>", lambda _e: self.fire_refresh())
                self.comboboxes[fld.name] = combo
                widget = combo
            elif fld.kind == "bool":
                combo = ttk.Combobox(
                    self.inner,
                    textvariable=var,
                    values=["true", "false"],
                    state="readonly",
                    width=8,
                )
                combo.bind("<<ComboboxSelected>>", lambda _e: self.fire_refresh())
                widget = combo
            else:
                entry = ttk.Entry(self.inner, textvariable=var, width=24)
                entry.bind("<Return>", lambda _e: self.fire_refresh())
                widget = entry
            widget.grid(row=0, column=col, sticky="w", padx=(0, 8), pady=2)
            col += 1

        # Refresh button — always present, even when no service-side fields exist.
        ttk.Button(self.inner, text="Refresh", command=self.fire_refresh).grid(row=0, column=col, padx=(4, 8), pady=2)
        col += 1

        # Client-side JMESPath filter ─────────────────────────────────────────
        ttk.Separator(self.inner, orient="vertical").grid(row=0, column=col, sticky="ns", padx=4)
        col += 1
        ttk.Label(self.inner, text="Filter rows (JMESPath):").grid(row=0, column=col, sticky="w", padx=(4, 2), pady=2)
        col += 1
        client_entry = ttk.Entry(self.inner, textvariable=self.client_var, width=30)
        client_entry.grid(row=0, column=col, sticky="ew", padx=(0, 4), pady=2)
        col += 1
        # Hint as ghost label on the right.
        ttk.Label(
            self.inner,
            text="e.g.  contains(status, 'available')   or just  prod",
            foreground="gray",
        ).grid(row=0, column=col, sticky="w", padx=4, pady=2)

        # Now that all initial values have been written, allow change events
        # to flow to the listener.
        self.suppress_change = False

    # ── Internal: callbacks ──────────────────────────────────────────────────

    def fire_field_change(self, name: str, value: str) -> None:
        """Notify the listener that a service-side filter field value has changed.

        This event is suppressed during initial rendering to avoid redundant
        callbacks before the UI is stable.
        """
        if self.suppress_change:
            return
        if self.on_field_change is not None:
            self.on_field_change(name, value)

    def fire_refresh(self) -> None:
        """Notify the listener that the user has explicitly requested a data refresh.

        Triggered by clicking the Refresh button, pressing Enter in an entry field,
        or selecting a value from a dropdown.
        """
        if self.on_refresh is not None:
            self.on_refresh()

    def on_client_change(self) -> None:
        """Handle user input in the client-side JMESPath filter entry.

        Includes debouncing to prevent excessive re-filtering of large tables
        while the user is typing.
        """
        if self.on_client_filter is None:
            return
        # Debounce keystrokes so we don't filter the table on every character.
        if self.client_after_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self.client_after_id)
        self.client_after_id = self.after(250, self.fire_client_filter)

    def fire_client_filter(self) -> None:
        """Execute the debounced client-side filter callback."""
        self.client_after_id = None
        if self.on_client_filter is not None:
            self.on_client_filter(self.client_filter())
