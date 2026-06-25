# Threading current state

## Summary

The GUI now has one clear rule for AWS and Moto API traffic: **read and write API work is serialized through `SerialWorker`** in `gui4aws/gui/main_window.py`, and cached read hits bypass that worker entirely because they return from `AppContext` without making a network call.

That is a meaningful improvement over the prior "many daemon threads pile up against Moto" behavior, especially because Moto is effectively single-threaded and real AWS calls are often slow enough to make concurrent fan-out feel worse instead of better.

## Current thread model

1. **Tk main thread**

   - Owns widgets, `after(...)`, result dispatch, dialogs, status updates, and table rendering.
   - `poll_queue()` drains `results_queue` every 50ms.

1. **`SerialWorker` background thread**

   - Runs queued API work FIFO.
   - Used for:
     - default sidebar read actions
     - eager filter-choice reads
     - sub-panel reads
     - action execution
     - cache prewarming after successful writes
     - cache seeding after the demo seed flow
   - This is the main protection against request pileups.

1. **Ad hoc daemon threads**

   - `seed_demo_resources()` starts one worker thread for the seed operation itself.
   - `on_moto_toggle(start=True)` starts one worker thread to boot Moto.
   - These threads do not touch Tk directly; they post results back through `results_queue`.

## What looks good

- **Tk access is still confined to the UI thread.** Background work communicates back by queue message, which is the right pattern here.
- **Network work is serialized.** That matches Moto's behavior much better than a pool.
- **Read cache removes a large class of unnecessary calls.** Reopening the same nav, re-reading eager dropdown sources, and revisiting sub-panels can now skip both Moto and AWS for 30 minutes.
- **Post-write cache warming is also serialized.** We avoid reintroducing parallel request storms while still repopulating invalidated reads.

## Current wonkiness / remaining risks

### 1. `SerialWorker` has no lifecycle hook tied to window shutdown

`SerialWorker.close()` exists, but this file does not currently bind window close/destroy to it. In practice that is usually harmless because the worker thread is daemonized, but it does mean shutdown is not especially tidy.

### 2. Cache warming shares the same serial queue as foreground actions

That was intentional so cache warming cannot recreate Moto pileups, but it does mean a large background warm-up can sit ahead of later user-triggered actions in the same queue. The new cache should reduce how often that hurts, but this is still the main tradeoff in the current design.

### 3. Demo seeding still uses its own thread before queue-based cache warming starts

The seed operation itself is serial inside `demo_resources.py`, which is good, but it is still separate from `SerialWorker`. That is acceptable because it is a distinct long-running menu command, not interactive nav traffic.

### 4. Result polling is timer-driven forever

`poll_queue()` always reschedules itself with `after(50, ...)`. That is fine during normal runtime, but there is no explicit cancellation path during shutdown.

### 5. Broad exception handling remains in a few safety rails

There are still intentionally broad guards around queue dispatch and worker execution so one bad callback does not freeze the UI. They are pragmatic, but they can hide exactly where a race or bad result originated unless logging is watched closely.

## Bottom line

The threading model is now **mostly sane for a Tk app talking to slow backends**:

- one UI thread
- one serialized API worker
- queue handoff for cross-thread communication
- read cache to avoid reusing the worker when data is already fresh

The biggest remaining architectural concern is not correctness so much as **queue fairness**: background cache warming can still delay later foreground requests because both share the same serial worker.
