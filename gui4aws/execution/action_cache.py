"""Thread-safe cache for read-only action results."""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Any

from gui4aws.execution.endpoint_config import EndpointConfig
from gui4aws.execution.execution_mode import ExecutionMode
from gui4aws.models import ActionDefinition, RiskLevel

__all__ = ["ActionCache", "CacheKey"]


@dataclass(frozen=True)
class CacheKey:
    """Stable cache key for one read-only action invocation."""

    action_id: str
    service_id: str
    mode: str
    profile_name: str | None
    region_name: str
    endpoint_mode: str
    endpoint_url: str | None
    inputs: tuple[tuple[str, str], ...]


@dataclass
class CacheEntry:
    expires_at: float
    value: Any


class ActionCache:
    """Simple TTL cache keyed by action identity plus runtime context."""

    def __init__(self, ttl_seconds: float = 30 * 60, *, clock: Any | None = None) -> None:
        self.ttl_seconds = ttl_seconds
        self.clock = clock or time.monotonic
        self.lock = threading.RLock()
        self.entries: dict[CacheKey, CacheEntry] = {}
        self.stats: dict[str, int] = {
            "hits": 0,
            "misses": 0,
            "puts": 0,
            "service_invalidations": 0,
            "entry_invalidations": 0,
            "clears": 0,
            "expired": 0,
        }
        self.recent_events: deque[str] = deque(maxlen=50)

    def build_key(
        self,
        action: ActionDefinition,
        inputs: dict[str, str],
        *,
        mode: ExecutionMode,
        profile_name: str | None,
        region_name: str,
        endpoint_config: EndpointConfig,
    ) -> CacheKey:
        """Build the cache key for one action call."""
        return CacheKey(
            action_id=action.action_id,
            service_id=action.service_id,
            mode=mode.value,
            profile_name=profile_name,
            region_name=region_name,
            endpoint_mode=endpoint_config.mode.value,
            endpoint_url=endpoint_config.resolved_url(),
            inputs=tuple(sorted((name, str(value)) for name, value in inputs.items())),
        )

    def get(self, key: CacheKey) -> Any | None:
        """Return a cached value, evicting stale entries lazily."""
        now = self.clock()
        with self.lock:
            entry = self.entries.get(key)
            if entry is None:
                self.stats["misses"] += 1
                self.record_event(f"MISS {key.action_id} [{key.service_id}]")
                return None
            if entry.expires_at <= now:
                self.entries.pop(key, None)
                self.stats["expired"] += 1
                self.stats["misses"] += 1
                self.record_event(f"EXPIRED {key.action_id} [{key.service_id}]")
                return None
            self.stats["hits"] += 1
            self.record_event(f"HIT {key.action_id} [{key.service_id}]")
            return entry.value

    def put(self, key: CacheKey, value: Any) -> None:
        """Store a cached value."""
        with self.lock:
            self.entries[key] = CacheEntry(expires_at=self.clock() + self.ttl_seconds, value=value)
            self.stats["puts"] += 1
            self.record_event(f"PUT {key.action_id} [{key.service_id}]")

    def invalidate_service(self, service_id: str) -> None:
        """Drop all cached reads for one service."""
        with self.lock:
            stale = [key for key in self.entries if key.service_id == service_id]
            for key in stale:
                self.entries.pop(key, None)
            self.stats["service_invalidations"] += 1
            self.record_event(f"INVALIDATE service={service_id} removed={len(stale)}")

    def invalidate_entry(
        self,
        *,
        service_id: str,
        action_id: str,
        mode: str,
        inputs: dict[str, str],
    ) -> bool:
        """Drop one cached read matching the visible diagnostics entry."""
        normalized_inputs = tuple(sorted((name, str(value)) for name, value in inputs.items()))
        with self.lock:
            for key in list(self.entries):
                if (
                    key.service_id == service_id
                    and key.action_id == action_id
                    and key.mode == mode
                    and key.inputs == normalized_inputs
                ):
                    self.entries.pop(key, None)
                    self.stats["entry_invalidations"] += 1
                    self.record_event(f"INVALIDATE entry={action_id} [{service_id}]")
                    return True
        return False

    def clear(self) -> None:
        """Drop all cached entries."""
        with self.lock:
            removed = len(self.entries)
            self.entries.clear()
            self.stats["clears"] += 1
            self.record_event(f"CLEAR removed={removed}")

    def size(self) -> int:
        """Return the number of live cached entries."""
        self.purge_expired()
        with self.lock:
            return len(self.entries)

    def snapshot(self) -> dict[str, Any]:
        """Return cache state for diagnostics."""
        self.purge_expired()
        with self.lock:
            entries = [
                {
                    "action_id": key.action_id,
                    "service_id": key.service_id,
                    "mode": key.mode,
                    "inputs": dict(key.inputs),
                }
                for key, entry in sorted(
                    self.entries.items(),
                    key=lambda item: (item[0].service_id, item[0].action_id, item[0].inputs),
                )
            ]
            return {
                "ttl_seconds": self.ttl_seconds,
                "size": len(self.entries),
                "stats": dict(self.stats),
                "entries": entries,
                "recent_events": list(self.recent_events),
            }

    def should_cache(self, action: ActionDefinition, result: Any) -> bool:
        """Return True when the action/result pair is safe to cache."""
        return action.risk_level is RiskLevel.READ_ONLY and not hasattr(result, "exception_class")

    def purge_expired(self) -> None:
        """Evict all entries whose TTL has passed."""
        now = self.clock()
        with self.lock:
            stale = [key for key, entry in self.entries.items() if entry.expires_at <= now]
            for key in stale:
                self.entries.pop(key, None)
            if stale:
                self.stats["expired"] += len(stale)
                self.record_event(f"PURGE expired={len(stale)}")

    def record_event(self, message: str) -> None:
        """Append a timestamped message to the event log."""
        stamp = time.strftime("%H:%M:%S")
        self.recent_events.append(f"{stamp} {message}")
