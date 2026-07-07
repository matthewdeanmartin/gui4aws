"""Sprint 01 service-polish regression tests."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from gui4aws.models import RowAction
from gui4aws.services.aurora.models import AuroraClusterSummary
from gui4aws.services.aurora.service import SERVICE as AURORA_SERVICE
from gui4aws.services.ecs.actions import LIST_CLUSTERS
from gui4aws.services.ecs.views import to_cluster_summaries
from gui4aws.services.iam.actions import GET_POLICY
from gui4aws.services.iam.service import SERVICE as IAM_SERVICE
from gui4aws.services.kms.actions import LIST_KEYS
from gui4aws.services.kms.views import to_key_summaries
from gui4aws.services.sqs.actions import LIST_QUEUES
from gui4aws.services.sqs.views import to_queue_summaries


class FakePaginator:
    """Tiny paginator used by the fake boto3 clients below."""

    def __init__(self, pages: Iterable[dict[str, Any]]) -> None:
        self.pages = list(pages)

    def paginate(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Return the stored pages and record no extra behavior."""
        del kwargs
        return self.pages


class FakeEcsClient:
    """Enough ECS client behavior for list+describe cluster enrichment."""

    def get_paginator(self, operation_name: str) -> FakePaginator:
        """Return fake cluster pages."""
        assert operation_name == "list_clusters"
        return FakePaginator([{"clusterArns": ["arn:aws:ecs:us-east-1:123:cluster/prod"]}])

    def describe_clusters(self, clusters: list[str]) -> dict[str, Any]:
        """Return full cluster details for the listed ARNs."""
        assert clusters == ["arn:aws:ecs:us-east-1:123:cluster/prod"]
        return {
            "clusters": [
                {
                    "clusterName": "prod",
                    "clusterArn": clusters[0],
                    "status": "ACTIVE",
                    "runningTasksCount": 7,
                    "pendingTasksCount": 2,
                    "activeServicesCount": 3,
                }
            ]
        }


class FakeKmsClient:
    """Enough KMS client behavior for list+describe key enrichment."""

    def get_paginator(self, operation_name: str) -> FakePaginator:
        """Return fake key pages."""
        assert operation_name == "list_keys"
        return FakePaginator([{"Keys": [{"KeyId": "key-1", "KeyArn": "arn:key-1"}]}])

    def describe_key(self, KeyId: str) -> dict[str, Any]:
        """Return full key metadata for the listed key."""
        assert KeyId == "key-1"
        return {
            "KeyMetadata": {
                "KeyId": "key-1",
                "Arn": "arn:key-1",
                "Description": "primary app key",
                "KeyState": "Enabled",
                "KeyUsage": "ENCRYPT_DECRYPT",
                "KeySpec": "SYMMETRIC_DEFAULT",
                "Enabled": True,
            }
        }


class FakeSqsClient:
    """Enough SQS client behavior for list+attribute queue enrichment."""

    def list_queues(self, **kwargs: Any) -> dict[str, Any]:
        """Return a queue URL and assert the prefix is passed through."""
        assert kwargs == {"QueueNamePrefix": "prod"}
        return {"QueueUrls": ["https://sqs.us-east-1.amazonaws.com/123456789012/prod-events"]}

    def get_queue_attributes(self, QueueUrl: str, AttributeNames: list[str]) -> dict[str, Any]:
        """Return common queue attributes."""
        assert QueueUrl.endswith("/prod-events")
        assert "QueueArn" in AttributeNames
        return {
            "Attributes": {
                "QueueArn": "arn:aws:sqs:us-east-1:123456789012:prod-events",
                "ApproximateNumberOfMessages": "42",
                "VisibilityTimeout": "60",
            }
        }


class FakeIamClient:
    """Enough IAM client behavior for active policy document lookup."""

    def get_policy(self, PolicyArn: str) -> dict[str, Any]:
        """Return policy metadata with a default version."""
        assert PolicyArn == "arn:aws:iam::123:policy/app"
        return {"Policy": {"Arn": PolicyArn, "DefaultVersionId": "v3"}}

    def get_policy_version(self, PolicyArn: str, VersionId: str) -> dict[str, Any]:
        """Return the requested policy document."""
        assert PolicyArn == "arn:aws:iam::123:policy/app"
        assert VersionId == "v3"
        return {
            "PolicyVersion": {
                "Document": {
                    "Version": "2012-10-17",
                    "Statement": [{"Effect": "Allow", "Action": "s3:ListBucket", "Resource": "*"}],
                }
            }
        }


def test_ecs_list_clusters_enriches_status_and_counts() -> None:
    """The default ECS cluster list should not render blank/zero ARN-only rows."""
    assert LIST_CLUSTERS.boto3_execute_fn is not None

    response = LIST_CLUSTERS.boto3_execute_fn(FakeEcsClient(), {})
    rows = to_cluster_summaries(response)

    assert rows[0].cluster_name == "prod"
    assert rows[0].status == "ACTIVE"
    assert rows[0].running_tasks == 7
    assert rows[0].pending_tasks == 2
    assert rows[0].active_services == 3


def test_kms_list_keys_enriches_describe_key_metadata() -> None:
    """KMS key list rows should contain useful metadata, not just ID/ARN."""
    assert LIST_KEYS.boto3_execute_fn is not None

    response = LIST_KEYS.boto3_execute_fn(FakeKmsClient(), {})
    rows = to_key_summaries(response)

    assert rows[0].key_id == "key-1"
    assert rows[0].description == "primary app key"
    assert rows[0].key_state == "Enabled"
    assert rows[0].enabled is True


def test_sqs_list_queues_includes_queue_arn_and_counts() -> None:
    """SQS detail rows should include QueueArn and common attributes."""
    assert LIST_QUEUES.boto3_execute_fn is not None

    response = LIST_QUEUES.boto3_execute_fn(FakeSqsClient(), {"queue_name_prefix": "prod"})
    rows = to_queue_summaries(response)

    assert rows[0].name == "prod-events"
    assert rows[0].arn == "arn:aws:sqs:us-east-1:123456789012:prod-events"
    assert rows[0].approximate_messages == "42"
    assert rows[0].visibility_timeout == "60"


def test_iam_get_policy_includes_active_document() -> None:
    """The policy action exposed from policy rows should show the document."""
    assert GET_POLICY.boto3_execute_fn is not None

    response = GET_POLICY.boto3_execute_fn(FakeIamClient(), {"policy_arn": "arn:aws:iam::123:policy/app"})

    assert response["DefaultVersionId"] == "v3"
    assert response["Document"]["Statement"][0]["Action"] == "s3:ListBucket"


def test_aurora_cluster_has_cross_service_kms_row_action() -> None:
    """Aurora clusters should expose a row action that opens KMS describe-key."""
    clusters_nav = next(item for item in AURORA_SERVICE.navigation_items if item.item_id == "clusters")
    kms_action = next(action for action in clusters_nav.row_actions if action.action_id == "kms.describe_key")
    row = AuroraClusterSummary(
        cluster_identifier="db1",
        engine="aurora-postgresql",
        engine_version="15",
        status="available",
        endpoint=None,
        reader_endpoint=None,
        multi_az=False,
        member_count=0,
        arn=None,
        kms_key_id="arn:aws:kms:us-east-1:123:key/key-1",
    )

    assert isinstance(kms_action, RowAction)
    assert kms_action.prefill["key_id"] == "kms_key_id"
    assert getattr(row, kms_action.prefill["key_id"]) == "arn:aws:kms:us-east-1:123:key/key-1"


def test_iam_policy_row_primary_action_mentions_document() -> None:
    """Policy rows should make document retrieval obvious."""
    policies_nav = next(item for item in IAM_SERVICE.navigation_items if item.item_id == "policies")
    labels = {action.action_id: action.button_label for action in policies_nav.row_actions}

    assert labels["iam.get_policy"] == "Get Policy + Document"
