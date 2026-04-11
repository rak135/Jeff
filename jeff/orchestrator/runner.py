"""Deterministic orchestrator runner over explicit public stage handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Mapping

from jeff.action import EvaluationResult
from jeff.core.schemas import Scope

from .flows import FlowFamily, StageName, stage_order_for_flow
from .lifecycle import FlowLifecycle, update_lifecycle
from .routing import (
    RoutingDecision,
    route_evaluation_followup,
    route_governance_outcome,
    route_memory_write_outcome,
    route_selection_outcome,
)
from .trace import OrchestrationEvent, build_event
from .validation import ValidationResult, validate_handoff, validate_stage_output, validate_stage_sequence

StageHandler = Callable[[object | None], object]


@dataclass(frozen=True, slots=True)
class FlowRunResult:
    lifecycle: FlowLifecycle
    outputs: dict[StageName, object]
    events: tuple[OrchestrationEvent, ...]
    routing_decision: RoutingDecision | None = None


def run_flow(
    *,
    flow_id: str,
    flow_family: FlowFamily,
    scope: Scope,
    stage_handlers: Mapping[StageName, StageHandler],
    initial_input: object | None = None,
) -> FlowRunResult:
    stages = stage_order_for_flow(flow_family)
    sequence_validation = validate_stage_sequence(flow_family=flow_family, stages=tuple(stage_handlers.keys()))
    if not sequence_validation.valid:
        raise ValueError(sequence_validation.reason)

    lifecycle = FlowLifecycle(
        flow_id=flow_id,
        flow_family=flow_family,
        scope=scope,
        lifecycle_state="started",
    )
    events: list[OrchestrationEvent] = []
    outputs: dict[StageName, object] = {}

    _append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage=None,
        event_type="flow_started",
        summary=f"flow {flow_id} started",
    )
    lifecycle = update_lifecycle(lifecycle, lifecycle_state="active")

    previous_stage: StageName | None = None
    previous_output = initial_input

    for stage in stages:
        if previous_stage is not None:
            routing = _route_before_next_stage(
                previous_stage=previous_stage,
                previous_output=previous_output,
                next_stage=stage,
                scope=scope,
            )
            if routing is not None:
                return _finish_with_routing(
                    lifecycle=lifecycle,
                    outputs=outputs,
                    events=events,
                    routing=routing,
                    flow_family=flow_family,
                )

            handoff_validation = validate_handoff(
                previous_stage=previous_stage,
                previous_output=previous_output,
                next_stage=stage,
                flow_scope=scope,
            )
            if not handoff_validation.valid:
                return _finish_with_validation_failure(
                    lifecycle=lifecycle,
                    outputs=outputs,
                    events=events,
                    flow_family=flow_family,
                    scope=scope,
                    stage=stage,
                    validation=handoff_validation,
                )

        _append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage=stage,
            event_type="stage_entered",
            summary=f"entered {stage}",
        )
        lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage=stage)

        handler = stage_handlers[stage]
        try:
            stage_output = handler(previous_output)
        except Exception as exc:
            _append_event(
                events,
                flow_family=flow_family,
                scope=scope,
                stage=stage,
                event_type="flow_failed",
                summary=f"{stage} handler failed: {exc}",
            )
            lifecycle = update_lifecycle(
                lifecycle,
                lifecycle_state="failed",
                current_stage=stage,
                reason_summary=str(exc),
            )
            return FlowRunResult(
                lifecycle=lifecycle,
                outputs=outputs,
                events=tuple(events),
            )

        output_validation = validate_stage_output(stage=stage, output=stage_output, flow_scope=scope)
        if not output_validation.valid:
            return _finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage=stage,
                validation=output_validation,
            )

        outputs[stage] = stage_output
        _append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage=stage,
            event_type="stage_exited",
            summary=f"exited {stage}",
        )
        previous_stage = stage
        previous_output = stage_output

    terminal_routing = _terminal_routing(
        flow_family=flow_family,
        last_stage=previous_stage,
        last_output=previous_output,
        scope=scope,
    )
    if terminal_routing is not None:
        return _finish_with_routing(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            routing=terminal_routing,
            flow_family=flow_family,
        )

    _append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage=previous_stage,
        event_type="flow_completed",
        summary=f"{flow_family} completed",
    )
    lifecycle = update_lifecycle(
        lifecycle,
        lifecycle_state="completed",
        current_stage=previous_stage,
        reason_summary=f"{flow_family} completed",
    )
    return FlowRunResult(
        lifecycle=lifecycle,
        outputs=outputs,
        events=tuple(events),
    )


def _route_before_next_stage(
    *,
    previous_stage: StageName,
    previous_output: object,
    next_stage: StageName,
    scope: Scope,
) -> RoutingDecision | None:
    if previous_stage == "selection" and next_stage in {"planning", "action"}:
        return route_selection_outcome(selection=previous_output, scope=scope)
    if previous_stage == "governance" and next_stage == "execution":
        return route_governance_outcome(decision=previous_output, scope=scope)
    if previous_stage == "memory" and next_stage == "transition":
        return route_memory_write_outcome(memory_write=previous_output, scope=scope)
    return None


def _terminal_routing(
    *,
    flow_family: FlowFamily,
    last_stage: StageName | None,
    last_output: object | None,
    scope: Scope,
) -> RoutingDecision | None:
    if last_stage == "selection":
        return route_selection_outcome(selection=last_output, scope=scope)
    if last_stage == "governance":
        return route_governance_outcome(decision=last_output, scope=scope)
    if flow_family == "evaluation_driven_followup" and isinstance(last_output, EvaluationResult):
        return route_evaluation_followup(evaluation=last_output, scope=scope)
    if last_stage == "transition" and getattr(last_output, "transition_result", None) == "rejected":
        return RoutingDecision(
            route_kind="stop",
            routed_outcome="blocked",
            scope=scope,
            source_stage="transition",
            reason_summary="transition rejected the proposed truth mutation",
        )
    return None


def _finish_with_validation_failure(
    *,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    flow_family: FlowFamily,
    scope: Scope,
    stage: StageName,
    validation: ValidationResult,
) -> FlowRunResult:
    _append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage=stage,
        event_type="validation_failed",
        summary=validation.reason or "validation failed",
    )
    invalidated_lifecycle = update_lifecycle(
        lifecycle,
        lifecycle_state="invalidated",
        current_stage=stage,
        reason_summary=validation.reason,
    )
    return FlowRunResult(
        lifecycle=invalidated_lifecycle,
        outputs=outputs,
        events=tuple(events),
        routing_decision=RoutingDecision(
            route_kind="stop",
            routed_outcome="invalidated",
            scope=scope,
            source_stage=stage,
            reason_summary=validation.reason or "validation failed",
        ),
    )


def _finish_with_routing(
    *,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    routing: RoutingDecision,
    flow_family: FlowFamily,
) -> FlowRunResult:
    _append_event(
        events,
        flow_family=flow_family,
        scope=routing.scope,
        stage=routing.source_stage,
        event_type="routing_decision",
        summary=f"{routing.routed_outcome}: {routing.reason_summary}",
    )
    if routing.routed_outcome == "blocked":
        _append_event(
            events,
            flow_family=flow_family,
            scope=routing.scope,
            stage=routing.source_stage,
            event_type="flow_blocked",
            summary=routing.reason_summary,
        )
        next_state = "blocked"
    elif routing.routed_outcome == "escalated":
        _append_event(
            events,
            flow_family=flow_family,
            scope=routing.scope,
            stage=routing.source_stage,
            event_type="flow_escalated",
            summary=routing.reason_summary,
        )
        next_state = "escalated"
    elif routing.route_kind == "hold":
        next_state = "waiting"
    elif routing.routed_outcome == "invalidated":
        next_state = "invalidated"
    else:
        next_state = "completed"

    routed_lifecycle = update_lifecycle(
        lifecycle,
        lifecycle_state=next_state,
        current_stage=routing.source_stage,
        reason_summary=routing.reason_summary,
    )
    return FlowRunResult(
        lifecycle=routed_lifecycle,
        outputs=outputs,
        events=tuple(events),
        routing_decision=routing,
    )


def _append_event(
    events: list[OrchestrationEvent],
    *,
    flow_family: FlowFamily,
    scope: Scope,
    stage: StageName | None,
    event_type,
    summary: str,
) -> None:
    events.append(
        build_event(
            ordinal=len(events) + 1,
            flow_family=flow_family,
            scope=scope,
            stage=stage,
            event_type=event_type,
            summary=summary,
        )
    )
