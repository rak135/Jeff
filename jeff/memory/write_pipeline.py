"""Selective memory write pipeline — orchestrates the v1 write stages.

Pipeline stages per MEMORY_V1.md §13:
1. candidate creation (candidate_builder)
2. candidate validation (validator)
3. deduplication and incremental-value check (dedupe)
4. type assignment and review-required check (type_assigner)
5. scope validation (scope_assigner)
6. compression into committed form (compressor)
7. accept / reject / defer decision
8. commit and storage (store)
9. indexing (indexer)
10. linking (linker)

Dry-run mode (used by evaluate_candidate): all decision logic runs but no state
is mutated.  A preview sentinel memory_id is used so the decision object is
structurally valid; no record is durably stored.

Supersede and merge paths execute the full write pipeline then additionally
update the target record's status and create the relevant cross-links.
"""

from __future__ import annotations

import uuid

from jeff.core.schemas import Scope, coerce_memory_id

from .candidate_builder import build_candidate
from .compressor import compress_candidate
from .dedupe import check_dedupe
from .ids import coerce_write_event_id
from .indexer import index_record
from .linker import build_merge_link, build_support_links, build_supersession_link
from .models import (
    CommittedMemoryRecord,
    MemoryCandidate,
    MemorySupportRef,
    MemoryWriteDecision,
)
from .schemas import MemoryWriteEvent, MemoryWriteResult
from .scope_assigner import assert_candidate_scope
from .telemetry import record_write_outcome
from .type_assigner import requires_review_by_type
from .types import normalized_identity, utc_now
from .validator import validate_candidate

# Low-value why_it_matters phrases — candidates with these are rejected outright
_LOW_VALUE_WHY = {
    "for reference",
    "maybe useful later",
    "might matter later",
    "good to remember",
}

# Sentinel memory_id used in dry-run mode; never persisted
_DRY_RUN_MEMORY_ID = "memory-eval-preview"


def create_memory_candidate(
    *,
    candidate_id: str,
    memory_type: str,
    scope: Scope,
    summary: str,
    remembered_points: tuple[str, ...],
    why_it_matters: str,
    support_refs: tuple[MemorySupportRef, ...],
    support_quality: str = "moderate",
    stability: str = "tentative",
) -> MemoryCandidate:
    """Backward-compatible alias for build_candidate."""
    return build_candidate(
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
    store,
    embedder=None,
) -> MemoryWriteDecision:
    """Run the full write pipeline and return the write decision.

    Accepts any store satisfying MemoryStoreProtocol.
    """
    result = _run_pipeline(candidate=candidate, store=store, embedder=embedder)
    return result.write_decision


def process_candidate(
    *,
    candidate: MemoryCandidate,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Run the full write pipeline and return the combined result including links."""
    return _run_pipeline(candidate=candidate, store=store, embedder=embedder)


def supersede_candidate(
    *,
    candidate: MemoryCandidate,
    supersedes_memory_id: str,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Commit a new record and supersede an existing one.

    The target must exist in the same project.  After committing the new record,
    the superseded record's status is set to 'superseded' and a cross-link is
    created.  This is the approved execution path for deferred dedupe_ambiguity
    candidates after operator review.
    """
    if not isinstance(candidate, MemoryCandidate):
        raise TypeError("supersede_candidate requires a MemoryCandidate")

    # Validate basic candidate properties
    validation_decision = validate_candidate(candidate)
    if validation_decision is not None:
        record_write_outcome(validation_decision.write_outcome)
        return MemoryWriteResult(write_decision=validation_decision)

    try:
        assert_candidate_scope(candidate)
    except ValueError as exc:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(str(exc),),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Validate supersession target
    target_id = coerce_memory_id(supersedes_memory_id)
    old_record = store.get_committed(str(target_id))
    if old_record is None:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(f"supersession target '{supersedes_memory_id}' not found",),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    if str(old_record.scope.project_id) != str(candidate.scope.project_id):
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=("cross-project supersession is forbidden",),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Commit new record
    new_memory_id = store.allocate_memory_id()
    record = compress_candidate(
        candidate=candidate,
        memory_id=new_memory_id,
        created_from_run_id=str(candidate.scope.run_id) if candidate.scope.run_id else None,
    )
    # Attach supersedes reference before storing
    record = CommittedMemoryRecord(
        memory_id=record.memory_id,
        memory_type=record.memory_type,
        scope=record.scope,
        summary=record.summary,
        remembered_points=record.remembered_points,
        why_it_matters=record.why_it_matters,
        support_quality=record.support_quality,
        stability=record.stability,
        record_status=record.record_status,
        conflict_posture=record.conflict_posture,
        created_at=record.created_at,
        updated_at=record.updated_at,
        support_refs=record.support_refs,
        freshness_sensitivity=record.freshness_sensitivity,
        created_from_run_id=record.created_from_run_id,
        schema_version=record.schema_version,
        supersedes_memory_id=str(target_id),
    )
    store._store_committed_record(record)

    # Mark old record as superseded
    store._mark_superseded(superseded_memory_id=target_id, new_memory_id=new_memory_id)

    # Build and persist links
    support_links = build_support_links(record=record)
    supersession_link = build_supersession_link(
        new_memory_id=new_memory_id,
        superseded_memory_id=target_id,
    )
    all_links = support_links + (supersession_link,)
    for link in all_links:
        store.store_link(link)

    # Index
    index_record(record, store=store, embedder=embedder)

    # Emit write event
    _emit_write_event(
        store=store,
        candidate=candidate,
        outcome="supersede_existing",
        memory_id=str(new_memory_id),
    )
    record_write_outcome("supersede_existing")

    decision = MemoryWriteDecision(
        write_outcome="supersede_existing",
        candidate_id=candidate.candidate_id,
        memory_id=record.memory_id,
        committed_record=record,
        superseded_memory_id=target_id,
    )
    return MemoryWriteResult(write_decision=decision, links_created=all_links)


def merge_into_candidate(
    *,
    candidate: MemoryCandidate,
    merge_target_id: str,
    store,
    embedder=None,
) -> MemoryWriteResult:
    """Merge a candidate into an existing record.

    The candidate's points and support_refs are folded into the target record
    (bounded to 5 points, deduped by content).  The target record retains its
    memory_id.  A merge link records the lineage.
    """
    if not isinstance(candidate, MemoryCandidate):
        raise TypeError("merge_into_candidate requires a MemoryCandidate")

    validation_decision = validate_candidate(candidate)
    if validation_decision is not None:
        record_write_outcome(validation_decision.write_outcome)
        return MemoryWriteResult(write_decision=validation_decision)

    try:
        assert_candidate_scope(candidate)
    except ValueError as exc:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(str(exc),),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Validate merge target
    target_id = coerce_memory_id(merge_target_id)
    old_record = store.get_committed(str(target_id))
    if old_record is None:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(f"merge target '{merge_target_id}' not found",),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    if str(old_record.scope.project_id) != str(candidate.scope.project_id):
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=("cross-project merge is forbidden",),
        )
        record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Merge points (dedupe, cap at 5)
    existing_norms = {normalized_identity(p) for p in old_record.remembered_points}
    new_points = [
        p for p in candidate.remembered_points
        if normalized_identity(p) not in existing_norms
    ]
    merged_points = tuple(list(old_record.remembered_points) + new_points)[:5]

    # Merge support_refs (dedupe by ref_id)
    existing_ref_ids = {r.ref_id for r in old_record.support_refs}
    new_refs = [r for r in candidate.support_refs if r.ref_id not in existing_ref_ids]
    merged_refs = tuple(list(old_record.support_refs) + new_refs)

    # Take stronger support quality
    quality_rank = {"weak": 0, "moderate": 1, "strong": 2}
    merged_quality = max(
        [old_record.support_quality, candidate.support_quality],
        key=lambda q: quality_rank.get(q, 0),
    )

    now = utc_now()
    updated = CommittedMemoryRecord(
        memory_id=old_record.memory_id,
        memory_type=old_record.memory_type,
        scope=old_record.scope,
        summary=old_record.summary,
        remembered_points=merged_points,
        why_it_matters=old_record.why_it_matters,
        support_quality=merged_quality,
        stability=old_record.stability,
        record_status=old_record.record_status,
        conflict_posture=old_record.conflict_posture,
        created_at=old_record.created_at,
        updated_at=now,
        support_refs=merged_refs,
        freshness_sensitivity=old_record.freshness_sensitivity,
        created_from_run_id=old_record.created_from_run_id,
        schema_version=old_record.schema_version,
        supersedes_memory_id=old_record.supersedes_memory_id,
        superseded_by_memory_id=old_record.superseded_by_memory_id,
        merged_into_memory_id=old_record.merged_into_memory_id,
    )
    store._store_committed_record(updated)

    # Build and persist merge link
    merge_link = build_merge_link(
        target_memory_id=target_id,
        merged_into_memory_id=target_id,
    )
    store.store_link(merge_link)

    # Re-index the updated record
    index_record(updated, store=store, embedder=embedder)

    # Emit write event
    _emit_write_event(
        store=store,
        candidate=candidate,
        outcome="merge_into_existing",
        memory_id=str(target_id),
    )
    record_write_outcome("merge_into_existing")

    decision = MemoryWriteDecision(
        write_outcome="merge_into_existing",
        candidate_id=candidate.candidate_id,
        memory_id=updated.memory_id,
        committed_record=updated,
    )
    return MemoryWriteResult(write_decision=decision, links_created=(merge_link,))


def _run_pipeline(
    *,
    candidate: MemoryCandidate,
    store,
    embedder=None,
    dry_run: bool = False,
) -> MemoryWriteResult:
    """Core write pipeline.

    When dry_run=True, all decision logic runs but no state is mutated.
    The returned decision uses a sentinel memory_id and is not durably stored.
    """
    if not isinstance(candidate, MemoryCandidate):
        raise TypeError("memory write pipeline requires a MemoryCandidate")

    # Stage 2: validation
    validation_decision = validate_candidate(candidate)
    if validation_decision is not None:
        if not dry_run:
            record_write_outcome(validation_decision.write_outcome)
        return MemoryWriteResult(write_decision=validation_decision)

    # Stage 3: scope validation
    try:
        assert_candidate_scope(candidate)
    except ValueError as exc:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(str(exc),),
        )
        if not dry_run:
            record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Stage 4: duplicate detection
    dedupe_decision = check_dedupe(candidate=candidate, store=store)
    if dedupe_decision is not None:
        if not dry_run:
            record_write_outcome(dedupe_decision.write_outcome)
        return MemoryWriteResult(write_decision=dedupe_decision)

    # Stage 5a: low-value rejection
    low_value = _low_value_reason(candidate)
    if low_value is not None:
        decision = MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(low_value,),
        )
        if not dry_run:
            record_write_outcome("reject")
        return MemoryWriteResult(write_decision=decision)

    # Stage 5b: volatile/weak quality → defer
    if candidate.stability == "volatile" or candidate.support_quality == "weak":
        decision = MemoryWriteDecision(
            write_outcome="defer",
            candidate_id=candidate.candidate_id,
            defer_reason_code="insufficient_support",
            reasons=("support is not yet stable or strong enough for committed memory",),
        )
        if not dry_run:
            record_write_outcome("defer")
        return MemoryWriteResult(write_decision=decision)

    # Stage 5c: type-based review requirement
    if requires_review_by_type(candidate):
        decision = MemoryWriteDecision(
            write_outcome="defer",
            candidate_id=candidate.candidate_id,
            defer_reason_code="review_required",
            reasons=("this memory type and scope requires review before commit",),
        )
        if not dry_run:
            record_write_outcome("defer")
        return MemoryWriteResult(write_decision=decision)

    # Stage 6: compression into committed record
    if dry_run:
        memory_id = coerce_memory_id(_DRY_RUN_MEMORY_ID)
    else:
        memory_id = store.allocate_memory_id()

    record = compress_candidate(
        candidate=candidate,
        memory_id=memory_id,
        created_from_run_id=str(candidate.scope.run_id) if candidate.scope.run_id else None,
    )

    if dry_run:
        # Return preview decision without any store mutations
        decision = MemoryWriteDecision(
            write_outcome="write",
            candidate_id=candidate.candidate_id,
            memory_id=record.memory_id,
            committed_record=record,
        )
        return MemoryWriteResult(write_decision=decision)

    # Stage 7: commit
    store._store_committed_record(record)

    # Stage 8: indexing (committed record stands even if indexing fails)
    index_record(record, store=store, embedder=embedder)

    # Stage 9: linking
    links = build_support_links(record=record)
    for link in links:
        store.store_link(link)

    # Emit write event
    _emit_write_event(store=store, candidate=candidate, outcome="write", memory_id=str(memory_id))
    record_write_outcome("write")

    decision = MemoryWriteDecision(
        write_outcome="write",
        candidate_id=candidate.candidate_id,
        memory_id=record.memory_id,
        committed_record=record,
    )
    return MemoryWriteResult(write_decision=decision, links_created=links)


def _low_value_reason(candidate: MemoryCandidate) -> str | None:
    normalized_why = normalized_identity(candidate.why_it_matters)
    if normalized_why in _LOW_VALUE_WHY:
        return "candidate lacks strong durable continuity value"
    if normalized_identity(candidate.summary) == normalized_why:
        return "candidate does not explain why the memory matters beyond restating itself"
    return None


def _emit_write_event(
    *,
    store,
    candidate: MemoryCandidate,
    outcome: str,
    memory_id: str | None = None,
) -> None:
    try:
        event = MemoryWriteEvent(
            write_event_id=coerce_write_event_id(f"we-{uuid.uuid4().hex[:12]}"),
            candidate_id=candidate.candidate_id,
            project_id=str(candidate.scope.project_id),
            write_outcome=outcome,
            decision_summary=f"{outcome} for candidate {candidate.candidate_id}",
            created_at=utc_now(),
            related_memory_id=memory_id,
        )
        store.store_write_event(event)
    except Exception:
        # Audit failure must not break the write pipeline
        pass
