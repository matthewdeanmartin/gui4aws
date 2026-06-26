"""Tests for MainWindow's Target-selector orchestration (mutually-exclusive backends).

See spec/mutually_exclusive.md. These exercise ``on_target_changed`` and the
emulator result handlers using ``object.__new__(MainWindow)`` so no real Tk
window is needed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.gui.main_window import MainWindow


@dataclass
class FakeToolbar:
    """Records the state-sync calls MainWindow makes on the toolbar."""

    endpoint_url: str = ""
    target: EndpointMode = EndpointMode.AWS
    busy: bool | None = None
    moto_running: bool = False
    robotocore_running: bool = False
    profile_set: list[str | None] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.endpoint_url_var = _Var(self)
        self.url_entry = _FocusableEntry()

    def set_target(self, mode: EndpointMode) -> None:
        self.target = mode

    def set_transition_busy(self, busy: bool) -> None:
        self.busy = busy

    def set_profile(self, profile_name: str | None) -> None:
        self.profile_set.append(profile_name)


class _FocusableEntry:
    focused: bool = False

    def focus_set(self) -> None:
        self.focused = True


class _Var:
    def __init__(self, owner: FakeToolbar) -> None:
        self._owner = owner

    def get(self) -> str:
        return self._owner.endpoint_url

    def set(self, value: str) -> None:
        self._owner.endpoint_url = value


@dataclass
class FakeManager:
    running: bool = False
    started: bool = False
    stopped: bool = False
    endpoint_url: str = "http://emulator:1234"

    def start(self, **_kw: Any) -> None:
        self.started = True
        self.running = True

    def stop(self) -> None:
        self.stopped = True
        self.running = False


@dataclass
class FakeStatusBar:
    status: str = ""

    def set_status(self, status: str) -> None:
        self.status = status


def _make_window(endpoint_mode: EndpointMode = EndpointMode.AWS) -> MainWindow:
    window = object.__new__(MainWindow)
    window.context = AppContext()
    if endpoint_mode is not EndpointMode.AWS:
        window.context.set_endpoint(endpoint_mode, "http://emulator:1234")
    window.toolbar = FakeToolbar()
    window.status_bar = FakeStatusBar()
    window.moto_manager = FakeManager()
    window.robotocore_manager = FakeManager()
    window.on_toolbar_changed = lambda: None  # type: ignore[method-assign]
    return window


def test_choosing_moto_starts_moto_and_marks_busy() -> None:
    window = _make_window()
    moto_calls: list[bool] = []
    window.on_moto_toggle = lambda start: moto_calls.append(start)  # type: ignore[method-assign]

    window.on_target_changed(EndpointMode.MOTO)

    assert moto_calls == [True]  # start requested
    assert window.toolbar.busy is True  # selector locked during transition


def test_choosing_robotocore_starts_it() -> None:
    window = _make_window()
    rc_calls: list[bool] = []
    window.on_robotocore_toggle = lambda currently_running: rc_calls.append(currently_running)  # type: ignore[method-assign]

    window.on_target_changed(EndpointMode.ROBOTOCORE)

    assert rc_calls == [False]  # False == "not running yet" -> start
    assert window.toolbar.busy is True


def test_switching_away_from_moto_stops_it() -> None:
    window = _make_window(EndpointMode.MOTO)
    window.moto_manager.running = True
    window.toolbar.moto_running = True

    window.on_target_changed(EndpointMode.AWS)

    assert window.moto_manager.stopped is True
    assert window.context.endpoint_config.mode is EndpointMode.AWS
    assert window.toolbar.target is EndpointMode.AWS


def test_switching_from_moto_to_robotocore_stops_moto_and_starts_rc() -> None:
    window = _make_window(EndpointMode.MOTO)
    window.moto_manager.running = True
    window.toolbar.moto_running = True
    rc_calls: list[bool] = []
    window.on_robotocore_toggle = lambda currently_running: rc_calls.append(currently_running)  # type: ignore[method-assign]

    window.on_target_changed(EndpointMode.ROBOTOCORE)

    assert window.moto_manager.stopped is True  # only one emulator at a time
    assert rc_calls == [False]


def test_custom_without_url_does_not_switch() -> None:
    window = _make_window()
    window.toolbar.endpoint_url = ""

    window.on_target_changed(EndpointMode.CUSTOM)

    # No URL -> stays on AWS, prompts the user.
    assert window.context.endpoint_config.mode is EndpointMode.AWS
    assert "URL" in window.status_bar.status


def test_custom_with_url_switches() -> None:
    window = _make_window()
    window.toolbar.endpoint_url = "http://my-localstack:4566"

    window.on_target_changed(EndpointMode.CUSTOM)

    assert window.context.endpoint_config.mode is EndpointMode.CUSTOM
    assert window.context.endpoint_config.endpoint_url == "http://my-localstack:4566"
    assert window.toolbar.target is EndpointMode.CUSTOM


def test_moto_error_reverts_target_to_aws(monkeypatch: Any) -> None:
    window = _make_window()
    window.toolbar.busy = True
    # dispatch_result pops a messagebox on error; silence it.
    monkeypatch.setattr("gui4aws.gui.main_window.messagebox.showerror", lambda *a, **k: None)

    window.dispatch_result("moto_error", None, "boom", None)

    assert window.toolbar.target is EndpointMode.AWS
    assert window.toolbar.busy is False
    assert window.context.endpoint_config.mode is EndpointMode.AWS
    assert window.toolbar.moto_running is False
