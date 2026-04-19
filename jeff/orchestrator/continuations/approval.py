"""Explicit operator-triggered continuation helpers for approval-bound runs."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING

from jeff.governance import ActionEntryDecision

from ..lifecycle import update_lifecycle
from ..routing import RoutingDecision
from ..trace import OrchestrationEvent, build_event

if TYPE_CHECKING:
    from jeff.action.execution import ExecutionResult
    from jeff.cognitive import EvaluationResult, Outcome
    from ..runner import FlowRunResult


def continue_approval_workflow(
    *,
    prior_flow_run: FlowRunResult,
    governance_decision: ActionEntryDecision,
    support_outputs: Mapping[str, object] | None = None,
    routing_decision: RoutingDecision | None = None,
    execution_result: ExecutionResult | None = None,
    outcome: Outcome | None = None,
    evaluation: EvaluationResult | None = None,
) -> FlowRunResult:
    from ..runner import FlowRunResult

    outputs = dict(prior_flow_run.outputs)
    outputs["governance"] = governance_decision
    for key in ("execution", "outcome", "evaluation"):
        outputs.pop(key, None)
    if support_outputs is not None:
        outputs.update(dict(support_outputs))
    if execution_result is not None:
        outputs["execution"] = execution_result
    if outcome is not None:
        outputs["outcome"] = outcome
    if evaluation is not None:
        outputs["evaluation"] = evaluation

    events = list(prior_flow_run.events)
    _append_event(
        events,
        prior_flow_run=prior_flow_run,
        stage="governance",
        event_type="stage_entered",
        summary="operator-triggered governance continuation started",
    )
    _append_event(
        events,
        prior_flow_run=prior_flow_run,
        stage="governance",
        event_type="stage_exited",
        summary=(
            f"governance outcome {governance_decision.governance_outcome} "
            f"with approval_verdict {governance_decision.approval_verdict}"
        ),
    )

    if execution_result is not None:
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="execution",
            event_type="stage_entered",
            summary="execution continuation started",
        )
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="execution",
            event_type="stage_exited",
            summary=f"execution finished with status {execution_result.execution_status}",
        )
    if outcome is not None:
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="outcome",
            event_type="stage_entered",
            summary="outcome normalization started",
        )
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="outcome",
            event_type="stage_exited",
            summary=f"outcome normalized as {outcome.outcome_state}",
        )
    if evaluation is not None:
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="evaluation",
            event_type="stage_entered",
            summary="evaluation continuation started",
        )
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage="evaluation",
            event_type="stage_exited",
            summary=f"evaluation finished with verdict {evaluation.evaluation_verdict}",
        )

    if routing_decision is not None:
        _append_event(
            events,
            prior_flow_run=prior_flow_run,
            stage=routing_decision.source_stage,
            event_type="routing_decision",
            summary=f"{routing_decision.routed_outcome}: {routing_decision.reason_summary}",
        )
        if routing_decision.routed_outcome == "blocked":
            _append_event(
                events,
                prior_flow_run=prior_flow_run,
                stage=routing_decision.source_stage,
                event_type="flow_blocked",
                summary=routing_decision.reason_summary,
            )
            lifecycle_state = "blocked"
        elif routing_decision.routed_outcome == "escalated":
            _append_event(
                events,
                prior_flow_run=prior_flow_run,
                stage=routing_decision.source_stage,
                event_type="flow_escalated",
                summary=routing_decision.reason_summary,
            )
            lifecycle_state = "escalated"
        elif routing_decision.route_kind == "hold":
            lifecycle_state = "waiting"
        elif routing_decision.routed_outcome == "invalidated":
            lifecycle_state = "invalidated"
        else:
            lifecycle_state = "completed"
        lifecycle = update_lifecycle(
            prior_flow_run.lifecycle,
            lifecycle_state=lifecycle_state,
            current_stage=routing_decision.source_stage,
            reason_summary=routing_decision.reason_summary,
        )
        return FlowRunResult(
            lifecycle=lifecycle,
            outputs=outputs,
            events=tuple(events),
            routing_decision=routing_decision,
        )

    _append_event(
        events,
        prior_flow_run=prior_flow_run,
        stage="evaluation" if evaluation is not None else "governance",
        event_type="flow_completed",
        summary="operator-triggered continuation completed",
    )
    lifecycle = update_lifecycle(
        prior_flow_run.lifecycle,
        lifecycle_state="completed",
        current_stage="evaluation" if evaluation is not None else "governance",
        reason_summary="operator-triggered continuation completed",
    )
    return FlowRunResult(
        lifecycle=lifecycle,
        outputs=outputs,
        events=tuple(events),
        routing_decision=None,
    )


def _append_event(
    events: list[OrchestrationEvent],
    *,
    prior_flow_run: FlowRunResult,
    stage,
    event_type,
    summary: str,
) -> None:
    events.append(
        build_event(
            ordinal=len(events) + 1,
            flow_family=prior_flow_run.lifecycle.flow_family,
            scope=prior_flow_run.lifecycle.scope,
            stage=stage,
            event_type=event_type,
            summary=summary,
        )
    )