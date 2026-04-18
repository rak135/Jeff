"""Compression — converts an accepted candidate into a concise committed record shape.

Compression preserves summary, remembered points, why_it_matters, support
quality, stability, freshness sensitivity, and explicit links.  It must not
produce report-sized prose, stitched truth narratives, or hidden source dumps.
"""

from __future__ import annotations

from jeff.core.schemas import MemoryId, Scope

from .models import CommittedMemoryRecord, MemoryCandidate, MemorySupportRef
from .types import utc_now

_STABILITY_CANDIDATE_TO_RECORD = {
    "stable": "stable",
    "tentative": "tentative",
    "volatile": "tentative",  # volatile candidates that escape defer become tentative records
}


def compress_candidate(
    *,
    candidate: MemoryCandidate,
    memory_id: MemoryId,
    freshness_sensitivity: str = "low",
    created_from_run_id: str | None = None,
) -> CommittedMemoryRecord:
    """Produce a committed record from a validated, accepted candidate.

    The candidate must have already passed validation and deduplication.
    No further filtering occurs here; this step is purely structural.
    """
    timestamp = utc_now()
    record_stability = _STABILITY_CANDIDATE_TO_RECORD.get(candidate.stability, "tentative")

    return CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type=candidate.memory_type,
        scope=candidate.scope,
        summary=candidate.summary,
        remembered_points=candidate.remembered_points,
        why_it_matters=candidate.why_it_matters,
        support_quality=candidate.support_quality,
        stability=record_stability,
        record_status="active",
        conflict_posture="none",
        created_at=timestamp,
        updated_at=timestamp,
        support_refs=candidate.support_refs,
        freshness_sensitivity=freshness_sensitivity,
        created_from_run_id=created_from_run_id,
        schema_version="1.0",
    )
