# gui4aws spec

`gui4aws` is a Tkinter desktop GUI for browsing and managing AWS resources. It is a thinking layer over boto3 and the AWS CLI: every action should be visible, reviewable, and exportable as a boring script.

It is not an AWS Console clone, Terraform, CloudFormation Designer, LocalStack replacement, or credential manager.

## Current product

The package and CLI are both named `gui4aws`.

The app has:

- a persistent top toolbar for execution mode, target, profile, partition, region, endpoint URL, cache, and network settings;
- a service sidebar backed by explicit `ServiceDefinition` registrations;
- a browser panel with filters, resource tables, detail trees, sub-tables, row actions, output, generated scripts, and Prev/Next pagination;
- a script editor;
- Moto and Robotocore management panels;
- diagnostics for request queue and read cache;
- action history and script export.

The default execution mode is boto3. AWS CLI mode is still a first-class execution mode.

Targets are `AWS`, `Moto`, `Robotocore`, and `Custom`. Moto and Robotocore are mutually exclusive managed local targets. Custom is for user-managed AWS-compatible endpoints.

## Service surface

Services currently registered by default:

- Aurora/RDS clusters
- AWS Backup
- ECS
- Secrets Manager
- SSM Parameter Store
- Networking
- KMS
- Athena
- S3
- SQS
- Lambda
- CloudWatch
- CloudFormation
- SNS
- SES
- IAM

Not every service has equal depth. The contract is that each service action declares risk, inputs, CLI template, boto3 template, result view, and likely IAM permissions.

## Architecture rules

Use the standard library first: tkinter, argparse, dataclasses, pathlib, logging, threading, and queue.

Runtime dependencies stay small: boto3/botocore, keyring, TOML read support for older Python, and optional SQL drivers.

The GUI must not import or call AWS SDK clients directly. Service modules define actions and normalization. Executors run boto3 or AWS CLI. The GUI binds those pieces.

The service registry is explicit. There is no filesystem scanning or plugin auto-discovery in the app core.

Do not use a leading underscore to mean private. Use module boundaries, `__all__`, and clear names.

All new code has type annotations.

Use logging, not print.

## Safety model

Actions use `RiskLevel`:

- `READ_ONLY`
- `SAFE_WRITE`
- `COST_AFFECTING`
- `DESTRUCTIVE`

Read-only actions can run from navigation and may be cached.

Safe-write and cost-affecting actions go through a review dialog with generated CLI and Python.

Destructive actions require typed confirmation as well as the normal review path.

Secret input fields are marked with `InputField.is_secret`. They are masked in forms, redacted from history/diagnostics, and rendered as environment placeholders in generated scripts.

Demo seeding is only available when the active target is a managed emulator started by the app.

## Threading

Tk owns widgets and state rendering.

AWS and emulator calls run through one serialized worker queue. This avoids freezing Tk and avoids request storms against Moto.

Background work posts results to `results_queue`; the Tk thread drains it with `after(...)`.

Cached read hits can bypass the worker because they do not touch the network.

## Config

Config is stored as TOML under the user config directory, for example `%APPDATA%/gui4aws/config.toml` on Windows.

The config persists the last profile, partition, region, mode, endpoint mode, window size, history settings, local endpoints, and network/proxy/TLS settings.

An empty profile means "no profile"; boto3/AWS CLI then use their normal environment and default credential chains.

## Testing

Use `uv` for all Python tooling.

Default tests are `uv run pytest`. Full local gate is `uv run make check`.

Tests should keep logic outside Tk where possible. Tk integration tests can use real widgets and a manually pumped event loop, but must skip cleanly when no display is available.

Moto is the first integration target. Robotocore is supported as a local target, but app behavior must not rely on Robotocore-only behavior.

## Current gaps

The authoritative backlog is in `spec/road_map/road_map.md`.

Known high-value gaps are live-AWS polish, service-specific correctness fixes, better pagination coverage, global write/delete enable gates, and packaging/release hardening.
