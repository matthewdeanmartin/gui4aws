# Route 53 Support

Add Amazon Route 53 to gui4aws following the established per-service pattern
(`gui4aws/services/<id>/{models,views,actions,service}.py` + registry wiring +
demo seeding + moto/robotocore parity tests).

## Background: how a service is wired

Every service is four files plus registry + demo + test wiring:

- `models.py` — frozen dataclass summaries (plain data, no boto3/tk).
- `views.py` — `to_*_summaries(response)` normalizers: raw boto3 dict → list of summaries.
- `actions.py` — `ActionDefinition`s (READ_ONLY list/get, SAFE_WRITE create, DESTRUCTIVE delete),
  each carrying a `CliTemplate`, `Boto3Template`, `ResultViewDefinition`, and `iam_permissions`.
  Multi-step calls use a `boto3_execute_fn(client, inputs)`; input massaging uses
  `boto3_params_builder` / `cli_args_builder`.
- `service.py` — a `ServiceDefinition` with `NavigationItem`s tying nav entries to a default
  read action and `RowAction` buttons (with `prefill` from the selected row's attributes).
- Registered in `services/service_registry.py::default_registry()` inside a `try/except ImportError`.
- Demo seeding in `demo_resources/` + wired into `_seed_with_client_factory`.
- Tests: moto-backed in `tests/`, robotocore parity in `tests_robotocore/`.

## Route 53 specifics that shape the design

Route 53 is **global** (no region); boto3 service name and CLI name are both `route53`.
The awkward parts versus other services:

- **Record sets are nested inside a hosted zone.** `list_resource_record_sets` and
  `change_resource_record_sets` both require `HostedZoneId`. Records have no standalone
  list — you always scope by zone. → these actions need `boto3_execute_fn` /
  builder functions, not plain templates.
- **Create/delete records go through one API:** `change_resource_record_sets` with an
  action `UPSERT` / `DELETE` and a nested `ChangeBatch` structure. → build the
  `ChangeBatch` dict in a `boto3_execute_fn`; the CLI equivalent needs a `--change-batch`
  JSON blob, so the CLI template is best-effort.
- **Hosted zone IDs** come back as `/hostedzone/ABC123`; the change/list APIs accept the
  bare id or the prefixed form. Normalize to bare id in views, accept either in builders.
- **moto** supports `create_hosted_zone`, `list_hosted_zones`, `get_hosted_zone`,
  `delete_hosted_zone`, `change_resource_record_sets`, `list_resource_record_sets` — enough
  for full validation. robotocore (LocalStack-family) covers the same core.

## Phase 1 — Hosted zones (minimum viable)

Deliver hosted-zone CRUD, the registry wiring, and moto tests. This alone satisfies the
"at absolute minimum, hosted zone setup" bar.

Files: `gui4aws/services/route53/{__init__,models,views,actions,service}.py`.

- **models.py**: `HostedZoneSummary(zone_id, name, private, record_count, comment)`.
- **views.py**: `to_hosted_zone_summaries(response)` over `HostedZones` — strip the
  `/hostedzone/` prefix from `Id`, read `Config.PrivateZone`, `ResourceRecordSetCount`,
  `Config.Comment`.
- **actions.py**:
  - `LIST_HOSTED_ZONES` (READ_ONLY, `list_hosted_zones`, TABLE).
  - `GET_HOSTED_ZONE` (READ_ONLY, `get_hosted_zone`, RAW_JSON, input `zone_id`).
  - `CREATE_HOSTED_ZONE` (SAFE_WRITE): inputs `name` (required), `comment`, `private` (bool),
    `vpc_id` + `vpc_region` (for private zones). Needs a `boto3_params_builder` to build the
    `CallerReference` (unique — use a uuid), `HostedZoneConfig`, and optional `VPC` block.
  - `DELETE_HOSTED_ZONE` (DESTRUCTIVE, `delete_hosted_zone`, input `zone_id`). Accept prefixed
    or bare id (builder strips/normalizes).
- **service.py**: one `NavigationItem("hosted_zones", "Hosted Zones")` defaulting to
  `LIST_HOSTED_ZONES`, with row actions Get / Create / Delete (prefill `zone_id` from `zone_id`).
- Register `route53` in `default_registry()`.
- Tests `tests/test_route53_actions.py`: create → list (assert present) → get → delete,
  plus a pure test of the params builder (CallerReference present, VPC omitted when public).

## Phase 2 — Record sets

Add record-set browsing and editing scoped to a zone.

- **models.py**: add `RecordSetSummary(name, type, ttl, records, alias_target)`.
- **views.py**: `to_record_set_summaries(response)` over `ResourceRecordSets` — join
  `ResourceRecords[].Value` into a newline/`, `-separated string, surface `AliasTarget.DNSName`
  when present (alias records have no TTL/ResourceRecords).
- **actions.py**:
  - `LIST_RECORD_SETS` (READ_ONLY): input `zone_id` (required), `boto3_execute_fn` calling
    `list_resource_record_sets(HostedZoneId=...)`, TABLE view.
  - `UPSERT_RECORD_SET` (SAFE_WRITE): inputs `zone_id`, `record_name`, `record_type`
    (choice A/AAAA/CNAME/TXT/MX/NS), `ttl` (int, default 300), `value` (multiline — one
    value per line). `boto3_execute_fn` builds a `ChangeBatch` with `Action=UPSERT` and calls
    `change_resource_record_sets`.
  - `DELETE_RECORD_SET` (DESTRUCTIVE): same inputs; `Action=DELETE`. DELETE requires the exact
    existing record (name/type/ttl/values), so the row action prefills all of them.
- **service.py**: add a `NavigationItem("record_sets", "Record Sets")` with a `zone_id`
  filter field (so the list is scoped), and row actions Upsert / Delete prefilled from the
  selected record. Also add an Upsert/Delete/List-records row action on the Hosted Zones nav
  that prefills `zone_id`.
- Tests: extend `tests/test_route53_actions.py` — create zone, upsert an A record, list and
  assert it's present, delete it, list and assert gone. Pure test of the ChangeBatch builder.

## Phase 3 — Demo seeding + robotocore parity + polish

- **demo_resources/route53.py**: `seed_route53(r53)` — create a `demo.internal.` private-ish
  hosted zone (public is fine for moto), add a couple of record sets (an A record
  `www.demo.internal.` and a TXT). Tag via comment (`gui4aws:demo`). Wire into
  `_seed_with_client_factory` (`created.update(seed_route53(client("route53")))`).
- **tests_robotocore/test_robotocore.py**: mirror the moto zone+record test against robotocore.
- Update `test_service_registry.py` (route53 present, hosted_zones nav default action) and
  the README/CHANGELOG service list.
- Confirm `make prerelease` stays green (mypy, bandit, dev-status); run tests with
  `uv run --no-sync`.

## Out of scope (note for later)

Health checks, traffic policies, DNSSEC, domain registration (`route53domains` is a
separate boto3 service), and alias-target creation UI (alias records are read-only-surfaced
in Phase 2, not editable).
