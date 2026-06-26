# Mutually-exclusive backend selection

## The problem

The toolbar currently exposes several controls that *look* independent but
actually describe **one** underlying decision — "where do my AWS calls go?" —
and they can be put into nonsensical combinations:

| Control | Widget | Problem |
| --- | --- | --- |
| Endpoint mode | combobox: `aws / moto / robotocore / docker / custom` | `docker` is a dead enum value with no behavior ("(what?)"). The combobox lets you pick `robotocore` while Moto is running, etc. |
| Profile | combobox | Meaningful only on live AWS. When Moto/Robotocore/custom is active the credentials are ignored, yet the control stays enabled and editable. |
| Start/Stop Moto | button | Can be started while Robotocore is running, even though they are alternative emulators. |
| Start/Stop Robotocore | button | Same — can be started while Moto is running. |
| "Use Moto instead" | checkbox (Robotocore panel) | A *third* place that flips the endpoint, hidden on another tab. Overlaps confusingly with the Moto button + endpoint combobox. |

The result: three different widgets can each change the endpoint, they can
disagree, and the user can express states that don't mean anything ("Robotocore
running, endpoint=moto, profile=prod").

### Root cause

There is no single source of truth. `EndpointMode`, `MotoServerManager.running`,
and `RobotocoreManager.running` are three independent pieces of state that the
user can poke individually. The "Use Moto instead" checkbox adds a fourth.

## The model we want

The user is always in exactly **one target backend**. These are mutually
exclusive by definition:

1. **Live AWS** — real credentials; the Profile selector matters.
2. **Moto** — local in-process emulator; credentials irrelevant.
3. **Robotocore** — containerized emulator (LocalStack); credentials irrelevant.
4. **Custom endpoint** — a user-supplied URL; credentials usually irrelevant.

`EndpointMode` already enumerates these (minus the spurious `docker`). We make
**the endpoint mode the single source of truth** and let it *drive* everything
else, instead of being one of several competing controls.

## Design

### 1. Rename the control and remove the dead option

- The endpoint combobox becomes the **"Target"** selector with exactly four
  choices: `AWS`, `Moto`, `Robotocore`, `Custom`.
- **Remove `EndpointMode.DOCKER`** — it has no `resolved_url()` branch, no
  manager, and no UI behavior. It is dead code that only adds confusion.

### 2. Target drives server lifecycle (no separate toggle buttons)

Selecting a target *is* the start/stop gesture:

- **Choose Moto** → start the Moto server (if not already running), point the
  endpoint at it. Leaving Moto (choosing another target) stops it.
- **Choose Robotocore** → start the Robotocore container, point at it. Leaving
  stops it.
- **Choose AWS / Custom** → stop whichever emulator was running.

Because choosing a target can only ever run *one* emulator, Moto and Robotocore
can never be simultaneously active — the mutual exclusion is structural, not
enforced by ad-hoc checks.

The standalone **"Start Moto" / "Start Robotocore" toolbar buttons are
removed.** Their lifecycle is now implied by the Target selector. The per-server
**management** actions (Restart, Reset State, Open Dashboard, Pull Image) remain
on their diagnostic tabs, where they belong, but are only enabled when that
server is the active target.

### 3. Profile is disabled unless target == AWS

The Profile combobox is set to `state="disabled"` whenever the target is not
`AWS`, with its value shown as `(emulator — n/a)`. On returning to AWS it is
re-enabled and the previously chosen profile restored.

This makes the "profile doesn't mean anything" cases visually obvious instead of
silently ignored.

### 4. Custom URL entry only shown for Custom

The URL entry is only relevant for `Custom`. For Moto/Robotocore the URL is
managed by the server manager; for AWS there is no URL. The entry is therefore
**disabled (and cleared of user-editability) unless target == Custom**. When a
server is running we still *display* its URL there read-only so the user can see
and copy it.

### 5. Retire the "Use Moto instead" checkbox

With the Target selector owning the endpoint, the Robotocore panel's "Use Moto
instead" checkbox becomes a redundant fourth path. It is **removed**; the user
switches between Moto and Robotocore by changing the Target.

## Resulting state table

| Target | Moto server | Robotocore | Profile field | URL field |
| --- | --- | --- | --- | --- |
| AWS | stopped | stopped | **enabled** | hidden/disabled |
| Moto | **running** | stopped | disabled (n/a) | read-only (shows moto URL) |
| Robotocore | stopped | **running** | disabled (n/a) | read-only (shows rc URL) |
| Custom | stopped | stopped | disabled (n/a) | **editable** |

Every row is reachable; no other combination is expressible from the UI. That is
the mutual exclusion we wanted.

## Implementation notes

- `Toolbar` gains a single `on_target_changed(EndpointMode)` callback and owns
  the enable/disable logic for the Profile and URL widgets via a
  `apply_target_state()` method driven by `context.endpoint_config.mode` plus
  the running flags.
- `MainWindow.on_target_changed` orchestrates start/stop:
  - leaving an emulator → stop it;
  - entering Moto/Robotocore → start it (async, as today), and on the
    `*_started` result the endpoint + URL are set and `apply_target_state()` is
    re-run.
- The existing async `*_started` / `*_stopped` / `*_error` result handlers in
  `dispatch_result` already set the endpoint and flip button text; they are
  updated to call `toolbar.apply_target_state()` instead of toggling the
  now-removed buttons, and to re-enable the Target selector (which is disabled
  while a start/stop is in flight, to prevent a second click mid-transition).
- `seed_demo_resources` and `robotocore_use_moto_changed` lose their dependence
  on the removed checkbox; backend is derived purely from `endpoint_config.mode`.
- Persistence: `default_endpoint_mode` continues to round-trip; `docker` is no
  longer a valid value (loader coerces an unknown/legacy value back to `aws`).

## Out of scope

- No change to how calls are *executed* once the endpoint is chosen.
- No change to the network/proxy settings (separate feature).
- Auto-starting Docker for Robotocore is unchanged — if Docker is unavailable
  the async start fails and surfaces the existing error dialog, after which the
  Target reverts to AWS.
