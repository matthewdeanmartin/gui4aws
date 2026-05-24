"""Tkinter tests that run the real GUI against moto in HTTP server mode.

The moto server is launched once per module (session-scoped fixture) and reset
between tests. These tests open actual Tk widgets, drive them programmatically,
and verify that the application wires correctly to the moto HTTP endpoint.

These are included in the default test run and must pass in CI.  Tk is skipped
gracefully on headless environments that lack a display.
"""

from __future__ import annotations

import time
import tkinter as tk
from typing import Any

import pytest

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.moto_server import MotoServerManager

# ── Module-scoped moto server ─────────────────────────────────────────────────


@pytest.fixture(scope="module")
def moto_server() -> Any:
    """Start a moto HTTP server once for the whole module."""
    mgr = MotoServerManager()
    mgr.start(timeout=30)
    yield mgr
    mgr.stop()


@pytest.fixture(autouse=True)
def reset_moto(moto_server: MotoServerManager) -> Any:
    """Wipe moto state between tests so they don't interfere."""
    yield
    moto_server.reset_state()


# ── Tk root ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tk_root() -> Any:
    """One Tk root per module; skipped when Tk is unavailable."""
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        pytest.skip(f"Tk unavailable: {exc}")
    root.withdraw()
    yield root
    root.destroy()


# ── Helpers ───────────────────────────────────────────────────────────────────


def moto_context(moto_server: MotoServerManager) -> AppContext:
    """Build an AppContext wired to the running moto server."""
    cfg = EndpointConfig(mode=EndpointMode.MOTO, endpoint_url=moto_server.endpoint_url)
    return AppContext(region_name="us-east-1", endpoint_config=cfg)


def pump(root: tk.Tk, duration: float = 0.1) -> None:
    """Run the Tk event loop for *duration* seconds, processing pending events."""
    deadline = time.monotonic() + duration
    while time.monotonic() < deadline:
        root.update()
        time.sleep(0.01)


# ── Tests ─────────────────────────────────────────────────────────────────────


def test_moto_server_is_running(moto_server: MotoServerManager) -> None:
    """Sanity check that the module fixture started successfully."""
    assert moto_server.running
    assert moto_server.endpoint_url.startswith("http://")


def test_moto_context_list_sqs_queues_via_http(moto_server: MotoServerManager) -> None:
    """AppContext can call SQS list_queues through the moto HTTP server."""
    import boto3

    from gui4aws.services.sqs.actions import LIST_QUEUES
    from gui4aws.services.sqs.views import to_queue_summaries

    sqs = boto3.client("sqs", region_name="us-east-1", endpoint_url=moto_server.endpoint_url)
    sqs.create_queue(QueueName="http-test-queue")

    context = moto_context(moto_server)
    from gui4aws.execution.boto3_executor import Boto3Result

    result = context.execute(LIST_QUEUES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_queue_summaries(result.response)
    assert any(s.name == "http-test-queue" for s in summaries)


def test_moto_context_list_secrets_via_http(moto_server: MotoServerManager) -> None:
    """AppContext can call SecretsManager list_secrets through the moto HTTP server."""
    import boto3

    from gui4aws.execution.boto3_executor import Boto3Result
    from gui4aws.services.secrets.actions import LIST_SECRETS
    from gui4aws.services.secrets.views import to_secret_summaries

    sm = boto3.client("secretsmanager", region_name="us-east-1", endpoint_url=moto_server.endpoint_url)
    sm.create_secret(Name="http-secret", SecretString="hunter2")

    context = moto_context(moto_server)
    result = context.execute(LIST_SECRETS, inputs={"name_prefix": "", "include_deleted": "false"})
    assert isinstance(result, Boto3Result)
    summaries = to_secret_summaries(result.response)
    assert any(s.name == "http-secret" for s in summaries)


def test_moto_context_list_s3_buckets_via_http(moto_server: MotoServerManager) -> None:
    """AppContext can call S3 list_buckets through the moto HTTP server."""
    import boto3

    from gui4aws.execution.boto3_executor import Boto3Result
    from gui4aws.services.s3.actions import LIST_BUCKETS
    from gui4aws.services.s3.views import to_bucket_summaries

    s3 = boto3.client("s3", region_name="us-east-1", endpoint_url=moto_server.endpoint_url)
    s3.create_bucket(Bucket="http-test-bucket")

    context = moto_context(moto_server)
    result = context.execute(LIST_BUCKETS, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_bucket_summaries(result.response)
    assert any(s.name == "http-test-bucket" for s in summaries)


def test_action_dialog_opens_and_closes(tk_root: tk.Tk, moto_server: MotoServerManager) -> None:
    """ActionDialog can be constructed and destroyed without error."""
    from gui4aws.gui.action_dialog import ActionDialog
    from gui4aws.services.sqs.actions import CREATE_QUEUE

    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            CREATE_QUEUE,
            on_generate_scripts=lambda _action, inputs: (inputs.get("queue_name", ""), "python"),
        )
        pump(tk_root)
        assert dialog.winfo_exists()
    finally:
        if dialog is not None:
            dialog.destroy()
    pump(tk_root)


def test_action_dialog_form_values_round_trip(tk_root: tk.Tk, moto_server: MotoServerManager) -> None:
    """ActionDialog with prefill exposes the pre-filled values in form.values()."""
    from gui4aws.gui.action_dialog import ActionDialog
    from gui4aws.services.sqs.actions import SEND_MESSAGE

    dialog: ActionDialog | None = None
    try:
        dialog = ActionDialog(
            tk_root,
            SEND_MESSAGE,
            prefill={"queue_url": "http://localhost/my-queue", "message_body": "test payload"},
            on_generate_scripts=lambda _action, inputs: (inputs.get("message_body", ""), "python"),
        )
        pump(tk_root)
        values = dialog.form.values()
        assert values["queue_url"] == "http://localhost/my-queue"
        assert values["message_body"] == "test payload"
    finally:
        if dialog is not None:
            dialog.destroy()


def test_toolbar_builds_without_error(tk_root: tk.Tk, moto_server: MotoServerManager) -> None:
    """Toolbar can be constructed with a moto-backed context."""
    from gui4aws.gui.toolbar import Toolbar

    context = moto_context(moto_server)
    toolbar = Toolbar(tk_root, context)
    pump(tk_root)
    assert toolbar.winfo_exists()
    toolbar.destroy()


def test_moto_reset_clears_state(moto_server: MotoServerManager) -> None:
    """reset_state wipes resources created in a previous call."""
    import boto3

    from gui4aws.execution.boto3_executor import Boto3Result
    from gui4aws.services.sqs.actions import LIST_QUEUES
    from gui4aws.services.sqs.views import to_queue_summaries

    sqs = boto3.client("sqs", region_name="us-east-1", endpoint_url=moto_server.endpoint_url)
    sqs.create_queue(QueueName="ephemeral-queue")

    context = moto_context(moto_server)
    before = context.execute(LIST_QUEUES, inputs={})
    assert isinstance(before, Boto3Result)
    assert any(s.name == "ephemeral-queue" for s in to_queue_summaries(before.response))

    moto_server.reset_state()

    # Use a fresh context so the cache doesn't hide the reset.
    context2 = moto_context(moto_server)
    after = context2.execute(LIST_QUEUES, inputs={})
    assert isinstance(after, Boto3Result)
    assert not any(s.name == "ephemeral-queue" for s in to_queue_summaries(after.response))
