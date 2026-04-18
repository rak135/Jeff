"""Conflict labeling — compares committed memory against a truth anchor.

Memory that conflicts with current truth must stay labeled as support,
contradiction, stale memory, or uncertainty support.  It must never override
truth.  Conflict labels are informational; they do not mutate truth.
"""

from __future__ import annotations

from .models import CommittedMemoryRecord
from .types import normalized_identity


def label_conflict_posture(
    *,
    record: CommittedMemoryRecord,
    truth_anchor: str | None,
) -> str:
    """Return the appropriate conflict_posture value for a record given truth.

    Returns one of: 'none', 'stale_support', 'contradiction_support', 'mismatch_support'.

    If truth_anchor is None, returns the record's existing conflict_posture unchanged.
    """
    if truth_anchor is None:
        return record.conflict_posture

    # Already marked superseded or deprecated → stale_support
    if record.record_status in {"superseded", "deprecated", "quarantined"}:
        return "stale_support"

    if not truth_anchor.strip():
        return record.conflict_posture

    anchor_norm = normalized_identity(truth_anchor)
    summary_norm = normalized_identity(record.summary)

    # Check for explicit contradiction signal in truth anchor
    contradiction_signals = {"contradicts", "no longer", "changed to", "now false", "incorrect"}
    for signal in contradiction_signals:
        if signal in anchor_norm and summary_norm[:30] in anchor_norm:
            return "contradiction_support"

    # Check for staleness: truth anchor explicitly states something different
    stale_signals = {"has changed", "updated to", "replaced by", "no longer applies"}
    for signal in stale_signals:
        if signal in anchor_norm:
            return "stale_support"

    return record.conflict_posture


def apply_conflict_labels(
    *,
    records: tuple[CommittedMemoryRecord, ...],
    truth_anchor: str | None,
) -> tuple[CommittedMemoryRecord, ...]:
    """Return records with conflict_posture updated based on the truth anchor.

    Records are returned in the same order.  The truth anchor is the caller's
    summary of current truth (from canonical state).
    """
    if truth_anchor is None:
        return records

    result = []
    for record in records:
        new_posture = label_conflict_posture(record=record, truth_anchor=truth_anchor)
        if new_posture == record.conflict_posture:
            result.append(record)
            continue
        # Re-create record with updated conflict posture (dataclasses are frozen)
        updated = CommittedMemoryRecord(
            memory_id=record.memory_id,
            memory_type=record.memory_type,
            scope=record.scope,
            summary=record.summary,
            remembered_points=record.remembered_points,
            why_it_matters=record.why_it_matters,
            support_quality=record.support_quality,
            stability=record.stability,
            record_status=record.record_status,
            conflict_posture=new_posture,
            created_at=record.created_at,
            updated_at=record.updated_at,
            support_refs=record.support_refs,
            freshness_sensitivity=record.freshness_sensitivity,
            created_from_run_id=record.created_from_run_id,
            schema_version=record.schema_version,
            supersedes_memory_id=record.supersedes_memory_id,
            superseded_by_memory_id=record.superseded_by_memory_id,
            merged_into_memory_id=record.merged_into_memory_id,
        )
        result.append(updated)

    return tuple(result)


def has_conflict(record: CommittedMemoryRecord) -> bool:
    return record.conflict_posture != "none"
