"""Tests for config.py."""

from __future__ import annotations

from pathlib import Path

from gui4aws.config import (
    AppConfig,
    config_path,
    load_config,
    network_config_from_app_config,
    save_config,
)


def test_config_path() -> None:
    path = config_path()
    assert path.name == "config.toml"
    assert "gui4aws" in str(path)


def test_load_default_config(tmp_path: Path) -> None:
    # No file exists
    config = load_config(tmp_path / "missing.toml")
    assert config.default_region == "us-east-1"


def test_save_and_load_config(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    config = AppConfig(default_profile="test-prof", window_width=100, local_endpoints={"s3": "http://loc"})
    save_config(config, path)

    loaded = load_config(path)
    assert loaded.default_profile == "test-prof"
    assert loaded.window_width == 100
    assert loaded.local_endpoints["s3"] == "http://loc"


def test_network_settings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    config = AppConfig(
        network_use_env_proxy=False,
        network_http_proxy="http://proxy.corp:8080",
        network_ca_bundle_path=r"C:\certs\enterprise.pem",
        network_verify_ssl=False,
    )
    save_config(config, path)

    loaded = load_config(path)
    assert loaded.network_use_env_proxy is False
    assert loaded.network_http_proxy == "http://proxy.corp:8080"
    # Windows path with backslashes survives the TOML round-trip.
    assert loaded.network_ca_bundle_path == r"C:\certs\enterprise.pem"
    assert loaded.network_verify_ssl is False

    net = network_config_from_app_config(loaded)
    assert net.http_proxy == "http://proxy.corp:8080"
    assert net.ca_bundle_path == r"C:\certs\enterprise.pem"
    assert net.verify_ssl is False
    assert net.use_env_proxy is False


def test_load_json_config(tmp_path: Path) -> None:
    path = tmp_path / "config.json"
    path.write_text('{"default_region": "us-west-2", "window": {"width": 800}}', encoding="utf-8")

    config = load_config(path)
    assert config.default_region == "us-west-2"
    assert config.window_width == 800
