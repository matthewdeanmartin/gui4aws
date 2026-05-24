"""Tests for CDK and Terraform dialogs."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator

import pytest

from gui4aws.gui.cdk_dialog import CdkDialog, _CDK_SUBCOMMANDS
from gui4aws.gui.terraform_dialog import TerraformDialog


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


def test_cdk_dialog_command_building(tk_root: tk.Tk) -> None:
    dialog = CdkDialog(tk_root)

    # Test 'list' subcommand
    # list is index 0 in _CDK_SUBCOMMANDS
    dialog._select_subcommand(_CDK_SUBCOMMANDS[0])
    dialog._field_vars["--long"].set(True)
    cmd = dialog._build_command()
    assert "list" in cmd
    assert "--long" in cmd

    # Test 'deploy' with STACKS
    # deploy is index 3
    dialog._select_subcommand(_CDK_SUBCOMMANDS[3])
    dialog._field_vars["STACKS"].set("stack1 stack2")
    cmd = dialog._build_command()
    assert "deploy" in cmd
    assert "stack1" in cmd
    assert "stack2" in cmd

    # Test dry run for deploy (should use synth)
    cmd_dry = dialog._build_command(dry_run=True)
    assert "synth" in cmd_dry
    assert "deploy" not in cmd_dry

    dialog.destroy()


def test_terraform_dialog_init(tk_root: tk.Tk) -> None:
    dialog = TerraformDialog(tk_root)
    assert dialog.title() == "Terraform Launcher (not yet implemented)"
    dialog.destroy()
