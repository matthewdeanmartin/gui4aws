"""SQS action definitions."""

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
from gui4aws.services.sqs.views import to_queue_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_QUEUE",
    "DELETE_QUEUE",
    "LIST_QUEUES",
    "PURGE_QUEUE",
    "RECEIVE_MESSAGES",
    "SEND_MESSAGE",
]


LIST_QUEUES = ActionDefinition(
    action_id="sqs.list_queues",
    display_name="List queues",
    service_id="sqs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="queue_name_prefix",
            label="Queue name prefix (optional)",
            required=False,
            help_text="Filter queues by name prefix.",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="list-queues",
        arg_map={"queue_name_prefix": "queue-name-prefix"},
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="list_queues",
        param_map={"queue_name_prefix": "QueueNamePrefix"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "url", "approximate_messages", "visibility_timeout", "arn"),
        title="SQS Queues",
    ),
    iam_permissions=("sqs:ListQueues",),
    description="List SQS queues, optionally filtered by name prefix.",
    view=to_queue_summaries,
)


CREATE_QUEUE = ActionDefinition(
    action_id="sqs.create_queue",
    display_name="Create queue",
    service_id="sqs",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="queue_name", label="Queue name", required=True, help_text="Use .fifo suffix for FIFO queues."),
        InputField(
            name="visibility_timeout",
            label="Visibility timeout (seconds)",
            kind="int",
            required=False,
            default="30",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="create-queue",
        arg_map={"queue_name": "queue-name"},
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="create_queue",
        param_map={"queue_name": "QueueName"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create queue result"),
    iam_permissions=("sqs:CreateQueue",),
    description="Create a new SQS queue.",
    cache_refresh_nav_ids=("queues",),
)


DELETE_QUEUE = ActionDefinition(
    action_id="sqs.delete_queue",
    display_name="Delete queue",
    service_id="sqs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="queue_url",
            label="Queue URL",
            required=True,
            help_text="Full SQS queue URL.",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="delete-queue",
        arg_map={"queue_url": "queue-url"},
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="delete_queue",
        param_map={"queue_url": "QueueUrl"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete queue result"),
    iam_permissions=("sqs:DeleteQueue",),
    description="Permanently delete an SQS queue and all its messages.",
    cache_refresh_nav_ids=("queues",),
)


SEND_MESSAGE = ActionDefinition(
    action_id="sqs.send_message",
    display_name="Send message",
    service_id="sqs",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="queue_url", label="Queue URL", required=True),
        InputField(
            name="message_body",
            label="Message body",
            kind="multiline",
            required=True,
        ),
        InputField(
            name="delay_seconds",
            label="Delay (seconds)",
            kind="int",
            required=False,
            default="0",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="send-message",
        arg_map={"queue_url": "queue-url", "message_body": "message-body", "delay_seconds": "delay-seconds"},
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="send_message",
        param_map={"queue_url": "QueueUrl", "message_body": "MessageBody", "delay_seconds": "DelaySeconds"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Send message result"),
    iam_permissions=("sqs:SendMessage",),
    description="Send a message to an SQS queue.",
)


RECEIVE_MESSAGES = ActionDefinition(
    action_id="sqs.receive_messages",
    display_name="Receive messages",
    service_id="sqs",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="queue_url", label="Queue URL", required=True),
        InputField(
            name="max_number_of_messages",
            label="Max messages (1-10)",
            kind="int",
            required=False,
            default="1",
        ),
        InputField(
            name="wait_time_seconds",
            label="Wait time (seconds, 0-20)",
            kind="int",
            required=False,
            default="0",
            help_text="Long polling wait time. 0 = short poll.",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="receive-message",
        arg_map={
            "queue_url": "queue-url",
            "max_number_of_messages": "max-number-of-messages",
            "wait_time_seconds": "wait-time-seconds",
        },
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="receive_message",
        param_map={
            "queue_url": "QueueUrl",
            "max_number_of_messages": "MaxNumberOfMessages",
            "wait_time_seconds": "WaitTimeSeconds",
        },
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Received messages"),
    iam_permissions=("sqs:ReceiveMessage",),
    description="Receive up to 10 messages from an SQS queue.",
)


PURGE_QUEUE = ActionDefinition(
    action_id="sqs.purge_queue",
    display_name="Purge queue",
    service_id="sqs",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="queue_url",
            label="Queue URL",
            required=True,
            help_text="All messages in the queue will be deleted.",
        ),
    ),
    cli_template=CliTemplate(
        service="sqs",
        command="purge-queue",
        arg_map={"queue_url": "queue-url"},
    ),
    boto3_template=Boto3Template(
        service="sqs",
        operation="purge_queue",
        param_map={"queue_url": "QueueUrl"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Purge queue result"),
    iam_permissions=("sqs:PurgeQueue",),
    description="Delete all messages from an SQS queue. This action cannot be undone.",
)


ALL_ACTIONS = (
    LIST_QUEUES,
    CREATE_QUEUE,
    DELETE_QUEUE,
    SEND_MESSAGE,
    RECEIVE_MESSAGES,
    PURGE_QUEUE,
)
