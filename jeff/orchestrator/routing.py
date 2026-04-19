"""Bounded routing helpers for explicit non-forward outcomes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.cognitive import EvaluationResult
from jeff.core.schemas import Scope
from jeff.governance import ActionEntryDecision
from jeff.memory import MemoryWriteDecision

from .flows import StageName

RouteKind = Literal["stop", "hold", "follow_up"]
RoutedOutcome = Literal[
    "blocked",
    "escalated",
    "planning",
    "proposal_input_boundary",
    "proposal_output_ready",
    "selection_output_ready",
    "research_followup",
    "retry",
    "revalidate",
    "recover",
    "terminate_and_replan",
    "request_clarification",
    "reject_all",
    "defer",
    "approval_required",
    "invalidated",
]


@dataclass(frozen=True, slots=True)
class RoutingDecision:
    route_kind: RouteKind
    routed_outcome: RoutedOutcome
    scope: Scope
    source_stage: StageName
    reason_summary: str
    auto_execute: bool = False

    def __post_init__(self) -> None:
        normalized_reason = self.reason_summary.strip()
        if not normalized_reason:
            raise ValueError("reason_summary must be non-empty")
        object.__setattr__(self, "reason_summary", normalized_reason)
        if self.auto_execute:
            raise ValueError("orchestrator routing must remain non-authorizing and non-auto-executing")


def route_selection_outcome(*, selection, scope: Scope) -> RoutingDecision | None:
    if selection.selected_proposal_id is not None:
        return None
    if selection.non_selection_outcome == "reject_all":
        return RoutingDecision(
            route_kind="stop",
            routed_outcome="reject_all",
            scope=scope,
            source_stage="selection",
            reason_summary=selection.rationale,
        )
    if selection.non_selection_outcome == "defer":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="defer",
            scope=scope,
            source_stage="selection",
            reason_summary=selection.rationale,
        )
    if selection.non_selection_outcome == "escalate":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="escalated",
            scope=scope,
            source_stage="selection",
            reason_summary=selection.rationale,
        )
    return None


def route_governance_outcome(*, decision: ActionEntryDecision, scope: Scope) -> RoutingDecision | None:
    if decision.allowed_now:
        return None

    readiness = decision.readiness
    reason = "; ".join(readiness.reasons or readiness.cautions or ("governance did not allow this action",))
    mapping: dict[str, tuple[RouteKind, RoutedOutcome]] = {
        "blocked": ("stop", "blocked"),
        "approval_required": ("hold", "approval_required"),
        "deferred_pending_revalidation": ("hold", "revalidate"),
        "invalidated": ("stop", "invalidated"),
        "escalated": ("hold", "escalated"),
    }
    route_kind, routed_outcome = mapping[decision.governance_outcome]
    return RoutingDecision(
        route_kind=route_kind,
        routed_outcome=routed_outcome,
        scope=scope,
        source_stage="governance",
        reason_summary=reason,
    )


def route_evaluation_followup(*, evaluation: EvaluationResult, scope: Scope) -> RoutingDecision | None:
    mapping: dict[str, tuple[RouteKind, RoutedOutcome]] = {
        "retry": ("follow_up", "retry"),
        "revalidate": ("follow_up", "revalidate"),
        "recover": ("follow_up", "recover"),
        "terminate_and_replan": ("follow_up", "terminate_and_replan"),
        "request_clarification": ("hold", "request_clarification"),
        "escalate": ("hold", "escalated"),
    }
    if evaluation.recommended_next_step not in mapping:
        return None

    route_kind, routed_outcome = mapping[evaluation.recommended_next_step]
    return RoutingDecision(
        route_kind=route_kind,
        routed_outcome=routed_outcome,
        scope=scope,
        source_stage="evaluation",
        reason_summary=evaluation.rationale,
    )


def route_memory_write_outcome(*, memory_write: MemoryWriteDecision, scope: Scope) -> RoutingDecision | None:
    if memory_write.write_outcome == "write":
        return None
    if memory_write.write_outcome == "defer":
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="defer",
            scope=scope,
            source_stage="memory",
            reason_summary="; ".join(memory_write.reasons),
        )
    return RoutingDecision(
        route_kind="stop",
        routed_outcome="blocked",
        scope=scope,
        source_stage="memory",
        reason_summary="; ".join(memory_write.reasons),
    )
