# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-06-26
### Added
- Network & Proxy settings dialog, opened from the new "🌐 Network…" toolbar button, for configuring an HTTP/HTTPS proxy, no-proxy hosts, a trusted CA bundle, and a client certificate. Includes a toggle to ignore the proxy environment variables entirely ("try without the proxy despite the vars") and an option to disable TLS verification as a last-resort diagnostic. Settings are persisted and are reflected in generated AWS CLI and boto3 scripts.

### Changed
- Replaced the separate endpoint dropdown, "Start Moto"/"Start Robotocore" buttons, and "Use Moto instead" checkbox with a single **Target** selector (AWS / Moto / Robotocore / Custom). Selecting a target now both routes calls and manages the emulator lifecycle, so Moto and Robotocore can no longer be active at the same time and impossible combinations can't be expressed. The Profile field is disabled when a target makes credentials irrelevant, and the endpoint URL field is editable only for Custom. See `spec/mutually_exclusive.md`.
- Demo resource seeding is now restricted to a verified local emulator. The "Seed demo resources" menu item only appears while Moto or Robotocore (started from the Target selector) is the active endpoint, and the seeding code positively probes the endpoint for a Moto/Robotocore signature before writing anything. See `spec/demo_safety.md`.

### Removed
- The unused `docker` endpoint mode, which had no behavior. A persisted `docker` endpoint mode is now loaded as `aws`.

### Fixed
- AWS calls failed with "certificate verify failed" for users behind a TLS-inspecting enterprise proxy, because there was no way to trust the proxy's (or AWS's) CA certificate — the app appeared broken. Users can now point the app at a CA bundle so certificate verification succeeds.
- Users behind a corporate HTTP proxy could not configure or override proxy settings from the GUI, and had no way to bypass proxy environment variables when they were set incorrectly.
- The toolbar let users select nonsensical combinations: a Profile while connected to an emulator (where credentials are ignored), an endpoint mode that conflicted with which server was running, and a meaningless `docker` endpoint option.
- Demo resources could be created on real AWS (the previous guard was a single, dismissible confirmation dialog, and seeding was allowed against any custom endpoint). It is now impossible: seeding requires a positively-verified Moto or Robotocore emulator that the app itself started.

## [0.0.1] - 2026-06-25
### Added
- Tkinter desktop GUI for browsing and managing AWS resources, organized as a sidebar of services with a resource table, detail tree, and result panels.
- Support for 16 AWS services: Aurora/RDS, Backup, ECS, Secrets Manager, SSM, networking (VPC), KMS, Athena, S3, SQS, Lambda, CloudWatch, CloudFormation, SNS, SES, and IAM.
- Two execution modes: live boto3 API calls or generated AWS CLI commands.
- Custom endpoint support for pointing the app at Moto, LocalStack, or any non-AWS endpoint.
- Built-in Moto server management: start, stop, restart, reset state, and open the Moto dashboard from the toolbar.
- Built-in Robotocore (containerized AWS emulator) management with start, stop, restart, reset, and image pull.
- Demo-resource seeding that populates Moto or Robotocore with sample resources for each service.
- Risk-level classification of every action (read-only, safe-write, cost-affecting, destructive) that gates the confirmation flow.
- Review dialog showing the generated CLI and Python before any write action runs.
- Typed-confirmation dialog requiring the user to type the resource identifier before a destructive action executes.
- Live AWS CLI and boto3 (Python) script generation for the currently configured action and inputs.
- Terraform configuration generator dialog.
- AWS CDK launcher dialog with subcommand help.
- Script Editor panel that records every successful action's CLI as an editable, savable script.
- Full-screen JSON viewer that splits response metadata from data and renders the payload as a navigable tree.
- Interactive JMESPath query designer with a builder palette, history, and save/load of named queries.
- SQL Runner dialog for querying Aurora MySQL/PostgreSQL clusters with results table and CSV export.
- OS keyring integration for storing and retrieving database connection strings, plus discovery of connection strings in AWS Secrets Manager.
- Aurora "Update master password" action that applies the new password and saves a connection string to the keyring.
- AWS partition support (aws, aws-us-gov, aws-cn, aws-iso, aws-iso-b) with partition-aware region lists.
- AWS profile and region selection from the toolbar, with CLI-over-config-over-default precedence.
- Per-action response caching with a cache diagnostics panel to inspect and clear entries.
- Pagination of list/describe results with next/previous page navigation.
- Filter bar with eager-loaded dropdown choices sourced from other actions' responses.
- Row-action buttons and read-only sub-panels that prefill follow-up actions from the selected resource.
- Single-worker request queue so at most one API call is in flight, with a request-queue diagnostics panel.
- Action history tracking for recently run actions.
- Diagnostic panels for Moto output, Robotocore, the request queue, and the cache.
- `gui4aws doctor` command reporting boto3/botocore versions, AWS CLI and Docker presence, Moto availability, and configured profiles.
- `gui4aws list-profiles` and `gui4aws list-regions` commands for scripting and diagnostics.
- Optional SQL driver extras (`mysql`, `postgresql`, `sql`) for pymysql and pg8000.
- Configurable logging with adjustable log level and optional log file.
- Persisted user configuration of default profile, region, partition, execution mode, and endpoint mode.
