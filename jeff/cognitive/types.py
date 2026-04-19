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

    def __post_init__(self) -> None:
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
