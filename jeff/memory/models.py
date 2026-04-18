"""Memory-layer candidate, record, and decision models.

Canonical home of committed memory dataclasses.  schemas.py re-exports these
plus extended v1 schemas (links, events, maintenance).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jeff.core.schemas import MemoryId, Scope, coerce_memory_id

from .types import (
    CANDIDATE_STATUSES,
    CONFLICT_POSTURES,
    DEFER_REASON_CODES,
    FRESHNESS_SENSITIVITIES,
    MEMORY_RECORD_STATUSES,
    MEMORY_TYPES,
    RECORD_STABILITY_POSTURES,
    STABILITY_POSTURES,
    SUPPORT_QUALITIES,
    SUPPORT_REF_KINDS,
    WRITE_OUTCOMES,
    MemoryCandidateId,
    assert_not_global_scope,
    coerce_memory_candidate_id,
    normalize_text_list,
    require_concise_text,
    require_text,
)

_MEMORY_CANDIDATE_TOKEN = object()


@dataclass(frozen=True, slots=True)
class MemorySupportRef:
    ref_kind: str
    ref_id: str
    summary: str

    def __post_init__(self) -> None:
        if self.ref_kind not in SUPPORT_REF_KINDS:
            raise ValueError(f"unsupported memory support ref_kind: {self.ref_kind}")
        object.__setattr__(self, "ref_id", require_text(self.ref_id, field_name="ref_id"))
        object.__setattr__(
            self,
            "summary",
            require_concise_text(self.summary, field_name="summary", max_length=160),
        )


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    candidate_id: MemoryCandidateId
    memory_type: str
    scope: Scope
    summary: str
    remembered_points: tuple[str, ...]
    why_it_matters: str
    support_refs: tuple[MemorySupportRef, ...]
    support_quality: str
    stability: str
    candidate_status: str = "pending_review"
    _origin_token: object = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self._origin_token is not _MEMORY_CANDIDATE_TOKEN:
            raise ValueError(
                "memory candidates must be created by jeff.memory.candidate_builder"
            )
        if self.memory_type not in MEMORY_TYPES:
            raise ValueError(f"unsupported memory_type: {self.memory_type}")
        if self.support_quality not in SUPPORT_QUALITIES:
            raise ValueError(f"unsupported support_quality: {self.support_quality}")
        if self.stability not in STABILITY_POSTURES:
            raise ValueError(f"unsupported stability: {self.stability}")
        if self.candidate_status not in CANDIDATE_STATUSES:
            raise ValueError(f"unsupported candidate_status: {self.candidate_status}")

        object.__setattr__(
            self,
            "candidate_id",
            coerce_memory_candidate_id(str(self.candidate_id)),
        )
        object.__setattr__(
            self,
            "summary",
            require_concise_text(self.summary, field_name="summary", max_length=200),
        )
        object.__setattr__(
            self,
            "why_it_matters",
            require_concise_text(
                self.why_it_matters,
                field_name="why_it_matters",
                max_length=200,
            ),
        )
        object.__setattr__(
            self,
            "remembered_points",
            normalize_text_list(self.remembered_points, field_name="remembered_points"),
        )
        if not self.remembered_points:
            raise ValueError("memory candidates must carry at least one remembered point")
        if len(self.remembered_points) > 5:
            raise ValueError("memory candidates must stay bounded to five remembered points or fewer")
        for point in self.remembered_points:
            require_concise_text(point, field_name="remembered_points", max_length=200)
        if not self.support_refs:
            raise ValueError("memory candidates must carry at least one support_ref")

        # Hard-reject global/system scope at candidate creation time
        assert_not_global_scope(str(self.scope.project_id))


@dataclass(frozen=True, slots=True)
class CommittedMemoryRecord:
    memory_id: MemoryId
    memory_type: str
    scope: Scope
    summary: str
    remembered_points: tuple[str, ...]
    why_it_matters: str
    support_quality: str
    stability: str
    record_status: str = "active"
    conflict_posture: str = "none"
    created_at: str = ""
    updated_at: str = ""
    support_refs: tuple[MemorySupportRef, ...] = ()
    # v1 extended fields (all optional with defaults for backward compat)
    freshness_sensitivity: str = "low"
    created_from_run_id: str | None = None
    schema_version: str = "1.0"
    supersedes_memory_id: str | None = None
    superseded_by_memory_id: str | None = None
    merged_into_memory_id: str | None = None

    def __post_init__(self) -> None:
        if self.memory_type not in MEMORY_TYPES:
            raise ValueError(f"unsupported memory_type: {self.memory_type}")
        if self.support_quality not in SUPPORT_QUALITIES:
            raise ValueError(f"unsupported support_quality: {self.support_quality}")
        if self.stability not in RECORD_STABILITY_POSTURES:
            raise ValueError(f"unsupported stability for committed record: {self.stability}")
        if self.record_status not in MEMORY_RECORD_STATUSES:
            raise ValueError(f"unsupported record_status: {self.record_status}")
        if self.conflict_posture not in CONFLICT_POSTURES:
            raise ValueError(f"unsupported conflict_posture: {self.conflict_posture}")
        if self.freshness_sensitivity not in FRESHNESS_SENSITIVITIES:
            raise ValueError(f"unsupported freshness_sensitivity: {self.freshness_sensitivity}")
        object.__setattr__(self, "memory_id", coerce_memory_id(str(self.memory_id)))
        object.__setattr__(
            self,
            "summary",
            require_concise_text(self.summary, field_name="summary", max_length=200),
        )
        object.__setattr__(
            self,
            "remembered_points",
            normalize_text_list(self.remembered_points, field_name="remembered_points"),
        )
        if not self.remembered_points:
            raise ValueError("committed memory requires at least one remembered point")
        if len(self.remembered_points) > 5:
            raise ValueError("committed memory must stay bounded to five remembered points or fewer")
        for point in self.remembered_points:
            require_concise_text(point, field_name="remembered_points", max_length=200)
        object.__setattr__(
            self,
            "why_it_matters",
            require_concise_text(
                self.why_it_matters,
                field_name="why_it_matters",
                max_length=200,
            ),
        )
        object.__setattr__(self, "created_at", require_text(self.created_at, field_name="created_at"))
        object.__setattr__(self, "updated_at", require_text(self.updated_at, field_name="updated_at"))
        if not self.support_refs:
            raise ValueError("committed memory requires support_refs for inspectable grounding")

        # Hard-reject global/system scope
        assert_not_global_scope(str(self.scope.project_id))


@dataclass(frozen=True, slots=True)
class MemoryWriteDecision:
    write_outcome: str
    candidate_id: MemoryCandidateId
    memory_id: MemoryId | None = None
    committed_record: CommittedMemoryRecord | None = None
    reasons: tuple[str, ...] = ()
    defer_reason_code: str | None = None
    superseded_memory_id: MemoryId | None = None

    def __post_init__(self) -> None:
        if self.write_outcome not in WRITE_OUTCOMES:
            raise ValueError(f"unsupported write_outcome: {self.write_outcome}")
        object.__setattr__(
            self,
            "candidate_id",
            coerce_memory_candidate_id(str(self.candidate_id)),
        )
        object.__setattr__(self, "reasons", normalize_text_list(self.reasons, field_name="reasons"))

        if self.defer_reason_code is not None and self.defer_reason_code not in DEFER_REASON_CODES:
            raise ValueError(f"unsupported defer_reason_code: {self.defer_reason_code}")

        _commit_outcomes = {"write", "merge_into_existing", "supersede_existing"}
        if self.write_outcome in _commit_outcomes:
            if self.memory_id is None or self.committed_record is None:
                raise ValueError(f"{self.write_outcome} decisions require memory_id and committed_record")
            object.__setattr__(self, "memory_id", coerce_memory_id(str(self.memory_id)))
        else:
            # reject / defer — no committed memory exposed
            if self.memory_id is not None or self.committed_record is not None:
                raise ValueError("reject/defer decisions must not expose committed memory")
            if not self.reasons:
                raise ValueError("reject/defer decisions must include reasons")
            if self.write_outcome == "defer" and self.defer_reason_code is None:
                raise ValueError("defer decisions must include a defer_reason_code")


def make_memory_candidate(
    *,
    candidate_id: str,
    memory_type: str,
    scope: Scope,
    summary: str,
    remembered_points: tuple[str, ...],
    why_it_matters: str,
    support_refs: tuple[MemorySupportRef, ...],
    support_quality: str,
    stability: str,
) -> MemoryCandidate:
    return MemoryCandidate(
        candidate_id=candidate_id,
        memory_type=memory_type,
        scope=scope,
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=support_refs,
        support_quality=support_quality,
        stability=stability,
        _origin_token=_MEMORY_CANDIDATE_TOKEN,
    )
