"""Moto-backed tests for SES actions."""

from __future__ import annotations

import boto3
import pytest

from gui4aws.app import AppContext
from gui4aws.execution.boto3_executor import Boto3Result
from gui4aws.services.ses.actions import (
    DELETE_IDENTITY,
    LIST_IDENTITIES,
    LIST_TEMPLATES,
    VERIFY_EMAIL_IDENTITY,
)
from gui4aws.services.ses.views import to_identity_summaries, to_template_summaries


def test_list_identities_empty(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_IDENTITIES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_identity_summaries(result.response)
    assert summaries == []


def test_identity_actions(mock_aws_env: None) -> None:
    context = AppContext(region_name="us-east-1")
    
    # Verify
    result = context.execute(VERIFY_EMAIL_IDENTITY, inputs={"email_address": "test@example.com"})
    assert isinstance(result, Boto3Result)

    # List
    list_result = context.execute(LIST_IDENTITIES, inputs={})
    summaries = to_identity_summaries(list_result.response)
    assert any(s.identity == "test@example.com" for s in summaries)

    # Delete
    del_result = context.execute(DELETE_IDENTITY, inputs={"identity": "test@example.com"})
    assert isinstance(del_result, Boto3Result)


def test_list_templates(mock_aws_env: None) -> None:
    ses = boto3.client("ses", region_name="us-east-1")
    ses.create_template(
        Template={
            "TemplateName": "test-template",
            "SubjectPart": "Hello",
            "TextPart": "World"
        }
    )

    context = AppContext(region_name="us-east-1")
    result = context.execute(LIST_TEMPLATES, inputs={})
    assert isinstance(result, Boto3Result)
    summaries = to_template_summaries(result.response)
    assert any(s.name == "test-template" for s in summaries)
