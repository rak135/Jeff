"""Orchestration-local lifecycle state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import Scope

from .flows import FlowFamily, StageName

FlowLifecycleState = Literal[
    "started",
    "active",
    "waiting",
    "blocked",
    "escalated",
    "completed",
    "failed",
    "invalidated",
]


@dataclass(frozen=True, slots=True)
class FlowLifecycle:
    flow_id: str
    flow_family: FlowFamily
    scope: Scope
    lifecycle_state: FlowLifecycleState
    current_stage: StageName | None = None
    reason_summary: str | None = None

    def __post_init__(self) -> None:
        normalized_flow_id = self.flow_id.strip()
        if not normalized_flow_id:
            raise ValueError("flow_id must be a non-empty string")
        object.__setattr__(self, "flow_id", normalized_flow_id)
        if self.reason_summary is not None:
            normalized_reason = self.reason_summary.strip()
            if not normalized_reason:
                raise ValueError("reason_summary must be non-empty when provided")
            object.__setattr__(self, "reason_summary", normalized_reason)


def update_lifecycle(
    lifecycle: FlowLifecycle,
    *,
    lifecycle_state: FlowLifecycleState,
    current_stage: StageName | None = None,
    reason_summary: str | None = None,
) -> FlowLifecycle:
    return FlowLifecycle(
        flow_id=lifecycle.flow_id,
        flow_family=lifecycle.flow_family,
        scope=lifecycle.scope,
        lifecycle_state=lifecycle_state,
        current_stage=current_stage,
        reason_summary=reason_summary,
    )
