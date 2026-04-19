"""Deterministic orchestrator runner over explicit public stage handlers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Mapping

from jeff.cognitive import (
    ContextPackage,
    EvaluationResult,
    PlanArtifact,
    ProposalResult,
    ResearchArtifact,
    SelectionBridgeError,
    SelectionBridgeRequest,
    SelectionBridgeResult,
    SelectionRequest,
    SelectionResult,
    build_and_run_selection,
)
from jeff.cognitive.proposal import (
    ProposalGenerationBridgeRequest,
    ProposalGenerationBridgeResult,
    ProposalInputPackage,
    ProposalSupportConsumerRequest,
    build_and_run_proposal_generation,
    consume_proposal_support_package,
)
from jeff.cognitive.post_selection import (
    NextStageResolutionRequest,
    NextStageResolutionResult,
    OperatorSelectionOverride,
    PlanActionBridgeRequest,
    PlannedActionBridgeResult,
    ProposalSupportPackage,
    ResearchDecisionSupportHandoff,
    ResearchDecisionSupportRequest,
    ResearchOutputSufficiencyRequest,
    ResearchOutputSufficiencyResult,
    ResearchProposalConsumerRequest,
    SelectionActionResolutionRequest,
    SelectionEffectiveProposalRequest,
    build_research_decision_support_handoff,
    bridge_plan_to_action,
    consume_research_for_proposal_support,
    evaluate_research_output_sufficiency,
    materialize_effective_proposal,
    resolve_next_stage,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection.api import SelectionRunFailure, run_selection_hybrid
from jeff.core.schemas import Scope

from .continuations import (
    PROPOSAL_GENERATION_BRIDGE_OUTPUT_KEY,
    PROPOSAL_INPUT_OUTPUT_KEY,
    PROPOSAL_OUTPUT_OUTPUT_KEY,
    RESEARCH_DECISION_SUPPORT_OUTPUT_KEY,
    RESEARCH_PROPOSAL_SUPPORT_OUTPUT_KEY,
    RESEARCH_SUFFICIENCY_OUTPUT_KEY,
    SELECTION_BRIDGE_OUTPUT_KEY,
    SELECTION_OUTPUT_OUTPUT_KEY,
)
from .continuations.boundary_routes import (
    route_planning_boundary as _continuation_route_planning_boundary,
    route_research_boundary as _continuation_route_research_boundary,
)
from .continuations.planning import bridge_planned_action as _continuation_bridge_planned_action
from .continuations.post_research import (
    build_and_run_proposal_generation_from_research_followup as _continuation_build_and_run_proposal_generation,
    build_proposal_input_package as _continuation_build_proposal_input_package,
    build_research_decision_support as _continuation_build_research_decision_support,
    consume_research_proposal_support as _continuation_consume_research_proposal_support,
    evaluate_research_output as _continuation_evaluate_research_output,
    handle_post_research_continuation,
)
from .continuations.post_selection import (
    continue_from_research_selection_output as _continuation_continue_from_research_selection_output,
    resolve_selection_next_stage as _continuation_resolve_selection_next_stage,
    route_next_stage_resolution as _continuation_route_next_stage_resolution,
)
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
    objective_summary: str | None = None
    memory_handoff_attempted: bool = False
    memory_handoff_result: object | None = None
    memory_handoff_note: str | None = None


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
                    return handle_post_research_continuation(
                        flow_id=flow_id,
                        lifecycle=lifecycle,
                        outputs=outputs,
                        events=events,
                        flow_family=flow_family,
                        scope=scope,
                        stage_handlers=stage_handlers,
                        research_output=previous_output,
                        finish_with_validation_failure=_finish_with_validation_failure,
                        finish_with_routing=_finish_with_routing,
                        evaluate_research_output_sufficiency_fn=_evaluate_research_output_sufficiency,
                        build_research_decision_support_handoff_fn=_build_research_decision_support_handoff,
                        consume_research_for_proposal_support_fn=_consume_research_for_proposal_support,
                        consume_proposal_support_package_fn=_consume_proposal_support_package,
                        build_and_run_proposal_generation_from_research_followup_fn=
                            _build_and_run_proposal_generation_from_research_followup,
                        build_and_run_selection_from_proposal_output_fn=_build_and_run_selection_from_proposal_output,
                        continue_from_research_selection_output_fn=_continue_from_research_selection_output,
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
    return _continuation_resolve_selection_next_stage(
        flow_id=flow_id,
        proposal_output=proposal_output,
        selection_output=selection_output,
        operator_override=operator_override,
        resolve_next_stage_fn=resolve_next_stage,
    )


def _route_next_stage_resolution(
    *,
    next_stage_resolution: NextStageResolutionResult,
    next_stage: StageName,
    scope: Scope,
) -> tuple[RoutingDecision | None, bool]:
    return _continuation_route_next_stage_resolution(
        next_stage_resolution=next_stage_resolution,
        next_stage=next_stage,
        scope=scope,
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
    return _continuation_bridge_planned_action(
        flow_id=flow_id,
        plan_output=plan_output,
        scope=scope,
        bridge_plan_to_action_fn=bridge_plan_to_action,
    )


def _evaluate_research_output_sufficiency(
    *,
    flow_id: str,
    research_output: object,
) -> ResearchOutputSufficiencyResult:
    return _continuation_evaluate_research_output(
        flow_id=flow_id,
        research_output=research_output,
        evaluate_research_output_sufficiency_fn=evaluate_research_output_sufficiency,
    )


def _build_research_decision_support_handoff(
    *,
    flow_id: str,
    research_output: object,
    sufficiency_result: ResearchOutputSufficiencyResult,
) -> ResearchDecisionSupportHandoff:
    return _continuation_build_research_decision_support(
        flow_id=flow_id,
        research_output=research_output,
        sufficiency_result=sufficiency_result,
        build_research_decision_support_handoff_fn=build_research_decision_support_handoff,
    )


def _consume_research_for_proposal_support(
    *,
    flow_id: str,
    decision_support_handoff: ResearchDecisionSupportHandoff,
) -> ProposalSupportPackage:
    return _continuation_consume_research_proposal_support(
        flow_id=flow_id,
        decision_support_handoff=decision_support_handoff,
        consume_research_for_proposal_support_fn=consume_research_for_proposal_support,
    )


def _consume_proposal_support_package(
    *,
    flow_id: str,
    proposal_support_package: ProposalSupportPackage,
) -> ProposalInputPackage:
    return _continuation_build_proposal_input_package(
        flow_id=flow_id,
        proposal_support_package=proposal_support_package,
        consume_proposal_support_package_fn=consume_proposal_support_package,
    )


def _build_and_run_proposal_generation_from_research_followup(
    *,
    flow_id: str,
    proposal_input_package: ProposalInputPackage,
    context_output: object | None,
    research_output: object,
    research_handler: StageHandler | HybridSelectionStageConfig,
) -> ProposalGenerationBridgeResult:
    return _continuation_build_and_run_proposal_generation(
        flow_id=flow_id,
        proposal_input_package=proposal_input_package,
        context_output=context_output,
        research_output=research_output,
        research_handler=research_handler,
        build_and_run_proposal_generation_fn=build_and_run_proposal_generation,
    )


def _build_and_run_selection_from_proposal_output(
    *,
    flow_id: str,
    proposal_output: ProposalResult,
    research_handler: StageHandler | HybridSelectionStageConfig,
) -> SelectionBridgeResult:
    selection_id = getattr(research_handler, "selection_bridge_selection_id", _missing_selection_bridge_id())
    if selection_id is _MISSING_SELECTION_BRIDGE_ID:
        selection_id = f"{flow_id}:post-research-selection"

    return build_and_run_selection(
        SelectionBridgeRequest(
            request_id=f"{flow_id}:proposal-output-to-selection",
            proposal_result=proposal_output,
            selection_id=selection_id,
        )
    )


_MISSING_SELECTION_BRIDGE_ID = object()


def _missing_selection_bridge_id() -> object:
    return _MISSING_SELECTION_BRIDGE_ID


def _continue_from_research_selection_output(
    *,
    flow_id: str,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    flow_family: FlowFamily,
    scope: Scope,
    stage_handlers: Mapping[StageName, StageHandler | HybridSelectionStageConfig],
    research: ResearchArtifact,
    decision_support_handoff: ResearchDecisionSupportHandoff,
    proposal_support_package: ProposalSupportPackage,
    proposal_input_package: ProposalInputPackage,
    proposal_generation_bridge_result: ProposalGenerationBridgeResult,
    proposal_output: ProposalResult,
    selection_bridge_result: SelectionBridgeResult,
    selection_output: SelectionResult,
) -> FlowRunResult:
    return _continuation_continue_from_research_selection_output(
        flow_id=flow_id,
        lifecycle=lifecycle,
        outputs=outputs,
        events=events,
        flow_family=flow_family,
        scope=scope,
        stage_handlers=stage_handlers,
        research=research,
        decision_support_handoff=decision_support_handoff,
        proposal_support_package=proposal_support_package,
        proposal_input_package=proposal_input_package,
        proposal_generation_bridge_result=proposal_generation_bridge_result,
        proposal_output=proposal_output,
        selection_bridge_result=selection_bridge_result,
        selection_output=selection_output,
        resolve_selection_next_stage_fn=_resolve_selection_next_stage,
        invoke_stage_handler=_invoke_stage_handler,
        stage_summary=_stage_summary,
        append_event=_append_event,
        finish_with_validation_failure=_finish_with_validation_failure,
        finish_with_routing=_finish_with_routing,
        bridge_planned_action=_bridge_planned_action,
        route_planning_boundary=_route_planning_boundary,
        terminal_routing=_terminal_routing,
        flow_result_factory=FlowRunResult,
    )


def _route_planning_boundary(
    *,
    plan: PlanArtifact,
    scope: Scope,
    bridge_result: PlannedActionBridgeResult | None = None,
) -> RoutingDecision:
    return _continuation_route_planning_boundary(
        plan=plan,
        scope=scope,
        bridge_result=bridge_result,
    )


def _route_research_boundary(
    *,
    research: ResearchArtifact,
    sufficiency_result: ResearchOutputSufficiencyResult,
    decision_support_handoff: ResearchDecisionSupportHandoff | None,
    proposal_support_package: ProposalSupportPackage | None,
    proposal_input_package: ProposalInputPackage | None,
    proposal_generation_bridge_result: ProposalGenerationBridgeResult | None,
    proposal_output: ProposalResult | None,
    selection_bridge_result: SelectionBridgeResult | None,
    selection_output: SelectionResult | None,
    selection_bridge_reason: str | None,
    scope: Scope,
) -> RoutingDecision:
    return _continuation_route_research_boundary(
        research=research,
        sufficiency_result=sufficiency_result,
        decision_support_handoff=decision_support_handoff,
        proposal_support_package=proposal_support_package,
        proposal_input_package=proposal_input_package,
        proposal_generation_bridge_result=proposal_generation_bridge_result,
        proposal_output=proposal_output,
        selection_bridge_result=selection_bridge_result,
        selection_output=selection_output,
        selection_bridge_reason=selection_bridge_reason,
        scope=scope,
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
