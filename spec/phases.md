# PHASES: `gui4aws` implementation roadmap

This document breaks the work in `spec/spec.md` into discrete, mergeable phases. It is the
working plan for both human and AI contributors. Read this **before** reading the spec end-to-end
when you need to know "what should I do next?".

The package name in this repo is `gui4aws` (not `aws_think_console` as in the original spec).
Everywhere the spec says `aws_think_console`, read `gui4aws`. Everywhere it says
`aws-think-console` as a CLI, read `gui4aws`.

---

## Guiding rules for every phase

These rules come from `spec/spec.md` and `AGENTS.md`. They are not optional:

1. **Stdlib first.** tkinter, argparse, dataclasses, pathlib, logging, threading, queue. The only
   non-stdlib runtime dependencies are `boto3` / `botocore`. No click, no typer, no rich, no
   textual, no customtkinter, no PyQt.
2. **`_` means unused, not private.** Use module boundaries, `__all__`, and clear naming for
   encapsulation. Never write `def _helper(...)` to mean "internal helper".
3. **Type annotations on everything.** Public *and* internal functions.
4. **`logging`, not `print`.** Configure logging once via `gui4aws/logging_config.py`.
5. **`pathlib.Path`, not string path math.**
6. **GUI logic is testable without tkinter.** Each service module exposes plain functions /
   dataclasses that the GUI binds to. Widget construction lives in `gui/`, AWS logic does not.
7. **AWS calls never block the tk event loop.** Run them in a worker thread, deliver results
   through a `queue.Queue`, and let the main loop poll with `widget.after(...)`.
8. **No raw JSON dumps as the primary UI.** Tables, trees, key/value grids. Raw JSON is
   available behind a "View raw response" button.
9. **Every GUI action is also an exportable script.** AWS CLI and boto3. The exported code must
   be boring, explicit, paste-into-a-real-project Python — no `gui4aws` imports in generated
   scripts.
10. **Moto-first.** Development and CI run against moto. Real AWS comes later and is opt-in.

---

## Moto constraints we are designing around

We are intentionally working *against moto* in early phases. That means our service modules and
tests have to accept these realities:

- Moto's RDS / Aurora support covers the common describe/create/delete/restore-snapshot paths,
  but engine-version validation, parameter group inheritance, and event history are partial.
  Treat anything beyond the documented `mock_aws` coverage as best-effort.
- Moto's AWS Backup support covers backup vaults, backup plans, and recovery-point listing for
  several resource types, but `StartBackupJob` against arbitrary resource ARNs is not a perfect
  emulation — recovery points may need to be planted directly with the moto backend or via
  `create_backup_vault` + `start_backup_job` on supported resource types (EFS, DynamoDB, RDS).
- Moto's IAM/STS support is fine for our needs — `sts:GetCallerIdentity` works and returns a
  stable fake account id (`123456789012`).
- Tests use `from moto import mock_aws` (moto 5+ unified decorator). Old service-specific
  decorators (`mock_rds`, `mock_backup`) are removed.
- For features moto cannot emulate, the **service module still ships**, but the corresponding
  test is marked `@pytest.mark.integration` and skipped in the default `make test` run.

When a moto limitation forces a design choice, document it in the relevant service module's
top-of-file docstring, not in scattered comments.

---

## Phase 0 — Project hygiene (done before phase 1)

Already in place from the cookiecutter:

- `pyproject.toml`, `Makefile`, `tox.ini`, ruff/mypy/pylint config, pre-commit, mkdocs.
- `gui4aws/{__init__,__about__,__main__,cli}.py`, `tests/test_cli.py`.

What this phase still owes:

- [x] Add `moto` and `pytest-mock` to the dev dependency group.
- [ ] Add `boto3` as a runtime dep (already declared in `pyproject.toml`).
- [ ] Make sure `uv sync --all-extras && uv run pytest` is green before starting phase 1.

---

## Phase 1 — Application shell

Goal: a runnable tkinter window with the layout from spec §7, even if every panel is empty. No
AWS calls yet. This phase is **not** allowed to import boto3 from any `gui/` module — the GUI
only talks to executors, never directly to boto3.

### Deliverables

```
gui4aws/
  app.py                       # AppContext: profile/region/mode/endpoint, wires executors + registry
  config.py                    # Load/save user config (TOML preferred, JSON fallback ok)
  logging_config.py            # configure_logging(level, file)
  models.py                    # Shared dataclasses: ResourceSummary, ActionDefinition, RiskLevel, ...

  gui/
    __init__.py
    main_window.py             # MainWindow: composes toolbar, sidebar, main panel, status bar
    toolbar.py                 # Mode / profile / region / endpoint selectors, copy buttons
    sidebar.py                 # Service tree, driven by service_registry
    main_panel.py              # Notebook container for resource list / detail / action / output
    resource_table.py          # ttk.Treeview wrapper for sortable resource lists
    detail_tree.py             # ttk.Treeview wrapper for nested property trees
    action_form.py             # Dynamic form built from list[InputField]
    output_panel.py            # Structured output viewer (text + "view raw JSON" button)
    script_viewer.py           # Read-only viewer for generated CLI/Python
    status_bar.py              # Status / last operation / duration / mode display

  execution/
    __init__.py
    execution_mode.py          # ExecutionMode enum + EndpointMode enum
    endpoint_config.py         # EndpointConfig: AWS / moto / docker / custom + URL
    aws_cli_executor.py        # Run `aws` subprocess; capture stdout/stderr/exit/duration
    boto3_executor.py          # Build session/client honoring endpoint_url, run operation
    action_history.py          # In-memory history of executed actions + export helpers
    script_generator.py        # Render an ActionDefinition + bound inputs as CLI or Python

  services/
    __init__.py
    service_registry.py        # Registry of ServiceDefinition objects, loaded at startup

  testing/
    __init__.py
    moto_support.py            # Helpers: mock_aws context, planting fixture data, endpoint helpers
```

### Acceptance for phase 1

1. `gui4aws gui` opens a window with the three-region layout, a toolbar, and a status bar.
2. The toolbar shows mode (AWS CLI / boto3), profile, region, and endpoint selectors. Changing
   them updates `AppContext` (verified via a unit test on `AppContext`, not the widget).
3. `gui4aws doctor` prints environment diagnostics: python version, boto3 version, aws CLI on
   PATH yes/no, moto importable yes/no, default profile/region.
4. `gui4aws list-profiles` and `gui4aws list-regions` work.
5. `import gui4aws` and every `gui4aws.gui.*` module import cleanly **without** opening a tk
   window. Tk widget construction must be inside class `__init__` methods or factory functions,
   not at module import time.
6. `uv run pytest` is green and covers: `AppContext`, `script_generator` with a fake action,
   `action_history` add/list/export, `endpoint_config` parsing.

### Notes / gotchas

- On headless CI, tkinter cannot create a root window. Tests that need tk must either be marked
  `@pytest.mark.integration` or use a fixture that calls `Tk()` inside a `try/except` and
  `pytest.skip()` if the display is unavailable. Default unit tests must not need a display.
- The `ScriptGenerator` should accept a frozen dataclass of inputs and produce a string. It
  must not introspect tk widgets.

---

## Phase 2 — RDS Aurora (read-only) against moto

Goal: a user can launch `gui4aws gui --endpoint-mode moto`, click "Aurora → Clusters", and see
clusters planted by a moto fixture rendered in a sortable table. Same for cluster snapshots and
cluster member instances. No write actions yet.

### Why Aurora before plain RDS?

The spec calls out Aurora as cluster-centered and the operational workflow (restore-from-snapshot)
is the most useful demo case. Plain RDS reuses most of the same machinery and will follow in a
later phase.

### Deliverables

```
gui4aws/services/aurora/
  __init__.py
  service.py             # ServiceDefinition for Aurora
  models.py              # AuroraClusterSummary, AuroraClusterSnapshotSummary, AuroraInstanceSummary
  actions.py             # describe_db_clusters, describe_db_cluster_snapshots, describe_db_instances
  views.py               # Functions that take raw boto3 response -> list[AuroraClusterSummary]
  cli_templates.py       # CliTemplate per action
  boto3_templates.py     # Boto3Template per action
```

### Acceptance for phase 2

1. `services/aurora/service.py` exposes a `SERVICE: ServiceDefinition` constant. Importing it
   does not touch AWS.
2. `actions.describe_db_clusters(executor, region, **filters)` runs through both the boto3 and
   AWS CLI executors and returns a `list[AuroraClusterSummary]`.
3. A moto-backed test plants two clusters and verifies the action returns both, normalized.
4. The Aurora sidebar entry appears under "Aurora" with `Clusters`, `Snapshots`,
   `Instances`. Clicking each populates a `resource_table` widget. (This is a widget test —
   may be marked integration if display is unavailable.)
5. `Copy current action as AWS CLI` and `Copy current action as Python` produce text that, if
   pasted into a shell or `.py` file, runs the same describe and prints results — verified by
   parsing the generated text in a unit test (no need to actually execute it).

### Restore-from-snapshot — script generation only, in this phase

We do *not* run restore against moto in phase 2. We do generate the CLI and Python for it from a
form, and we add a unit test asserting the generated script matches the spec §17.2 example
shape. Running the restore is phase 4.

---

## Phase 3 — AWS Backup (read-only) against moto

Goal: list backup vaults, backup plans, recovery points (per vault), and recent backup/restore
jobs. The sidebar lights up under "AWS Backup".

### Deliverables

```
gui4aws/services/backup/
  __init__.py
  service.py
  models.py              # BackupVaultSummary, BackupPlanSummary, RecoveryPointSummary, BackupJobSummary
  actions.py             # list_backup_vaults, list_backup_plans, list_recovery_points_by_backup_vault, list_backup_jobs, list_restore_jobs
  views.py
  cli_templates.py
  boto3_templates.py
```

### Acceptance for phase 3

1. Moto-backed test creates a backup vault, asserts `list_backup_vaults` returns it.
2. Moto-backed test creates a backup plan, asserts `list_backup_plans` returns it normalized.
3. Recovery points: because moto's behavior here is partial, the test plants a recovery point
   via the moto backend directly (using `moto.backup.models.backup_backends`) when needed, and
   that is the documented exception to "use the public API in tests".
4. The action history captures every list call with timing and request params.
5. CLI and Python export match what `aws backup list-...` and `boto3.client("backup").list_...`
   would write.

---

## Phase 4 — Safe write workflows against moto ✅

Goal: forms that perform `create_db_cluster_snapshot`, `restore_db_cluster_from_snapshot`,
`create_backup_vault` against the moto endpoint. Each form generates a preview script before
executing and writes the action to history. (`start_backup_job` is deferred — moto doesn't
implement it.)

This phase introduced:

- `gui/action_form.py` rendering from `list[InputField]` (built in phase 1, wired in here).
- `gui/review_dialog.py` — review screen for `safe_write` / `cost_affecting` actions with
  generated CLI + Python and an explicit Confirm. `ReviewDecision` is the headless state
  helper.
- `gui/confirmation_dialog.py` — typed-text confirmation for destructive actions. Built in
  phase 4, used in phase 6. `TypedConfirmation` is the headless state helper.
- `NavigationItem.form_action_id` — second navigation slot for actions that should open a form
  rather than auto-run a read-only describe.
- `MainPanel.show_action_form(...)` + an "Action" Notebook tab.
- `MainWindow.review_then_run(...)` — generates scripts, opens the review dialog, and only
  runs the action after Confirm.
- `MainWindow.record_history(...)` — every executed action lands in `AppContext.history`.

### Acceptance for phase 4

- [x] Restore Aurora cluster from snapshot, end-to-end against moto: plant a snapshot, run the
      form, assert a new cluster appears in `describe_db_clusters`.
      (`tests/test_phase4_write_flows.py::test_create_db_cluster_snapshot_then_restore_creates_new_cluster`)
- [x] Create backup vault via the form, list it back.
      (`tests/test_phase4_write_flows.py::test_create_backup_vault_then_list`)
- [x] Generated script export for the restore matches the spec example shape.
      (`tests/test_phase4_write_flows.py::test_restore_python_script_matches_spec_example_shape`)
- [x] Dialog decision logic covered headlessly.
      (`tests/test_dialogs.py`)

---

## Phase 5 — Plain RDS, ElastiCache, OpenSearch, DynamoDB

Goal: fill in the remaining initial services per spec §17, in the order from §30.2 (DynamoDB
moves up because moto support is excellent there). Each gets the same read-views-first treatment
as Aurora.

### Sequence

1. Plain RDS (instances, snapshots, parameter groups). Most code reuses Aurora's machinery.
2. DynamoDB (tables, items, backups). Add a conservative item editor.
3. ElastiCache (replication groups, cache clusters, snapshots). Distinguish Redis / Valkey /
   Memcached in the UI but preserve AWS names in scripts.
4. OpenSearch (domains, versions). Cost-affecting warning on create.

---

## Phase 6 — Destructive workflows

Goal: delete with typed confirmation per spec §18.1, only after a review-screen showing the
generated CLI/Python. AWS Backup deletion stays disabled until further notice because of
retention-lock complications (spec §17.3 footnote).

---

## Phase 7 — Real AWS, endpoints, packaging

Goal: stop being moto-only.

- `--endpoint-mode aws` is the new default. `--endpoint-mode moto` still works.
- Custom endpoint URLs propagate into generated scripts (spec §13.4, §19).
- `gui4aws doctor` learns to call `sts:GetCallerIdentity` and report account / ARN.
- Build a wheel and verify `gui4aws gui` launches from a fresh `uv tool install`.

---

## How to start work in any phase

1. `git pull && uv sync --all-extras`.
2. `uv run pytest` must be green before you write a line.
3. Find the next unchecked acceptance bullet in the current phase. That is your scope.
4. Add or update tests **first**. Moto fixtures live in `gui4aws/testing/moto_support.py` and
   `tests/conftest.py`. Reuse them.
5. Implement until the new test passes. Run `uv run make check`.
6. One commit per logical change. Update the phase checklist in this file if you completed an
   acceptance bullet.

---

## Open questions / parked decisions

- **Config format.** Spec prefers TOML. Stdlib `tomllib` (Python 3.11+) reads TOML, but writing
  it needs `tomli-w` or hand-rolled output. We will hand-roll writes initially to stay
  stdlib-only; revisit if writes get complex.
- **Where the sidebar tree is defined.** The `service_registry` owns the tree. Each
  `ServiceDefinition` declares its `navigation_items`. The sidebar walks the registry. No magic
  discovery.
- **Action IDs.** Globally unique strings of the form `<service_id>.<verb>_<noun>`, e.g.
  `aurora.describe_db_clusters`, `backup.list_backup_vaults`. Generated scripts reference the
  underlying AWS operation, not the action_id.
- **Threading model.** One worker thread per action, results posted to a `queue.Queue` that the
  main window drains via `after(50, ...)`. Cancellation in MVP is "ignore the result"; real
  cancellation is later.
