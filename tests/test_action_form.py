"""Tk-backed widget tests for action forms and dialogs."""

from __future__ import annotations

import tkinter as tk
from typing import cast

import pytest

from gui4aws.gui.action_dialog import ActionDialog
from gui4aws.gui.action_form import ActionForm
from gui4aws.services.secrets.actions import CREATE_SECRET
from gui4aws.services.ssm.actions import PUT_PARAMETER


@pytest.fixture(scope="module")
def tk_root() -> tk.Tk:
    """Create one Tk root for the module or skip if Tk is unavailable."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk is unavailable in this environment: {exc}")
    root.withdraw()
    yield root
    root.destroy()


def test_action_form_multiline_prefill_and_values(tk_root: tk.Tk) -> None:
    """Multiline fields round-trip through the form like single-line inputs."""
    form = ActionForm(tk_root, CREATE_SECRET, prefill={"name": "demo-secret", "secret_string": '{"demo": true}'})
    assert form.values()["secret_string"] == '{"demo": true}'

    widget = form._text_widgets["secret_string"]
    widget.delete("1.0", "end")
    widget.insert("1.0", "rotated-value")

    assert form.values()["secret_string"] == "rotated-value"
    assert form.validate() == []


def test_action_form_requires_multiline_content(tk_root: tk.Tk) -> None:
    """Required multiline inputs validate the same way as entry widgets."""
    form = ActionForm(tk_root, PUT_PARAMETER)
    assert "Value is required" in form.validate()

    widget = form._text_widgets["value"]
    widget.insert("1.0", "parameter body")

    assert "Value is required" not in form.validate()


def test_action_dialog_uses_scrollable_body_and_refreshes_multiline_scripts(tk_root: tk.Tk) -> None:
    """Scrollable dialogs still refresh generated scripts from multiline fields."""
    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            CREATE_SECRET,
            on_generate_scripts=lambda _action, inputs: (inputs.get("secret_string", ""), "python"),
        )
        tk_root.update_idletasks()

        assert hasattr(dialog, "_body_canvas")
        assert dialog._body_canvas.cget("yscrollcommand")
        assert dialog.form.master is dialog._body

        widget = dialog.form._text_widgets["secret_string"]
        widget.insert("1.0", "updated secret")
        tk_root.update()

        cli_text = cast(tk.Text, dialog._cli_text)
        assert cli_text.get("1.0", "end-1c") == "updated secret"
    finally:
        if dialog is not None:
            dialog.destroy()
