"""Candidate validation — enforces hard write rules and shape rules.

Validation must fail closed.  Any ambiguous candidate that cannot be cleanly
validated should be deferred rather than committed.
"""

from __future__ import annotations

from .models import MemoryCandidate, MemoryWriteDecision
from .types import (
    MEMORY_TYPES,
    SUPPORT_QUALITIES,
    assert_not_global_scope,
    normalized_identity,
    require_text,
)

# Phrases that signal archive-dump or current-truth masquerade behavior
_ARCHIVE_DUMP_SIGNALS = {
    "summary of everything",
    "all findings",
    "full brief",
    "complete research",
    "all notes",
    "raw output",
    "transcript",
    "full log",
    "entire conversation",
    "everything we learned",
}

_CURRENT_TRUTH_SIGNALS = {
    "current state is",
    "current status is",
    "the project is currently",
    "right now the",
    "as of today",
}


def validate_candidate(candidate: MemoryCandidate) -> MemoryWriteDecision | None:
    """Return a terminal write decision if validation fails, else None (pass through).

    A returned MemoryWriteDecision is always reject or defer.
    None means validation passed and the pipeline may continue.
    """
    # Scope: project_id must be present and not global/system
    try:
        assert_not_global_scope(str(candidate.scope.project_id))
    except ValueError as exc:
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(str(exc),),
        )

    project_id = str(candidate.scope.project_id)
    if not project_id.strip():
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=("project_id is required on all memory write paths",),
        )

    # Type must be one of the fixed v1 set (already validated in MemoryCandidate.__post_init__,
    # but re-checked here so the validator is a complete authority surface)
    if candidate.memory_type not in MEMORY_TYPES:
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=(f"invalid memory type: {candidate.memory_type}",),
        )

    # Support refs must exist (already validated in MemoryCandidate but double-checked here)
    if not candidate.support_refs:
        return MemoryWriteDecision(
            write_outcome="reject",
            candidate_id=candidate.candidate_id,
            reasons=("candidate must carry at least one support_ref",),
        )

    # Archive-dump detection: candidate must not be a wholesale dump of research/briefs
    summary_lower = normalized_identity(candidate.summary)
    why_lower = normalized_identity(candidate.why_it_matters)
    for signal in _ARCHIVE_DUMP_SIGNALS:
        if signal in summary_lower or signal in why_lower:
            return MemoryWriteDecision(
                write_outcome="reject",
                candidate_id=candidate.candidate_id,
                reasons=("candidate resembles archive-dump behavior and must not become memory",),
            )

    # Current-truth masquerade: memory must not encode current state as if it were truth
    for signal in _CURRENT_TRUTH_SIGNALS:
        if signal in summary_lower:
            return MemoryWriteDecision(
                write_outcome="reject",
                candidate_id=candidate.candidate_id,
                reasons=("candidate encodes current truth rather than durable continuity",),
            )

    # Freshness: volatile candidates are never directly committable
    if candidate.stability == "volatile" and candidate.support_quality == "weak":
        return MemoryWriteDecision(
            write_outcome="defer",
            candidate_id=candidate.candidate_id,
            defer_reason_code="insufficient_support",
            reasons=("volatile stability with weak support cannot be committed in v1",),
        )

    return None  # validation passed


def validate_project_id_present(project_id: str) -> None:
    """Raise if project_id is missing or forbidden (used on retrieval paths too)."""
    try:
        require_text(project_id, field_name="project_id")
    except (TypeError, ValueError) as exc:
        raise ValueError(f"project_id is required on all memory paths: {exc}") from exc
    assert_not_global_scope(project_id)
