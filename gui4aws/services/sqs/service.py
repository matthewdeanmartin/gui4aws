"""ServiceDefinition for SQS."""

from __future__ import annotations

from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.sqs.actions import (
    ALL_ACTIONS,
    CREATE_QUEUE,
    DELETE_QUEUE,
    LIST_QUEUES,
    PURGE_QUEUE,
    RECEIVE_MESSAGES,
    SEND_MESSAGE,
)

__all__ = ["SERVICE"]


SERVICE = ServiceDefinition(
    service_id="sqs",
    display_name="SQS",
    boto3_service_name="sqs",
    cli_service_name="sqs",
    navigation_items=(
        NavigationItem(
            item_id="queues",
            display_name="Queues",
            default_action_id=LIST_QUEUES.action_id,
            row_actions=(
                RowAction(
                    action_id=SEND_MESSAGE.action_id,
                    button_label="Send Message",
                    prefill={"queue_url": "url"},
                ),
                RowAction(
                    action_id=RECEIVE_MESSAGES.action_id,
                    button_label="Receive Messages",
                    prefill={"queue_url": "url"},
                ),
                RowAction(
                    action_id=CREATE_QUEUE.action_id,
                    button_label="Create Queue",
                    prefill={},
                ),
                RowAction(
                    action_id=PURGE_QUEUE.action_id,
                    button_label="Purge Queue",
                    prefill={"queue_url": "url"},
                ),
                RowAction(
                    action_id=DELETE_QUEUE.action_id,
                    button_label="Delete Queue",
                    prefill={"queue_url": "url"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
