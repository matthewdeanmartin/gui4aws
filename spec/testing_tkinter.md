# Integration testing a Tkinter app headlessly

This is how we drive `gui4aws`'s Tkinter GUI from a test script — no human
needed, no manual clicking, no screenshots. The exact technique that found
the "all panels stop loading" freeze under rapid arrow-key navigation.

The trick is that Tkinter is event-driven and the test script doubles as the
event loop driver. You instantiate the real `Tk` root, build the real window
classes, then *manually* pump the event loop in short bursts while
synthesising input events between bursts. The window doesn't need to be
mapped to the screen — `root.withdraw()` works — but for keyboard event
synthesis it helps if it is, because Tk needs an active window to deliver
key events.

## The four primitives

### 1. Build the app like production does

```python
import os, tkinter as tk
from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.gui.main_window import MainWindow

# Use moto so no real AWS is called. AppContext defaults work; just point it
# at moto via endpoint_config.
ctx = AppContext()
ctx.set_endpoint(EndpointMode.MOTO, "http://127.0.0.1:5000")  # or whatever
root = tk.Tk()                # real Tk root
# root.withdraw()             # uncomment to hide the window
w = MainWindow(ctx, root=root, profiles=[], regions=["us-east-1"])
```

Don't call `w.run()` (it would enter `mainloop()` and block). You drive the
loop yourself.

### 2. The `pump()` helper — your event loop on a leash

```python
import time

def pump(seconds: float) -> None:
    """Run the Tk event loop for `seconds`, yielding to background threads.

    This is the headless equivalent of "user does nothing for a moment".
    Without this between actions, queued <<TreeviewSelect>> events, after()
    callbacks, and poll_queue cycles never fire.
    """
    end = time.time() + seconds
    while time.time() < end:
        root.update_idletasks()  # process pending Tk geometry / variable updates
        root.update()            # process pending events (keys, mouse, after())
        time.sleep(0.01)         # let worker threads breathe; 10ms is fine
```

`update_idletasks()` then `update()` is the right order: idle tasks first
(geometry, variable traces) so anything they queue can fire in the same
pump.

### 3. Spin up moto in-process so the app has something to talk to

The app speaks boto3 against an endpoint URL. Use the project's
`MotoServerManager`, which forks a real moto subprocess and gives you the
URL:

```python
os.environ["AWS_ACCESS_KEY_ID"] = "test"      # boto3 refuses without creds
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from gui4aws.moto_server import MotoServerManager
mgr = MotoServerManager()
mgr.start(timeout=15.0)   # blocks until /moto-api responds

# Seed with whatever the test needs, BEFORE building the GUI:
import boto3
sm = boto3.client("secretsmanager", endpoint_url=mgr.endpoint_url, region_name="us-east-1")
sm.create_secret(Name="hello", SecretString="world")

ctx.set_endpoint(EndpointMode.MOTO, mgr.endpoint_url)

# ... drive the GUI ...

mgr.stop()
```

Seed BEFORE building `MainWindow`, otherwise the first nav-select will
trigger a default-action that races the seed.

### 4. Synthesise input

For most things, just call the underlying widget API directly — no need to
fake events:

```python
# Pick a sidebar entry by service+item id (more stable than the Tk node id):
secrets_node = None
for node_id, sel in w.sidebar.node_to_selection.items():
    if sel.service_id == "secrets" and sel.item_id == "secrets":
        secrets_node = node_id
        break

w.sidebar.tree.selection_set(secrets_node)
w.sidebar.tree.focus(secrets_node)
pump(0.3)   # let <<TreeviewSelect>> fire and the worker queue kick off
```

`selection_set` triggers `<<TreeviewSelect>>` which calls
`on_sidebar_select` exactly as a real click does. You almost never need to
synthesise key events. But when you DO need to test key bindings
specifically, use `event_generate`:

```python
w.sidebar.tree.focus_set()              # the widget must own focus
w.sidebar.tree.event_generate("<Down>")
pump(0.2)
```

The widget must be inside a *mapped* window (no `withdraw`) for keyboard
events to be delivered, in our experience.

### 5. Pick at internal state with no shame

These are tests; reach in and read whatever you need:

```python
# How many rows are currently shown?
len(w.main_panel._current_rows)

# Is the loading overlay visible?
bool(w._loading_overlay.winfo_ismapped())

# What's queued waiting for the worker thread?
w._action_queue._queue.qsize()

# What's the current nav generation?
w._nav_generation
```

A real production codebase might gate these behind a test-only protocol;
for a small Tk app, just reach in. The tests are the only callers anyway.

## Two important debugging tricks

### Stack-trace a hung thread

When the UI appears frozen, dump the offending thread's stack to see where
it's actually blocked. This is what found the moto-server wedge:

```python
import sys, threading, traceback
for t in threading.enumerate():
    if t.name == "action-worker":
        frame = sys._current_frames().get(t.ident)
        if frame:
            traceback.print_stack(frame, file=sys.stdout)
```

Python's `sys._current_frames()` gives a snapshot of every thread's call
stack from the outside. Don't reach for `pdb` here — the thread is *busy*
(blocked in a syscall), and `pdb` only attaches to your interactive
session. `_current_frames` works on truly stuck threads.

### Monkey-patch the internals to instrument timing

When you suspect a slow code path, swap out the real implementation with a
traced one BEFORE building the window:

```python
from gui4aws.gui.main_window import MainWindow, SerialWorker

# Trace per-job latency through the worker queue.
def traced_loop(self):
    while True:
        fn, is_current = self._queue.get()
        if self._closed: return
        if is_current is not None and not is_current():
            continue
        t0 = time.monotonic()
        try:
            fn()
        except Exception:
            pass
        dt = (time.monotonic() - t0) * 1000
        if dt > 500:
            print(f"!! slow job: {dt:.0f}ms  queue_left={self._queue.qsize()}")
SerialWorker._loop = traced_loop      # patch CLASS, before construction

w = MainWindow(...)
```

Same pattern works for `MainWindow.dispatch_result`, `LoadingOverlay.show`,
etc. Capture the original first if you want to delegate:

```python
real_show = LoadingOverlay.show
def traced_show(self):
    print(f">>> SHOW (gen={_w._nav_generation})")
    real_show(self)
LoadingOverlay.show = traced_show
```

## A complete stress harness

This was the test that exposed the freeze. It builds the GUI, walks every
sidebar node into a flat list, then rapidly switches between random nodes
with very little pump time between (~10ms — faster than any human could
arrow-key, but a useful upper bound). After the stress, it waits for things
to settle and asserts that the UI recovers.

```python
import os, time, tkinter as tk, threading, random
os.environ["AWS_ACCESS_KEY_ID"] = "test"
os.environ["AWS_SECRET_ACCESS_KEY"] = "test"
os.environ["AWS_DEFAULT_REGION"] = "us-east-1"

from gui4aws.moto_server import MotoServerManager
mgr = MotoServerManager(); mgr.start(timeout=15.0)

import boto3
sm = boto3.client("secretsmanager", endpoint_url=mgr.endpoint_url, region_name="us-east-1")
sm.create_secret(Name="hello", SecretString="world")
rds = boto3.client("rds", endpoint_url=mgr.endpoint_url, region_name="us-east-1")
rds.create_db_cluster(
    DBClusterIdentifier="aur1", Engine="aurora-mysql",
    MasterUsername="admin", MasterUserPassword="x123456789",
)
ecs = boto3.client("ecs", endpoint_url=mgr.endpoint_url, region_name="us-east-1")
ecs.create_cluster(clusterName="alpha")

from gui4aws.app import AppContext
from gui4aws.execution.endpoint_config import EndpointMode
from gui4aws.gui.main_window import MainWindow

ctx = AppContext(); ctx.set_endpoint(EndpointMode.MOTO, mgr.endpoint_url)
root = tk.Tk()
w = MainWindow(ctx, root=root, profiles=[], regions=["us-east-1"])

def pump(s):
    end = time.time() + s
    while time.time() < end:
        root.update_idletasks(); root.update(); time.sleep(0.01)

# Flatten every visible sidebar node.
nodes = []
def walk(parent=""):
    for n in w.sidebar.tree.get_children(parent):
        nodes.append(n)
        walk(n)
walk()

random.seed(42)  # deterministic stress
for _ in range(50):
    n = random.choice(nodes)
    w.sidebar.tree.selection_set(n)
    w.sidebar.tree.focus(n)
    pump(0.05)   # tighter than this == DOSing your test backend

pump(5.0)        # let the SerialWorker drain
assert w._action_queue._queue.qsize() == 0, "worker queue stuck"
assert threading.active_count() <= 3, f"thread leak: {threading.active_count()}"

# Sanity: a normal selection still loads.
for node_id, sel in w.sidebar.node_to_selection.items():
    if sel.service_id == "secrets" and sel.item_id == "secrets":
        w.sidebar.tree.selection_set(node_id)
        w.sidebar.tree.focus(node_id)
        break
pump(3.0)
assert not w._loading_overlay.winfo_ismapped(), "overlay stuck after stress"
assert [r.name for r in w.main_panel._current_rows] == ["hello"]

root.destroy()
mgr.stop()
```

## Pitfalls

- **Don't call `root.mainloop()`** in tests. It blocks. Use `pump()`.
- **Don't trust `update_idletasks()` alone.** It only fires idle tasks, not
  `after()` callbacks or key events. You need `update()` too.
- **Seed AWS resources before constructing `MainWindow`.** Otherwise the
  first nav-select races your seeding.
- **Moto's dev server is single-threaded.** A stress test that fires
  requests faster than moto serves them will wedge moto itself, not the
  app. If `threading.active_count()` stays low but the queue never drains,
  that's a moto problem, not a gui4aws bug. Confirm by hitting moto
  directly with a fresh boto3 client.
- **Patch classes, not instances, before construction.** `SerialWorker._loop
  = traced_loop` works because the construction reads the class attribute.
  Patching `w._action_queue._loop` after construction does nothing — the
  thread is already running with the unpatched method.
- **Daemon threads don't show errors.** If a worker raises and you didn't
  log inside the worker, you'll just see "nothing happened." Always wrap
  worker bodies in `try/except Exception: logger.exception(...)`.
- **`event_generate` needs a mapped, focused widget.** If your test passes
  with `selection_set` but not `event_generate`, that's why.
