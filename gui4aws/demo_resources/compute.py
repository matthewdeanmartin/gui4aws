"""Seed demo Lambda functions."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _make_lambda_zip() -> bytes:
    """Create a minimal in-memory deployment zip containing a handler module."""
    import io
    import zipfile

    handler_code = (
        "def handler(event, context):\n"
        '    return {"statusCode": 200, "body": "Hello from gui4aws demo"}\n'
    )
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("handler.py", handler_code)
    return buf.getvalue()


def seed_lambda(lambda_client: Any, iam: Any) -> dict[str, list[str]]:
    """Seed demo Lambda functions and their execution roles.

    Creates sample Python-based serverless functions to demonstrate function
    browsing, configuration, and IAM role association in the GUI.
    """
    import json

    created: dict[str, list[str]] = {"lambda_functions": []}

    zip_bytes = _make_lambda_zip()

    # Moto validates that the role actually exists in IAM, so create it first.
    demo_role_arn = "arn:aws:iam::123456789012:role/DemoLambdaRole"
    try:
        resp = iam.create_role(
            RoleName="DemoLambdaRole",
            AssumeRolePolicyDocument=json.dumps(
                {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"Service": "lambda.amazonaws.com"},
                            "Action": "sts:AssumeRole",
                        }
                    ],
                }
            ),
            Description="Demo IAM role for gui4aws Lambda functions",
        )
        demo_role_arn = resp["Role"]["Arn"]
        logger.info("created IAM role DemoLambdaRole: %s", demo_role_arn)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        logger.warning("could not create IAM role DemoLambdaRole: %s", exc)

    functions = [
        (
            "demo-order-processor",
            "python3.11",
            "handler.handler",
            "Demo Lambda: processes orders from SQS",
        ),
        (
            "demo-notification-sender",
            "python3.11",
            "handler.handler",
            "Demo Lambda: sends email/SMS notifications",
        ),
    ]

    for function_name, runtime, handler, description in functions:
        try:
            lambda_client.create_function(
                FunctionName=function_name,
                Runtime=runtime,
                Role=demo_role_arn,
                Handler=handler,
                Code={"ZipFile": zip_bytes},
                Description=description,
                Timeout=30,
                MemorySize=128,
                Tags={
                    "gui4aws:demo": "true",
                    "Name": function_name,
                },
            )
            logger.info("created Lambda function %s", function_name)
            created["lambda_functions"].append(function_name)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.warning("skipped Lambda function %s: %s", function_name, exc)

    return created
