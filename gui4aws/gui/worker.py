"""SerialWorker: single background thread that runs queued jobs FIFO."""

# pylint: disable=broad-exception-caught

from __future__ import annotations

import logging
import queue
import threading
import time
from collections import deque
from typing import Any

__all__ = ["SerialWorker"]

logger = logging.getLogger(__name__)


class SerialWorker:
    """A single background thread that runs jobs FIFO, skipping stale ones.

    ``submit(fn, is_current)`` queues ``fn``. When the worker dequeues a job,
    it first calls ``is_current()`` — if False, the job is dropped without
    being run. This lets rapid nav switches enqueue many jobs while ensuring
    only the ones still relevant when the worker gets to them actually hit
    moto.

    Why serial and not a pool: moto's dev server is single-threaded, so
    parallelism doesn't help and 100+ in-flight HTTP requests pile up faster
    than moto can serve them, freezing the UI.
    """

    def __init__(self) -> None:
        """Initialize the serial worker and start its background thread."""
        self.queue: queue.Queue[Any] = queue.Queue()
        self.closed = False
        self.lock = threading.RLock()
        self.current_description: str | None = None
        self.submitted_jobs = 0
        self.started_jobs = 0
        self.completed_jobs = 0
        self.dropped_jobs = 0
        self.failed_jobs = 0
        self.recent_events: deque[str] = deque(maxlen=100)
        self.thread = threading.Thread(target=self.loop, name="action-worker", daemon=True)
        self.thread.start()

    def submit(self, fn: Any, is_current: Any, description: str = "job") -> None:
        """Queue ``fn`` for serial execution.

        ``is_current`` is a 0-arg callable returning bool, checked just before
        dispatch. If it returns False, the job is dropped. This prevents stale
        background tasks from updating the UI after navigation has changed.
        """
        if self.closed:
            return
        with self.lock:
            self.submitted_jobs += 1
            self.record_event(f"queued {description}")
        self.queue.put((fn, is_current, description))

    def close(self) -> None:
        """Shut down the worker and its background thread."""
        self.closed = True
        self.queue.put((None, None, "shutdown"))

    def clear_pending(self) -> int:
        """Drop queued jobs that have not started yet.

        Returns the number of jobs removed from the queue.
        """
        removed = 0
        drained: list[tuple[Any, Any, str]] = []
        while True:
            try:
                job = self.queue.get_nowait()
            except queue.Empty:
                break
            if job[2] == "shutdown":
                drained.append(job)
                continue
            removed += 1
        for job in drained:
            self.queue.put(job)
        if removed:
            with self.lock:
                self.dropped_jobs += removed
                self.record_event(f"cleared pending count={removed}")
        return removed

    def loop(self) -> None:
        """Main worker loop that pulls jobs from the queue and runs them."""
        while True:
            fn, is_current, description = self.queue.get()
            if self.closed:
                return
            if is_current is not None:
                try:
                    if not is_current():
                        with self.lock:
                            self.dropped_jobs += 1
                            self.record_event(f"dropped stale {description}")
                        continue
                except Exception:
                    logger.exception("worker is_current check raised — dropping job")
                    with self.lock:
                        self.dropped_jobs += 1
                        self.record_event(f"dropped error-check {description}")
                    continue
            with self.lock:
                self.started_jobs += 1
                self.current_description = description
                self.record_event(f"started {description}")
            try:
                fn()
            except Exception:
                logger.exception("worker job raised")
                with self.lock:
                    self.failed_jobs += 1
                    self.record_event(f"failed {description}")
            else:
                with self.lock:
                    self.completed_jobs += 1
                    self.record_event(f"completed {description}")
            finally:
                with self.lock:
                    self.current_description = None

    def snapshot(self) -> dict[str, Any]:
        """Return a snapshot of the worker's current state for diagnostics."""
        with self.lock:
            return {
                "pending_jobs": self.queue.qsize(),
                "current_job": self.current_description,
                "submitted_jobs": self.submitted_jobs,
                "started_jobs": self.started_jobs,
                "completed_jobs": self.completed_jobs,
                "dropped_jobs": self.dropped_jobs,
                "failed_jobs": self.failed_jobs,
                "recent_events": list(self.recent_events),
            }

    def record_event(self, message: str) -> None:
        """Record a timestamped event for diagnostic history."""
        stamp = time.strftime("%H:%M:%S")
        self.recent_events.append(f"{stamp} {message}")
