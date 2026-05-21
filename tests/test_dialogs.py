"""Headless tests for the dialog decision-logic helpers.

The Tk Toplevel widgets themselves are exercised by the GUI integration tests; here we just
verify the pure-Python logic that determines confirm/cancel state.
"""

from __future__ import annotations

from gui4aws.gui.confirmation_dialog import TypedConfirmation, matches
from gui4aws.gui.review_dialog import ReviewDecision, needs_review, warning_banner
from gui4aws.models import RiskLevel
from gui4aws.services.aurora.actions import (
    CREATE_DB_CLUSTER_SNAPSHOT,
    DESCRIBE_DB_CLUSTERS,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
)


def test_needs_review_false_for_read_only() -> None:
    """Read-only actions skip the review screen."""
    assert needs_review(DESCRIBE_DB_CLUSTERS) is False


def test_needs_review_true_for_safe_write() -> None:
    """Safe-write actions require review."""
    assert needs_review(CREATE_DB_CLUSTER_SNAPSHOT) is True


def test_needs_review_true_for_cost_affecting() -> None:
    """Cost-affecting actions require review."""
    assert needs_review(RESTORE_DB_CLUSTER_FROM_SNAPSHOT) is True


def test_warning_banner_only_for_cost_or_destructive() -> None:
    """Banner appears for cost-affecting and destructive actions, otherwise None."""
    assert warning_banner(DESCRIBE_DB_CLUSTERS) is None
    assert warning_banner(CREATE_DB_CLUSTER_SNAPSHOT) is None  # safe_write -> no banner
    assert warning_banner(RESTORE_DB_CLUSTER_FROM_SNAPSHOT) is not None
    assert RiskLevel.COST_AFFECTING.value not in warning_banner(RESTORE_DB_CLUSTER_FROM_SNAPSHOT)  # human text


def test_review_decision_confirm_path() -> None:
    """Confirming a review decision sets confirmed=True and locks the state."""
    decision = ReviewDecision(action=CREATE_DB_CLUSTER_SNAPSHOT)
    decision.confirm()
    assert decision.confirmed
    assert not decision.cancelled
    assert decision.is_resolved()
    # Late cancel is ignored once confirmed.
    decision.cancel()
    assert not decision.cancelled


def test_review_decision_cancel_path() -> None:
    """Cancelling a review decision locks the state."""
    decision = ReviewDecision(action=CREATE_DB_CLUSTER_SNAPSHOT)
    decision.cancel()
    assert decision.cancelled
    assert not decision.confirmed
    decision.confirm()  # ignored
    assert not decision.confirmed


def test_typed_confirmation_matches_exact() -> None:
    """Whitespace-trimmed, case-sensitive matching."""
    assert matches("prod-cluster", "prod-cluster")
    assert matches("prod-cluster", "  prod-cluster  ")
    assert not matches("prod-cluster", "PROD-CLUSTER")
    assert not matches("prod-cluster", "prod-cluster!")
    assert not matches("", "")  # empty expected never matches


def test_typed_confirmation_can_confirm_only_when_matching() -> None:
    """can_confirm() returns True only after the typed text matches."""
    confirmation = TypedConfirmation(expected_text="my-cluster")
    assert not confirmation.can_confirm()
    confirmation.set_typed("my")
    assert not confirmation.can_confirm()
    confirmation.set_typed("my-cluster")
    assert confirmation.can_confirm()
    assert confirmation.confirm() is True
    assert confirmation.confirmed
    # Late cancel is ignored.
    confirmation.cancel()
    assert not confirmation.cancelled


def test_typed_confirmation_confirm_blocked_on_mismatch() -> None:
    """confirm() returns False when the typed text does not match."""
    confirmation = TypedConfirmation(expected_text="my-cluster")
    confirmation.set_typed("nope")
    assert confirmation.confirm() is False
    assert not confirmation.confirmed
