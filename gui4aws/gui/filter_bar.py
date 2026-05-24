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
        self._on_refresh = on_refresh
        self._on_client_filter = on_client_filter
        self._on_field_change = on_field_change

        self._inner = ttk.Frame(self)
        self._inner.grid(row=0, column=0, sticky="ew", padx=4, pady=2)
        self._inner.grid_columnconfigure(99, weight=1)  # absorb trailing space
        self.grid_columnconfigure(0, weight=1)

        # Per-field state — rebuilt every time set_fields() is called.
        self._fields: tuple[InputField, ...] = ()
        self._variables: dict[str, tk.StringVar] = {}
        self._comboboxes: dict[str, ttk.Combobox] = {}
        # Set during _render to suppress on_field_change while we're populating
        # initial values from prefill / defaults / auto-select.
        self._suppress_change: bool = False

        # Client-side JMESPath filter — persistent across nav switches if user wants it.
        self._client_var = tk.StringVar()
        self._client_after_id: str | None = None
        self._client_var.trace_add("write", lambda *_: self._on_client_change())

        # Build an empty bar so geometry stays stable.
        self._render([])

    # ── Public API ───────────────────────────────────────────────────────────

    def set_fields(self, fields: Iterable[InputField], values: dict[str, str] | None = None) -> None:
        """Rebuild the bar for a new navigation item."""
        self._fields = tuple(fields)
        # Reset client filter when nav changes — a JMESPath for clusters makes no
        # sense applied to a snapshots table.
        self._client_var.set("")
        self._render(list(self._fields), values or {})

    def values(self) -> dict[str, str]:
        """Snapshot of current field values (excluding the client filter)."""
        return {name: var.get() for name, var in self._variables.items()}

    def client_filter(self) -> str:
        """Current JMESPath expression (may be empty)."""
        return self._client_var.get().strip()

    def set_choices(self, field_name: str, choices: list[str], *, auto_select: bool = True) -> None:
        """Populate a combobox's choice list (used by eager dropdowns).

        If ``auto_select`` is True and the field is currently empty, the first
        choice is selected and a refresh is fired. Callers should set this False
        for optional fields where "blank" is meaningful (e.g. ECS task service
        filter — blank means all services).
        """
        combo = self._comboboxes.get(field_name)
        if combo is None:
            return
        combo.configure(values=choices)
        if not auto_select:
            return
        var = self._variables.get(field_name)
        if var is not None and not var.get() and choices:
            var.set(choices[0])
            # Drive a refresh now that we have a viable cluster name.
            if self._on_refresh is not None:
                self._on_refresh()

    # ── Internal: rendering ──────────────────────────────────────────────────

    def _render(self, fields: list[InputField], prefill: dict[str, str] | None = None) -> None:
        prefill = prefill or {}
        for child in self._inner.winfo_children():
            child.destroy()
        self._variables.clear()
        self._comboboxes.clear()

        self._suppress_change = True
        col = 0
        # Service-side filter fields ──────────────────────────────────────────
        for fld in fields:
            ttk.Label(self._inner, text=fld.label + (" *" if fld.required else "") + ":").grid(
                row=0, column=col, sticky="w", padx=(4, 2), pady=2
            )
            col += 1
            initial = prefill.get(fld.name, fld.default or "")
            var = tk.StringVar(value=initial)
            var.trace_add(
                "write",
                lambda *_a, _name=fld.name, _var=var: self._fire_field_change(_name, _var.get()),
            )
            self._variables[fld.name] = var
            widget: tk.Widget
            if fld.kind == "choice" and fld.choices:
                combo = ttk.Combobox(
                    self._inner, textvariable=var, values=list(fld.choices), width=24
                )
                combo.bind("<<ComboboxSelected>>", lambda _e: self._fire_refresh())
                self._comboboxes[fld.name] = combo
                widget = combo
            elif fld.kind == "choice":
                # Choices not known yet — eager loader will fill them in.
                combo = ttk.Combobox(self._inner, textvariable=var, values=[], width=24)
                combo.bind("<<ComboboxSelected>>", lambda _e: self._fire_refresh())
                self._comboboxes[fld.name] = combo
                widget = combo
            elif fld.kind == "bool":
                combo = ttk.Combobox(
                    self._inner, textvariable=var, values=["true", "false"],
                    state="readonly", width=8,
                )
                combo.bind("<<ComboboxSelected>>", lambda _e: self._fire_refresh())
                widget = combo
            else:
                entry = ttk.Entry(self._inner, textvariable=var, width=24)
                entry.bind("<Return>", lambda _e: self._fire_refresh())
                widget = entry
            widget.grid(row=0, column=col, sticky="w", padx=(0, 8), pady=2)
            col += 1

        # Refresh button — always present, even when no service-side fields exist.
        ttk.Button(self._inner, text="Refresh", command=self._fire_refresh).grid(
            row=0, column=col, padx=(4, 8), pady=2
        )
        col += 1

        # Client-side JMESPath filter ─────────────────────────────────────────
        ttk.Separator(self._inner, orient="vertical").grid(
            row=0, column=col, sticky="ns", padx=4
        )
        col += 1
        ttk.Label(self._inner, text="Filter rows (JMESPath):").grid(
            row=0, column=col, sticky="w", padx=(4, 2), pady=2
        )
        col += 1
        client_entry = ttk.Entry(self._inner, textvariable=self._client_var, width=30)
        client_entry.grid(row=0, column=col, sticky="ew", padx=(0, 4), pady=2)
        col += 1
        # Hint as ghost label on the right.
        ttk.Label(
            self._inner,
            text="e.g.  contains(status, 'available')   or just  prod",
            foreground="gray",
        ).grid(row=0, column=col, sticky="w", padx=4, pady=2)

        # Now that all initial values have been written, allow change events
        # to flow to the listener.
        self._suppress_change = False

    # ── Internal: callbacks ──────────────────────────────────────────────────

    def _fire_field_change(self, name: str, value: str) -> None:
        if self._suppress_change:
            return
        if self._on_field_change is not None:
            self._on_field_change(name, value)

    def _fire_refresh(self) -> None:
        if self._on_refresh is not None:
            self._on_refresh()

    def _on_client_change(self) -> None:
        if self._on_client_filter is None:
            return
        # Debounce keystrokes so we don't filter the table on every character.
        if self._client_after_id is not None:
            with contextlib.suppress(Exception):
                self.after_cancel(self._client_after_id)
        self._client_after_id = self.after(250, self._fire_client_filter)

    def _fire_client_filter(self) -> None:
        self._client_after_id = None
        if self._on_client_filter is not None:
            self._on_client_filter(self.client_filter())
