# Demo-seeding safety: never on real AWS

## The danger

"Seed demo resources" creates Aurora clusters, VPCs, Backup vaults, Lambda
functions, and more. On a local emulator that is harmless and useful. On **real
AWS** it creates real, billable, possibly hard-to-clean-up infrastructure. The
previous design only put a confirmation dialog in front of the live-AWS case —
one mis-click away from disaster — and still allowed seeding against any custom
endpoint URL.

Requirement: make it **impossible** to create demo assets on real AWS.

## Threat model

Demo data could reach real AWS through:

1. The endpoint being set to `aws` (live).
2. A `custom` endpoint URL that points at real AWS (or a proxy to it).
3. A `custom` URL the user *believes* is a local moto/robotocore but isn't.
4. Programmatic misuse of `seed_demo_resources` with a real-AWS session.

A single confirmation dialog does not address any of these robustly.

## Defense in depth

Two independent guards, either of which is sufficient to block real AWS:

### Guard 1 — UI gate (`demo_seeding_allowed`)

The "Seed demo resources" menu item is **only present** when the active endpoint
is an emulator **that this app started and is managing**:

- endpoint mode is `moto` and `MotoServerManager.running` and the resolved URL
  equals the manager's `endpoint_url`; or
- endpoint mode is `robotocore` and `RobotocoreManager.running` and the resolved
  URL equals the manager's `endpoint_url`.

`aws` and `custom` never qualify — even a moto the user spun up independently and
pointed at via a custom URL. The Demo cascade uses Tk's `postcommand` to rebuild
itself every time it opens, so the item appears/disappears live as the Target
changes; there is no stale enabled state.

### Guard 2 — code-level positive verification (`verify_emulator`)

Independently of the UI, `seed_demo_resources` requires a `VerifiedEmulator`
proof token. The only way to obtain one is `verify_emulator(endpoint_url)`, which:

1. rejects an empty URL;
2. rejects any URL containing `amazonaws.com` (belt-and-suspenders);
3. **probes** the endpoint for an emulator-specific signature that real AWS does
   not serve:
   - Moto: `GET {url}/moto-api/` returns 2xx;
   - Robotocore/LocalStack: `GET {url}/_localstack/health` returns 2xx JSON with
     a `services` map;
4. raises `EmulatorVerificationError` if neither matches.

Because the seeding function's signature *requires* the token, there is no code
path — GUI or programmatic — that writes demo data to an endpoint that failed the
probe. A real-AWS endpoint cannot produce a token.

## Why both

- Guard 1 alone could be bypassed by a future caller of the seeding API.
- Guard 2 alone would let the menu offer seeding in states that then error out —
  worse UX. Together: the menu only offers it when it will work, and the code
  refuses anything that isn't provably an emulator.

## Test seam

The in-process `moto.mock_aws` patcher (used by unit tests) has no HTTP endpoint
to probe. Tests therefore call the internal `_seed_with_client_factory` with a
boto3 client factory directly. The **public** `seed_demo_resources` always
requires a verified token; the internal helper is underscore-prefixed and only
reachable from tests, so the guard on the public path is never bypassed in
shipping code.

## Out of scope

- Cleaning up / deleting demo resources (the package only ever writes).
- Verifying that an emulator's data won't later be pointed at real AWS — once
  resources exist in moto/robotocore they live only there.
