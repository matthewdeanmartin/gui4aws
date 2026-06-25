# Coverage improvement plan

**Baseline:** 47% overall (5965 stmts, 3182 missed)
**Date:** 2026-05-23
**Goal:** ~70% without touching GUI/main-window integration paths that require a full running app

______________________________________________________________________

## Current state by bucket

| Bucket | Files | Status |
|---|---|---|
| Models / dataclasses | models.py, all services/\*/models.py | 99-100% ✓ |
| Service definitions (actions + service.py) | Most services | 69-100% ✓ |
| **View functions** (boto3 → Summary) | networking, ecs, cloudwatch, athena, ssm, ses, sns, lambdas | 16-36% ← big target |
| **Moto action integration** | ecs, cloudformation, sns, ses, ssm, lambdas, networking | 0-46% ← big target |
| Execution layer | boto3_executor, action_cache, action_history, endpoint_config | 92-98% ✓ |
| CLI executor | aws_cli_executor.py | 40% |
| GUI widgets | main_window, main_panel, sidebar, filter_bar, toolbar, dialogs | 12-78% |
| Unstarted modules | config.py, demo_resources.py, cdk_dialog.py, terraform_dialog.py | 0% |

______________________________________________________________________

## Priority 1 — view function pure tests (no moto needed)

These are all pure functions: `dict → list[Summary]`. They require zero AWS, zero moto, just
constructed dicts. Each one is currently 16-36% covered. Write them in
**`tests/test_views_pure.py`** — one file, all view functions, no fixtures.

### ECS views (`gui4aws/services/ecs/views.py` — 20%)

- `to_cluster_summaries` with `clusters` key (describe_clusters path)
- `to_cluster_summaries` with `clusterArns` key (list_clusters path)
- `to_cluster_summaries` with empty response
- `to_service_summaries` with `services` key (describe_services path)
- `to_service_summaries` with `serviceArns` key (list_services path)
- `to_task_summaries` with `tasks` key (describe_tasks path)
- `to_task_summaries` with `taskArns` key (list_tasks path)
- `to_task_definition_summaries` with `taskDefinitionArns` list
- `to_task_definition_summaries` with `taskDefinition` single-item path
- `_arn_to_family_revision` for `family:revision`, plain `family`, full ARN

### Networking views (`gui4aws/services/networking/views.py` — 16%)

- `to_vpc_summaries` with named VPC (tag Key=Name) and unnamed VPC
- `to_subnet_summaries` with subnets
- `to_security_group_summaries` with security groups
- `to_security_group_rule_summaries` with inbound/outbound rules
- `to_alb_summaries` with load balancers
- `to_target_group_summaries` with target groups
- `_name_from_tags` with missing Name tag, present Name tag, empty tags list

### CloudWatch views (`gui4aws/services/cloudwatch/views.py` — 24%)

- `to_alarm_summaries` with alarms including threshold and description
- `to_alarm_summaries` with empty response
- `to_log_group_summaries` with retention_days present and absent
- `to_log_stream_summaries` with lastEventTimestamp (ms epoch)
- `to_log_stream_summaries` with missing timestamps
- `to_log_event_summaries` with events, trailing newline stripped
- `_fmt_ts` with valid ms epoch, None, invalid value

### Athena views (`gui4aws/services/athena/views.py` — 25%)

Read the file first to see what functions exist, then mirror the same pattern.

### SSM views (`gui4aws/services/ssm/views.py` — 33%)

- `to_parameter_summaries` with `Parameters` key
- `to_parameter_summaries` with optional fields absent (Description, LastModifiedDate, Version, Tier)
- `to_parameter_summaries` with empty response

### SNS views (`gui4aws/services/sns/views.py` — 33%)

- `to_topic_summaries` with topics, empty response
- `to_subscription_summaries` with confirmed subscription
- `to_subscription_summaries` with `PendingConfirmation` ARN
- `to_subscription_summaries` with empty response

### SES views (`gui4aws/services/ses/views.py` — 33%)

Read the file, then add equivalent cases.

### Lambda views (`gui4aws/services/lambdas/views.py` — 36%)

- `to_function_summaries` with functions list
- `to_function_summaries` with empty response
- Fields: runtime, handler, role, memory, timeout, last_modified

### CloudFormation views (`gui4aws/services/cloudformation/views.py` — 47%)

- `to_stack_summaries` with stacks
- `to_stack_summaries` with empty response

### IAM views (`gui4aws/services/iam/views.py` — 48%)

Read the file, then cover all normalizer functions.

### Backup views (`gui4aws/services/backup/views.py` — 53%)

- `to_recovery_point_summaries` (the uncovered path)
- `to_backup_job_summaries` (the uncovered path)
- Check the exact missing lines (53-74, 102-119, 124-125, 142, 151)

______________________________________________________________________

## Priority 2 — moto action integration tests (new service files)

Each file below needs its own `tests/test_<service>_actions.py`. Follow the exact pattern
of `test_sqs_actions.py` and `test_secrets_actions.py`: use `mock_aws_env` fixture,
call `AppContext.execute(ACTION, inputs={...})`, assert `Boto3Result`, call view function,
assert summaries.

### `tests/test_ecs_actions.py`

Moto supports ECS fully. Cover:

- `LIST_CLUSTERS` / `DESCRIBE_CLUSTERS` — create cluster via boto3, assert it appears
- `CREATE_CLUSTER` via action
- `REGISTER_TASK_DEFINITION` via action — creates a task def, verify with `LIST_TASK_DEFINITIONS`
- `DESCRIBE_TASK_DEFINITION` via action
- `LIST_TASK_DEFINITIONS` returns planted task def
- `CREATE_SERVICE` / `LIST_SERVICES` / `DESCRIBE_SERVICES`
- `DELETE_CLUSTER` removes cluster
- `DELETE_SERVICE` removes service

### `tests/test_ssm_actions.py`

Moto supports SSM. Cover:

- `PUT_PARAMETER` (create) via action
- `GET_PARAMETER` by name
- `DESCRIBE_PARAMETERS` returns planted parameter
- `GET_PARAMETERS_BY_PATH` with a path prefix
- `DELETE_PARAMETER` removes it
- Optional: `GET_PARAMETER_HISTORY`

### `tests/test_sns_actions.py`

Moto supports SNS. Cover:

- `CREATE_TOPIC` via action
- `LIST_TOPICS` returns planted topic
- `SUBSCRIBE` (to SQS endpoint — moto supports this)
- `LIST_SUBSCRIPTIONS_BY_TOPIC`
- `PUBLISH` message to topic
- `DELETE_TOPIC`

### `tests/test_cloudformation_actions.py`

Moto supports CloudFormation. Cover:

- `LIST_STACKS` empty
- Create a stack via boto3, `LIST_STACKS` returns it, `DESCRIBE_STACK` describes it
- `_list_stacks_boto3_params` builder with status filter (pure — no moto needed)
- `_list_stacks_cli_args` builder with status filter (pure)
- `DELETE_STACK` via action

### `tests/test_networking_actions.py`

Moto supports EC2 networking. Cover:

- `DESCRIBE_VPCS` returns default VPC
- Create VPC via boto3, `DESCRIBE_VPCS` shows it
- `DESCRIBE_SUBNETS` with planted subnet
- `DESCRIBE_SECURITY_GROUPS` with planted group
- `DESCRIBE_INTERNET_GATEWAYS` (check moto support first)
- `DESCRIBE_ROUTE_TABLES` with planted route table

### `tests/test_cloudwatch_actions.py`

Moto supports CloudWatch and CloudWatch Logs. Cover:

- `DESCRIBE_ALARMS` empty, then with planted alarm
- Create log group via boto3, `DESCRIBE_LOG_GROUPS` returns it
- `DESCRIBE_LOG_STREAMS` with planted stream
- `GET_LOG_EVENTS` with planted events (put_log_events via boto3, then GET_LOG_EVENTS action)

### `tests/test_iam_actions.py`

Moto supports IAM. Cover:

- `LIST_USERS` empty, then with planted user
- `LIST_ROLES` empty, then with planted role
- `LIST_POLICIES` with planted policy
- `LIST_GROUPS` with planted group
- Check `gui4aws/services/iam/actions.py` lines 20-31 (the builder functions)

### `tests/test_ses_actions.py`

Moto supports SES (email identity verification). Cover:

- `LIST_IDENTITIES` with planted verified email
- Verify an email identity via boto3, assert it appears
- Check what other actions exist in ses/actions.py

### `tests/test_lambda_actions.py`

Moto supports Lambda. Cover:

- `LIST_FUNCTIONS` empty, then with planted function
- `CREATE_FUNCTION` via action (needs zip bytes — use a minimal zip in the test)
- `GET_FUNCTION` by name
- `DELETE_FUNCTION` removes it
- `_create_function_boto3_params` builder (pure — test the zip_file_path absent/present branches)

______________________________________________________________________

## Priority 3 — execution layer gaps

### `tests/test_boto3_executor.py` (currently 92%, fill the 8%)

Missing: lines 80, 160-162, 179, 181, 183

- Line 80: `build_session` when `profile_name` is set — needs mock since real profiles don't exist in CI.
  Use `pytest-mock` to patch `boto3.Session` and verify it's called with `profile_name=`.
- Lines 160-162, 179, 181, 183: error handling in `execute` — `ClientError`, `BotoCoreError`,
  unexpected exception paths. Use `mock_aws_env` + manually raise inside boto3 call via monkeypatch.

### `tests/test_aws_cli_executor.py` (currently 40%)

Missing: lines 58-61, 69-103, 111-161, 174-178, 186-187 — essentially the full `execute` method.

Strategy: use `pytest.MonkeyPatch` to stub `subprocess.run` to return controlled output.
No real `aws` CLI binary needed.

- `_build_argv` returns expected CLI args for a simple action
- `execute` with stubbed subprocess returning exit 0 + JSON stdout → `AwsCliResult`
- `execute` with exit 1 → `AwsCliFailure`
- `execute` with `aws` binary not found (FileNotFoundError) → `AwsCliFailure`
- Endpoint URL wiring: verify `--endpoint-url` appears in argv when mode != AWS
- Profile wiring: verify `--profile` appears in argv when profile_name is set

### `tests/test_script_generator.py` additions (currently 83%)

Missing: lines 48-62, 89 — the CLI script path for endpoint injection and the AWS CLI mode path.

- `generate_cli_script` with `MOTO` endpoint mode — verify `--endpoint-url` in output
- `generate_cli_script` with profile — verify `--profile` in output
- `generate_python_script` for an action that has a `boto3_params_builder` (e.g. LIST_SECRETS)

______________________________________________________________________

## Priority 4 — GUI widget tests (Tk, medium difficulty)

All of these use the `tk_root` module-scoped fixture pattern from `test_action_form.py`.
These tests do NOT need moto; they just verify widget construction and event wiring.

### `tests/test_gui_widgets.py`

- **Sidebar**: construct with a registry, verify it populates nav items without error.
  `sidebar.select(service_id="sqs")` fires selection callback.
- **StatusBar**: construct, call `set_status("Loading...")`, verify `winfo_exists()`.
- **FilterBar**: construct, type in filter text, verify `get_filter()` returns the text.
- **ResourceTable**: construct, call `set_rows(rows, columns)`, verify row count.
- **OutputPanel**: construct, call `append("hello")`, verify content visible.
- **DetailTree**: construct, call `show({"key": "value"})`, verify it exists.
- **ConfirmationDialog**: construct with DESTRUCTIVE action, verify the confirm button exists.
  Do not click it (no callback needed).

### `tests/test_toolbar.py` additions (currently 69%)

Missing: lines 129-184, 193 — the toggle callbacks for moto/robotocore and the clear-cache button.

- Construct Toolbar, call `on_moto_toggle(True)` — verify `toolbar.moto_running` becomes True.
- Simulate mode combobox change — verify `context.mode` updates.
- Simulate region combobox change — verify `context.region_name` updates.
- Clear-cache button: call `on_clear_cache` callback, verify it fires.

### `tests/test_action_dialog_extended.py` (currently 78%)

Missing: lines 112-119, 220, 223-224, 237-260, 263, 269-287 — run/stop/copy buttons, result display.

- Construct dialog with a DESTRUCTIVE action — verify confirmation step appears.
- Construct dialog with a READ_ONLY action — verify no confirmation step.
- The "Copy" button on the script tab: simulate click, verify it doesn't raise.
- The result text widget: feed a Boto3Result via `dialog.show_result(result)`,
  verify `result_text` contains expected content.

______________________________________________________________________

## Priority 5 — config, demo, and zero-coverage modules

### `gui4aws/config.py` (0%, 76 stmts)

This likely handles loading/saving settings (CDK config panel etc.). Read the file first.
Pure unit tests: construct the config object with defaults, load from dict, save to dict,
round-trip serialization. No I/O should be needed — patch `open`/`pathlib.Path` if required.

### `gui4aws/demo_resources.py` (0%, 391 stmts)

Demo seeding functions. These should be testable with `mock_aws_env` — they call boto3
directly to create resources. A single test per service (secrets, ECS, S3, etc.) that calls
the relevant `seed_*` function and asserts at least one resource appears. Put these in
**`tests/test_demo_resources.py`**.

### `gui4aws/testing/moto_support.py` (0%, 11 stmts)

Helper used in test infrastructure. Read the file — it probably has a convenience context
manager or fixture builder. Write a test that exercises it.

### `gui4aws/gui/terraform_dialog.py` and `cdk_dialog.py` (0%, 26 + 309 stmts)

Tk dialogs. Use the same pattern as `test_action_dialog_*.py`: construct with `tk_root`,
verify `winfo_exists()`, pump the event loop, destroy. The cdk_dialog has 309 stmts so
it's complex — just cover construction and the main UI elements.

______________________________________________________________________

## What NOT to test

- `gui4aws/__main__.py` (1 stmt — trivial `main()` call, not worth the process spawn)
- `gui4aws/gui/main_window.py` integration paths — the 661 missing lines are deep
  MainWindow event-loop interactions (toolbar callbacks firing nav refreshes, worker
  threads completing, result dispatch). These require a full running app and are better
  covered by the moto-server Tk tests once those are expanded. Don't chase them with
  unit mocks — you'll be mocking everything and testing nothing.
- `gui4aws/robotocore_server.py` Docker paths — the 125 missing lines are `_docker_run`,
  `_docker_stop`, `_start_log_reader`. These require Docker to be running. Leave them
  in `tests_robotocore/`.

______________________________________________________________________

## Expected coverage after this plan

| Module group | Current | After Priority 1+2 | After Priority 3+4 |
|---|---|---|---|
| View functions | ~25% avg | ~95% | ~95% |
| Service actions | ~60% avg | ~85% | ~85% |
| Execution layer | ~80% avg | ~80% | ~95% |
| GUI widgets | ~30% avg | ~30% | ~55% |
| Config/demo | 0% | ~70% | ~70% |
| **Overall** | **47%** | **~62%** | **~70%** |

______________________________________________________________________

## Test file checklist for next clanker

```
tests/test_views_pure.py           ← Priority 1 (all view functions, pure dicts)
tests/test_ecs_actions.py          ← Priority 2
tests/test_ssm_actions.py          ← Priority 2
tests/test_sns_actions.py          ← Priority 2
tests/test_cloudformation_actions.py  ← Priority 2
tests/test_networking_actions.py   ← Priority 2
tests/test_cloudwatch_actions.py   ← Priority 2
tests/test_iam_actions.py          ← Priority 2
tests/test_ses_actions.py          ← Priority 2
tests/test_lambda_actions.py       ← Priority 2
tests/test_boto3_executor.py       ← Priority 3 (gap fill)
tests/test_aws_cli_executor.py     ← Priority 3
tests/test_script_generator.py     ← Priority 3 (gap fill in existing file)
tests/test_gui_widgets.py          ← Priority 4
tests/test_toolbar.py              ← Priority 4 (gap fill in existing test)
tests/test_action_dialog_extended.py  ← Priority 4 (gap fill)
tests/test_demo_resources.py       ← Priority 5
tests/test_config.py               ← Priority 5
```

Start with **Priority 1** (`test_views_pure.py`) — highest coverage gain per line of test code,
zero infrastructure needed, can be written and verified in minutes.
