"""ServiceDefinition for S3."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition, SubAction
from gui4aws.services.s3.actions import (
    ALL_ACTIONS,
    CREATE_BUCKET,
    DELETE_BUCKET,
    DOWNLOAD_FILE,
    LIST_BUCKETS,
    LIST_OBJECTS,
    UPLOAD_FILE,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="s3",
    display_name="S3",
    boto3_service_name="s3",
    cli_service_name="s3api",
    navigation_items=(
        NavigationItem(
            item_id="buckets",
            display_name="Buckets",
            default_action_id=LIST_BUCKETS.action_id,
            row_actions=(
                RowAction(
                    action_id=LIST_OBJECTS.action_id,
                    button_label="List Objects",
                    prefill={"bucket_name": "name"},
                ),
                RowAction(
                    action_id=UPLOAD_FILE.action_id,
                    button_label="Upload File",
                    prefill={"bucket_name": "name"},
                ),
                RowAction(
                    action_id=DOWNLOAD_FILE.action_id,
                    button_label="Download File",
                    prefill={"bucket_name": "name"},
                ),
                RowAction(
                    action_id=CREATE_BUCKET.action_id,
                    button_label="Create Bucket",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_BUCKET.action_id,
                    button_label="Delete Bucket",
                    prefill={"bucket_name": "name"},
                ),
            ),
            sub_action=SubAction(
                action_id=LIST_OBJECTS.action_id,
                panel_label="Objects",
                prefill={"bucket_name": "name"},
                columns=("key", "size", "last_modified", "storage_class"),
                row_actions=(
                    RowAction(
                        action_id=DOWNLOAD_FILE.action_id,
                        button_label="Download",
                        prefill={"s3_key": "key"},
                    ),
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
