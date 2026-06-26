"""Tests for demo_resources.py."""

from __future__ import annotations

from gui4aws.demo_resources import _seed_with_client_factory


def test_seed_demo_resources(mock_aws_env: None) -> None:
    # Run seeding in the in-process Moto (mock_aws) environment. There is no HTTP
    # endpoint to verify here, so we drive the seeders directly via a client
    # factory rather than the verified public entry point.
    from typing import Any

    import boto3

    def client(service: str) -> Any:
        return boto3.client(service, region_name="us-east-1")  # type: ignore[call-overload]

    report = _seed_with_client_factory(client, is_robotocore=False)

    # Check that we got a report with various resources
    assert "vpcs" in report
    assert "s3_buckets" in report
    assert "iam_users" in report
    assert "ssm_parameters" in report

    assert len(report["vpcs"]) > 0
    assert len(report["s3_buckets"]) > 0
    assert len(report["iam_users"]) > 0
