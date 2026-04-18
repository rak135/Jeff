"""Extended v1 memory schemas: links, audit events, maintenance job records.

The core candidate/record/decision models live in models.py.
This module adds the v1 thin-link, audit, and maintenance schemas and
re-exports everything into a single import surface for consumers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from jeff.core.schemas import MemoryId

from .ids import MemoryLinkId, MemoryWriteEventId, MemoryRetrievalEventId, MaintenanceJobId
from .models import (  # noqa: F401 — re-export canonical models
    CommittedMemoryRecord,
    MemoryCandidate,
    MemorySupportRef,
    MemoryWriteDecision,
    make_memory_candidate,
)
from .types import (
    DEFER_REASON_CODES,
    LINK_TYPES,
    MAINTENANCE_JOB_STATUSES,
    MAINTENANCE_JOB_TYPES,
    WRITE_OUTCOMES,
    MemoryCandidateId,
    normalize_text_list,
    require_text,
)


@dataclass(frozen=True, slots=True)
class MemoryLink:
    """Typed thin-link from a committed memory record to a support object."""

    memory_link_id: MemoryLinkId
    memory_id: MemoryId
    link_type: str
    target_id: str
    target_family: str
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.link_type not in LINK_TYPES:
            raise ValueError(f"unsupported link_type: {self.link_type}")
        object.__setattr__(self, "target_id", require_text(self.target_id, field_name="target_id"))
        object.__setattr__(
            self,
            "target_family",
            require_text(self.target_family, field_name="target_family"),
        )


@dataclass(frozen=True, slots=True)
class MemoryWriteEvent:
    """Audit record for a memory write decision."""

    write_event_id: MemoryWriteEventId
    candidate_id: MemoryCandidateId
    project_id: str
    write_outcome: str
    decision_summary: str
    created_at: str
    defer_reason_code: str | None = None
    related_memory_id: str | None = None

    def __post_init__(self) -> None:
        if self.write_outcome not in WRITE_OUTCOMES:
            raise ValueError(f"unsupported write_outcome: {self.write_outcome}")
        if self.defer_reason_code is not None and self.defer_reason_code not in DEFER_REASON_CODES:
            raise ValueError(f"unsupported defer_reason_code: {self.defer_reason_code}")
        object.__setattr__(
            self,
            "decision_summary",
            require_text(self.decision_summary, field_name="decision_summary"),
        )


@dataclass(frozen=True, slots=True)
class MemoryRetrievalEvent:
    """Retrieval audit record for evaluation and observability."""

    retrieval_event_id: MemoryRetrievalEventId
    project_id: str
    purpose: str
    returned_count: int
    explicit_hit_count: int
    lexical_hit_count: int
    semantic_hit_count: int
    contradiction_count: int
    created_at: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))


@dataclass(frozen=True, slots=True)
class MaintenanceJobRecord:
    """Registry record for a memory maintenance job."""

    job_id: MaintenanceJobId
    job_type: str
    project_id: str
    job_status: str
    created_at: str
    updated_at: str
    details: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.job_type not in MAINTENANCE_JOB_TYPES:
            raise ValueError(f"unsupported job_type: {self.job_type}")
        if self.job_status not in MAINTENANCE_JOB_STATUSES:
            raise ValueError(f"unsupported job_status: {self.job_status}")
        object.__setattr__(self, "project_id", require_text(self.project_id, field_name="project_id"))


@dataclass(frozen=True, slots=True)
class MemoryWriteResult:
    """Combined result of process_candidate — the top-level write API entry point."""

    write_decision: MemoryWriteDecision
    write_event: MemoryWriteEvent | None = None
    links_created: tuple[MemoryLink, ...] = ()

    @property
    def write_outcome(self) -> str:
        return self.write_decision.write_outcome

    @property
    def memory_id(self) -> MemoryId | None:
        return self.write_decision.memory_id

    @property
    def committed_record(self) -> CommittedMemoryRecord | None:
        return self.write_decision.committed_record
