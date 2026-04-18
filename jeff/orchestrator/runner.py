"""Deterministic orchestrator runner over explicit public stage handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping

from jeff.cognitive import EvaluationResult, PlanArtifact, ProposalResult, ResearchArtifact, SelectionRequest, SelectionResult
from jeff.cognitive.post_selection import (
    NextStageResolutionRequest,
    NextStageResolutionResult,
    OperatorSelectionOverride,
    PlanActionBridgeRequest,
    PlannedActionBridgeResult,
    ResearchOutputSufficiencyRequest,
    ResearchOutputSufficiencyResult,
    SelectionActionResolutionRequest,
    SelectionEffectiveProposalRequest,
    bridge_plan_to_action,
    evaluate_research_output_sufficiency,
    materialize_effective_proposal,
    resolve_next_stage,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection.api import SelectionRunFailure, run_selection_hybrid
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

if TYPE_CHECKING:
    from jeff.infrastructure import InfrastructureServices

StageHandler = Callable[[object | None], object]


@dataclass(frozen=True, slots=True)
class HybridSelectionStageConfig:
    selection_id: str
    infrastructure_services: InfrastructureServices
    adapter_id: str | None = None
    request_id: str | None = None


@dataclass(frozen=True, slots=True)
class FlowRunResult:
    lifecycle: FlowLifecycle
    outputs: dict[StageName, object]
    events: tuple[OrchestrationEvent, ...]
    routing_decision: RoutingDecision | None = None
    selection_failure: SelectionRunFailure | None = None


def run_flow(
    *,
    flow_id: str,
    flow_family: FlowFamily,
    scope: Scope,
    stage_handlers: Mapping[StageName, StageHandler | HybridSelectionStageConfig],
    initial_input: object | None = None,
    operator_override: OperatorSelectionOverride | None = None,
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
            if previous_stage == "selection" and stage in {"planning", "research", "action"}:
                try:
                    next_stage_resolution = _resolve_selection_next_stage(
                        flow_id=flow_id,
                        proposal_output=outputs.get("proposal"),
                        selection_output=previous_output,
                        operator_override=operator_override,
                    )
                    routing, skip_stage = _route_next_stage_resolution(
                        next_stage_resolution=next_stage_resolution,
                        next_stage=stage,
                        scope=scope,
                    )
                except Exception as exc:
                    return _finish_with_validation_failure(
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        flow_family=flow_family,
                        scope=scope,
                        stage=stage,
                        validation=ValidationResult(
                            valid=False,
                            code="post_selection_next_stage_resolution_failed",
                            reason=str(exc),
                        ),
                    )
                if routing is not None:
                    return _finish_with_routing(
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        routing=routing,
                        flow_family=flow_family,
                    )
                if skip_stage:
                    continue
            else:
                if previous_stage == "research" and stage == "action":
                    try:
                        research_sufficiency = _evaluate_research_output_sufficiency(
                            flow_id=flow_id,
                            research_output=previous_output,
                        )
                    except Exception as exc:
                        return _finish_with_validation_failure(
                            lifecycle=lifecycle,
                            outputs=outputs,
                            events=events,
                            flow_family=flow_family,
                            scope=scope,
                            stage=stage,
                            validation=ValidationResult(
                                valid=False,
                                code="research_output_sufficiency_bridge_failed",
                                reason=str(exc),
                            ),
                        )

                    return _finish_with_routing(
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        routing=_route_research_boundary(
                            research=previous_output,
                            sufficiency_result=research_sufficiency,
                            scope=scope,
                        ),
                        flow_family=flow_family,
                    )

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

            if previous_stage == "planning" and stage == "action":
                try:
                    bridged_action = _bridge_planned_action(
                        flow_id=flow_id,
                        plan_output=previous_output,
                        scope=scope,
                    )
                except Exception as exc:
                    return _finish_with_validation_failure(
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        flow_family=flow_family,
                        scope=scope,
                        stage=stage,
                        validation=ValidationResult(
                            valid=False,
                            code="plan_action_bridge_failed",
                            reason=str(exc),
                        ),
                    )

                if not bridged_action.action_formed:
                    return _finish_with_routing(
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        routing=_route_planning_boundary(
                            plan=previous_output,
                            bridge_result=bridged_action,
                            scope=scope,
                        ),
                        flow_family=flow_family,
                    )

                _append_event(
                    events,
                    flow_family=flow_family,
                    scope=scope,
                    stage=stage,
                    event_type="stage_entered",
                    summary="entered action via planning bridge",
                )
                lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage=stage)

                stage_output = bridged_action.action
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
                    summary="exited action via planning bridge",
                )
                previous_stage = stage
                previous_output = stage_output
                continue

        _append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage=stage,
            event_type="stage_entered",
            summary=_stage_summary(stage=stage, phase="entered", handler=stage_handlers[stage]),
        )
        lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage=stage)

        handler = stage_handlers[stage]
        try:
            stage_output = _invoke_stage_handler(stage=stage, handler=handler, previous_output=previous_output)
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

        if stage == "selection" and isinstance(stage_output, SelectionRunFailure):
            return _finish_with_selection_hybrid_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                failure=stage_output,
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
            summary=_stage_summary(stage=stage, phase="exited", handler=handler),
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


def _resolve_selection_next_stage(
    *,
    flow_id: str,
    proposal_output: object | None,
    selection_output: object,
    operator_override: OperatorSelectionOverride | None,
) -> NextStageResolutionResult:
    if not isinstance(proposal_output, ProposalResult):
        raise TypeError("post-selection routing requires ProposalResult output from the proposal stage")
    if not isinstance(selection_output, SelectionResult):
        raise TypeError("post-selection routing requires SelectionResult output from the selection stage")

    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id=f"{flow_id}:selection-action-resolution",
            selection_result=selection_output,
            operator_override=operator_override,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id=f"{flow_id}:selection-effective-proposal",
            proposal_result=proposal_output,
            resolved_basis=resolved_basis,
        )
    )
    return resolve_next_stage(
        NextStageResolutionRequest(
            request_id=f"{flow_id}:next-stage-resolution",
            materialized_effective_proposal=materialized,
        )
    )


def _route_next_stage_resolution(
    *,
    next_stage_resolution: NextStageResolutionResult,
    next_stage: StageName,
    scope: Scope,
) -> tuple[RoutingDecision | None, bool]:
    if next_stage_resolution.next_stage_target == "governance":
        if next_stage in {"planning", "research"}:
            return None, True
        if next_stage != "action":
            raise ValueError(
                f"governance next stage requires action continuation, but the flow expects {next_stage}"
            )
        return None, False

    if next_stage_resolution.next_stage_target == "planning":
        if next_stage == "planning":
            return None, False
        return (
            RoutingDecision(
                route_kind="hold",
                routed_outcome="planning",
                scope=scope,
                source_stage="selection",
                reason_summary=(
                    f"{next_stage_resolution.summary} Planning is the next required downstream stage, "
                    "and this flow stops before entering it."
                ),
            ),
            False,
        )

    if next_stage_resolution.next_stage_target == "research_followup":
        if next_stage == "research":
            return None, False
        return (
            RoutingDecision(
                route_kind="hold",
                routed_outcome="research_followup",
                scope=scope,
                source_stage="selection",
                reason_summary=(
                    f"{next_stage_resolution.summary} Bounded research follow-up is the next required downstream "
                    "stage, and this flow stops before entering it."
                ),
            ),
            False,
        )

    if next_stage_resolution.next_stage_target == "terminal_non_selection":
        routed_outcome = "reject_all" if next_stage_resolution.non_selection_outcome == "reject_all" else "defer"
        return (
            RoutingDecision(
                route_kind="stop",
                routed_outcome=routed_outcome,
                scope=scope,
                source_stage="selection",
                reason_summary=(
                    f"{next_stage_resolution.summary} This remains a terminal non-execution path in the current slice."
                ),
            ),
            False,
        )

    if next_stage_resolution.next_stage_target == "escalation_surface":
        return (
            RoutingDecision(
                route_kind="hold",
                routed_outcome="escalated",
                scope=scope,
                source_stage="selection",
                reason_summary=(
                    f"{next_stage_resolution.summary} This route stops at an explicit escalation surface in the "
                    "current slice."
                ),
            ),
            False,
        )

    raise ValueError(
        f"unsupported post-selection next_stage_target: {next_stage_resolution.next_stage_target}"
    )


def _invoke_stage_handler(
    *,
    stage: StageName,
    handler: StageHandler | HybridSelectionStageConfig,
    previous_output: object | None,
) -> object:
    if stage == "selection" and isinstance(handler, HybridSelectionStageConfig):
        if not isinstance(previous_output, ProposalResult):
            raise TypeError("hybrid selection stage requires ProposalResult input")
        request_id = handler.request_id or f"{previous_output.request_id}:selection"
        hybrid_result = run_selection_hybrid(
            SelectionRequest(request_id=request_id, proposal_result=previous_output),
            selection_id=handler.selection_id,
            infrastructure_services=handler.infrastructure_services,
            adapter_id=handler.adapter_id,
        )
        if isinstance(hybrid_result, SelectionRunFailure):
            return hybrid_result
        return hybrid_result.selection_result

    return handler(previous_output)


def _stage_summary(
    *,
    stage: StageName,
    phase: str,
    handler: StageHandler | HybridSelectionStageConfig,
) -> str:
    if stage == "selection":
        path = "hybrid" if isinstance(handler, HybridSelectionStageConfig) else "deterministic"
        return f"{phase} selection via {path} path"
    return f"{phase} {stage}"


def _route_before_next_stage(
    *,
    previous_stage: StageName,
    previous_output: object,
    next_stage: StageName,
    scope: Scope,
) -> RoutingDecision | None:
    if previous_stage == "selection" and next_stage in {"planning", "research", "action"}:
        return route_selection_outcome(selection=previous_output, scope=scope)
    if previous_stage == "planning" and next_stage == "action":
        return None
    if previous_stage == "governance" and next_stage == "execution":
        return route_governance_outcome(decision=previous_output, scope=scope)
    if previous_stage == "memory" and next_stage == "transition":
        return route_memory_write_outcome(memory_write=previous_output, scope=scope)
    return None


def _bridge_planned_action(
    *,
    flow_id: str,
    plan_output: object,
    scope: Scope,
) -> PlannedActionBridgeResult:
    if not isinstance(plan_output, PlanArtifact):
        raise TypeError("plan action bridge requires PlanArtifact output from the planning stage")

    return bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id=f"{flow_id}:plan-action-bridge",
            plan_artifact=plan_output,
            scope=scope,
        )
    )


def _evaluate_research_output_sufficiency(
    *,
    flow_id: str,
    research_output: object,
) -> ResearchOutputSufficiencyResult:
    if not isinstance(research_output, ResearchArtifact):
        raise TypeError("research output sufficiency bridge requires ResearchArtifact output from the research stage")

    return evaluate_research_output_sufficiency(
        ResearchOutputSufficiencyRequest(
            request_id=f"{flow_id}:research-output-sufficiency",
            research_artifact=research_output,
        )
    )


def _route_planning_boundary(
    *,
    plan: PlanArtifact,
    scope: Scope,
    bridge_result: PlannedActionBridgeResult | None = None,
) -> RoutingDecision:
    proposal_summary = (
        "the selected proposal"
        if plan.selected_proposal_id is None
        else f"proposal {plan.selected_proposal_id}"
    )
    bridge_reason = (
        "no repo-local plan-to-action bridge is implemented in the current slice."
        if bridge_result is None
        else f"no Action could be formed from the current plan output because {bridge_result.no_action_reason}"
    )
    return RoutingDecision(
        route_kind="hold",
        routed_outcome="planning",
        scope=scope,
        source_stage="planning",
        reason_summary=(
            f"Planning entered and produced a bounded plan artifact for {proposal_summary} "
            f"with {len(plan.intended_steps)} intended step(s). Planning remains support-only; "
            "no governance evaluation occurred, no action permission exists, no execution occurred, "
            f"and {bridge_reason}"
        ),
    )
def _route_research_boundary(
    *,
    research: ResearchArtifact,
    sufficiency_result: ResearchOutputSufficiencyResult,
    scope: Scope,
) -> RoutingDecision:
    if sufficiency_result.sufficient_for_downstream_use:
        return RoutingDecision(
            route_kind="hold",
            routed_outcome="research_followup",
            scope=scope,
            source_stage="research",
            reason_summary=(
                f"Research entered and produced a bounded research artifact for question '{research.question}' "
                f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
                "Sufficiency evaluation: decision_support_ready. Current research is sufficient for bounded "
                f"downstream decision support with supported points: {', '.join(sufficiency_result.key_supported_points)}. "
                "Research remains support-only; no governance evaluation occurred, no action permission exists, "
                "no execution occurred, and no repo-local decision-support-to-action, governance, or execution "
                "bridge is implemented in the current slice."
            ),
        )

    unresolved_items = "; ".join(sufficiency_result.unresolved_items)
    contradiction_note = (
        " Contradictions remain visible and unresolved."
        if sufficiency_result.contradictions_present
        else ""
    )
    return RoutingDecision(
        route_kind="hold",
        routed_outcome="research_followup",
        scope=scope,
        source_stage="research",
        reason_summary=(
            f"Research entered and produced a bounded research artifact for question '{research.question}' "
            f"with {len(research.findings)} finding(s) across {len(research.source_ids)} source(s). "
            "Sufficiency evaluation: more_research_needed. Current research is not yet sufficient for bounded "
            f"downstream use because these unresolved items remain: {unresolved_items}.{contradiction_note} "
            "Research remains support-only; no governance evaluation occurred, no action permission exists, "
            "no execution occurred, and Jeff does not auto-loop into more research or any downstream action in "
            "the current slice."
        ),
    )


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


def _finish_with_selection_hybrid_failure(
    *,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    flow_family: FlowFamily,
    scope: Scope,
    failure: SelectionRunFailure,
) -> FlowRunResult:
    summary = f"selection hybrid {failure.failure_stage} failure: {failure.error}"
    _append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="selection",
        event_type="flow_failed",
        summary=summary,
    )
    failed_lifecycle = update_lifecycle(
        lifecycle,
        lifecycle_state="failed",
        current_stage="selection",
        reason_summary=summary,
    )
    return FlowRunResult(
        lifecycle=failed_lifecycle,
        outputs=outputs,
        events=tuple(events),
        selection_failure=failure,
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
