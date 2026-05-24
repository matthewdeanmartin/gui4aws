"""Tests for config.py."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from gui4aws.config import AppConfig, config_path, load_config, save_config


def test_config_path():
    path = config_path()
    assert path.name == "config.toml"
    assert "gui4aws" in str(path)


def test_load_default_config(tmp_path: Path):
    # No file exists
    config = load_config(tmp_path / "missing.toml")
    assert config.default_region == "us-east-1"


def test_save_and_load_config(tmp_path: Path):
    path = tmp_path / "config.toml"
    config = AppConfig(
        default_profile="test-prof",
        window_width=100,
        local_endpoints={"s3": "http://loc"}
    )
    save_config(config, path)
    
    loaded = load_config(path)
    assert loaded.default_profile == "test-prof"
    assert loaded.window_width == 100
    assert loaded.local_endpoints["s3"] == "http://loc"


def test_load_json_config(tmp_path: Path):
    path = tmp_path / "config.json"
    path.write_text('{"default_region": "us-west-2", "window": {"width": 800}}', encoding="utf-8")
    
    config = load_config(path)
    assert config.default_region == "us-west-2"
    assert config.window_width == 800
