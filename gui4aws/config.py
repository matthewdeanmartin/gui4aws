"""User configuration: load/save preferences in a per-OS config dir.

We hand-roll a minimal TOML writer to stay stdlib-only on the write path. Reading uses
``tomllib`` (Python 3.11+). For Python 3.10 we fall back to JSON.
"""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

__all__ = ["AppConfig", "config_path", "load_config", "save_config"]


@dataclass
class AppConfig:
    """User-visible app config."""

    default_profile: str = ""
    default_region: str = "us-east-1"
    default_partition: str = "aws"
    default_mode: str = "boto3"
    default_endpoint_mode: str = "aws"
    window_width: int = 1400
    window_height: int = 900
    history_enabled: bool = True
    history_max_entries: int = 500
    local_endpoints: dict[str, str] = field(default_factory=dict)


def config_path() -> Path:
    """Return the OS-appropriate config file path."""
    if sys.platform.startswith("win"):
        base = Path(os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming")))
        return base / "gui4aws" / "config.toml"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "gui4aws" / "config.toml"
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / "gui4aws" / "config.toml"


def load_config(path: Path | None = None) -> AppConfig:
    """Load config from disk, returning defaults if no file exists."""
    if path is None:
        path = config_path()
    if not path.exists():
        return AppConfig()
    raw = path.read_text(encoding="utf-8")
    data: dict[str, Any]
    if path.suffix == ".json":
        data = json.loads(raw)
    else:
        try:
            if sys.version_info >= (3, 11):
                import tomllib
            else:
                import tomli as tomllib

            data = tomllib.loads(raw)
        except ImportError:  # pragma: no cover
            # Fallback if neither is available (should not happen with our deps)
            data = json.loads(raw)
    return apply(data)


def save_config(config: AppConfig, path: Path | None = None) -> None:
    """Save config to disk in TOML."""
    if path is None:
        path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_toml(config), encoding="utf-8")


def apply(data: dict[str, Any]) -> AppConfig:
    """Map a raw dictionary (from TOML/JSON) onto an AppConfig instance."""
    config = AppConfig()
    for key in (
        "default_profile",
        "default_region",
        "default_partition",
        "default_mode",
        "default_endpoint_mode",
    ):
        if key in data:
            setattr(config, key, str(data[key]))
    window = data.get("window", {})
    if isinstance(window, dict):
        if "width" in window:
            config.window_width = int(window["width"])
        if "height" in window:
            config.window_height = int(window["height"])
    history = data.get("history", {})
    if isinstance(history, dict):
        if "enabled" in history:
            config.history_enabled = bool(history["enabled"])
        if "max_entries" in history:
            config.history_max_entries = int(history["max_entries"])
    endpoints = data.get("local_endpoints", {})
    if isinstance(endpoints, dict):
        for service, value in endpoints.items():
            if isinstance(value, dict) and "endpoint_url" in value:
                config.local_endpoints[str(service)] = str(value["endpoint_url"])
            elif isinstance(value, str):
                config.local_endpoints[str(service)] = value
    return config


def render_toml(config: AppConfig) -> str:
    """Serialize AppConfig to a TOML string."""
    lines = [
        f'default_profile = "{config.default_profile}"',
        f'default_region = "{config.default_region}"',
        f'default_partition = "{config.default_partition}"',
        f'default_mode = "{config.default_mode}"',
        f'default_endpoint_mode = "{config.default_endpoint_mode}"',
        "",
        "[window]",
        f"width = {config.window_width}",
        f"height = {config.window_height}",
        "",
        "[history]",
        f"enabled = {'true' if config.history_enabled else 'false'}",
        f"max_entries = {config.history_max_entries}",
    ]
    for service, url in sorted(config.local_endpoints.items()):
        lines.extend(
            [
                "",
                f"[local_endpoints.{service}]",
                f'endpoint_url = "{url}"',
            ]
        )
    lines.append("")
    return "\n".join(lines)
