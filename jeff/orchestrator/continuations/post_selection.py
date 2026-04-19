"""Orchestration-local continuation helpers after Selection output exists."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Mapping

from jeff.cognitive import ProposalResult, SelectionResult
from jeff.cognitive.post_selection import (
    NextStageResolutionRequest,
    NextStageResolutionResult,
    OperatorSelectionOverride,
    SelectionActionResolutionRequest,
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
    resolve_next_stage,
    resolve_selection_action_basis,
)
from jeff.core.schemas import Scope

from ..flows import FlowFamily, StageName
from ..lifecycle import FlowLifecycle, update_lifecycle
from ..routing import RoutingDecision
from ..trace import OrchestrationEvent
from ..validation import validate_handoff, validate_stage_output
from .boundary_routes import build_research_post_selection_prefix

if TYPE_CHECKING:
    from ..runner import FlowRunResult, HybridSelectionStageConfig

StageHandler = Callable[[object | None], object]


def resolve_selection_next_stage(
    *,
    flow_id: str,
    proposal_output: object | None,
    selection_output: object,
    operator_override: OperatorSelectionOverride | None,
    resolve_next_stage_fn=resolve_next_stage,
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
    return resolve_next_stage_fn(
        NextStageResolutionRequest(
            request_id=f"{flow_id}:next-stage-resolution",
            materialized_effective_proposal=materialized,
        )
    )


def route_next_stage_resolution(
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


def continue_from_preserved_action(
    *,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    flow_family: FlowFamily,
    scope: Scope,
    governance_handler: StageHandler | HybridSelectionStageConfig,
    action_output: object,
    continuation_prefix: str,
    invoke_stage_handler,
    stage_summary,
    append_event,
    terminal_routing,
    finish_with_validation_failure,
    finish_with_routing,
    flow_result_factory,
) -> FlowRunResult:
    handoff_validation = validate_handoff(
        previous_stage="action",
        previous_output=action_output,
        next_stage="governance",
        flow_scope=scope,
    )
    if not handoff_validation.valid:
        return finish_with_validation_failure(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage="governance",
            validation=handoff_validation,
        )

    append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="governance",
        event_type="stage_entered",
        summary=stage_summary(stage="governance", phase="entered", handler=governance_handler),
    )
    lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage="governance")
    try:
        governance_output = invoke_stage_handler(
            stage="governance",
            handler=governance_handler,
            previous_output=action_output,
        )
    except Exception as exc:
        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="governance",
            event_type="flow_failed",
            summary=f"governance handler failed: {exc}",
        )
        lifecycle = update_lifecycle(
            lifecycle,
            lifecycle_state="failed",
            current_stage="governance",
            reason_summary=str(exc),
        )
        return flow_result_factory(lifecycle=lifecycle, outputs=outputs, events=tuple(events))

    output_validation = validate_stage_output(stage="governance", output=governance_output, flow_scope=scope)
    if not output_validation.valid:
        return finish_with_validation_failure(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage="governance",
            validation=output_validation,
        )

    outputs["governance"] = governance_output
    append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="governance",
        event_type="stage_exited",
        summary=stage_summary(stage="governance", phase="exited", handler=governance_handler),
    )

    routing = terminal_routing(
        flow_family=flow_family,
        last_stage="governance",
        last_output=governance_output,
        scope=scope,
    )
    if routing is not None:
        return finish_with_routing(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            routing=RoutingDecision(
                route_kind=routing.route_kind,
                routed_outcome=routing.routed_outcome,
                scope=routing.scope,
                source_stage=routing.source_stage,
                reason_summary=f"{continuation_prefix}{routing.reason_summary}",
            ),
            flow_family=flow_family,
        )

    append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="governance",
        event_type="flow_completed",
        summary=f"{flow_family} completed",
    )
    lifecycle = update_lifecycle(
        lifecycle,
        lifecycle_state="completed",
        current_stage="governance",
        reason_summary=f"{continuation_prefix}{flow_family} completed",
    )
    return flow_result_factory(
        lifecycle=lifecycle,
        outputs=outputs,
        events=tuple(events),
    )


def continue_from_research_selection_output(
    *,
    flow_id: str,
    lifecycle: FlowLifecycle,
    outputs: dict[StageName, object],
    events: list[OrchestrationEvent],
    flow_family: FlowFamily,
    scope: Scope,
    stage_handlers: Mapping[StageName, StageHandler | HybridSelectionStageConfig],
    research,
    decision_support_handoff,
    proposal_support_package,
    proposal_input_package,
    proposal_generation_bridge_result,
    proposal_output,
    selection_bridge_result,
    selection_output,
    resolve_selection_next_stage_fn,
    invoke_stage_handler,
    stage_summary,
    append_event,
    finish_with_validation_failure,
    finish_with_routing,
    bridge_planned_action,
    route_planning_boundary,
    terminal_routing,
    flow_result_factory,
) -> FlowRunResult:
    next_stage_resolution = resolve_selection_next_stage_fn(
        flow_id=f"{flow_id}:post-research-selection-output",
        proposal_output=proposal_output,
        selection_output=selection_output,
        operator_override=None,
    )
    continuation_prefix = build_research_post_selection_prefix(
        research=research,
        decision_support_handoff=decision_support_handoff,
        proposal_support_package=proposal_support_package,
        proposal_input_package=proposal_input_package,
        proposal_generation_bridge_result=proposal_generation_bridge_result,
        proposal_output=proposal_output,
        selection_bridge_result=selection_bridge_result,
        selection_output=selection_output,
    )

    if next_stage_resolution.next_stage_target == "research_followup":
        return finish_with_routing(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            routing=RoutingDecision(
                route_kind="hold",
                routed_outcome="research_followup",
                scope=scope,
                source_stage="research",
                reason_summary=(
                    f"{continuation_prefix}{next_stage_resolution.summary} Continued post-selection routing would "
                    "re-enter research_followup, but this slice does not auto-enter recursive research from "
                    "preserved selection output. A separate explicit slice or operator-mediated continuation is "
                    "required to avoid a hidden loop. Selection output remains selection-only and non-authorizing; "
                    "no action formed, no governance evaluation occurred, and no execution occurred."
                ),
            ),
            flow_family=flow_family,
        )

    if next_stage_resolution.next_stage_target == "terminal_non_selection":
        routed_outcome = "reject_all" if next_stage_resolution.non_selection_outcome == "reject_all" else "defer"
        return finish_with_routing(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            routing=RoutingDecision(
                route_kind="stop" if routed_outcome == "reject_all" else "hold",
                routed_outcome=routed_outcome,
                scope=scope,
                source_stage="research",
                reason_summary=(
                    f"{continuation_prefix}{next_stage_resolution.summary} Continued post-selection routing reaches "
                    "a terminal non-execution boundary. Selection output remains non-authorizing; no action formed, "
                    "no governance evaluation occurred, and no execution occurred."
                ),
            ),
            flow_family=flow_family,
        )

    if next_stage_resolution.next_stage_target == "escalation_surface":
        return finish_with_routing(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            routing=RoutingDecision(
                route_kind="hold",
                routed_outcome="escalated",
                scope=scope,
                source_stage="research",
                reason_summary=(
                    f"{continuation_prefix}{next_stage_resolution.summary} Continued post-selection routing reaches "
                    "an explicit escalation surface. Selection output remains non-authorizing; no action formed, no "
                    "governance evaluation occurred, and no execution occurred."
                ),
            ),
            flow_family=flow_family,
        )

    if next_stage_resolution.next_stage_target == "planning":
        planning_handler = stage_handlers.get("planning")
        if planning_handler is None:
            return finish_with_routing(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                routing=RoutingDecision(
                    route_kind="hold",
                    routed_outcome="planning",
                    scope=scope,
                    source_stage="research",
                    reason_summary=(
                        f"{continuation_prefix}{next_stage_resolution.summary} Planning is the next lawful downstream "
                        "stage, but this research-followup flow has no planning stage handler configured for the "
                        "continued path. Selection output remains non-authorizing; no governance evaluation occurred, "
                        "and no execution occurred."
                    ),
                ),
                flow_family=flow_family,
            )

        handoff_validation = validate_handoff(
            previous_stage="selection",
            previous_output=selection_output,
            next_stage="planning",
            flow_scope=scope,
        )
        if not handoff_validation.valid:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="planning",
                validation=handoff_validation,
            )

        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="planning",
            event_type="stage_entered",
            summary=stage_summary(stage="planning", phase="entered", handler=planning_handler),
        )
        lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage="planning")
        try:
            planning_output = invoke_stage_handler(
                stage="planning",
                handler=planning_handler,
                previous_output=selection_output,
            )
        except Exception as exc:
            append_event(
                events,
                flow_family=flow_family,
                scope=scope,
                stage="planning",
                event_type="flow_failed",
                summary=f"planning handler failed: {exc}",
            )
            lifecycle = update_lifecycle(
                lifecycle,
                lifecycle_state="failed",
                current_stage="planning",
                reason_summary=str(exc),
            )
            return flow_result_factory(lifecycle=lifecycle, outputs=outputs, events=tuple(events))

        output_validation = validate_stage_output(stage="planning", output=planning_output, flow_scope=scope)
        if not output_validation.valid:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="planning",
                validation=output_validation,
            )

        outputs["planning"] = planning_output
        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="planning",
            event_type="stage_exited",
            summary=stage_summary(stage="planning", phase="exited", handler=planning_handler),
        )

        bridged_action = bridge_planned_action(
            flow_id=f"{flow_id}:post-research-selection-output",
            plan_output=planning_output,
            scope=scope,
        )
        if not bridged_action.action_formed:
            planning_routing = route_planning_boundary(
                plan=planning_output,
                bridge_result=bridged_action,
                scope=scope,
            )
            return finish_with_routing(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                routing=RoutingDecision(
                    route_kind=planning_routing.route_kind,
                    routed_outcome=planning_routing.routed_outcome,
                    scope=planning_routing.scope,
                    source_stage=planning_routing.source_stage,
                    reason_summary=(
                        f"{continuation_prefix}Planning entered through the existing downstream post-selection "
                        f"chain. {planning_routing.reason_summary}"
                    ),
                ),
                flow_family=flow_family,
            )

        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            event_type="stage_entered",
            summary="entered action via planning bridge",
        )
        lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage="action")
        action_output = bridged_action.action
        output_validation = validate_stage_output(stage="action", output=action_output, flow_scope=scope)
        if not output_validation.valid:
            return finish_with_validation_failure(
                lifecycle=lifecycle,
                outputs=outputs,
                events=events,
                flow_family=flow_family,
                scope=scope,
                stage="action",
                validation=output_validation,
            )

        outputs["action"] = action_output
        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            event_type="stage_exited",
            summary="exited action via planning bridge",
        )

        return continue_from_preserved_action(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            governance_handler=stage_handlers["governance"],
            action_output=action_output,
            continuation_prefix=(
                f"{continuation_prefix}Planning then continued through the existing plan-to-action bridge. "
                "Selection output remained non-authorizing until governance evaluated the formed action. "
            ),
            invoke_stage_handler=invoke_stage_handler,
            stage_summary=stage_summary,
            append_event=append_event,
            terminal_routing=terminal_routing,
            finish_with_validation_failure=finish_with_validation_failure,
            finish_with_routing=finish_with_routing,
            flow_result_factory=flow_result_factory,
        )

    handoff_validation = validate_handoff(
        previous_stage="selection",
        previous_output=selection_output,
        next_stage="action",
        flow_scope=scope,
    )
    if not handoff_validation.valid:
        return finish_with_validation_failure(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            validation=handoff_validation,
        )

    append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="action",
        event_type="stage_entered",
        summary=stage_summary(stage="action", phase="entered", handler=stage_handlers["action"]),
    )
    lifecycle = update_lifecycle(lifecycle, lifecycle_state="active", current_stage="action")
    try:
        action_output = invoke_stage_handler(
            stage="action",
            handler=stage_handlers["action"],
            previous_output=selection_output,
        )
    except Exception as exc:
        append_event(
            events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            event_type="flow_failed",
            summary=f"action handler failed: {exc}",
        )
        lifecycle = update_lifecycle(
            lifecycle,
            lifecycle_state="failed",
            current_stage="action",
            reason_summary=str(exc),
        )
        return flow_result_factory(lifecycle=lifecycle, outputs=outputs, events=tuple(events))

    output_validation = validate_stage_output(stage="action", output=action_output, flow_scope=scope)
    if not output_validation.valid:
        return finish_with_validation_failure(
            lifecycle=lifecycle,
            outputs=outputs,
            events=events,
            flow_family=flow_family,
            scope=scope,
            stage="action",
            validation=output_validation,
        )

    outputs["action"] = action_output
    append_event(
        events,
        flow_family=flow_family,
        scope=scope,
        stage="action",
        event_type="stage_exited",
        summary=stage_summary(stage="action", phase="exited", handler=stage_handlers["action"]),
    )

    return continue_from_preserved_action(
        lifecycle=lifecycle,
        outputs=outputs,
        events=events,
        flow_family=flow_family,
        scope=scope,
        governance_handler=stage_handlers["governance"],
        action_output=action_output,
        continuation_prefix=(
            f"{continuation_prefix}Continued post-selection routing then entered the existing action and governance "
            "path. Selection output remained non-authorizing until governance evaluated the formed action. "
        ),
        invoke_stage_handler=invoke_stage_handler,
        stage_summary=stage_summary,
        append_event=append_event,
        terminal_routing=terminal_routing,
        finish_with_validation_failure=finish_with_validation_failure,
        finish_with_routing=finish_with_routing,
        flow_result_factory=flow_result_factory,
    )
