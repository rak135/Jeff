from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ProposalOption, ProposalSet, SelectionResult, evaluate_outcome
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, TransitionResult, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.interface.commands import InterfaceContext
from jeff.orchestrator.lifecycle import FlowLifecycle
from jeff.orchestrator.routing import RoutingDecision
from jeff.orchestrator.runner import FlowRunResult
from jeff.orchestrator.trace import OrchestrationEvent


def build_state_with_run() -> tuple[object, Scope]:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "CLI coverage"},
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


def build_flow_run(
    scope: Scope,
    *,
    flow_family: str = "bounded_proposal_selection_action",
    lifecycle_state: str = "completed",
    current_stage: str = "evaluation",
    approval_required: bool = False,
    approval_granted: bool = False,
    execution_status: str = "completed",
    outcome_state: str = "complete",
    target_effect_posture: str = "target reached",
    evidence_quality_posture: str = "strong",
    transition_result: str | None = None,
    routed_outcome: str | None = None,
    route_kind: str = "hold",
    route_reason: str = "operator follow-up is required",
    reason_summary: str | None = None,
    selected_proposal_id: str = "proposal-1",
) -> FlowRunResult:
    proposal_set = ProposalSet(
        scope=scope,
        options=(
            ProposalOption(
                proposal_id=selected_proposal_id,
                proposal_type="direct_action",
                option_summary="Bounded CLI-visible action",
                scope=scope,
            ),
        ),
        scarcity_reason="Only one serious bounded option is available.",
    )
    selection = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
        selected_proposal_id=selected_proposal_id,
        rationale="One bounded option remains under review.",
    )
    action = Action(
        action_id="action-1",
        scope=scope,
        intent_summary="Drive the bounded flow",
        basis_state_version=3,
    )
    policy = Policy(approval_required=approval_required)
    approval = None
    if approval_required and approval_granted:
        approval = Approval.granted_for(
            action_id=str(action.action_id),
            action_binding_key=action.binding_key,
            basis_state_version=3,
        )
    governance = evaluate_action_entry(
        action=action,
        policy=policy,
        approval=approval,
        truth=CurrentTruthSnapshot(scope=scope, state_version=3),
    )
    outputs: dict[str, object] = {
        "selection": selection,
        "governance": governance,
    }

    if governance.allowed_now:
        execution = ExecutionResult(
            governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
            execution_status=execution_status,
            output_summary="Execution reached its operational endpoint.",
        )
        outcome = normalize_outcome(
            execution_result=execution,
            outcome_state=outcome_state,
            observed_completion_posture=f"execution {execution_status}",
            target_effect_posture=target_effect_posture,
            artifact_posture="artifact present",
            side_effect_posture="contained",
        )
        evaluation = evaluate_outcome(
            objective_summary="Drive the bounded flow",
            outcome=outcome,
            evidence_quality_posture=evidence_quality_posture,
        )
        outputs["execution"] = execution
        outputs["outcome"] = outcome
        outputs["evaluation"] = evaluation

    if transition_result is not None:
        outputs["transition"] = TransitionResult(
            transition_id="transition-final",
            transition_result=transition_result,
            state_before_version=3,
            state_after_version=4 if transition_result == "committed" else 3,
            state=build_state_with_run()[0],
            changed_paths=("projects.project-1.work_units.wu-1.runs.run-1",),
        )

    routing = None
    if routed_outcome is not None:
        routing = RoutingDecision(
            route_kind=route_kind,
            routed_outcome=routed_outcome,
            scope=scope,
            source_stage=current_stage,
            reason_summary=route_reason,
        )

    lifecycle = FlowLifecycle(
        flow_id="flow-1",
        flow_family=flow_family,
        scope=scope,
        lifecycle_state=lifecycle_state,
        current_stage=current_stage,
        reason_summary=reason_summary,
    )
    events = (
        OrchestrationEvent(
            ordinal=1,
            flow_family=flow_family,
            scope=scope,
            stage=None,
            event_type="flow_started",
            summary="flow started",
            emitted_at="2026-04-11T09:00:00+00:00",
        ),
        OrchestrationEvent(
            ordinal=2,
            flow_family=flow_family,
            scope=scope,
            stage="context",
            event_type="stage_entered",
            summary="entered context",
            emitted_at="2026-04-11T09:00:01+00:00",
        ),
        OrchestrationEvent(
            ordinal=3,
            flow_family=flow_family,
            scope=scope,
            stage="proposal",
            event_type="stage_entered",
            summary="entered proposal",
            emitted_at="2026-04-11T09:00:02+00:00",
        ),
        OrchestrationEvent(
            ordinal=4,
            flow_family=flow_family,
            scope=scope,
            stage="selection",
            event_type="stage_exited",
            summary="exited selection",
            emitted_at="2026-04-11T09:00:03+00:00",
        ),
        OrchestrationEvent(
            ordinal=5,
            flow_family=flow_family,
            scope=scope,
            stage=current_stage,
            event_type="stage_entered",
            summary=f"entered {current_stage}",
            emitted_at="2026-04-11T09:00:04+00:00",
        ),
    )
    return FlowRunResult(
        lifecycle=lifecycle,
        outputs=outputs,
        events=events,
        routing_decision=routing,
    )


def build_interface_context(*, flow_run: FlowRunResult | None = None) -> tuple[InterfaceContext, Scope]:
    state, scope = build_state_with_run()
    context = InterfaceContext(
        state=state,
        flow_runs={} if flow_run is None else {str(scope.run_id): flow_run},
    )
    return context, scope


def build_interface_context_with_flow(**flow_kwargs: object) -> tuple[InterfaceContext, Scope]:
    state, scope = build_state_with_run()
    flow_run = build_flow_run(scope, **flow_kwargs)
    context = InterfaceContext(
        state=state,
        flow_runs={str(scope.run_id): flow_run},
    )
    return context, scope
