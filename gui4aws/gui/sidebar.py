"""Sidebar: a ttk.Treeview of registered services + their navigation items."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from tkinter import ttk
from typing import Any

from gui4aws.services.service_registry import ServiceRegistry

__all__ = ["Sidebar", "SidebarSelection"]


class SidebarSelection:
    """Identifies the currently-selected sidebar entry."""

    def __init__(self, service_id: str, item_id: str | None) -> None:
        self.service_id = service_id
        self.item_id = item_id

    def __repr__(self) -> str:
        return f"SidebarSelection(service_id={self.service_id!r}, item_id={self.item_id!r})"


class Sidebar(ttk.Frame):
    """Tree of services and their navigation items."""

    def __init__(
        self,
        parent: tk.Misc,
        registry: ServiceRegistry,
        *,
        on_select: Callable[[SidebarSelection], None] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(parent, **kwargs)
        self.registry = registry
        self.on_select = on_select or (lambda _: None)

        self.tree = ttk.Treeview(self, show="tree", height=24)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.node_to_selection: dict[str, SidebarSelection] = {}
        self.populate()
        self.tree.bind("<<TreeviewSelect>>", self.on_tree_select)

    def populate(self) -> None:
        """Rebuild the tree from the current registry."""
        for child in self.tree.get_children():
            self.tree.delete(child)
        self.node_to_selection.clear()
        for service in self.registry:
            service_node = self.tree.insert("", "end", text=service.display_name, open=True)
            self.node_to_selection[service_node] = SidebarSelection(service.service_id, None)
            for nav in service.navigation_items:
                item_node = self.tree.insert(service_node, "end", text=nav.display_name)
                self.node_to_selection[item_node] = SidebarSelection(service.service_id, nav.item_id)

    def on_tree_select(self, event: object = None) -> None:
        """Forward a tree selection to ``on_select``."""
        del event
        selected = self.tree.selection()
        if not selected:
            return
        node = selected[0]
        selection = self.node_to_selection.get(node)
        if selection is not None:
            self.on_select(selection)
