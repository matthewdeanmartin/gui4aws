"""Script generation tests."""

from __future__ import annotations

from gui4aws.execution.endpoint_config import EndpointConfig, EndpointMode
from gui4aws.execution.script_generator import generate_cli_script, generate_python_script
from gui4aws.services.aurora.actions import (
    DESCRIBE_DB_CLUSTERS,
    RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
)


def test_cli_script_for_describe_db_clusters() -> None:
    """Describe clusters with no filter renders a minimal CLI line."""
    text = generate_cli_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name="default",
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "aws rds describe-db-clusters" in text
    assert "--region us-east-1" in text
    assert "--profile default" in text
    assert "--endpoint-url" not in text


def test_cli_script_includes_endpoint_url_for_moto() -> None:
    """Moto endpoint mode propagates --endpoint-url."""
    text = generate_cli_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig(mode=EndpointMode.MOTO),
    )
    assert "--endpoint-url" in text
    assert "127.0.0.1:5000" in text


def test_python_script_for_describe_db_clusters() -> None:
    """Python export is paste-ready."""
    text = generate_python_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name="default",
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "import boto3" in text
    assert 'session.client("rds")' in text
    assert "describe_db_clusters()" in text


def test_python_script_for_restore_includes_required_params() -> None:
    """Restore export inlines the required PascalCase kwargs."""
    inputs = {
        "new_cluster_identifier": "restored-cluster",
        "snapshot_identifier": "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snap",
        "engine": "aurora-postgresql",
    }
    text = generate_python_script(
        RESTORE_DB_CLUSTER_FROM_SNAPSHOT,
        inputs=inputs,
        profile_name="default",
        region_name="us-east-1",
        endpoint_config=EndpointConfig(),
    )
    assert "restore_db_cluster_from_snapshot(" in text
    assert "DBClusterIdentifier='restored-cluster'" in text
    assert "SnapshotIdentifier=" in text
    assert "Engine='aurora-postgresql'" in text


def test_python_script_includes_endpoint_url_for_custom() -> None:
    """Custom endpoint URL is inlined into the boto3 client construction."""
    text = generate_python_script(
        DESCRIBE_DB_CLUSTERS,
        inputs={},
        profile_name=None,
        region_name="us-east-1",
        endpoint_config=EndpointConfig.for_mode(EndpointMode.CUSTOM, "http://localhost:5555"),
    )
    assert "endpoint_url='http://localhost:5555'" in text
