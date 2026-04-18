"""Memory observability — counters and trace-safe events.

Telemetry is support only.  It must not become hidden semantics.
Events are emitted by the write and retrieval pipelines and can be
consumed by external observability backends without affecting memory law.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class MemoryCounters:
    """In-process memory metric counters.  Thread-safe via lock."""

    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    candidate_created: int = 0
    candidate_rejected: int = 0
    candidate_deferred: int = 0
    candidate_committed: int = 0
    duplicate_rejected: int = 0
    merge_count: int = 0
    supersession_count: int = 0

    retrieval_count: int = 0
    explicit_hit_count: int = 0
    lexical_hit_count: int = 0
    semantic_hit_count: int = 0
    contradiction_labeled_count: int = 0

    def increment(self, counter_name: str, by: int = 1) -> None:
        with self._lock:
            current = getattr(self, counter_name, 0)
            object.__setattr__(self, counter_name, current + by)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                k: v
                for k, v in self.__dict__.items()
                if not k.startswith("_") and isinstance(v, int)
            }


# Module-level default counters instance (can be replaced for testing)
_default_counters = MemoryCounters()


def get_counters() -> MemoryCounters:
    return _default_counters


def record_write_outcome(write_outcome: str, *, counters: MemoryCounters | None = None) -> None:
    c = counters or _default_counters
    c.candidate_created += 1
    if write_outcome == "write":
        c.candidate_committed += 1
    elif write_outcome == "reject":
        c.candidate_rejected += 1
    elif write_outcome == "defer":
        c.candidate_deferred += 1
    elif write_outcome == "merge_into_existing":
        c.merge_count += 1
        c.candidate_committed += 1
    elif write_outcome == "supersede_existing":
        c.supersession_count += 1
        c.candidate_committed += 1


def record_retrieval(
    *,
    returned_count: int,
    contradiction_count: int = 0,
    counters: MemoryCounters | None = None,
) -> None:
    c = counters or _default_counters
    c.retrieval_count += 1
    c.contradiction_labeled_count += contradiction_count
