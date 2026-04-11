"""Explicit bootstrap helpers for the current operator-ready demo context."""

from __future__ import annotations

from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ProposalOption, ProposalSet, SelectionResult, evaluate_outcome
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import GlobalState, bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.infrastructure import (
    InfrastructureServices,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.interface.commands import InterfaceContext
from jeff.orchestrator.lifecycle import FlowLifecycle
from jeff.orchestrator.runner import FlowRunResult
from jeff.orchestrator.trace import OrchestrationEvent


def build_infrastructure_runtime(
    config: ModelAdapterRuntimeConfig,
) -> InfrastructureServices:
    return build_infrastructure_services(config)


def build_demo_interface_context() -> InterfaceContext:
    state, scope = build_demo_state()
    flow_run = build_demo_flow_run(scope)
    return InterfaceContext(
        state=state,
        flow_runs={str(scope.run_id): flow_run},
    )


def build_demo_state() -> tuple[GlobalState, Scope]:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Jeff Demo Project"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={
                "work_unit_id": str(scope.work_unit_id),
                "objective": "Inspect the current Jeff v1 backbone through the CLI.",
            },
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=str(scope.project_id), work_unit_id=str(scope.work_unit_id)),
            payload={"run_id": str(scope.run_id)},
        ),
    ).state
    return state, scope


def build_demo_flow_run(scope: Scope) -> FlowRunResult:
    proposal_set = ProposalSet(
        scope=scope,
        options=(
            ProposalOption(
                proposal_id="proposal-1",
                proposal_type="direct_action",
                option_summary="Inspect the bounded Jeff demo flow.",
                scope=scope,
            ),
        ),
        scarcity_reason="Only one serious bounded demo option is available.",
    )
    selection = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
        selected_proposal_id="proposal-1",
        rationale="The bounded operator-inspection path is the active demo selection.",
    )
    action = Action(
        action_id="action-1",
        scope=scope,
        intent_summary="Render one truthful demo flow for operator inspection.",
        basis_state_version=3,
    )
    governance = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=Approval.not_required(),
        truth=CurrentTruthSnapshot(scope=scope, state_version=3),
    )
    execution = ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
        execution_status="completed",
        output_summary="Demo execution reached its bounded operational endpoint.",
    )
    outcome = normalize_outcome(
        execution_result=execution,
        outcome_state="complete",
        observed_completion_posture="execution completed",
        target_effect_posture="target reached",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Expose one bounded demo flow for operator inspection",
        outcome=outcome,
        evidence_quality_posture="strong",
    )
    lifecycle = FlowLifecycle(
        flow_id="flow-demo-1",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        lifecycle_state="completed",
        current_stage="evaluation",
        reason_summary="demo bootstrap flow completed",
    )
    events = (
        OrchestrationEvent(
            ordinal=1,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage=None,
            event_type="flow_started",
            summary="demo flow started",
            emitted_at="2026-04-11T09:00:00+00:00",
        ),
        OrchestrationEvent(
            ordinal=2,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="context",
            event_type="stage_entered",
            summary="entered context",
            emitted_at="2026-04-11T09:00:01+00:00",
        ),
        OrchestrationEvent(
            ordinal=3,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="proposal",
            event_type="stage_entered",
            summary="entered proposal",
            emitted_at="2026-04-11T09:00:02+00:00",
        ),
        OrchestrationEvent(
            ordinal=4,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="selection",
            event_type="stage_exited",
            summary="exited selection",
            emitted_at="2026-04-11T09:00:03+00:00",
        ),
        OrchestrationEvent(
            ordinal=5,
            flow_family="bounded_proposal_selection_action",
            scope=scope,
            stage="evaluation",
            event_type="flow_completed",
            summary="demo flow completed",
            emitted_at="2026-04-11T09:00:04+00:00",
        ),
    )
    return FlowRunResult(
        lifecycle=lifecycle,
        outputs={
            "selection": selection,
            "governance": governance,
            "execution": execution,
            "outcome": outcome,
            "evaluation": evaluation,
        },
        events=events,
    )


def run_startup_preflight() -> tuple[str, ...]:
    context = build_demo_interface_context()
    checks = [
        "package imports resolved",
        "demo interface context bootstrapped",
        f"demo project scope ready: {next(iter(context.state.projects.keys()))}",
        "CLI entry surface is available through jeff.interface.JeffCLI",
    ]
    return tuple(checks)
