"""Tests for demo_resources.py."""

from __future__ import annotations

from gui4aws.demo_resources import seed_demo_resources


def test_seed_demo_resources(mock_aws_env: None) -> None:
    # Run seeding in Moto environment
    report = seed_demo_resources(region_name="us-east-1")

    # Check that we got a report with various resources
    assert "vpcs" in report
    assert "s3_buckets" in report
    assert "iam_users" in report
    assert "ssm_parameters" in report

    assert len(report["vpcs"]) > 0
    assert len(report["s3_buckets"]) > 0
    assert len(report["iam_users"]) > 0
