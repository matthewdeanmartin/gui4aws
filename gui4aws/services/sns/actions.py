"""SNS action definitions."""

from __future__ import annotations

from gui4aws.models import (
    ActionDefinition,
    Boto3Template,
    CliTemplate,
    InputField,
    ResultViewDefinition,
    ResultViewKind,
    RiskLevel,
)
from gui4aws.services.sns.views import to_subscription_summaries, to_topic_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_TOPIC",
    "DELETE_TOPIC",
    "LIST_SUBSCRIPTIONS",
    "LIST_TOPICS",
    "PUBLISH",
    "SUBSCRIBE",
    "UNSUBSCRIBE",
]

LIST_TOPICS = ActionDefinition(
    action_id="sns.list_topics",
    display_name="List topics",
    service_id="sns",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="sns", command="list-topics"),
    boto3_template=Boto3Template(service="sns", operation="list_topics"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "arn"),
        title="SNS Topics",
    ),
    iam_permissions=("sns:ListTopics",),
    description="List SNS topics in the current region.",
    view=to_topic_summaries,
)

CREATE_TOPIC = ActionDefinition(
    action_id="sns.create_topic",
    display_name="Create topic",
    service_id="sns",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="topic_name", label="Topic name", required=True),
        InputField(
            name="topic_type",
            label="Type",
            kind="choice",
            choices=("Standard", "FIFO"),
            default="Standard",
        ),
    ),
    cli_template=CliTemplate(service="sns", command="create-topic", arg_map={"topic_name": "name"}),
    boto3_template=Boto3Template(service="sns", operation="create_topic", param_map={"topic_name": "Name"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create topic result"),
    iam_permissions=("sns:CreateTopic",),
    description="Create a new SNS topic.",
    cache_refresh_nav_ids=("topics",),
)

DELETE_TOPIC = ActionDefinition(
    action_id="sns.delete_topic",
    display_name="Delete topic",
    service_id="sns",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="topic_arn", label="Topic ARN", required=True),),
    cli_template=CliTemplate(service="sns", command="delete-topic", arg_map={"topic_arn": "topic-arn"}),
    boto3_template=Boto3Template(service="sns", operation="delete_topic", param_map={"topic_arn": "TopicArn"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete topic result"),
    iam_permissions=("sns:DeleteTopic",),
    description="Delete an SNS topic and all its subscriptions.",
    cache_refresh_nav_ids=("topics",),
)

LIST_SUBSCRIPTIONS = ActionDefinition(
    action_id="sns.list_subscriptions",
    display_name="List subscriptions",
    service_id="sns",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="sns", command="list-subscriptions"),
    boto3_template=Boto3Template(service="sns", operation="list_subscriptions"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("subscription_id", "topic_arn", "protocol", "endpoint", "status"),
        title="SNS Subscriptions",
    ),
    iam_permissions=("sns:ListSubscriptions",),
    description="List all SNS subscriptions.",
    view=to_subscription_summaries,
)

SUBSCRIBE = ActionDefinition(
    action_id="sns.subscribe",
    display_name="Subscribe",
    service_id="sns",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="topic_arn", label="Topic ARN", required=True),
        InputField(
            name="protocol",
            label="Protocol",
            kind="choice",
            choices=("email", "email-json", "http", "https", "sqs", "lambda", "sms", "application"),
            default="email",
        ),
        InputField(
            name="endpoint", label="Endpoint", required=True, help_text="Email address, URL, SQS ARN, Lambda ARN, etc."
        ),
    ),
    cli_template=CliTemplate(
        service="sns",
        command="subscribe",
        arg_map={"topic_arn": "topic-arn", "protocol": "protocol", "endpoint": "notification-endpoint"},
    ),
    boto3_template=Boto3Template(
        service="sns",
        operation="subscribe",
        param_map={"topic_arn": "TopicArn", "protocol": "Protocol", "endpoint": "Endpoint"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Subscribe result"),
    iam_permissions=("sns:Subscribe",),
    description="Subscribe an endpoint to an SNS topic.",
    cache_refresh_nav_ids=("subscriptions",),
)

UNSUBSCRIBE = ActionDefinition(
    action_id="sns.unsubscribe",
    display_name="Unsubscribe",
    service_id="sns",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(InputField(name="subscription_arn", label="Subscription ARN", required=True),),
    cli_template=CliTemplate(service="sns", command="unsubscribe", arg_map={"subscription_arn": "subscription-arn"}),
    boto3_template=Boto3Template(
        service="sns", operation="unsubscribe", param_map={"subscription_arn": "SubscriptionArn"}
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Unsubscribe result"),
    iam_permissions=("sns:Unsubscribe",),
    description="Remove a subscription from an SNS topic.",
    cache_refresh_nav_ids=("subscriptions",),
)

PUBLISH = ActionDefinition(
    action_id="sns.publish",
    display_name="Publish message",
    service_id="sns",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="topic_arn", label="Topic ARN", required=True),
        InputField(name="message", label="Message", required=True, kind="multiline"),
        InputField(name="subject", label="Subject (optional)", required=False),
    ),
    cli_template=CliTemplate(
        service="sns",
        command="publish",
        arg_map={"topic_arn": "topic-arn", "message": "message", "subject": "subject"},
    ),
    boto3_template=Boto3Template(
        service="sns",
        operation="publish",
        param_map={"topic_arn": "TopicArn", "message": "Message", "subject": "Subject"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Publish result"),
    iam_permissions=("sns:Publish",),
    description="Publish a message to an SNS topic.",
)

ALL_ACTIONS = (
    LIST_TOPICS,
    CREATE_TOPIC,
    DELETE_TOPIC,
    LIST_SUBSCRIPTIONS,
    SUBSCRIBE,
    UNSUBSCRIBE,
    PUBLISH,
)
