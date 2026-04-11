from jeff.action import GovernedExecutionRequest, normalize_outcome
from jeff.action.execution import ExecutionResult
from jeff.cognitive import PlanArtifact, ProposalOption, ProposalSet, SelectionResult, assemble_context_package, evaluate_outcome
from jeff.cognitive.types import PlanStep, TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, TransitionResult, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate
from jeff.orchestrator import run_flow, stage_order_for_flow, validate_stage_sequence


def _state_with_scope(scope: Scope):
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
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Ship orchestration"},
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
    return state


def _standard_stage_handlers(scope: Scope):
    state = _state_with_scope(scope)
    store = InMemoryMemoryStore()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive a bounded proposal-selection-action flow"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(context):
        return ProposalSet(
            scope=context.scope,
            options=(
                ProposalOption(
                    proposal_id="proposal-1",
                    proposal_type="direct_action",
                    option_summary="Apply the bounded orchestration slice",
                    scope=scope,
                    planning_needed=False,
                ),
            ),
            scarcity_reason="Only one bounded direct action path is honest here.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The direct bounded option is the only serious fit.",
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Apply the bounded orchestration slice",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    def execution_stage(governance):
        action = Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Apply the bounded orchestration slice",
            basis_state_version=3,
        )
        return ExecutionResult(
            governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
            execution_status="completed",
            output_summary="Execution completed cleanly",
        )

    def outcome_stage(execution):
        return normalize_outcome(
            execution_result=execution,
            outcome_state="complete",
            observed_completion_posture="completed as intended",
            target_effect_posture="target reached",
            artifact_posture="artifact not required",
            side_effect_posture="contained",
        )

    def evaluation_stage(outcome):
        return evaluate_outcome(
            objective_summary="Finish the bounded orchestration slice",
            outcome=outcome,
            evidence_quality_posture="strong",
        )

    def memory_stage(_evaluation):
        candidate = create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="operational",
            scope=scope,
            summary="Keep orchestration stage order explicit and fail-closed",
            remembered_points=("Stage sequencing should stop on malformed handoffs instead of guessing.",),
            why_it_matters="This preserves orchestration non-ownership and inspectability.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="evaluation",
                    ref_id="evaluation-1",
                    summary="Evaluation confirmed the bounded flow shape worked cleanly",
                ),
            ),
            support_quality="strong",
            stability="stable",
        )
        return write_memory_candidate(candidate=candidate, store=store)

    def transition_stage(_memory_write):
        return TransitionResult(
            transition_id="transition-final",
            transition_result="committed",
            state_before_version=3,
            state_after_version=4,
            state=state,
            changed_paths=("projects.project-1.work_units.wu-1.runs.run-1",),
        )

    return {
        "context": context_stage,
        "proposal": proposal_stage,
        "selection": selection_stage,
        "action": action_stage,
        "governance": governance_stage,
        "execution": execution_stage,
        "outcome": outcome_stage,
        "evaluation": evaluation_stage,
        "memory": memory_stage,
        "transition": transition_stage,
    }


def test_flow_family_stage_orders_are_explicit() -> None:
    stages = stage_order_for_flow("bounded_proposal_selection_action")

    assert stages == (
        "context",
        "proposal",
        "selection",
        "action",
        "governance",
        "execution",
        "outcome",
        "evaluation",
        "memory",
        "transition",
    )
    assert validate_stage_sequence(
        flow_family="bounded_proposal_selection_action",
        stages=stages,
    ).valid is True


def test_impossible_stage_order_fails_validation() -> None:
    result = validate_stage_sequence(
        flow_family="bounded_proposal_selection_action",
        stages=("context", "action", "selection"),
    )

    assert result.valid is False
    assert result.code == "illegal_stage_order"


def test_lawful_stage_order_runs_to_transition_completion() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    result = run_flow(
        flow_id="flow-1",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        stage_handlers=_standard_stage_handlers(scope),
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.routing_decision is None
    assert tuple(result.outputs.keys()) == stage_order_for_flow("bounded_proposal_selection_action")
    assert [event.stage for event in result.events if event.event_type == "stage_entered"] == list(
        stage_order_for_flow("bounded_proposal_selection_action")
    )


def test_conditional_planning_flow_runs_with_explicit_planning_stage() -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    state = _state_with_scope(scope)
    store = InMemoryMemoryStore()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Run the planning insertion path"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        return ProposalSet(
            scope=scope,
            options=(
                ProposalOption(
                    proposal_id="proposal-1",
                    proposal_type="planning_insertion",
                    option_summary="Take the explicit planned path",
                    scope=scope,
                    planning_needed=True,
                ),
            ),
            scarcity_reason="Only the planned bounded path is honest here.",
        )

    def selection_stage(proposal_set):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_set.options),
            selected_proposal_id="proposal-1",
            rationale="The work is multi-step enough to justify planning.",
        )

    def planning_stage(_selection):
        return PlanArtifact(
            bounded_objective="Take the explicit planned path",
            intended_steps=(
                PlanStep(summary="Review scope and checkpoints", review_required=True),
                PlanStep(summary="Execute the bounded implementation"),
            ),
            selected_proposal_id="proposal-1",
        )

    def action_stage(_plan):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Execute the planned bounded path",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    def execution_stage(governance):
        action = Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Execute the planned bounded path",
            basis_state_version=3,
        )
        return ExecutionResult(
            governed_request=GovernedExecutionRequest(action=action, governance_decision=governance),
            execution_status="completed",
            output_summary="Execution completed",
        )

    def outcome_stage(execution):
        return normalize_outcome(
            execution_result=execution,
            outcome_state="complete",
            observed_completion_posture="planned execution completed",
            target_effect_posture="target reached",
            artifact_posture="artifact not required",
            side_effect_posture="contained",
        )

    def evaluation_stage(outcome):
        return evaluate_outcome(
            objective_summary="Finish the planned bounded path",
            outcome=outcome,
            evidence_quality_posture="strong",
        )

    def memory_stage(_evaluation):
        candidate = create_memory_candidate(
            candidate_id="candidate-2",
            memory_type="operational",
            scope=scope,
            summary="Planning should remain conditional in orchestration",
            remembered_points=("The planning stage appears only in the dedicated flow family.",),
            why_it_matters="This keeps planning from becoming universal workflow truth.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="evaluation",
                    ref_id="evaluation-2",
                    summary="Evaluation confirmed the planned path stayed bounded",
                ),
            ),
            support_quality="strong",
            stability="stable",
        )
        return write_memory_candidate(candidate=candidate, store=store)

    def transition_stage(_memory_write):
        return TransitionResult(
            transition_id="transition-final-2",
            transition_result="committed",
            state_before_version=3,
            state_after_version=4,
            state=state,
            changed_paths=("projects.project-1.work_units.wu-1.runs.run-1",),
        )

    result = run_flow(
        flow_id="flow-2",
        flow_family="conditional_planning_insertion",
        scope=scope,
        stage_handlers={
            "context": context_stage,
            "proposal": proposal_stage,
            "selection": selection_stage,
            "planning": planning_stage,
            "action": action_stage,
            "governance": governance_stage,
            "execution": execution_stage,
            "outcome": outcome_stage,
            "evaluation": evaluation_stage,
            "memory": memory_stage,
            "transition": transition_stage,
        },
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert [event.stage for event in result.events if event.event_type == "stage_entered"] == list(
        stage_order_for_flow("conditional_planning_insertion")
    )
