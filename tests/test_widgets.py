"""Tests for various GUI widgets."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from unittest.mock import MagicMock
from dataclasses import dataclass

import pytest

from gui4aws.app import AppContext
from gui4aws.gui.filter_bar import FilterBar
from gui4aws.gui.resource_table import ResourceTable
from gui4aws.gui.sidebar import Sidebar
from gui4aws.gui.status_bar import StatusBar
from gui4aws.gui.detail_tree import DetailTree
from gui4aws.gui.toolbar import Toolbar
from gui4aws.models import InputField, ServiceDefinition, NavigationItem
from gui4aws.services.service_registry import ServiceRegistry


@pytest.fixture(scope="module")
def tk_root() -> Generator[tk.Tk, None, None]:
    """Create one Tk root for the module or skip if Tk is unavailable."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable in this environment: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def test_toolbar(tk_root: tk.Tk) -> None:
    context = AppContext(region_name="us-east-1")
    on_change = MagicMock()
    toolbar = Toolbar(tk_root, context, on_change=on_change)

    # Change mode
    toolbar.mode_var.set("aws-cli")
    toolbar.on_mode_changed()
    assert context.mode == "aws-cli"
    assert on_change.call_count == 1

    # Change region
    toolbar.region_var.set("us-west-2")
    toolbar.on_region_changed()
    assert context.region_name == "us-west-2"
    assert on_change.call_count == 2


def test_detail_tree(tk_root: tk.Tk) -> None:
    tree = DetailTree(tk_root)
    data = {"k1": "v1", "k2": {"sub": 1}, "k3": [1, 2]}
    tree.set_data(data)

    children = tree.tree.get_children()
    assert len(children) == 3
    # Check rendered value for nested dict
    v2 = tree.tree.item(children[1])["values"][1]
    assert "sub: 1" in v2


def test_resource_table(tk_root: tk.Tk) -> None:
    @dataclass
    class Item:
        id: str
        name: str
        status: str
        deleted: bool = False

    on_select = MagicMock()
    table = ResourceTable(tk_root, columns=["id", "name", "status"], on_select=on_select)

    items = [
        Item(id="1", name="n1", status="active"),
        Item(id="2", name="n2", status="deleted", deleted=True),
    ]
    table.set_rows(items)

    # Auto-selected first row
    on_select.assert_called_with(items[0])

    # Check rendered content
    children = table.tree.get_children()
    assert len(children) == 2
    # Note: Tkinter may return numeric strings as ints/floats in values
    values = table.tree.item(children[0])["values"]
    assert str(values[0]) == "1"
    assert values[1] == "n1"
    assert values[2] == "active"
    assert "deleted" in table.tree.item(children[1])["tags"]

    # Simulate manual selection
    table.tree.selection_set("1")
    table._on_tree_select()
    assert on_select.call_count == 2
    on_select.assert_called_with(items[1])


def test_sidebar_populate_and_select(tk_root: tk.Tk) -> None:
    registry = ServiceRegistry()
    nav = NavigationItem(item_id="test-item", display_name="Test Item")
    svc = ServiceDefinition(
        service_id="test-svc",
        display_name="Test Service",
        boto3_service_name="s3",
        cli_service_name="s3",
        navigation_items=(nav,),
        actions=()
    )
    on_select = MagicMock()
    registry.register(svc)
    sidebar = Sidebar(tk_root, registry, on_select=on_select)

    # Check tree content
    children = sidebar.tree.get_children()
    assert len(children) == 1
    assert sidebar.tree.item(children[0])["text"] == "Test Service"

    sub_children = sidebar.tree.get_children(children[0])
    assert len(sub_children) == 1
    assert sidebar.tree.item(sub_children[0])["text"] == "Test Item"

    # Simulate selection
    sidebar.tree.selection_set(sub_children[0])
    sidebar.on_tree_select()

    on_select.assert_called_once()
    selection = on_select.call_args[0][0]
    assert selection.service_id == "test-svc"
    assert selection.item_id == "test-item"


def test_status_bar(tk_root: tk.Tk) -> None:
    context = AppContext(region_name="us-east-1")
    status_bar = StatusBar(tk_root, context)

    assert status_bar.status_var.get() == "Ready"
    assert "region=us-east-1" in status_bar.context_var.get()

    status_bar.set_status("Busy")
    assert status_bar.status_var.get() == "Busy"

    status_bar.set_last_action("Success")
    assert status_bar.last_action_var.get() == "Success"


def test_filter_bar(tk_root: tk.Tk) -> None:
    on_refresh = MagicMock()
    on_change = MagicMock()
    bar = FilterBar(tk_root, on_refresh=on_refresh, on_field_change=on_change)

    fields = [
        InputField(name="f1", label="L1", kind="text", default="v1"),
        InputField(name="f2", label="L2", kind="choice", choices=("a", "b")),
    ]
    bar.set_fields(fields)

    assert bar.values()["f1"] == "v1"
    assert bar.values()["f2"] == ""

    # Simulate change
    bar._variables["f1"].set("new-v")
    on_change.assert_called_with("f1", "new-v")

    # Simulate choices update
    bar.set_choices("f2", ["a", "b"], auto_select=True)
    assert bar.values()["f2"] == "a"
    on_refresh.assert_called_once()

    # Client filter (JMESPath)
    bar._client_var.set("some-expr")
    assert bar.client_filter() == "some-expr"
