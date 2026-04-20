"""Shared cognitive helper types."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal

from jeff.core.schemas import Scope

TriggerFamily = Literal["operator_input", "system_trigger"]
SupportFamily = Literal[
    "memory",
    "compiled_knowledge",
    "archive",
    "artifact",
    "evidence",
    "research",
    "operator_material",
]
SourceFamily = Literal[
    "canonical_truth",
    "artifact",
    "document",
    "operator_material",
    "research",
]

_BLOCKED_CONTEXT_FAMILIES = {"session_state", "ui_state", "trace", "log"}


def require_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")

    return normalized


def normalize_text_list(values: tuple[str, ...] | list[str] | None, *, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()

    normalized: list[str] = []
    for value in values:
        normalized.append(require_text(value, field_name=field_name))
    return tuple(normalized)


def normalized_identity(value: str) -> str:
    compact = re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
    return re.sub(r"\s+", " ", compact)


@dataclass(frozen=True, slots=True)
class TriggerInput:
    trigger_summary: str
    trigger_family: TriggerFamily = "operator_input"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "trigger_summary",
            require_text(self.trigger_summary, field_name="trigger_summary"),
        )


@dataclass(frozen=True, slots=True)
class TruthRecord:
    truth_family: Literal[
        "project",
        "work_unit",
        "run",
        "governance_blocker",
        "governance_integrity",
        "governance_approval_dependency",
        "governance_constraint",
        "governance_readiness",
    ]
    scope: Scope
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))


@dataclass(frozen=True, slots=True)
class SupportInput:
    source_family: str
    scope: Scope
    summary: str
    source_id: str | None = None
    include_full_body: bool = False

    def __post_init__(self) -> None:
        if self.source_family in _BLOCKED_CONTEXT_FAMILIES:
            raise ValueError(f"{self.source_family} is not valid context support")
        if self.source_family not in {
            "memory",
            "compiled_knowledge",
            "archive",
            "artifact",
            "evidence",
            "research",
            "operator_material",
        }:
            raise ValueError(f"unsupported support source_family: {self.source_family}")
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.source_id is not None:
            object.__setattr__(self, "source_id", require_text(self.source_id, field_name="source_id"))
        if self.include_full_body:
            raise ValueError("full-body or archive-style support is not allowed in bounded context")


@dataclass(frozen=True, slots=True)
class SourceSummary:
    source_id: str
    source_family: SourceFamily
    scope: Scope
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "source_id", require_text(self.source_id, field_name="source_id"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))


@dataclass(frozen=True, slots=True)
class ResearchFinding:
    statement: str
    source_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "statement", require_text(self.statement, field_name="statement"))
        object.__setattr__(
            self,
            "source_ids",
            normalize_text_list(self.source_ids, field_name="source_ids"),
        )
        if not self.source_ids:
            raise ValueError("research findings must keep at least one supporting source_id")


@dataclass(frozen=True, slots=True)
class ResearchInference:
    statement: str
    based_on_finding_indexes: tuple[int, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "statement", require_text(self.statement, field_name="statement"))
        if not self.based_on_finding_indexes:
            raise ValueError("research inference must point back to at least one finding")


@dataclass(frozen=True, slots=True)
class Recommendation:
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))


@dataclass(frozen=True, slots=True)
class PlanStep:
    summary: str
    review_required: bool = False
    step_id: str | None = None
    step_order: int = 1
    title: str | None = None
    step_objective: str | None = None
    step_type: Literal["bounded_action", "review", "validation", "analysis", "coordination"] = "bounded_action"
    step_inputs_summary: tuple[str, ...] = ()
    assumptions: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    entry_conditions: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()
    checkpoint_required: bool | None = None
    revalidation_required_on_resume: bool = False
    candidate_action_summary: str | None = None
    step_status: Literal["pending", "active", "completed", "blocked", "failed", "stopped"] = "pending"
    support_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if not isinstance(self.step_order, int):
            raise TypeError("step_order must be an integer")
        if self.step_order <= 0:
            raise ValueError("step_order must be greater than zero")
        if self.step_id is not None:
            object.__setattr__(self, "step_id", require_text(self.step_id, field_name="step_id"))
        if self.title is None:
            object.__setattr__(self, "title", self.summary)
        else:
            object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        if self.step_objective is None:
            object.__setattr__(self, "step_objective", self.summary)
        else:
            object.__setattr__(self, "step_objective", require_text(self.step_objective, field_name="step_objective"))
        if self.step_type not in {"bounded_action", "review", "validation", "analysis", "coordination"}:
            raise ValueError("step_type must remain a lawful bounded planning step kind")
        object.__setattr__(
            self,
            "step_inputs_summary",
            normalize_text_list(self.step_inputs_summary, field_name="step_inputs_summary"),
        )
        object.__setattr__(self, "assumptions", normalize_text_list(self.assumptions, field_name="assumptions"))
        object.__setattr__(self, "risks", normalize_text_list(self.risks, field_name="risks"))
        object.__setattr__(
            self,
            "dependencies",
            normalize_text_list(self.dependencies, field_name="dependencies"),
        )
        object.__setattr__(
            self,
            "entry_conditions",
            normalize_text_list(self.entry_conditions, field_name="entry_conditions"),
        )
        object.__setattr__(
            self,
            "success_criteria",
            normalize_text_list(self.success_criteria, field_name="success_criteria"),
        )
        if self.candidate_action_summary is None:
            object.__setattr__(self, "candidate_action_summary", self.summary)
        else:
            object.__setattr__(
                self,
                "candidate_action_summary",
                require_text(self.candidate_action_summary, field_name="candidate_action_summary"),
            )
        if self.checkpoint_required is None:
            object.__setattr__(self, "checkpoint_required", self.review_required)
        if self.step_status not in {"pending", "active", "completed", "blocked", "failed", "stopped"}:
            raise ValueError("step_status must remain a lawful bounded planning step state")
        object.__setattr__(self, "support_refs", normalize_text_list(self.support_refs, field_name="support_refs"))
