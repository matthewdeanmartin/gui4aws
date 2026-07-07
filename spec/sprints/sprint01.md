# Sprint 01

Status: complete.

Goal: make live AWS browsing more trustworthy.

## Scope

Fix the visible correctness bugs from the old TODO list:

- ECS service rows show real status, running count, pending count, and active count.
- KMS key browsing shows useful metadata without making users manually interpret a one-key describe result.
- Aurora cluster KMS links open the KMS detail flow when a cluster has `kms_key_id`.
- SQS detail includes the queue ARN.
- IAM policy rows make the active policy document easy to fetch and inspect.

Also add or update focused tests for each fixed normalization or row-action path.

## Out of scope

Global write/delete gates.

Large service redesigns.

Release packaging.

## Done when

`uv run pytest` is green.

The fixed service rows have regression tests at the view/action level.

The app docs in `spec/road_map/road_map.md` no longer list any item completed in this sprint.

## Completed

ECS cluster browsing now enriches `ListClusters` with `DescribeClusters`. ECS services already use list+describe through the default Services navigation.

KMS key browsing now enriches `ListKeys` with `DescribeKey`.

SQS queue browsing now fetches `QueueArn`, approximate message count, and visibility timeout.

IAM `Get Policy` now includes the active policy document, and the policy row label says so.

Aurora cluster KMS row-action wiring is covered by regression tests.
