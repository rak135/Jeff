from jeff.action import Outcome
from jeff.cognitive import EvaluationResult, ResearchRequest, ResearchResult, SelectionResult, assemble_context_package
from jeff.cognitive.types import Recommendation, SourceSummary, TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.memory import MemorySupportRef, create_memory_candidate
from jeff.orchestrator import run_flow, validate_handoff, validate_stage_output


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")


def _state():
    scope = _scope()
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


def _action() -> Action:
    return Action(
        action_id="action-1",
        scope=_scope(),
        intent_summary="Execute the bounded orchestrator action",
        basis_state_version=3,
    )


def _selection() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1",),
        selected_proposal_id="proposal-1",
        rationale="This is the chosen bounded path.",
    )


def _evaluation() -> EvaluationResult:
    return EvaluationResult(
        objective_summary="Finish the bounded objective",
        outcome=Outcome(
            action_id="action-1",
            scope=_scope(),
            outcome_state="inconclusive",
            observed_completion_posture="evidence missing",
            target_effect_posture="unknown",
            artifact_posture="missing verification",
            side_effect_posture="contained",
            uncertainty_markers=("verification missing",),
        ),
        evaluation_verdict="inconclusive",
        rationale="Evidence is insufficient and requires clarification before any follow-up.",
        recommended_next_step="request_clarification",
    )


def test_execution_without_governance_is_rejected() -> None:
    result = validate_handoff(
        previous_stage="action",
        previous_output=_action(),
        next_stage="execution",
        flow_scope=_scope(),
    )

    assert result.valid is False
    assert result.code == "impossible_handoff"


def test_selection_output_cannot_be_treated_as_permission() -> None:
    result = validate_handoff(
        previous_stage="selection",
        previous_output=_selection(),
        next_stage="execution",
        flow_scope=_scope(),
    )

    assert result.valid is False
    assert result.code == "impossible_handoff"


def test_evaluation_recommendation_cannot_be_treated_as_permission() -> None:
    result = validate_handoff(
        previous_stage="evaluation",
        previous_output=_evaluation(),
        next_stage="execution",
        flow_scope=_scope(),
    )

    assert result.valid is False
    assert result.code == "impossible_handoff"


def test_non_memory_candidate_is_not_a_valid_memory_stage_output() -> None:
    candidate = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="operational",
        scope=_scope(),
        summary="This candidate should not count as committed memory stage output",
        remembered_points=("Only MemoryWriteDecision can leave the memory stage.",),
        why_it_matters="The orchestrator must not accept raw candidates as committed output.",
        support_refs=(
            MemorySupportRef(
                ref_kind="evaluation",
                ref_id="evaluation-1",
                summary="Evaluation provided bounded support",
            ),
        ),
        support_quality="strong",
        stability="stable",
    )

    result = validate_stage_output(stage="memory", output=candidate, flow_scope=_scope())

    assert result.valid is False
    assert result.code == "wrong_stage_output_type"


def test_malformed_handoff_invalidates_instead_of_getting_patched() -> None:
    scope = _scope()
    state = _state()

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Drive a malformed flow"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        return ResearchResult(
            request=ResearchRequest(
                objective="Wrong object family",
                scope=scope,
                research_mode="decision_support",
            ),
            sources=(
                SourceSummary(
                    source_id="source-1",
                    source_family="research",
                    scope=scope,
                    summary="This is intentionally the wrong stage output.",
                ),
            ),
            findings=(),
            recommendation=Recommendation(summary="Do not treat research as proposal output here."),
        )

    result = run_flow(
        flow_id="flow-invalid",
        flow_family="bounded_proposal_selection_action",
        scope=scope,
        stage_handlers={
            "context": context_stage,
            "proposal": proposal_stage,
            "selection": lambda _proposal: _selection(),
            "action": lambda _selection: _action(),
            "governance": lambda action: evaluate_action_entry(
                action=action,
                policy=Policy(),
                approval=None,
                truth=CurrentTruthSnapshot(scope=scope, state_version=3),
            ),
            "execution": lambda _governance: None,
            "outcome": lambda _execution: None,
            "evaluation": lambda _outcome: _evaluation(),
            "memory": lambda _evaluation: None,
            "transition": lambda _memory: None,
        },
    )

    assert result.lifecycle.lifecycle_state == "invalidated"
    assert result.routing_decision is not None
    assert result.routing_decision.routed_outcome == "invalidated"
    assert any(event.event_type == "validation_failed" for event in result.events)
