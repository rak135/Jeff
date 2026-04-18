"""Duplicate detection and incremental-value checks for memory candidates.

Outcomes:
- exact/near duplicate with no new value → reject
- candidate is materially stronger → defer(dedupe_ambiguity) for operator review
- no match → continue to commit
"""

from __future__ import annotations

from .models import CommittedMemoryRecord, MemoryCandidate, MemoryWriteDecision
from .types import normalized_identity


def check_dedupe(
    *,
    candidate: MemoryCandidate,
    store,
) -> MemoryWriteDecision | None:
    """Return a terminal write decision if a dedupe condition is met, else None.

    None means no duplicate found; the pipeline may proceed to commit.
    Accepts any store satisfying MemoryStoreProtocol.
    """
    project_records = store.list_project_records(str(candidate.scope.project_id))
    active_records = [r for r in project_records if r.record_status == "active"]

    candidate_summary_norm = normalized_identity(candidate.summary)
    candidate_points_norm = tuple(normalized_identity(p) for p in candidate.remembered_points)

    for record in active_records:
        if record.memory_type != candidate.memory_type:
            continue

        record_summary_norm = normalized_identity(record.summary)
        record_points_norm = tuple(normalized_identity(p) for p in record.remembered_points)

        # Exact duplicate: same type, same scope, same summary, same points
        if (
            record.scope == candidate.scope
            and record_summary_norm == candidate_summary_norm
            and record_points_norm == candidate_points_norm
        ):
            if _is_stronger(candidate, record):
                return MemoryWriteDecision(
                    write_outcome="defer",
                    candidate_id=candidate.candidate_id,
                    defer_reason_code="dedupe_ambiguity",
                    reasons=("stronger duplicate may supersede existing record — requires review",),
                )
            return MemoryWriteDecision(
                write_outcome="reject",
                candidate_id=candidate.candidate_id,
                reasons=("duplicate committed memory already exists for this bounded memory",),
            )

        # Near-duplicate: same scope, same summary, high point overlap
        if (
            record.scope == candidate.scope
            and record_summary_norm == candidate_summary_norm
            and _high_point_overlap(candidate_points_norm, record_points_norm)
        ):
            if _is_stronger(candidate, record):
                return MemoryWriteDecision(
                    write_outcome="defer",
                    candidate_id=candidate.candidate_id,
                    defer_reason_code="dedupe_ambiguity",
                    reasons=("near-duplicate with existing record; may supersede — requires review",),
                )
            return MemoryWriteDecision(
                write_outcome="reject",
                candidate_id=candidate.candidate_id,
                reasons=("low-value near-duplicate of existing committed memory",),
            )

    return None  # no duplicate found


def _high_point_overlap(
    a: tuple[str, ...],
    b: tuple[str, ...],
    threshold: float = 0.7,
) -> bool:
    if not a or not b:
        return False
    set_a, set_b = set(a), set(b)
    overlap = len(set_a & set_b)
    return overlap / max(len(set_a), len(set_b)) >= threshold


def _is_stronger(candidate: MemoryCandidate, record: CommittedMemoryRecord) -> bool:
    quality_rank = {"weak": 0, "moderate": 1, "strong": 2}
    return quality_rank.get(candidate.support_quality, 0) > quality_rank.get(record.support_quality, 0)
