"""Shared constants and helpers used across demo resource seeders."""

from __future__ import annotations

DEMO_TAG = {"Key": "gui4aws:demo", "Value": "true"}
DEMO_DESC_TAG_KEY = "Description"


def tags(*extra: dict[str, str]) -> list[dict[str, str]]:
    """Return a tag list with the standard demo tag plus any extras."""
    return [DEMO_TAG, *extra]
