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

__all__ = [
    "AppConfig",
    "config_path",
    "load_config",
    "network_config_from_app_config",
    "save_config",
]


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
    # Network / proxy / TLS-trust settings (see execution.network_config.NetworkConfig).
    network_use_env_proxy: bool = True
    network_http_proxy: str = ""
    network_https_proxy: str = ""
    network_no_proxy: str = ""
    network_ca_bundle_path: str = ""
    network_client_cert_path: str = ""
    network_verify_ssl: bool = True


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


def network_config_from_app_config(config: AppConfig) -> Any:
    """Build a ``NetworkConfig`` from the persisted ``AppConfig`` fields."""
    from gui4aws.execution.network_config import NetworkConfig

    return NetworkConfig(
        use_env_proxy=config.network_use_env_proxy,
        http_proxy=config.network_http_proxy,
        https_proxy=config.network_https_proxy,
        no_proxy=config.network_no_proxy,
        ca_bundle_path=config.network_ca_bundle_path,
        client_cert_path=config.network_client_cert_path,
        verify_ssl=config.network_verify_ssl,
    )


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
    # Coerce a legacy/unknown endpoint mode (e.g. the removed "docker") back to AWS.
    if config.default_endpoint_mode not in {"aws", "moto", "robotocore", "custom"}:
        config.default_endpoint_mode = "aws"
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
    network = data.get("network", {})
    if isinstance(network, dict):
        if "use_env_proxy" in network:
            config.network_use_env_proxy = bool(network["use_env_proxy"])
        if "http_proxy" in network:
            config.network_http_proxy = str(network["http_proxy"])
        if "https_proxy" in network:
            config.network_https_proxy = str(network["https_proxy"])
        if "no_proxy" in network:
            config.network_no_proxy = str(network["no_proxy"])
        if "ca_bundle_path" in network:
            config.network_ca_bundle_path = str(network["ca_bundle_path"])
        if "client_cert_path" in network:
            config.network_client_cert_path = str(network["client_cert_path"])
        if "verify_ssl" in network:
            config.network_verify_ssl = bool(network["verify_ssl"])
    return config


def _toml_str(value: str) -> str:
    """Render a string as a TOML basic-string literal, escaping backslashes/quotes.

    Windows CA-bundle paths contain backslashes, which must be escaped in a TOML
    basic string (or the file fails to parse on reload).
    """
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


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
        "",
        "[network]",
        f"use_env_proxy = {'true' if config.network_use_env_proxy else 'false'}",
        f"http_proxy = {_toml_str(config.network_http_proxy)}",
        f"https_proxy = {_toml_str(config.network_https_proxy)}",
        f"no_proxy = {_toml_str(config.network_no_proxy)}",
        f"ca_bundle_path = {_toml_str(config.network_ca_bundle_path)}",
        f"client_cert_path = {_toml_str(config.network_client_cert_path)}",
        f"verify_ssl = {'true' if config.network_verify_ssl else 'false'}",
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
