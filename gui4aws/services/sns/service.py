"""ServiceDefinition for SNS."""
from __future__ import annotations
from gui4aws.models import NavigationItem, RowAction, ServiceDefinition
from gui4aws.services.sns.actions import (
    ALL_ACTIONS, CREATE_TOPIC, DELETE_TOPIC, LIST_SUBSCRIPTIONS,
    LIST_TOPICS, PUBLISH, SUBSCRIBE, UNSUBSCRIBE,
)

__all__ = ["SERVICE"]

SERVICE = ServiceDefinition(
    service_id="sns",
    display_name="SNS",
    boto3_service_name="sns",
    cli_service_name="sns",
    navigation_items=(
        NavigationItem(
            item_id="topics",
            display_name="Topics",
            default_action_id=LIST_TOPICS.action_id,
            row_actions=(
                RowAction(
                    action_id=PUBLISH.action_id,
                    button_label="Publish",
                    prefill={"topic_arn": "arn"},
                ),
                RowAction(
                    action_id=SUBSCRIBE.action_id,
                    button_label="Subscribe",
                    prefill={"topic_arn": "arn"},
                ),
                RowAction(
                    action_id=CREATE_TOPIC.action_id,
                    button_label="Create Topic",
                    prefill={},
                ),
                RowAction(
                    action_id=DELETE_TOPIC.action_id,
                    button_label="Delete Topic",
                    prefill={"topic_arn": "arn"},
                ),
            ),
        ),
        NavigationItem(
            item_id="subscriptions",
            display_name="Subscriptions",
            default_action_id=LIST_SUBSCRIPTIONS.action_id,
            row_actions=(
                RowAction(
                    action_id=UNSUBSCRIBE.action_id,
                    button_label="Unsubscribe",
                    prefill={"subscription_arn": "arn"},
                ),
            ),
        ),
    ),
    actions=ALL_ACTIONS,
)
