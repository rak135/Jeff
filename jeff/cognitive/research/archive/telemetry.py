"""In-process counters for research archive save and retrieval activity."""

from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock


@dataclass
class ArchiveCounters:
    _lock: Lock = field(default_factory=Lock, repr=False, compare=False)

    artifact_saved_count: int = 0
    retrieval_count: int = 0
    history_retrieval_count: int = 0
    rejected_cross_project_reads: int = 0

    def increment(self, counter_name: str, by: int = 1) -> None:
        with self._lock:
            current = getattr(self, counter_name, 0)
            object.__setattr__(self, counter_name, current + by)

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {
                key: value
                for key, value in self.__dict__.items()
                if not key.startswith("_") and isinstance(value, int)
            }


_default_counters = ArchiveCounters()


def get_counters() -> ArchiveCounters:
    return _default_counters


def record_save(*, counters: ArchiveCounters | None = None) -> None:
    (counters or _default_counters).increment("artifact_saved_count")


def record_retrieval(*, historical: bool, counters: ArchiveCounters | None = None) -> None:
    active = counters or _default_counters
    active.increment("retrieval_count")
    if historical:
        active.increment("history_retrieval_count")


def record_cross_project_rejection(*, counters: ArchiveCounters | None = None) -> None:
    (counters or _default_counters).increment("rejected_cross_project_reads")