"""S3 action definitions."""

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
from gui4aws.services.s3.views import to_bucket_summaries, to_object_summaries

__all__ = [
    "ALL_ACTIONS",
    "CREATE_BUCKET",
    "DELETE_BUCKET",
    "DOWNLOAD_FILE",
    "LIST_BUCKETS",
    "LIST_OBJECTS",
    "UPLOAD_FILE",
]


LIST_BUCKETS = ActionDefinition(
    action_id="s3.list_buckets",
    display_name="List buckets",
    service_id="s3",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(),
    cli_template=CliTemplate(service="s3api", command="list-buckets"),
    boto3_template=Boto3Template(service="s3", operation="list_buckets"),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("name", "region", "creation_date", "versioning_enabled"),
        title="S3 Buckets",
    ),
    iam_permissions=("s3:ListAllMyBuckets",),
    description="List all S3 buckets in the account.",
    view=to_bucket_summaries,
)


CREATE_BUCKET = ActionDefinition(
    action_id="s3.create_bucket",
    display_name="Create bucket",
    service_id="s3",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="bucket_name", label="Bucket name", required=True),
        InputField(
            name="region",
            label="Region (leave blank for us-east-1)",
            required=False,
            help_text="e.g. us-west-2. Leave blank to create in us-east-1.",
        ),
    ),
    cli_template=CliTemplate(
        service="s3api",
        command="create-bucket",
        arg_map={"bucket_name": "bucket", "region": "region"},
    ),
    boto3_template=Boto3Template(
        service="s3",
        operation="create_bucket",
        param_map={"bucket_name": "Bucket", "region": "CreateBucketConfiguration"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Create bucket result"),
    iam_permissions=("s3:CreateBucket",),
    description="Create a new S3 bucket.",
    cache_refresh_nav_ids=("buckets",),
)


DELETE_BUCKET = ActionDefinition(
    action_id="s3.delete_bucket",
    display_name="Delete bucket",
    service_id="s3",
    risk_level=RiskLevel.DESTRUCTIVE,
    input_fields=(
        InputField(
            name="bucket_name",
            label="Bucket name",
            required=True,
            help_text="The bucket must be empty before it can be deleted.",
        ),
    ),
    cli_template=CliTemplate(
        service="s3api",
        command="delete-bucket",
        arg_map={"bucket_name": "bucket"},
    ),
    boto3_template=Boto3Template(
        service="s3",
        operation="delete_bucket",
        param_map={"bucket_name": "Bucket"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Delete bucket result"),
    iam_permissions=("s3:DeleteBucket",),
    description="Delete an empty S3 bucket.",
    cache_refresh_nav_ids=("buckets",),
)


UPLOAD_FILE = ActionDefinition(
    action_id="s3.upload_file",
    display_name="Upload file",
    service_id="s3",
    risk_level=RiskLevel.SAFE_WRITE,
    input_fields=(
        InputField(name="bucket_name", label="Bucket name", required=True),
        InputField(name="local_path", label="Local file path", required=True, help_text="Absolute path to the local file."),
        InputField(name="s3_key", label="S3 key (object path)", required=True, help_text="e.g. folder/myfile.txt"),
    ),
    cli_template=CliTemplate(
        service="s3api",
        command="put-object",
        arg_map={"bucket_name": "bucket", "s3_key": "key", "local_path": "body"},
    ),
    boto3_template=Boto3Template(
        service="s3",
        operation="upload_file",
        param_map={"local_path": "Filename", "bucket_name": "Bucket", "s3_key": "Key"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Upload file result"),
    iam_permissions=("s3:PutObject",),
    description="Upload a local file to S3.",
)


DOWNLOAD_FILE = ActionDefinition(
    action_id="s3.download_file",
    display_name="Download file",
    service_id="s3",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="bucket_name", label="Bucket name", required=True),
        InputField(name="s3_key", label="S3 key (object path)", required=True),
        InputField(name="local_path", label="Local destination path", required=True, help_text="Absolute path where the file will be saved."),
    ),
    cli_template=CliTemplate(
        service="s3api",
        command="get-object",
        arg_map={"bucket_name": "bucket", "s3_key": "key", "local_path": "outfile"},
    ),
    boto3_template=Boto3Template(
        service="s3",
        operation="download_file",
        param_map={"bucket_name": "Bucket", "s3_key": "Key", "local_path": "Filename"},
    ),
    result_view=ResultViewDefinition(kind=ResultViewKind.RAW_JSON, title="Download file result"),
    iam_permissions=("s3:GetObject",),
    description="Download an S3 object to a local file.",
)


LIST_OBJECTS = ActionDefinition(
    action_id="s3.list_objects",
    display_name="List objects",
    service_id="s3",
    risk_level=RiskLevel.READ_ONLY,
    input_fields=(
        InputField(name="bucket_name", label="Bucket name", required=True),
        InputField(
            name="prefix",
            label="Prefix (optional)",
            required=False,
            help_text="Filter keys starting with this prefix, e.g. logs/2024/",
        ),
        InputField(
            name="max_keys",
            label="Max keys (default 200)",
            kind="int",
            required=False,
            default="200",
        ),
    ),
    cli_template=CliTemplate(
        service="s3api",
        command="list-objects-v2",
        arg_map={"bucket_name": "bucket", "prefix": "prefix", "max_keys": "max-keys"},
    ),
    boto3_template=Boto3Template(
        service="s3",
        operation="list_objects_v2",
        param_map={"bucket_name": "Bucket", "prefix": "Prefix", "max_keys": "MaxKeys"},
    ),
    result_view=ResultViewDefinition(
        kind=ResultViewKind.TABLE,
        columns=("key", "size", "last_modified", "storage_class"),
        title="Bucket Objects",
    ),
    iam_permissions=("s3:ListBucket",),
    description="List objects in an S3 bucket, optionally filtered by prefix.",
    view=to_object_summaries,
)


ALL_ACTIONS = (
    LIST_BUCKETS,
    LIST_OBJECTS,
    CREATE_BUCKET,
    DELETE_BUCKET,
    UPLOAD_FILE,
    DOWNLOAD_FILE,
)
