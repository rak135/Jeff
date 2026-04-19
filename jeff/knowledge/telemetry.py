"""Small counters for compiled knowledge activity."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class KnowledgeCounters:
    artifacts_saved: int = 0
    retrievals: int = 0
    duplicate_topic_note_rejections: int = 0
    supersessions: int = 0
    stale_reads: int = 0


_COUNTERS = KnowledgeCounters()


def get_counters() -> KnowledgeCounters:
    return _COUNTERS