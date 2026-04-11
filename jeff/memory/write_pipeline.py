"""Selective memory candidate creation and write discipline."""

from __future__ import annotations

from .models import (
    CommittedMemoryRecord,
    MemoryCandidate,
    MemorySupportRef,
    MemoryWriteDecision,
    make_memory_candidate,
)
from .store import InMemoryMemoryStore
from .types import normalized_identity, utc_now

_LOW_VALUE_WHY = {
    "for reference",
    "maybe useful later",
    "might matter later",
    "good to remember",
}


def create_memory_candidate(
    *,
    candidate_id: str,
    memory_type: str,
    scope,
    summary: str,
    remembered_points: tuple[str, ...],
    why_it_matters: str,
    support_refs: tuple[MemorySupportRef, ...],
    support_quality: str = "moderate",
    stability: str = "tentative",
) -> MemoryCandidate:
    return make_memory_candidate(
        candidate_id=candidate_id,
        memory_type=memory_type,
        scope=scope,
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=support_refs,
        support_quality=support_quality,
        stability=stability,
    )


def write_memory_candidate(
    *,
    candidate: MemoryCandidate,
    store: InMemoryMemoryStore,
) -> MemoryWriteDecision:
    if not isinstance(candidate, MemoryCandidate):
        raise TypeError("memory write pipeline requires a MemoryCandidate")
    if not isinstance(store, InMemoryMemoryStore):
        raise TypeError("memory write pipeline requires an InMemoryMemoryStore")

    duplicate_reason = _duplicate_reason(candidate=candidate, store=store)
    if duplicate_reason is not None:
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(duplicate_reason,),
        )

    low_value_reason = _low_value_reason(candidate)
    if low_value_reason is not None:
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(low_value_reason,),
        )

    if candidate.support_quality == "weak" or candidate.stability == "volatile":
        return MemoryWriteDecision(
            write_outcome="defer",
            candidate_id=candidate.candidate_id,
            reasons=("support is not yet stable or strong enough for committed memory",),
        )

    timestamp = utc_now()
    memory_id = store.allocate_memory_id()
    record = CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type=candidate.memory_type,
        scope=candidate.scope,
        summary=candidate.summary,
        remembered_points=candidate.remembered_points,
        why_it_matters=candidate.why_it_matters,
        support_quality=candidate.support_quality,
        stability=candidate.stability,
        created_at=timestamp,
        updated_at=timestamp,
        support_refs=candidate.support_refs,
    )
    store._store_committed_record(record)

    return MemoryWriteDecision(
        write_outcome="write",
        candidate_id=candidate.candidate_id,
        memory_id=record.memory_id,
        committed_record=record,
    )


def _low_value_reason(candidate: MemoryCandidate) -> str | None:
    normalized_why = normalized_identity(candidate.why_it_matters)
    if normalized_why in _LOW_VALUE_WHY:
        return "candidate lacks strong durable continuity value"
    if normalized_identity(candidate.summary) == normalized_why:
        return "candidate does not explain why the memory matters beyond restating itself"
    return None


def _duplicate_reason(
    *,
    candidate: MemoryCandidate,
    store: InMemoryMemoryStore,
) -> str | None:
    for record in store.list_project_records(str(candidate.scope.project_id)):
        if record.memory_type != candidate.memory_type:
            continue
        if record.scope != candidate.scope:
            continue
        if normalized_identity(record.summary) != normalized_identity(candidate.summary):
            continue
        if tuple(normalized_identity(point) for point in record.remembered_points) != tuple(
            normalized_identity(point) for point in candidate.remembered_points
        ):
            continue
        return "duplicate committed memory already exists for this bounded memory"
    return None
