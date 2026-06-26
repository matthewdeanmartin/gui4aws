"""Tests for the UI gate that hides demo seeding unless a managed emulator is active."""

from __future__ import annotations

from dataclasses import dataclass

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.gui.main_window import MainWindow


@dataclass
class FakeManager:
    running: bool
    endpoint_url: str


def _window(
    mode: EndpointMode,
    *,
    url: str | None = None,
    moto: FakeManager | None = None,
    robotocore: FakeManager | None = None,
) -> MainWindow:
    window = object.__new__(MainWindow)
    window.context = AppContext()
    if mode is EndpointMode.MOTO:
        window.context.set_endpoint(EndpointMode.MOTO, url)
    elif mode is EndpointMode.ROBOTOCORE:
        window.context.set_endpoint(EndpointMode.ROBOTOCORE, url)
    elif mode is EndpointMode.CUSTOM:
        window.context.set_endpoint(EndpointMode.CUSTOM, url or "http://x:1")
    window.moto_manager = moto or FakeManager(False, "http://127.0.0.1:5000")
    window.robotocore_manager = robotocore or FakeManager(False, "http://localhost:4566")
    return window


def test_allowed_for_running_moto_matching_url() -> None:
    window = _window(
        EndpointMode.MOTO,
        url="http://127.0.0.1:55001",
        moto=FakeManager(True, "http://127.0.0.1:55001"),
    )
    assert window.demo_seeding_allowed() is True


def test_allowed_for_running_robotocore() -> None:
    window = _window(
        EndpointMode.ROBOTOCORE,
        url="http://localhost:4566",
        robotocore=FakeManager(True, "http://localhost:4566"),
    )
    assert window.demo_seeding_allowed() is True


def test_blocked_on_aws() -> None:
    window = _window(EndpointMode.AWS)
    assert window.demo_seeding_allowed() is False


def test_blocked_on_custom_even_if_moto_url() -> None:
    # A moto the user started independently, reached via a custom URL, is refused.
    window = _window(
        EndpointMode.CUSTOM,
        url="http://127.0.0.1:5000",
        moto=FakeManager(True, "http://127.0.0.1:5000"),
    )
    assert window.demo_seeding_allowed() is False


def test_blocked_when_moto_selected_but_not_running() -> None:
    window = _window(
        EndpointMode.MOTO,
        url="http://127.0.0.1:5000",
        moto=FakeManager(False, "http://127.0.0.1:5000"),
    )
    assert window.demo_seeding_allowed() is False


def test_blocked_when_url_does_not_match_manager() -> None:
    # Endpoint points somewhere other than the manager we started.
    window = _window(
        EndpointMode.MOTO,
        url="http://127.0.0.1:9999",
        moto=FakeManager(True, "http://127.0.0.1:5000"),
    )
    assert window.demo_seeding_allowed() is False


def test_refresh_demo_menu_shows_seed_only_when_allowed() -> None:
    import tkinter as tk

    try:
        root = tk.Tk()
    except tk.TclError as exc:  # headless CI without a display
        import pytest

        pytest.skip(f"Tk unavailable: {exc}")
    root.withdraw()

    def command_labels(menu: tk.Menu) -> list[str]:
        end = menu.index("end")
        if end is None:
            return []
        labels: list[str] = []
        for i in range(end + 1):
            if menu.type(i) == "command":
                labels.append(str(menu.entrycget(i, "label")))
        return labels

    try:
        # Blocked on AWS: only the "About" entry, no seed item.
        window = _window(EndpointMode.AWS)
        window.demo_menu = tk.Menu(root, tearoff=False)
        window.refresh_demo_menu()
        assert not any("Seed demo resources" in label for label in command_labels(window.demo_menu))

        # Allowed with a running moto: the seed item appears (and names the backend).
        window2 = _window(
            EndpointMode.MOTO,
            url="http://127.0.0.1:5000",
            moto=FakeManager(True, "http://127.0.0.1:5000"),
        )
        window2.demo_menu = tk.Menu(root, tearoff=False)
        window2.refresh_demo_menu()
        assert any("Seed demo resources" in label for label in command_labels(window2.demo_menu))
    finally:
        root.destroy()


def test_seed_no_ops_when_not_allowed() -> None:
    window = _window(EndpointMode.AWS)

    @dataclass
    class _Status:
        text: str = ""

        def set_status(self, text: str) -> None:
            self.text = text

    window.status_bar = _Status()
    # Should return without spawning a worker / touching results_queue.
    window.seed_demo_resources()
    assert "Start Moto or Robotocore" in window.status_bar.text
