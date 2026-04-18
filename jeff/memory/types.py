"""Shared memory-layer types and small validation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, NewType

from .ids import MemoryCandidateId  # re-export for backward compat  # noqa: F401

MemoryType = Literal["episodic", "semantic", "directional", "operational"]
SupportQuality = Literal["strong", "moderate", "weak"]
# Candidate stability posture (volatile → triggers defer in write pipeline)
StabilityPosture = Literal["stable", "tentative", "volatile"]
# Committed record stability (reinforced = confirmed through repetition or merge)
RecordStabilityPosture = Literal["stable", "tentative", "reinforced"]
FreshnessSensitivity = Literal["low", "medium", "high"]
# v1 conflict posture values (none = no conflict)
ConflictPosture = Literal["none", "stale_support", "contradiction_support", "mismatch_support"]
CandidateStatus = Literal["pending_review", "deferred", "rejected"]
# Extended status for v1 quarantine/deprecation lifecycle
MemoryRecordStatus = Literal["active", "superseded", "deprecated", "quarantined"]
# Extended write outcomes: merge and supersede for incremental-value handling
WriteOutcome = Literal["write", "reject", "defer", "merge_into_existing", "supersede_existing"]
# Machine-readable defer reason codes
DeferReasonCode = Literal[
    "review_required",
    "dedupe_ambiguity",
    "insufficient_support",
    "scope_ambiguity",
    "candidate_needs_rewrite",
    "linkage_incomplete",
]
SupportRefKind = Literal[
    "artifact",
    "evidence",
    "research",
    "evaluation",
    "operator_input",
]
LinkType = Literal[
    "research_artifact_ref",
    "history_record_ref",
    "knowledge_artifact_ref",
    "source_ref",
    "evidence_ref",
    "related_memory_ref",
    "supersedes_ref",
    "merged_into_ref",
    "derived_from_ref",
]
MaintenanceJobType = Literal[
    "embedding_refresh",
    "dedupe_audit",
    "supersession_audit",
    "stale_memory_review",
    "broken_link_audit",
    "retrieval_quality_evaluation",
    "index_consistency_audit",
    "compression_refresh",
    "quarantine_review",
]
MaintenanceJobStatus = Literal["pending", "running", "completed", "failed"]


MEMORY_TYPES = {"episodic", "semantic", "directional", "operational"}
SUPPORT_QUALITIES = {"strong", "moderate", "weak"}
# Candidate posture set (includes volatile for deferral signaling)
STABILITY_POSTURES = {"stable", "tentative", "volatile"}
# Committed record posture set (reinforced replaces volatile — no volatile committed records)
RECORD_STABILITY_POSTURES = {"stable", "tentative", "reinforced"}
FRESHNESS_SENSITIVITIES = {"low", "medium", "high"}
# v1 conflict posture values (aligned removed; none is the neutral value)
CONFLICT_POSTURES = {"none", "stale_support", "contradiction_support", "mismatch_support"}
CANDIDATE_STATUSES = {"pending_review", "deferred", "rejected"}
MEMORY_RECORD_STATUSES = {"active", "superseded", "deprecated", "quarantined"}
WRITE_OUTCOMES = {"write", "reject", "defer", "merge_into_existing", "supersede_existing"}
DEFER_REASON_CODES = {
    "review_required",
    "dedupe_ambiguity",
    "insufficient_support",
    "scope_ambiguity",
    "candidate_needs_rewrite",
    "linkage_incomplete",
}
SUPPORT_REF_KINDS = {"artifact", "evidence", "research", "evaluation", "operator_input"}
LINK_TYPES = {
    "research_artifact_ref",
    "history_record_ref",
    "knowledge_artifact_ref",
    "source_ref",
    "evidence_ref",
    "related_memory_ref",
    "supersedes_ref",
    "merged_into_ref",
    "derived_from_ref",
}
MAINTENANCE_JOB_TYPES = {
    "embedding_refresh",
    "dedupe_audit",
    "supersession_audit",
    "stale_memory_review",
    "broken_link_audit",
    "retrieval_quality_evaluation",
    "index_consistency_audit",
    "compression_refresh",
    "quarantine_review",
}
MAINTENANCE_JOB_STATUSES = {"pending", "running", "completed", "failed"}

# Forbidden project_id sentinels for global/system memory (hard-forbidden in v1)
_FORBIDDEN_PROJECT_SENTINELS = {"global", "system", "*", "_global", "_system", "__global__"}


def require_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def coerce_memory_candidate_id(value: str) -> MemoryCandidateId:
    return MemoryCandidateId(require_text(value, field_name="candidate_id"))


def normalize_text_list(
    values: tuple[str, ...] | list[str] | None,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(require_text(value, field_name=field_name) for value in values)


def require_concise_text(
    value: str,
    *,
    field_name: str,
    max_length: int = 240,
) -> str:
    normalized = require_text(value, field_name=field_name)
    if len(normalized) > max_length:
        raise ValueError(f"{field_name} must stay concise and below {max_length} characters")
    if normalized.count("\n") > 2:
        raise ValueError(f"{field_name} must stay concise and not become a raw dump")
    return normalized


def normalized_identity(value: str) -> str:
    lowered = require_text(value, field_name="identity_value").lower()
    compact = "".join(character if character.isalnum() else " " for character in lowered)
    return " ".join(compact.split())


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def assert_not_global_scope(project_id: str) -> None:
    """Hard-reject global/system scope sentinels (forbidden in v1)."""
    if project_id.lower() in _FORBIDDEN_PROJECT_SENTINELS:
        raise ValueError(
            f"global/system memory is hard-forbidden in v1; project_id '{project_id}' is not allowed"
        )
