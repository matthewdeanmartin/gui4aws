"""SES action definitions."""
from __future__ import annotations
from gui4aws.models import (
    ActionDefinition, Boto3Template, CliTemplate, InputField,
    ResultViewDefinition, ResultViewKind, RiskLevel,
)
from gui4aws.services.ses.views import to_identity_summaries, to_template_summaries

__all__ = [
    "ALL_ACTIONS",
    "DELETE_IDENTITY",
    "LIST_IDENTITIES",
    "LIST_TEMPLATES",
    "SEND_EMAIL",
    "VERIFY_EMAIL_IDENTITY",
]

LIST_IDENTITIES = ActionDefinition(
    action_id="ses.list_identities",
    display_name="List identities",
    service_id="ses",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(
            name="identity_type",
            label="Identity type",
            kind="choice",
            choices=("EmailAddress", "Domain"),
            default="EmailAddress",
            required=False,
        ),
    ),
    cli_template=CliTemplate(service="ses", command="list-identities", arg_map={"identity_type": "identity-type"}),
    boto3_template=Boto3Template(service="ses", operation="list_identities", param_map={"identity_type": "IdentityType"}),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("identity", "identity_type", "verification_status", "dkim_enabled"),
        title="SES Identities",
    ),
    iam_permissions=("ses:ListIdentities",),
    description="List verified SES email address and domain identities.",
    view=to_identity_summaries,
)

VERIFY_EMAIL_IDENTITY = ActionDefinition(
    action_id="ses.verify_email_identity",
    display_name="Verify email",
    service_id="ses",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="email_address", label="Email address", required=True),
    ),
    cli_template=CliTemplate(service="ses", command="verify-email-identity", arg_map={"email_address": "email-address"}),
    boto3_template=Boto3Template(service="ses", operation="verify_email_identity", param_map={"email_address": "EmailAddress"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Verify email result"),
    iam_permissions=("ses:VerifyEmailIdentity",),
    description="Initiate email address verification for SES sending.",
    cache_refresh_nav_ids=("identities",),
)

DELETE_IDENTITY = ActionDefinition(
    action_id="ses.delete_identity",
    display_name="Delete identity",
    service_id="ses",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(name="identity", label="Email address or domain", required=True),
    ),
    cli_template=CliTemplate(service="ses", command="delete-identity", arg_map={"identity": "identity"}),
    boto3_template=Boto3Template(service="ses", operation="delete_identity", param_map={"identity": "Identity"}),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete identity result"),
    iam_permissions=("ses:DeleteIdentity",),
    description="Remove an email address or domain from SES.",
    cache_refresh_nav_ids=("identities",),
)

LIST_TEMPLATES = ActionDefinition(
    action_id="ses.list_templates",
    display_name="List templates",
    service_id="ses",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="ses", command="list-templates"),
    boto3_template=Boto3Template(service="ses", operation="list_templates"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "created_timestamp"),
        title="SES Templates",
    ),
    iam_permissions=("ses:ListTemplates",),
    description="List SES email templates.",
    view=to_template_summaries,
)

SEND_EMAIL = ActionDefinition(
    action_id="ses.send_email",
    display_name="Send email",
    service_id="ses",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="source", label="From address", required=True,
                   help_text="Must be a verified SES identity."),
        InputField(name="to_addresses", label="To (comma-sep addresses)", required=True),
        InputField(name="subject", label="Subject", required=True),
        InputField(name="body_text", label="Body (plain text)", required=True, kind="multiline"),
    ),
    cli_template=CliTemplate(service="ses", command="send-email"),
    boto3_template=Boto3Template(service="ses", operation="send_email"),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Send email result"),
    iam_permissions=("ses:SendEmail",),
    description="Send an email via SES (source must be a verified identity).",
)

ALL_ACTIONS = (
    LIST_IDENTITIES,
    VERIFY_EMAIL_IDENTITY,
    DELETE_IDENTITY,
    LIST_TEMPLATES,
    SEND_EMAIL,
)
