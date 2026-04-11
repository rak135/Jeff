"""Compact orchestration-level trace events."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from jeff.core.schemas import Scope

from .flows import FlowFamily, StageName

EventType = Literal[
    "flow_started",
    "stage_entered",
    "stage_exited",
    "validation_failed",
    "routing_decision",
    "flow_blocked",
    "flow_escalated",
    "flow_completed",
    "flow_failed",
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass(frozen=True, slots=True)
class OrchestrationEvent:
    ordinal: int
    flow_family: FlowFamily
    scope: Scope
    stage: StageName | None
    event_type: EventType
    summary: str
    emitted_at: str

    def __post_init__(self) -> None:
        if self.ordinal < 1:
            raise ValueError("event ordinal must be one or greater")
        normalized_summary = self.summary.strip()
        if not normalized_summary:
            raise ValueError("event summary must be non-empty")
        object.__setattr__(self, "summary", normalized_summary)
        normalized_emitted_at = self.emitted_at.strip()
        if not normalized_emitted_at:
            raise ValueError("emitted_at must be a non-empty string")
        object.__setattr__(self, "emitted_at", normalized_emitted_at)

    @property
    def run_id(self) -> str | None:
        return None if self.scope.run_id is None else str(self.scope.run_id)


def build_event(
    *,
    ordinal: int,
    flow_family: FlowFamily,
    scope: Scope,
    stage: StageName | None,
    event_type: EventType,
    summary: str,
) -> OrchestrationEvent:
    return OrchestrationEvent(
        ordinal=ordinal,
        flow_family=flow_family,
        scope=scope,
        stage=stage,
        event_type=event_type,
        summary=summary,
        emitted_at=_timestamp(),
    )
