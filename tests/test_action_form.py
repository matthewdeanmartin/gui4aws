"""Tk-backed widget tests for action forms and dialogs."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Generator
from typing import cast

import pytest

import gui4aws.gui.action_dialog as action_dialog_module
from gui4aws.gui.action_dialog import ActionDialog
from gui4aws.gui.action_form import ActionForm
from gui4aws.services.aurora.actions import DELETE_DB_CLUSTER
from gui4aws.services.secrets.actions import CREATE_SECRET
from gui4aws.services.ssm.actions import PUT_PARAMETER


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


def test_action_form_multiline_prefill_and_values(tk_root: tk.Tk) -> None:
    """Multiline fields round-trip through the form like single-line inputs."""
    form = ActionForm(tk_root, CREATE_SECRET, prefill={"name": "demo-secret", "secret_string": '{"demo": true}'})
    assert form.values()["secret_string"] == '{"demo": true}'

    widget = form.text_widgets["secret_string"]
    widget.delete("1.0", "end")
    widget.insert("1.0", "rotated-value")

    assert form.values()["secret_string"] == "rotated-value"
    assert form.validate() == []


def test_action_form_requires_multiline_content(tk_root: tk.Tk) -> None:
    """Required multiline inputs validate the same way as entry widgets."""
    form = ActionForm(tk_root, PUT_PARAMETER)
    assert "Value is required" in form.validate()

    widget = form.text_widgets["value"]
    widget.insert("1.0", "parameter body")

    assert "Value is required" not in form.validate()


def test_action_dialog_refreshes_multiline_scripts(tk_root: tk.Tk) -> None:
    """Editing a multiline field live-updates the generated script preview."""
    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            CREATE_SECRET,
            on_generate_scripts=lambda _action, inputs: (inputs.get("secret_string", ""), "python"),
        )
        tk_root.update_idletasks()

        # Dialog must expose the CLI text widget (script preview for write actions).
        cli_text = cast(tk.Text, dialog.cli_text)
        assert cli_text is not None

        # Editing the multiline field should refresh the script preview.
        widget = dialog.form.text_widgets["secret_string"]
        widget.insert("1.0", "updated secret")
        tk_root.update()

        assert cli_text.get("1.0", "end-1c") == "updated secret"

        # The result text widget must exist and be scrollable.
        assert hasattr(dialog, "result_text")
        assert dialog.result_text.cget("yscrollcommand")
    finally:
        if dialog is not None:
            dialog.destroy()


class _StubDecision:
    """Minimal stand-in for a dialog decision with a controllable confirmed flag."""

    def __init__(self, confirmed: bool) -> None:
        self.confirmed = confirmed


def _stub_dialog_factory(confirmed: bool) -> type:
    """Build a stub dialog whose ``show_modal`` returns a decision with ``confirmed``."""

    class _StubDialog:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def show_modal(self) -> _StubDecision:
            return _StubDecision(confirmed)

    return _StubDialog


def test_destructive_action_blocked_when_typed_confirmation_cancelled(
    tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A destructive action must NOT execute if the typed-confirmation step is cancelled."""
    ran: list[tuple[object, dict[str, str]]] = []
    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            DELETE_DB_CLUSTER,
            prefill={"cluster_identifier": "prod-db"},
            on_run=lambda action, inputs: ran.append((action, inputs)),
            on_generate_scripts=lambda _action, _inputs: ("cli", "python"),
        )
        # Review passes, but the user cancels at the typed-name step.
        monkeypatch.setattr(action_dialog_module, "ReviewDialog", _stub_dialog_factory(True))
        monkeypatch.setattr(action_dialog_module, "TypedConfirmationDialog", _stub_dialog_factory(False))

        dialog.on_run()

        assert ran == []  # nothing was executed
        assert dialog.running is False
    finally:
        if dialog is not None:
            dialog.destroy()


def test_destructive_action_runs_when_fully_confirmed(tk_root: tk.Tk, monkeypatch: pytest.MonkeyPatch) -> None:
    """A destructive action executes only after review AND typed confirmation pass."""
    ran: list[tuple[object, dict[str, str]]] = []
    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            DELETE_DB_CLUSTER,
            prefill={"cluster_identifier": "prod-db"},
            on_run=lambda action, inputs: ran.append((action, inputs)),
            on_generate_scripts=lambda _action, _inputs: ("cli", "python"),
        )
        monkeypatch.setattr(action_dialog_module, "ReviewDialog", _stub_dialog_factory(True))
        monkeypatch.setattr(action_dialog_module, "TypedConfirmationDialog", _stub_dialog_factory(True))

        dialog.on_run()

        assert len(ran) == 1
        assert ran[0][1]["cluster_identifier"] == "prod-db"
    finally:
        if dialog is not None:
            dialog.destroy()
