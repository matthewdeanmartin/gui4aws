"""Tests for various GUI widgets."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from dataclasses import dataclass
from unittest.mock import MagicMock

import pytest

from gui4aws.app import AppContext
from gui4aws.gui.detail_tree import DetailTree
from gui4aws.gui.filter_bar import FilterBar
from gui4aws.gui.resource_table import ResourceTable
from gui4aws.gui.sidebar import Sidebar
from gui4aws.gui.status_bar import StatusBar
from gui4aws.gui.toolbar import Toolbar
from gui4aws.models import InputField, NavigationItem, ServiceDefinition
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


def test_toolbar_network_button_present(tk_root: tk.Tk) -> None:
    context = AppContext(region_name="us-east-1")
    on_network = MagicMock()
    toolbar = Toolbar(tk_root, context, on_network_settings=on_network)
    toolbar.network_btn.invoke()
    assert on_network.call_count == 1
    # Default config -> non-starred label.
    assert "*" not in toolbar.network_btn.cget("text")


def test_network_settings_dialog_round_trip(tk_root: tk.Tk) -> None:
    from gui4aws.execution.network_config import NetworkConfig
    from gui4aws.gui.network_settings_dialog import NetworkSettingsDialog

    captured: list[NetworkConfig] = []
    dialog = NetworkSettingsDialog(
        tk_root,
        NetworkConfig(http_proxy="http://p:8080"),
        on_apply=captured.append,
    )
    # The seeded value shows up in the widget.
    assert dialog.http_proxy_var.get() == "http://p:8080"
    # Edit + apply -> callback receives the updated config and dialog closes.
    dialog.https_proxy_var.set("http://s:8443")
    dialog.verify_ssl_var.set(False)
    dialog._apply()  # pylint: disable=protected-access
    assert captured and captured[0].https_proxy == "http://s:8443"
    assert captured[0].verify_ssl is False


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
    table.on_tree_select()
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
        actions=(),
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
    filter_bar = FilterBar(tk_root, on_refresh=on_refresh, on_field_change=on_change)

    fields = [
        InputField(name="f1", label="L1", kind="text", default="v1"),
        InputField(name="f2", label="L2", kind="choice", choices=("a", "b")),
    ]
    filter_bar.set_fields(fields)

    assert filter_bar.values()["f1"] == "v1"
    assert filter_bar.values()["f2"] == ""

    # Simulate change
    filter_bar.variables["f1"].set("new-v")
    on_change.assert_called_with("f1", "new-v")

    # Simulate choices update
    filter_bar.set_choices("f2", ["a", "b"], auto_select=True)
    assert filter_bar.values()["f2"] == "a"
    on_refresh.assert_called_once()

    # Client filter (JMESPath)
    filter_bar.client_var.set("some-expr")
    assert filter_bar.client_filter() == "some-expr"
