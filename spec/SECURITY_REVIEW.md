# Security Review — gui4aws

**Date:** 2026-06-25
**Reviewer:** Claude (Opus 4.8), at maintainer's request
**Scope / threat model (agreed with maintainer):**

- This is a **desktop app**. Anyone who can install and run it already has the
  rights of the local user, so "code can call AWS / shell out" is *by design*,
  not a vulnerability.
- We **do not** model attacks from third-party machines or non-users against the
  running app. There is no network listener exposed to other hosts (the only
  HTTP servers — moto / robotocore — bind to localhost / are user-launched).
- We **do not** care if the user shoots their own foot (pastes a 1 GB file, runs
  a bad query, deletes their own cluster). Guardrails exist but are a UX feature,
  not a security boundary.
- We **do** care about:
  - sloppy credential / secret handling,
  - secrets leaking to the filesystem (or clipboard, or logs) when the user
    didn't ask for that,
  - supply-chain risk,
  - anything that turns *data the user views* into *code/commands that run*.

Findings are ranked by how much they matter under that threat model.

---

> **Status update (2026-06-25):** H1, H2, and M1 have been **fixed** in this same
> session (see the per-finding notes below). M3 (TLS verification) was
> **accepted/won't-fix** by the maintainer: developers run this against moto /
> robotocore where issuing trusted certs is impractical. M2 is believed handled
> (GHA actions pinned/upgraded). Remaining doc is kept for the record.

## High

### H1 — Plaintext DB passwords leak into action history, generated scripts, and disk exports

> **FIXED.** Added `is_secret` to `InputField` (`models.py`) + `secret_field_names()`
> and `redact_secrets()` helpers. Password fields in Aurora (`master_user_password`,
> `new_master_password`) and Secrets Manager (`secret_string`) are now marked secret.
> The form masks single-line secrets with `show="•"` (`action_form.py`). The script
> generators (`script_generator.py`) emit `$ENV_VAR` (bash) / `os.environ["ENV_VAR"]`
> (python) placeholders instead of the literal — covering both the live preview and
> the history-stored scripts. `record_history` (`window_helpers.py`) stores a
> `redact_secrets`-scrubbed `inputs` snapshot. Verified: a `SuperSecret123!` password
> no longer appears in any generated CLI/Python script or history entry.

**Where:**
- `gui4aws/services/aurora/actions.py` — `master_user_password` (Create DB
  cluster) and `new_master_password` (Update master password) are ordinary
  `InputField`s. There is **no "secret" field kind**, so:
- `gui4aws/gui/action_form.py:68` renders every non-choice field as a plain
  `ttk.Entry` — no `show="*"` masking. The password is visible on screen and
  shoulder-surfable.
- `gui4aws/gui/window_helpers.py:184` (`record_history`) copies the full
  `current_inputs` dict — **password included** — into `ActionHistoryEntry.inputs`,
  and calls `generate_cli_script` / `generate_python_script`, which **inline the
  password verbatim** (`script_generator.py:62`, `:138`).
- `gui4aws/execution/action_history.py:34` (`to_dict` / `export_json`) serializes
  `inputs` (with the password) to JSON; `export_bash` / `export_python` emit the
  password-bearing generated scripts.
- `gui4aws/gui/script_editor_panel.py:154` and the history export paths let the
  user **save these scripts to an arbitrary file** — so a cleartext master
  password lands on disk inside `aws rds create-db-cluster --master-user-password
  's3cr3t'` with no warning.

**Why it matters:** The user typed a secret into one field; without asking, the
app fans it out into in-memory history, the on-screen script preview, the
clipboard ("Copy all"), and any file they export. That's exactly the
"secrets leaking to the filesystem when the user didn't ask for that" case we
said we care about. Generated scripts are advertised as "Safe to paste into a
real project" — pasting a hardcoded master password into a repo is the opposite
of safe.

**Recommendations (pick what fits):**
1. Add an `is_secret: bool = False` flag to `InputField`; mark the password
   fields. In `action_form.py`, render secret fields with `show="•"`.
2. In `record_history` / `to_dict`, **redact** secret-flagged inputs (store
   `"***"` or omit). The history's value is the *shape* of the call, not the
   secret.
3. In `script_generator.py`, for secret params emit a placeholder + a comment
   (`--master-user-password "$DB_PASSWORD"  # set this; do not hardcode`) instead
   of the literal value. This also makes generated scripts genuinely safe to paste.

### H2 — Diagnostic panel renders raw inputs (incl. passwords) and they end up in bug reports

**Where:** `gui4aws/gui/diagnostic_panel.py:245` —
`json.dumps(entry["inputs"], sort_keys=True)` is shown in the cache/diagnostics
tree. Diagnostics panels are precisely what users screenshot or copy into a
GitHub issue. Same root cause as H1 (no secret flag); calling it out separately
because the *diagnostics → bug report* path is a very likely real-world leak.

**Recommendation:** Once H1's redaction lands at the `inputs` source (or in a
shared "redacted view" helper), this panel inherits the fix. Until then, redact
known-secret keys here too.

> **FIXED / not reachable.** Investigation showed the diagnostics "Entries" tree
> is fed by `action_cache.snapshot()`, and the cache only stores **READ_ONLY**
> results (`action_cache.should_cache` → `RiskLevel.READ_ONLY`). No READ_ONLY
> action has secret fields, so passwords never reach this panel. The real leak
> path was action *history*, which H1 now redacts at the source.

---

## Medium

### M1 — Bandit gate is broadened enough to hide real shell/credential findings

**Where:** `pyproject.toml:198`
```
skips = ["B101", "B404", "B602", "B603", "B604", "B605", "B606", "B607", "B105"]
```
- `B602` (`subprocess` with `shell=True`), `B604`/`B605`/`B606` (shell-injection
  family) and `B105` (hardcoded password string) are **globally skipped**. That
  means if someone later introduces a real `shell=True` or hardcodes a secret,
  Bandit stays green. The codebase today is clean here (everything uses argv
  lists, no `shell=True`), so the skips aren't covering a *current* bug — they're
  removing the *future* safety net.
- The code already uses targeted `# nosec` comments correctly
  (`aws_cli_executor.py:8,115`, `moto_server.py:165`), which is the right pattern.

**Recommendation:** Drop `B602`, `B604`, `B605`, `B606`, `B105` (and ideally
`B607`) from the global `skips`. Keep `B101`/`B404`/`B603` if they're noisy, but
prefer per-line `# nosec Bxxx` with a reason (as already done) over blanket
suppression. This is cheap insurance against H1-style regressions.

> **FIXED.** The shell-injection family (`B602/B604/B605/B606`) was removed from
> `skips` — verified zero current findings, so this is pure regression insurance.
> `B607` (partial exec path: `aws`/`docker`/`npx`) and `B105` were kept skipped:
> per the maintainer we don't flag commands we run on purpose, and `B105` is pure
> noise here (it flags boto3 param *names* like `'SecretId'`/`'secret-string'` and
> the intentional moto fake creds `'testing'`). The `skips` list now carries an
> inline comment explaining each remaining entry. Bandit passes clean.

### M2 — Supply-chain: SQL drivers and the keyring backend are unpinned beyond a floor

**Where:** `pyproject.toml:22-31`. Runtime deps (`boto3`, `keyring`) and the
optional SQL extras (`pymysql`, `pg8000`) are floor-pinned (`>=`). `uv.lock`
exists and pins the dev tree, but consumers installing via `pip install
gui4aws[sql]` get whatever resolves at install time. `pymysql`/`pg8000` handle
**live DB credentials**; `keyring` backends touch the OS secret store. A
compromised release of any of these is a credential-theft path.

This is inherent to publishing a library (you can't ship a lockfile to pip
users), so it's *Medium*, not High. Mitigations worth having:
- Keep `pip-audit` (already in dev deps) wired into the release gate so known
  CVEs in the locked tree block a release.
- Consider pinning `gha-update` SHAs for CI actions (the README TODO list at
  `README.md:20` still has `make gha-upgrade` unchecked — unpinned GitHub
  Actions are a real supply-chain vector for the *release pipeline*, which can
  push to PyPI).
- The `[skip ci]` release commits (see `git log`) mean some releases bypass CI —
  make sure the *publish* job itself always runs audit, even when `[skip ci]` is
  used on the source commit.

### M3 — Driver TLS verification is enabled but not enforced/validated

**Where:** `gui4aws/sql_runner/connection.py:206,233`. Good news first: both
drivers request TLS (`ssl_context=True` for pg8000, `ssl={"ssl": True}` for
pymysql). That's the right default. The gap:
- `pymysql`'s `ssl={"ssl": True}` enables TLS but, depending on version, does
  **not** verify the server cert / hostname unless `ssl_verify_cert` /
  `ssl_verify_identity` (or a CA) are set. So the connection can be silently
  downgraded to "encrypted but unauthenticated," which is MITM-able on a hostile
  network.
- pg8000's `ssl_context=True` uses a default context that *does* verify — so the
  two engines behave inconsistently.

**Why it matters (within our model):** the user didn't ask for an unauthenticated
channel; they reasonably assume "it uses SSL" means "it's verified." A network
attacker isn't *attacking the app*, but they can harvest the DB password mid-flight.

**Recommendation:** For pymysql, build an explicit
`ssl.create_default_context()` and pass it (and/or set `ssl_verify_identity=True`).
If users legitimately need to talk to self-signed/dev endpoints, make
verification the default and require an explicit opt-out toggle — never the
reverse.

---

## Low / informational

### L1 — Generated-script files and CSV exports are written with default permissions

`script_editor_panel.py:162`, `sql_runner_dialog.py:100` write to a
user-chosen path with default umask. On a shared/multi-user box a
password-bearing script (see H1) or a query-result CSV is world-readable until
the user notices. Once H1 redacts secrets from scripts this is mostly moot;
flagging for completeness. (Not worth `chmod 600` gymnastics unless H1 isn't done.)

### L2 — keyring connection strings are stored as plaintext JSON values

`sql_runner/connection.py:124` stores the whole connection dict (incl. password)
as a JSON string in the OS keyring. This is **correct** — the OS keyring is the
right place for secrets and encrypts at rest. Noted only to confirm it was
reviewed and is *not* a finding. The keyring username is the cluster id, which is
not sensitive. `list_keyring_sources`/`load_*` swallow keyring exceptions
quietly (`except Exception`) — fine for robustness, just means a misconfigured
backend fails silently rather than warning the user.

### L3 — moto fake-credential env injection is process-global and not concurrency-safe

`moto_server.py:194` (`inject_credentials`) overwrites `AWS_ACCESS_KEY_ID` etc.
in `os.environ` for the **whole process** and blanks `AWS_SHARED_CREDENTIALS_FILE`.
`restore_credentials` puts them back. This is fine for the GUI's single-user,
start/stop lifecycle. The only risk is if real boto3 calls race against a
moto start/stop and accidentally pick up `"testing"` creds (calls fail safely)
or, in reverse, that a crash between inject and restore leaves the env mutated
for the session. No secret leaks; correctness/UX nit, not a security hole.
Worth a comment that this is intentionally process-wide.

### L4 — Subprocess targets resolve from PATH (`aws`, `npx`, `docker`, `python -m moto`)

`aws_cli_executor.py:61` (`shutil.which("aws")`), `cdk_dialog.py:656` (`npx`),
`robotocore_server.py` (`docker`), `moto_server.py:104` (`sys.executable`).
All use **argv lists, never `shell=True`**, so there's no shell-injection
surface even with attacker-influenced field values — good. PATH hijacking
(a malicious `aws` earlier in PATH) is a pre-existing local-compromise scenario
outside our threat model (attacker already controls the user's environment).
Noted as reviewed-and-acceptable. `sys.executable` for moto is the safest choice.

### L5 — `--endpoint-url` / local endpoint config is user-controlled but localhost-scoped in practice

`endpoint_config` / `config.local_endpoints` feed `--endpoint-url` and boto3
`endpoint_url`. A user can point the app at an arbitrary URL, but that's the
user configuring their own tool (and the moto/robotocore reset POSTs go only to
the locally-derived endpoint). No SSRF concern *from another actor* because
there's no other actor in the model. Reviewed, not a finding.

---

## Things that are good (reviewed, no action needed)

- **No `eval`/`exec`/`pickle`/`os.system`/`shell=True` anywhere** in `gui4aws/`.
  All subprocess use is argv-list form. (Grep-confirmed.)
- **AWS credentials are never read or written by the app itself** — it defers to
  boto3's profile/env resolution and the AWS CLI. The app doesn't store AWS keys
  on disk.
- **Config file** (`config.py`) holds only non-secret prefs (profile *name*,
  region, window size, endpoint URLs). No secrets persisted there. Its
  hand-rolled TOML writer doesn't escape values, but the inputs are constrained
  enums/ints/URLs — low risk, and it never holds secrets.
- **moto / robotocore HTTP servers bind to `127.0.0.1`** (`moto_server.py:29`)
  or are explicit user-launched Docker containers — not exposed to the network.
- **TLS is requested** for both SQL drivers (the gap is *verification* on
  pymysql — see M3, not "plaintext").
- **Logging** (`logging_config.py`) pushes botocore credential chatter to
  WARNING and does not log secret inputs. (The one `logger.info` in
  `save_to_keyring` logs the service/username, **not** the password — good.)

---

## Suggested priority order

1. **H1** — add `is_secret` field flag → mask in form, redact in history/diagnostics,
   placeholder in generated scripts. (Fixes H1, H2, and L1 in one stroke.). DONE.
2. **M1** — tighten the Bandit `skips` so the fix above can't silently regress. DONE.
3. **M3** — enforce pymysql cert verification. WONT DO
4. **M2** — confirm `pip-audit` runs in the *publish* job even on `[skip ci]`
   releases; pin GHA SHAs. Eh, more of a periodic chore.
