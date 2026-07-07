# Road map

This is the current backlog after rationalizing the old phase docs, loose TODO files, and security review notes.

## Sprint-sized now

- Add global "Enable changes" and "Enable deletes" safety gates. These gates should hide or disable write/destructive buttons until enabled, without replacing existing review and typed-confirmation dialogs.
- Verify pagination across live AWS services. Prev/Next exists, but it needs broader coverage for token shapes and services that default to small result sets.

## Soon

- Add first/last page affordances if a service can support them. Most AWS APIs only expose next-token navigation, so "last" may be impossible for many services.
- Add queue fairness so foreground user actions can outrank background cache warming.
- Tie `SerialWorker.close()` and queue polling cleanup into window shutdown.
- Expand service-specific live-AWS smoke tests where they can run safely against read-only APIs.
- Update README, docs, and screenshots to match the current app.

## Later

- Deeper DynamoDB item workflows.
- More SQL runner polish and connection ergonomics.
- Optional Docker-backed local service docs where Moto/Robotocore are not enough.
- Release pipeline hardening: verify audit/publish behavior even when release-helper commits include `[skip ci]`.
- Consider upper bounds or policy for optional SQL/keyring dependencies before broader publishing.

## Done

- Partition changes refresh the region list.
- The app persists profile, partition, region, mode, endpoint mode, and network settings.
- "No profile" is selectable.
- Starting Moto/Robotocore clears cache and removes the live AWS profile from the active target.
- JMESPath filtering has an Apply button and a dedicated designer from output.
- Basic Prev/Next pagination exists.
- Secret fields are masked, redacted, and exported as placeholders.
- Bandit shell-injection checks are no longer globally skipped.
- ECS cluster/service browsing enriches list results with describe calls so status and counts are visible.
- KMS key browsing enriches `ListKeys` rows with `DescribeKey` metadata.
- Aurora cluster rows expose a KMS key detail action when `kms_key_id` is present.
- SQS queue rows include ARN and common queue attributes.
- IAM policy rows make the active policy document visible from the primary policy action.
