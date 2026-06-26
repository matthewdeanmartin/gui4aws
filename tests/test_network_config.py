"""Tests for NetworkConfig and its propagation into executors and scripts."""

from __future__ import annotations

from gui4aws.execution.aws_cli_executor import AwsCliExecutor
from gui4aws.execution.boto3_executor import Boto3Executor
from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.network_config import NetworkConfig
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.services.aurora.actions import DESCRIBE_DB_CLUSTERS


def test_default_is_default() -> None:
    assert NetworkConfig().is_default()
    assert not NetworkConfig(http_proxy="http://p:8080").is_default()


def test_explicit_proxies_map() -> None:
    cfg = NetworkConfig(http_proxy="http://p:8080", https_proxy="http://s:8443")
    assert cfg.explicit_proxies() == {"http": "http://p:8080", "https": "http://s:8443"}
    assert NetworkConfig().explicit_proxies() == {}


def test_botocore_verify_values() -> None:
    assert NetworkConfig().botocore_verify() is None
    assert NetworkConfig(ca_bundle_path="/etc/ca.pem").botocore_verify() == "/etc/ca.pem"
    assert NetworkConfig(verify_ssl=False).botocore_verify() is False
    # verify_ssl=False wins over a CA bundle.
    assert NetworkConfig(verify_ssl=False, ca_bundle_path="/x.pem").botocore_verify() is False


def test_env_overlay_sets_proxy_and_ca() -> None:
    cfg = NetworkConfig(http_proxy="http://p:8080", ca_bundle_path="/x.pem", no_proxy="localhost")
    overlay = cfg.env_overlay()
    assert overlay["HTTP_PROXY"] == "http://p:8080"
    assert overlay["http_proxy"] == "http://p:8080"
    assert overlay["NO_PROXY"] == "localhost"
    assert overlay["AWS_CA_BUNDLE"] == "/x.pem"


def test_env_overlay_unsets_proxy_when_env_ignored() -> None:
    overlay = NetworkConfig(use_env_proxy=False).env_overlay()
    # All proxy env vars get marked for removal (empty string).
    assert overlay["HTTP_PROXY"] == ""
    assert overlay["https_proxy"] == ""


def test_apply_to_environ_removes_and_sets() -> None:
    base = {"HTTP_PROXY": "http://inherited:1", "OTHER": "keep"}
    # use_env_proxy=False with no explicit proxy strips inherited proxy vars.
    env = NetworkConfig(use_env_proxy=False).apply_to_environ(base)
    assert "HTTP_PROXY" not in env
    assert env["OTHER"] == "keep"
    # An explicit proxy is set even when env is otherwise ignored.
    env2 = NetworkConfig(use_env_proxy=False, https_proxy="http://x:9").apply_to_environ(base)
    assert env2["HTTPS_PROXY"] == "http://x:9"


def test_boto3_executor_client_config_has_proxies() -> None:
    ex = Boto3Executor(
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
        network_config=NetworkConfig(https_proxy="http://s:8443"),
    )
    config = ex._client_config()  # white-box check
    assert getattr(config, "proxies") == {"https": "http://s:8443"}  # noqa: B009


def test_boto3_executor_default_config_unchanged() -> None:
    ex = Boto3Executor(profile_name=None, region_name="us-east-1", endpoint_config=EndpointConfig())
    # No proxy and env honored -> reuse the shared config object untouched.
    assert getattr(ex._client_config(), "proxies") in (None, {})  # noqa: B009


def test_cli_executor_adds_ca_bundle_flag() -> None:
    ex = AwsCliExecutor(
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
        network_config=NetworkConfig(ca_bundle_path="/etc/ca.pem"),
    )
    argv = ex.build_argv(DESCRIBE_DB_CLUSTERS, inputs={})
    assert "--ca-bundle" in argv
    assert "/etc/ca.pem" in argv


def test_cli_executor_adds_no_verify_ssl_flag() -> None:
    ex = AwsCliExecutor(
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
        network_config=NetworkConfig(verify_ssl=False),
    )
    argv = ex.build_argv(DESCRIBE_DB_CLUSTERS, inputs={})
    assert "--no-verify-ssl" in argv
    assert "--ca-bundle" not in argv


def test_cli_script_includes_proxy_exports_and_ca_bundle() -> None:
    text = generate_cli_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
        network_config=NetworkConfig(https_proxy="http://s:8443", ca_bundle_path="/etc/ca.pem"),
    )
    assert "export HTTPS_PROXY=" in text
    assert "http://s:8443" in text
    assert "--ca-bundle" in text


def test_python_script_includes_config_and_verify() -> None:
    text = generate_python_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
        network_config=NetworkConfig(https_proxy="http://s:8443", ca_bundle_path="/etc/ca.pem"),
    )
    assert "from botocore.config import Config" in text
    assert "proxies=" in text
    assert "verify='/etc/ca.pem'" in text


def test_python_script_no_verify_false() -> None:
    text = generate_python_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(mode=EndpointMode.MOTO),
        network_config=NetworkConfig(verify_ssl=False),
    )
    assert "verify=False" in text
