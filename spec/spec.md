# SPEC: `aws-think-console`

A tkinter desktop GUI that provides a “thinking layer” over AWS CLI and boto3 for selected AWS services. It is not a pixel-for-pixel AWS Console clone and does not attempt to reproduce complex visual IDE-like console features. Instead, it gives users discoverable forms, state views, safe workflows, and script export for AWS CLI and Python/boto3.

Initial services:

```text
RDS
RDS Aurora
AWS Backup
ElastiCache
OpenSearch
DynamoDB
```

Initial network/security support is read-only:

```text
VPCs
Subnets
Security groups
KMS keys, where needed for service forms
IAM roles, where needed for service forms
```

OpenStack and paid/nonlocal cloud emulators are out of scope.

---

## 1. Goals

`aws-think-console` provides a desktop GUI for AWS resource inspection and common administrative workflows.

Primary goals:

1. Let users browse supported AWS resources without memorizing CLI commands.
2. Let users perform common safe operations through forms.
3. Let users see current state in structured GUI views, not raw JSON dumps.
4. Let users switch between **AWS CLI mode** and **boto3 mode**.
5. Let users export the current workflow as:

   * AWS CLI shell script
   * Python boto3 script
6. Let users test workflows locally against moto and Docker-backed service emulators where practical.
7. Make destructive operations explicit, reviewable, and scriptable.

Non-goals:

1. Replacing every AWS Console feature.
2. Recreating visual designers, mini-IDEs, or graphical orchestration editors.
3. Creating a new cloud abstraction layer.
4. Supporting OpenStack.
5. Supporting all AWS services in the first release.
6. Hiding AWS concepts from users.
7. Inventing a state-management engine like Terraform or CloudFormation.

---

## 2. Product positioning

This tool is closer to:

```text
Postman for AWS APIs
+ pgAdmin-style resource browser
+ script generator
+ safety-focused admin console
```

It is not:

```text
Terraform
CloudFormation Designer
AWS Console clone
LocalStack replacement
OpenStack Horizon clone
```

The core product promise:

> Every GUI action teaches you the AWS CLI or boto3 equivalent.

---

## 3. Package identity

Recommended names:

```text
Project name: aws-think-console
Python package: aws_think_console
CLI entry point: aws-think-console
GUI title: AWS Think Console
```

Alternative names:

```text
aws-desktop-console
boto-console
aws-workbench-lite
```

This spec uses `aws-think-console`.

---

## 4. Technical stack

### 4.1 Required stack

```text
Python 3.12+
tkinter
argparse
subprocess
json
dataclasses
typing
pathlib
logging
threading
queue
boto3
botocore
```

### 4.2 Testing stack

```text
pytest
moto
pytest-cov
ruff
mypy
```

Optional but useful:

```text
docker
docker compose
```

### 4.3 Explicitly excluded

```text
click
typer
rich
textual
customtkinter
PyQt
Electron
```

Rationale: the initial application should remain close to the Python standard library, except for AWS SDK dependencies and test/emulation tooling.

---

## 5. Coding conventions

### 5.1 Naming

Do not use leading underscores to mean “private.”

Avoid this:

```python
def _load_clusters() -> list[Cluster]:
    ...
```

Prefer this:

```python
def load_clusters() -> list[Cluster]:
    ...
```

A leading underscore may be used only when the name is intentionally unused, especially in callbacks or unpacking:

```python
def handle_click(event: object) -> None:
    ...
```

or:

```python
for item, unused_metadata in rows:
    ...
```

If a symbol is internal, use one of these instead:

```text
module boundaries
clear naming
docstrings
__all__
package organization
```

Example:

```python
# aws_think_console/internal/service_registry.py
```

Not:

```python
def _register_service(...)
```

### 5.2 Type annotations

All public and internal functions must have type annotations.

```python
def list_db_clusters(region_name: str) -> list[DbClusterSummary]:
    ...
```

### 5.3 Logging

Use `logging`, not `print`.

```python
logger.info("Loaded %s RDS clusters", len(clusters))
```

### 5.4 Paths

Use `pathlib.Path`, not string path manipulation.

### 5.5 CLI parser

Use `argparse`, not Click or Typer.

---

## 6. Application modes

The application has an always-visible execution mode flag:

```text
Execution mode: [ AWS CLI | boto3 ]
```

This flag appears in the global toolbar and affects how generated actions are executed and exported.

### 6.1 AWS CLI mode

In AWS CLI mode, actions are executed by shelling out to the installed `aws` executable.

Example generated command:

```bash
aws rds describe-db-clusters \
  --region us-east-1 \
  --db-cluster-identifier my-cluster
```

The app should capture:

```text
stdout
stderr
exit code
duration
resolved command
environment summary
```

### 6.2 boto3 mode

In boto3 mode, actions are executed through boto3 clients.

Example generated Python:

```python
import boto3

client = boto3.client("rds", region_name="us-east-1")

response = client.describe_db_clusters(
    DBClusterIdentifier="my-cluster",
)
```

The app should capture:

```text
response object
botocore exception details
duration
client/service/region
request parameters
```

### 6.3 Mode switching

Switching the mode does not change the visible workflow.

For example, the same “Restore Aurora cluster from snapshot” form can generate either:

```text
AWS CLI restore-db-cluster-from-snapshot command
```

or:

```text
boto3 restore_db_cluster_from_snapshot call
```

---

## 7. User interface layout

The main window uses a stable three-region layout.

```text
+---------------------------------------------------------------------+
| File  Services  Profiles  Region  View  Tools  Help                 |
+---------------------------------------------------------------------+
| Mode: [AWS CLI v]  Profile: [default v]  Region: [us-east-1 v]      |
| Endpoint: [AWS / Local / Custom]  Account: 123456789012             |
+----------------------+----------------------------------------------+
| Service Sidebar      | Main Panel                                   |
|                      |                                              |
| RDS                  | Current state / form / workflow / output      |
|   DB Instances       |                                              |
|   DB Clusters        |                                              |
|   Snapshots          |                                              |
|   Parameter Groups   |                                              |
|                      |                                              |
| DynamoDB             |                                              |
|   Tables             |                                              |
|   Backups            |                                              |
|   Global Tables      |                                              |
+----------------------+----------------------------------------------+
| Status: Ready | Last action: describe-db-clusters | Copy CLI | Copy Py |
+---------------------------------------------------------------------+
```

### 7.1 Top menu

The top menu contains:

```text
File
Services
Profiles
Region
View
Tools
Help
```

### 7.2 Global toolbar

The global toolbar is always visible and contains:

```text
Execution mode selector: AWS CLI / boto3
AWS profile selector
Region selector
Endpoint mode selector
Refresh button
Copy current action as AWS CLI
Copy current action as Python
Open action history
```

### 7.3 Left sidebar

The sidebar changes based on the selected service.

Examples:

```text
RDS
  DB Instances
  DB Clusters
  DB Snapshots
  DB Cluster Snapshots
  Subnet Groups
  Parameter Groups
  Option Groups
  Events

Aurora
  Clusters
  Instances
  Snapshots
  Global Databases
  Backups
  Parameter Groups

AWS Backup
  Backup Vaults
  Backup Plans
  Recovery Points
  Protected Resources
  Jobs
  Restore Jobs

ElastiCache
  Redis / Valkey Replication Groups
  Memcached Clusters
  Snapshots
  Parameter Groups
  Subnet Groups

OpenSearch
  Domains
  Versions
  Packages
  VPC Options
  Snapshots

DynamoDB
  Tables
  Items
  Indexes
  Backups
  Streams
  Exports
  Imports
```

### 7.4 Main panel

The main panel has multiple view types:

```text
Resource list
Resource detail
Action form
Output viewer
Generated script viewer
Diff/review view
```

### 7.5 Status bar

The status bar shows:

```text
Ready / Loading / Error
Last operation
Duration
AWS profile
Region
Mode
Endpoint mode
```

---

## 8. GUI representation rules

The GUI should avoid dumping raw JSON unless requested.

Preferred representations:

| AWS data shape          | GUI representation                   |
| ----------------------- | ------------------------------------ |
| List of resources       | sortable table/grid                  |
| Nested properties       | tree view                            |
| Tags                    | editable or read-only key/value grid |
| ARNs                    | text field with copy button          |
| Status values           | label with refresh button            |
| Relationships           | clickable links                      |
| Events                  | chronological table                  |
| Parameters              | name/value/source table              |
| JSON policy or document | formatted text viewer                |
| Item attributes         | tree or attribute grid               |

Raw JSON remains available through:

```text
View raw response
Copy raw JSON
Save raw JSON
```

---

## 9. Service design

Each supported service is represented by a service module.

Suggested structure:

```text
src/aws_think_console/
  app.py
  cli.py
  config.py
  logging_config.py
  models.py

  gui/
    main_window.py
    toolbar.py
    sidebar.py
    resource_table.py
    detail_tree.py
    action_form.py
    output_panel.py
    script_viewer.py

  execution/
    execution_mode.py
    aws_cli_executor.py
    boto3_executor.py
    action_history.py
    script_generator.py
    endpoint_config.py

  services/
    service_registry.py

    rds/
      service.py
      models.py
      actions.py
      views.py
      cli_templates.py
      boto3_templates.py

    aurora/
      service.py
      models.py
      actions.py
      views.py

    backup/
      service.py
      models.py
      actions.py
      views.py

    elasticache/
      service.py
      models.py
      actions.py
      views.py

    opensearch/
      service.py
      models.py
      actions.py
      views.py

    dynamodb/
      service.py
      models.py
      actions.py
      views.py

    network/
      readonly.py
      models.py

  testing/
    moto_support.py
    docker_services.py
    fixtures.py
```

---

## 10. Service module contract

Each service module exposes a service definition.

Conceptual interface:

```python
@dataclass(frozen=True)
class ServiceDefinition:
    service_id: str
    display_name: str
    boto3_service_name: str
    cli_service_name: str
    navigation_items: list[NavigationItem]
    actions: list[ActionDefinition]
```

Example:

```python
ServiceDefinition(
    service_id="rds",
    display_name="RDS",
    boto3_service_name="rds",
    cli_service_name="rds",
    navigation_items=[
        NavigationItem("db_instances", "DB Instances"),
        NavigationItem("db_clusters", "DB Clusters"),
        NavigationItem("db_snapshots", "DB Snapshots"),
    ],
    actions=[
        describe_db_instances_action,
        create_db_snapshot_action,
        restore_db_instance_action,
    ],
)
```

---

## 11. Action model

Every user operation is modeled as an `ActionDefinition`.

```python
@dataclass(frozen=True)
class ActionDefinition:
    action_id: str
    display_name: str
    service_id: str
    risk_level: RiskLevel
    input_fields: list[InputField]
    cli_template: CliTemplate
    boto3_template: Boto3Template
    result_view: ResultViewDefinition
```

Risk levels:

```python
class RiskLevel(StrEnum):
    READ_ONLY = "read_only"
    SAFE_WRITE = "safe_write"
    COST_AFFECTING = "cost_affecting"
    DESTRUCTIVE = "destructive"
```

Examples:

| Action                | Risk           |
| --------------------- | -------------- |
| Describe DB clusters  | Read-only      |
| Create snapshot       | Safe write     |
| Restore from snapshot | Cost-affecting |
| Delete DB cluster     | Destructive    |
| Delete DynamoDB table | Destructive    |
| Modify cache cluster  | Cost-affecting |
| Start backup job      | Cost-affecting |

---

## 12. Action history and script export

The app maintains a session action history.

Each history item stores:

```text
timestamp
service
action
mode
profile
region
endpoint
input parameters
generated AWS CLI
generated Python
result status
duration
resource identifiers
```

The user can export:

```text
Current action as AWS CLI
Current action as Python
Selected actions as AWS CLI script
Selected actions as Python script
Full session as markdown runbook
Full session as JSON
```

### 12.1 AWS CLI export

Example:

```bash
#!/usr/bin/env bash
set -euo pipefail

AWS_PROFILE="default"
AWS_REGION="us-east-1"

aws rds describe-db-clusters \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION"

aws rds restore-db-cluster-from-snapshot \
  --profile "$AWS_PROFILE" \
  --region "$AWS_REGION" \
  --db-cluster-identifier "restored-cluster" \
  --snapshot-identifier "arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot" \
  --engine "aurora-postgresql"
```

### 12.2 Python export

Example:

```python
from __future__ import annotations

import boto3


def main() -> None:
    session = boto3.Session(profile_name="default", region_name="us-east-1")
    rds_client = session.client("rds")

    clusters_response = rds_client.describe_db_clusters()
    print(clusters_response)

    restore_response = rds_client.restore_db_cluster_from_snapshot(
        DBClusterIdentifier="restored-cluster",
        SnapshotIdentifier="arn:aws:rds:us-east-1:123456789012:cluster-snapshot:my-snapshot",
        Engine="aurora-postgresql",
    )
    print(restore_response)


if __name__ == "__main__":
    main()
```

The exported code should be boring, explicit, and easy to paste into a real project.

---

## 13. Endpoint modes

The app supports multiple endpoint modes.

```text
AWS
Moto
Local Docker
Custom
```

### 13.1 AWS mode

Uses normal AWS SDK and AWS CLI behavior.

### 13.2 Moto mode

Uses moto where supported.

The app should provide test fixtures and documented local startup patterns.

Example:

```bash
moto_server -H 127.0.0.1 -p 5000
```

Then:

```text
Endpoint URL: http://127.0.0.1:5000
```

### 13.3 Local Docker mode

For services that are better supported by local Docker containers, the project may include Docker Compose helpers.

Examples:

```text
DynamoDB Local
OpenSearch container
Valkey or Redis container
```

### 13.4 Custom endpoint mode

The user may provide a custom endpoint URL.

Useful for:

```text
LocalStack
moto_server
DynamoDB Local
custom AWS-compatible endpoints
```

OpenStack remains out of scope.

---

## 14. Authentication and profiles

The app should use existing AWS credential mechanisms.

Supported:

```text
AWS profiles
environment variables
AWS SSO profiles, if already configured
credential_process, if configured externally
assume-role profiles, if configured externally
```

The app should not become a credential manager in the first release.

The profile selector reads available profiles from boto3/botocore configuration.

The app should show:

```text
Current profile
Current region
Caller identity
Account ID
ARN
```

A “Test credentials” action should call:

```text
sts:GetCallerIdentity
```

---

## 15. Region handling

Region is always visible.

The app should support:

```text
Default region from profile/session
Manual region selection
Refresh available regions
```

Region-sensitive resources should refresh when the region changes.

---

## 16. Read-only network support

The initial app supports read-only lookup for:

```text
VPCs
Subnets
Security groups
KMS keys
IAM roles
```

These are shown in selection dialogs when needed.

Example: when restoring an Aurora cluster, the subnet group and VPC-related details should be selectable or viewable, but the app does not initially create VPCs, subnets, or security groups.

---

# 17. Initial service coverage

## 17.1 RDS

### Resource views

```text
DB instances
DB snapshots
DB subnet groups
DB parameter groups
Option groups
Events
```

### Initial read actions

```text
Describe DB instances
Describe DB snapshots
Describe DB subnet groups
Describe DB parameter groups
Describe events
View instance details
View snapshot details
```

### Initial write actions

```text
Create DB snapshot
Restore DB instance from snapshot
Start DB instance
Stop DB instance
Modify DB instance
Reboot DB instance
```

### Destructive actions

```text
Delete DB instance
Delete DB snapshot
```

Destructive actions require confirmation and script review.

---

## 17.2 RDS Aurora

Aurora should be treated distinctly from single-instance RDS because the operational model is cluster-centered.

### Resource views

```text
DB clusters
DB cluster members
DB cluster snapshots
DB instances belonging to clusters
Global databases
Cluster parameter groups
DB subnet groups
Events
```

### Initial read actions

```text
Describe DB clusters
Describe DB cluster snapshots
Describe DB instances
Describe global clusters
Describe events
View cluster topology
View cluster endpoints
View reader/writer instance roles
```

### Initial write actions

```text
Restore DB cluster from snapshot
Create DB instance in cluster
Create DB cluster snapshot
Start DB cluster
Stop DB cluster
Modify DB cluster
Fail over DB cluster
```

### Destructive actions

```text
Delete DB cluster
Delete DB instance
Delete DB cluster snapshot
```

### Special workflow: restore Aurora cluster from backup/snapshot

The GUI should explicitly support the practical post-restore workflow:

```text
1. Select source snapshot or recovery point.
2. Restore to new cluster identifier.
3. Select engine/version options.
4. Select subnet group and security groups.
5. Restore cluster.
6. Create or attach DB instances.
7. Wait for availability.
8. Show cluster endpoints.
9. Generate cutover notes.
10. Generate CLI or Python script for the whole operation.
```

The app should make clear that restored clusters do not automatically replace application connection strings.

A generated runbook should include:

```text
New writer endpoint
New reader endpoint
Old cluster identifier
New cluster identifier
DNS/CNAME update notes, if user supplies application DNS name
Secrets Manager update notes, if user supplies secret ARN
Manual app configuration notes
```

---

## 17.3 AWS Backup

### Resource views

```text
Backup vaults
Backup plans
Backup selections
Recovery points
Protected resources
Backup jobs
Restore jobs
Copy jobs
```

### Initial read actions

```text
List backup vaults
List backup plans
List recovery points by backup vault
List protected resources
List backup jobs
List restore jobs
View recovery point metadata
```

### Initial write actions

```text
Start backup job
Start restore job
Create backup vault
Create backup plan
```

### Destructive actions

```text
Delete backup vault
Delete recovery point
Delete backup plan
```

Deletion support may be delayed until later releases because AWS Backup deletion workflows can have retention and lock complications.

### Special workflow: restore from recovery point

The restore form should:

```text
Select vault
Select recovery point
Show protected resource type
Show restore metadata fields
Let user edit required metadata
Generate restore job
Track restore job status
Link restored resource to service-specific view where possible
```

---

## 17.4 ElastiCache

### Resource views

```text
Replication groups
Cache clusters
Users and user groups, if applicable
Subnet groups
Parameter groups
Snapshots
Events
```

### Initial read actions

```text
Describe replication groups
Describe cache clusters
Describe snapshots
Describe cache subnet groups
Describe cache parameter groups
Describe events
```

### Initial write actions

```text
Create snapshot
Restore from snapshot
Modify replication group
Reboot cache cluster
```

### Destructive actions

```text
Delete replication group
Delete cache cluster
Delete snapshot
```

The UI should distinguish:

```text
Redis
Valkey
Memcached
```

Where AWS API terminology differs from user terminology, the UI should preserve the AWS names in generated scripts.

---

## 17.5 OpenSearch

### Resource views

```text
Domains
Domain configuration
Versions
Packages
VPC options
Endpoints
Snapshots, where available through supported APIs
```

### Initial read actions

```text
List domain names
Describe domain
Describe domain config
List versions
List packages
List tags
```

### Initial write actions

```text
Create domain
Update domain config
Add tags
Remove tags
Start service software update, if available and appropriate
```

### Destructive actions

```text
Delete domain
```

The UI should show cost-affecting warnings for domain creation and instance-count changes.

---

## 17.6 DynamoDB

### Resource views

```text
Tables
Items
Indexes
Streams
Backups
Exports
Imports
Global tables
Tags
```

### Initial read actions

```text
List tables
Describe table
Scan table with limit
Query table
Describe backup
List backups
List tags of resource
Describe continuous backups
```

### Initial write actions

```text
Create table
Update table
Put item
Update item
Delete item
Create backup
Restore table from backup
Enable point-in-time recovery
Disable point-in-time recovery
```

### Destructive actions

```text
Delete table
Delete backup
Delete item
```

### DynamoDB item editor

The DynamoDB item editor should support:

```text
Key fields
Attribute grid
JSON view
DynamoDB typed attribute JSON view
Put item
Update item
Delete item
Copy as AWS CLI
Copy as Python
```

The first version may use a conservative attribute editor rather than trying to infer complex schemas.

---

# 18. Safety model

## 18.1 Destructive action confirmation

Destructive actions require:

```text
Review screen
Generated CLI/Python preview
Explicit confirmation text
```

Example:

```text
Type the DB cluster identifier to confirm deletion:
my-prod-cluster
```

## 18.2 Cost-affecting action warning

Cost-affecting actions require a warning screen but not necessarily typed confirmation.

Examples:

```text
Restoring a cluster may create billable resources.
Creating an OpenSearch domain may create billable resources.
Starting a backup job may incur storage charges.
```

## 18.3 Dry-run support

Where AWS APIs support dry-run, expose it.

Where dry-run is unavailable, the UI should not pretend.

Instead, use:

```text
Preview generated request
Validate required fields
Show likely affected resources
Show cost/destructive warning
```

---

# 19. Generated script policy

Generated scripts should be:

```text
explicit
readable
copy-pasteable
free of GUI dependencies
free of project-specific imports
```

No hidden framework.

No clever abstraction.

Prefer:

```python
client.restore_db_cluster_from_snapshot(...)
```

Over:

```python
run_action("restore_cluster", params)
```

Generated scripts should include:

```text
profile
region
endpoint URL, if non-AWS endpoint mode is active
basic error handling
comments for manual steps
```

---

# 20. CLI application

The project includes a CLI entry point:

```bash
aws-think-console
```

## 20.1 CLI responsibilities

The CLI can:

```text
Launch the GUI
Print version
Show environment diagnostics
Launch with selected profile
Launch with selected region
Launch with selected execution mode
Launch with selected endpoint URL
Run basic smoke checks
```

## 20.2 CLI syntax

Use `argparse`.

Example:

```bash
aws-think-console gui
```

```bash
aws-think-console gui \
  --profile default \
  --region us-east-1 \
  --mode boto3
```

```bash
aws-think-console gui \
  --profile default \
  --region us-east-1 \
  --mode aws-cli
```

```bash
aws-think-console doctor
```

```bash
aws-think-console doctor --check-aws-cli --check-boto3 --check-docker
```

```bash
aws-think-console list-profiles
```

```bash
aws-think-console list-regions
```

```bash
aws-think-console test-endpoint \
  --service dynamodb \
  --endpoint-url http://localhost:8000
```

## 20.3 CLI options

Common options:

```text
--profile
--region
--mode
--endpoint-url
--endpoint-mode
--log-level
--log-file
--debug
```

Execution mode values:

```text
aws-cli
boto3
```

Endpoint mode values:

```text
aws
moto
docker
custom
```

---

# 21. Configuration

Configuration is stored in a user config directory.

Example locations:

```text
Windows: %APPDATA%/aws-think-console/config.toml
Linux: ~/.config/aws-think-console/config.toml
macOS: ~/Library/Application Support/aws-think-console/config.toml
```

Even though macOS may work, Windows and Linux are the primary target platforms.

Example config:

```toml
default_profile = "default"
default_region = "us-east-1"
default_mode = "boto3"
default_endpoint_mode = "aws"

[window]
width = 1400
height = 900
remember_position = true

[history]
enabled = true
max_entries = 500

[local_endpoints.dynamodb]
endpoint_url = "http://localhost:8000"

[local_endpoints.moto]
endpoint_url = "http://localhost:5000"

[local_endpoints.opensearch]
endpoint_url = "http://localhost:9200"
```

If TOML writing is too much for the first version, JSON config is acceptable, but TOML is preferred for human editing.

---

# 22. Local testing and emulation

## 22.1 Moto-first policy

The first test target is moto.

Use moto for supported operations whenever possible.

Test categories:

```text
unit tests
service adapter tests
script generation tests
GUI model tests
moto integration tests
Docker integration tests
manual AWS smoke tests
```

## 22.2 Docker-backed services

Some services may need Docker-backed local emulation.

Initial candidates:

```text
DynamoDB Local
OpenSearch
Redis / Valkey
```

Example Docker Compose file:

```yaml
services:
  dynamodb-local:
    image: amazon/dynamodb-local
    ports:
      - "8000:8000"

  opensearch:
    image: opensearchproject/opensearch:latest
    environment:
      discovery.type: single-node
      plugins.security.disabled: "true"
      OPENSEARCH_INITIAL_ADMIN_PASSWORD: "local-dev-password-123"
    ports:
      - "9200:9200"

  valkey:
    image: valkey/valkey:latest
    ports:
      - "6379:6379"
```

The app should not require Docker for normal AWS usage.

## 22.3 LocalStack

LocalStack may be supported through custom endpoint configuration, but the project should not require paid LocalStack features.

The spec should avoid relying on LocalStack-only behavior.

---

# 23. Testing strategy

## 23.1 Unit tests

Unit tests cover:

```text
action definitions
input validation
CLI command generation
Python script generation
profile/region config
risk classification
resource model normalization
```

## 23.2 Service adapter tests

For each service action, test:

```text
boto3 parameter generation
AWS CLI argument generation
required fields
optional fields
risk level
script export
```

## 23.3 Moto integration tests

Moto tests cover:

```text
describe/list operations
basic create operations where supported
basic restore/backup flows where supported
error handling
endpoint URL configuration
```

## 23.4 Docker integration tests

Docker tests are optional and marked separately.

Example pytest marker:

```python
@pytest.mark.docker
def test_dynamodb_local_list_tables() -> None:
    ...
```

## 23.5 GUI tests

Tkinter GUI tests should focus on:

```text
widget construction
state transitions
form validation
button enable/disable behavior
generated script display
action history updates
```

Avoid brittle pixel-level tests.

The GUI should be structured so logic can be tested outside tkinter widgets.

---

# 24. Threading and responsiveness

AWS calls must not block the tkinter event loop.

Use worker threads and a queue.

Pattern:

```text
GUI schedules action
worker thread executes AWS CLI or boto3 call
worker posts result to queue
tkinter event loop polls queue using after()
GUI updates state
```

The app should support cancellation where practical, but first release may only support “ignore result after cancel.”

---

# 25. Error handling

Errors should be shown in a structured error panel.

For AWS CLI mode, show:

```text
command
exit code
stdout
stderr
parsed AWS error, if possible
```

For boto3 mode, show:

```text
exception class
AWS error code
message
operation name
request parameters
```

Common error hints:

```text
Expired credentials
Missing region
Access denied
Resource not found
Endpoint unavailable
AWS CLI not found
Docker service not running
Unsupported moto operation
```

The app should never show only “Something went wrong.”

---

# 26. Permissions model

The app does not manage IAM permissions in the first release.

However, each action definition should declare likely IAM permissions.

Example:

```text
rds:DescribeDBClusters
rds:RestoreDBClusterFromSnapshot
rds:CreateDBInstance
```

The GUI can show these in the action help panel.

This helps users understand why an action may fail.

---

# 27. Help system

The right side of the main panel, or an optional help drawer, should explain the selected action.

For each action:

```text
What this does
AWS API operation
AWS CLI command family
Required permissions
Risk level
Cost/destructive warning
Related resources
Script export notes
```

Example:

```text
Restore DB cluster from snapshot

This creates a new Aurora DB cluster from an existing DB cluster snapshot.
It does not automatically redirect applications to the new cluster.

AWS CLI:
aws rds restore-db-cluster-from-snapshot

boto3:
rds.restore_db_cluster_from_snapshot

Common next steps:
1. Create a DB instance in the restored cluster.
2. Wait for the cluster and instance to become available.
3. Update app connection strings or DNS.
4. Validate application behavior.
```

---

# 28. Resource relationships

The app should surface relationships as links where possible.

Examples:

```text
Aurora cluster -> member DB instances
Aurora cluster -> subnet group
Aurora cluster -> security groups
Aurora snapshot -> source cluster
DynamoDB table -> backups
DynamoDB table -> streams
OpenSearch domain -> VPC/subnets/security groups
ElastiCache replication group -> node groups
AWS Backup recovery point -> protected resource
```

Clicking a related resource should navigate to its view if the service is supported.

If unsupported, show a read-only detail panel.

---

# 29. Data model normalization

AWS responses are large and inconsistent. The app should normalize key fields into simple dataclasses for GUI display.

Example:

```python
@dataclass(frozen=True)
class ResourceSummary:
    service_id: str
    resource_type: str
    identifier: str
    arn: str | None
    status: str | None
    region: str
    account_id: str | None
    display_name: str
```

Service-specific models can extend this concept.

Example:

```python
@dataclass(frozen=True)
class AuroraClusterSummary:
    cluster_identifier: str
    engine: str
    engine_version: str | None
    status: str
    endpoint: str | None
    reader_endpoint: str | None
    multi_az: bool
    members: list[str]
```

---

# 30. MVP release

## 30.1 MVP scope

The first usable MVP should include:

```text
GUI shell
Profile selector
Region selector
Execution mode selector
Endpoint mode selector
STS caller identity
Action history
Copy current action as AWS CLI
Copy current action as Python
RDS/Aurora read views
DynamoDB read views
Basic AWS CLI executor
Basic boto3 executor
Moto-backed tests for supported reads
```

## 30.2 MVP services

Recommended MVP order:

```text
1. Core shell and execution framework
2. STS identity test
3. DynamoDB list/describe/query/scan
4. RDS describe instances/clusters/snapshots
5. Aurora restore-from-snapshot script generation
6. AWS Backup recovery point browsing
7. ElastiCache read views
8. OpenSearch read views
```

Write operations can come after the read model is stable.

---

# 31. Milestones

## Milestone 1: GUI shell

Deliver:

```text
Main tkinter window
Top menu
Toolbar
Sidebar
Main panel
Status bar
Profile selector
Region selector
Mode selector
Endpoint selector
```

## Milestone 2: Execution abstraction

Deliver:

```text
AWS CLI executor
boto3 executor
action model
action history
script generation
structured errors
```

## Milestone 3: Read-only AWS browsing

Deliver:

```text
STS identity
RDS describe
Aurora describe
DynamoDB list/describe
ElastiCache describe
OpenSearch describe
AWS Backup list views
```

## Milestone 4: Script export

Deliver:

```text
Copy current action as CLI
Copy current action as Python
Export selected actions as bash
Export selected actions as Python
Export markdown runbook
```

## Milestone 5: Safe write workflows

Deliver:

```text
Create RDS snapshot
Create Aurora cluster snapshot
Restore Aurora cluster from snapshot
Create DynamoDB backup
Restore DynamoDB table from backup
Start AWS Backup job
```

## Milestone 6: Destructive workflows

Deliver:

```text
typed confirmation
review screen
delete selected low-risk resources
high-quality generated scripts
```

---

# 32. Example user workflows

## 32.1 Browse Aurora clusters

```text
User selects Services -> Aurora.
User clicks Clusters.
App lists clusters in a sortable table.
User selects a cluster.
App shows:
  cluster status
  engine/version
  endpoints
  member instances
  subnet group
  security groups
  recent events
User clicks Copy Python.
App copies boto3 describe_db_clusters example.
```

## 32.2 Restore Aurora from snapshot

```text
User selects Aurora -> Snapshots.
User selects a snapshot.
User clicks Restore.
App opens restore form.
User fills new cluster identifier.
User selects subnet group and security groups.
User reviews generated action.
User runs action.
App tracks status.
App suggests next step: create DB instance in cluster.
User exports full workflow as bash script.
```

## 32.3 Inspect DynamoDB table

```text
User selects DynamoDB -> Tables.
User selects table.
App shows keys, billing mode, indexes, item count, stream status.
User opens Query tab.
User enters key condition.
User previews generated CLI/Python.
User runs query.
Results appear in a grid/tree.
```

## 32.4 Use local DynamoDB

```text
User starts DynamoDB Local through project docs.
User launches app with custom endpoint.
User selects DynamoDB.
User lists tables.
App uses endpoint URL in boto3 client or AWS CLI command.
Generated scripts include endpoint-url.
```

---

# 33. Documentation deliverables

The repository should include, SOMEDAY

```text
README.md
SPEC.md
ARCHITECTURE.md
DEVELOPING.md
TESTING.md
LOCAL_SERVICES.md
SECURITY.md
```

## 33.1 README

Should explain, SOMEDAY

```text
What this is
What this is not
Supported services
Install
Run
Basic screenshots
Safety warning
```

## 33.2 LOCAL_SERVICES

Should explain:

```text
moto_server setup
DynamoDB Local setup
OpenSearch container setup
Redis/Valkey setup
custom endpoint usage
known emulator limitations
```

## 33.3 SECURITY

Should explain:

```text
credentials are not stored by the app
uses existing AWS credential chain
generated scripts may contain resource names
logs may contain ARNs
destructive actions require confirmation
local endpoints are user-controlled
```

---

# 34. Acceptance criteria

The project is successful when:

1. A user can launch the GUI with `aws-think-console gui`.
2. The app can show current AWS identity.
3. The app can browse at least one supported service through boto3.
4. The app can browse the same service through AWS CLI mode.
5. The mode selector is always visible.
6. A user can copy the current action as AWS CLI.
7. A user can copy the current action as Python.
8. Long-running calls do not freeze the GUI.
9. Errors are understandable.
10. Moto-backed tests run in CI.
11. The code uses argparse, not Click.
12. The code avoids leading underscores as a “private” convention.
13. VPC, subnet, and security group data is available read-only where needed.
14. The app avoids raw JSON dumps as the primary UI.
15. Generated scripts are useful outside the app.

---

# 35. Design principle

The guiding rule:

> The GUI should make AWS operations easier to understand, easier to repeat, and easier to turn into scripts.

When there is a conflict between mimicking the AWS Console and generating clear AWS CLI/boto3 workflows, prefer the clear workflow.
