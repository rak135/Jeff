"""Shared action-layer types for execution and outcome contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import Scope

ExecutionStatus = Literal[
    "pending_start",
    "running",
    "completed",
    "completed_with_degradation",
    "failed",
    "interrupted",
    "aborted",
]

OutcomeState = Literal[
    "complete",
    "partial",
    "degraded",
    "blocked",
    "failed",
    "inconclusive",
    "mismatch_affected",
]

SupportRefType = Literal["artifact", "trace", "evidence"]


def require_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")

    return normalized


def normalize_text_list(
    values: tuple[str, ...] | list[str] | None,
    *,
    field_name: str,
) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(require_text(value, field_name=field_name) for value in values)


@dataclass(frozen=True, slots=True)
class SupportRef:
    ref_type: SupportRefType
    ref_id: str
    scope: Scope
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "ref_id", require_text(self.ref_id, field_name="ref_id"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
