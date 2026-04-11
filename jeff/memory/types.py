"""Shared memory-layer types and small validation helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal, NewType

MemoryType = Literal["episodic", "semantic", "directional", "operational"]
SupportQuality = Literal["strong", "moderate", "weak"]
StabilityPosture = Literal["stable", "tentative", "volatile"]
ConflictPosture = Literal["aligned", "stale", "contradicted", "mismatch_support"]
CandidateStatus = Literal["pending_review", "deferred", "rejected"]
MemoryRecordStatus = Literal["active", "superseded"]
WriteOutcome = Literal["write", "reject", "defer"]
SupportRefKind = Literal[
    "artifact",
    "evidence",
    "research",
    "evaluation",
    "operator_input",
]

MemoryCandidateId = NewType("MemoryCandidateId", str)


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


MEMORY_TYPES = {"episodic", "semantic", "directional", "operational"}
SUPPORT_QUALITIES = {"strong", "moderate", "weak"}
STABILITY_POSTURES = {"stable", "tentative", "volatile"}
CONFLICT_POSTURES = {"aligned", "stale", "contradicted", "mismatch_support"}
CANDIDATE_STATUSES = {"pending_review", "deferred", "rejected"}
MEMORY_RECORD_STATUSES = {"active", "superseded"}
WRITE_OUTCOMES = {"write", "reject", "defer"}
SUPPORT_REF_KINDS = {"artifact", "evidence", "research", "evaluation", "operator_input"}
