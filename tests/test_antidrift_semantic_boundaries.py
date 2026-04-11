import json

import pytest

from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import ProposalOption, ProposalSet
from jeff.cognitive.evaluation import evaluate_outcome
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import GlobalState, bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.interface import JeffCLI
from jeff.memory import (
    InMemoryMemoryStore,
    MemoryCandidate,
    MemoryRetrievalRequest,
    MemorySupportRef,
    build_truth_first_memory_view,
    create_memory_candidate,
    retrieve_memory,
    write_memory_candidate,
)
from jeff.orchestrator import run_flow

from tests.cli_test_helpers import build_interface_context_with_flow


def _state_with_two_projects() -> GlobalState:
    state = bootstrap_global_state()
    for project_id, name in (("project-1", "Alpha"), ("project-2", "Beta")):
        state = apply_transition(
            state,
            TransitionRequest(
                transition_id=f"transition-{project_id}",
                transition_type="create_project",
                basis_state_version=state.state_meta.state_version,
                scope=Scope(project_id=project_id),
                payload={"name": name},
            ),
        ).state
    return state


def _state_with_run() -> GlobalState:
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Backbone hardening"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    ).state
    return state


def _action(scope: Scope, *, basis_state_version: int) -> Action:
    return Action(
        action_id="action-1",
        scope=scope,
        intent_summary="Apply the bounded hardening slice",
        basis_state_version=basis_state_version,
    )


def _support_ref() -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="evaluation",
        ref_id="evaluation-1",
        summary="Evaluation provided bounded support.",
    )


def test_global_state_remains_one_root_with_nested_projects() -> None:
    state = _state_with_two_projects()

    assert isinstance(state, GlobalState)
    assert state.state_meta.state_version == 2
    assert tuple(state.projects.keys()) == ("project-1", "project-2")
    assert state.projects["project-1"].project_id == "project-1"
    assert state.projects["project-2"].project_id == "project-2"


def test_run_belongs_to_exactly_one_work_unit_and_one_project() -> None:
    state = _state_with_run()
    run = state.projects["project-1"].work_units["wu-1"].runs["run-1"]

    assert run.project_id == "project-1"
    assert run.work_unit_id == "wu-1"
    assert "run-1" not in state.projects["project-1"].work_units["wu-1"].runs.get("run-2", ())


def test_transition_only_changes_truth_and_downstream_objects_do_not() -> None:
    state = _state_with_run()
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    action = _action(scope, basis_state_version=state.state_meta.state_version)
    decision = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=None,
        truth=CurrentTruthSnapshot(scope=scope, state_version=state.state_meta.state_version),
    )
    execution = ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=decision),
        execution_status="completed",
        output_summary="Execution completed cleanly.",
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
        objective_summary="Finish the bounded hardening slice",
        outcome=outcome,
        evidence_quality_posture="strong",
    )

    assert state.state_meta.state_version == 3
    assert state.projects["project-1"].work_units["wu-1"].runs["run-1"].run_lifecycle_state == "created"
    assert evaluation.evaluation_verdict == "acceptable"


def test_approval_and_readiness_remain_distinct_after_approval_is_granted() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    action = _action(scope, basis_state_version=3)
    approval = Approval.granted_for(
        action_id=str(action.action_id),
        action_binding_key=action.binding_key,
        basis_state_version=3,
    )

    decision = evaluate_action_entry(
        action=action,
        policy=Policy(approval_required=True),
        approval=approval,
        truth=CurrentTruthSnapshot(
            scope=scope,
            state_version=3,
            requires_revalidation=True,
        ),
    )

    assert decision.approval_verdict == "granted"
    assert decision.readiness.readiness_state == "pending_revalidation"
    assert decision.governance_outcome == "deferred_pending_revalidation"
    assert decision.allowed_now is False


def test_execution_outcome_and_evaluation_remain_distinct() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    action = _action(scope, basis_state_version=3)
    decision = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=None,
        truth=CurrentTruthSnapshot(scope=scope, state_version=3),
    )
    execution = ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=decision),
        execution_status="completed",
        output_summary="Execution completed without proving full objective completion.",
    )
    outcome = normalize_outcome(
        execution_result=execution,
        outcome_state="partial",
        observed_completion_posture="execution completed",
        target_effect_posture="target moved partially",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Finish the backbone hardening slice",
        outcome=outcome,
        evidence_quality_posture="strong",
    )

    assert not hasattr(execution, "outcome_state")
    assert not hasattr(outcome, "evaluation_verdict")
    assert execution.execution_status == "completed"
    assert outcome.outcome_state == "partial"
    assert evaluation.evaluation_verdict == "partial"


def test_only_memory_layer_creates_candidates_and_memory_stays_support_only() -> None:
    with pytest.raises(ValueError, match="must be created by jeff.memory.write_pipeline"):
        MemoryCandidate(
            candidate_id="candidate-1",
            memory_type="operational",
            scope=Scope(project_id="project-1"),
            summary="Direct construction should fail.",
            remembered_points=("Only Memory may author candidates.",),
            why_it_matters="Boundary hardening.",
            support_refs=(_support_ref(),),
            support_quality="strong",
            stability="stable",
        )

    store = InMemoryMemoryStore()
    decision = write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-2",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Current truth changed after an earlier run.",
            remembered_points=("This remains support only.",),
            why_it_matters="It explains continuity without becoming present truth.",
            support_refs=(_support_ref(),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )
    retrieval = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="current truth comparison",
            scope=Scope(project_id="project-1"),
        ),
        store=store,
    )
    view = build_truth_first_memory_view(
        current_truth_summary="Current truth says the run is still active.",
        retrieval_result=retrieval,
    )

    assert decision.write_outcome == "write"
    assert view.truth_wins is True
    assert "state wins for current-truth questions" in view.notes[-1]


def test_orchestrator_invalidates_instead_of_synthesizing_missing_outputs() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")

    result = run_flow(
        flow_id="flow-invalid",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        stage_handlers={
            "context": lambda _input: ProposalSet(  # type: ignore[return-value]
                scope=scope,
                options=(
                    ProposalOption(
                        proposal_id="proposal-1",
                        proposal_type="direct_action",
                        option_summary="Wrong output family for context.",
                        scope=scope,
                    ),
                ),
                scarcity_reason="Only one option is present.",
            ),
            "proposal": lambda _input: ProposalSet(
                scope=scope,
                options=(
                    ProposalOption(
                        proposal_id="proposal-1",
                        proposal_type="direct_action",
                        option_summary="Bounded action.",
                        scope=scope,
                    ),
                ),
                scarcity_reason="Only one option is present.",
            ),
            "selection": lambda _proposal: pytest.fail("selection should not run"),
            "action": lambda _selection: pytest.fail("action should not run"),
            "governance": lambda _action: pytest.fail("governance should not run"),
            "execution": lambda _governance: pytest.fail("execution should not run"),
            "outcome": lambda _execution: pytest.fail("outcome should not run"),
            "evaluation": lambda _outcome: pytest.fail("evaluation should not run"),
            "memory": lambda _evaluation: pytest.fail("memory should not run"),
            "transition": lambda _memory: pytest.fail("transition should not run"),
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert tuple(result.outputs.keys()) == ()
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"


def test_cli_views_keep_truth_derived_support_and_permission_distinctions() -> None:
    context, _ = build_interface_context_with_flow(
        flow_family="blocked_or_escalation",
        lifecycle_state="waiting",
        current_stage="governance",
        approval_required=True,
        approval_granted=False,
        routed_outcome="approval_required",
        route_reason="required approval is absent",
    )
    cli = JeffCLI(context=context)
    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/run use run-1")

    show_payload = json.loads(cli.run_one_shot("/show", json_output=True))
    receipt_payload = json.loads(cli.run_one_shot("/approve", json_output=True))

    assert "selected_proposal_id" not in show_payload["truth"]
    assert "routing_decision" not in show_payload["truth"]
    assert show_payload["derived"]["selected_proposal_id"] == "proposal-1"
    assert show_payload["derived"]["allowed_now"] is False
    assert show_payload["derived"]["approval_verdict"] == "absent"
    assert show_payload["support"]["routing_decision"]["routed_outcome"] == "approval_required"
    assert receipt_payload["derived"]["effect_state"] == "request_accepted"
    assert "does not imply apply, completion, or truth mutation" in receipt_payload["support"]["note"]
