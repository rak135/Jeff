import pytest

from jeff.action.execution import ExecutionResult, GovernedExecutionRequest
from jeff.action.outcome import normalize_outcome
from jeff.action.types import SupportRef
from jeff.cognitive.evaluation import evaluate_outcome
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry, may_start_now


def _execution_result(*, with_artifact: bool = False) -> ExecutionResult:
    action = Action(
        action_id="action-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        intent_summary="Apply a bounded code edit",
        basis_state_version=3,
    )
    decision = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=None,
        truth=CurrentTruthSnapshot(
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            state_version=3,
        ),
    )
    artifact_refs = ()
    if with_artifact:
        artifact_refs = (
            SupportRef(
                ref_type="artifact",
                ref_id="artifact-1",
                scope=action.scope,
                summary="Generated patch",
            ),
        )
    return ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=decision),
        execution_status="completed",
        output_summary="Execution completed",
        artifact_refs=artifact_refs,
    )


def test_evaluation_requires_normalized_outcome() -> None:
    with pytest.raises(TypeError, match="normalized Outcome"):
        evaluate_outcome(
            objective_summary="Finish the bounded objective",
            outcome=_execution_result(),  # type: ignore[arg-type]
            evidence_quality_posture="strong",
        )


def test_deterministic_override_blocks_optimistic_verdict() -> None:
    outcome = normalize_outcome(
        execution_result=_execution_result(),
        outcome_state="complete",
        observed_completion_posture="execution completed",
        target_effect_posture="target effect observed",
        artifact_posture="required artifact missing",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Finish the bounded objective",
        outcome=outcome,
        evidence_quality_posture="strong",
        required_artifacts_present=False,
    )

    assert evaluation.evaluation_verdict == "blocked"
    assert evaluation.recommended_next_step == "revalidate"
    assert "required artifact missing" in evaluation.deterministic_override_reasons


def test_artifact_existence_alone_does_not_imply_success() -> None:
    outcome = normalize_outcome(
        execution_result=_execution_result(with_artifact=True),
        outcome_state="complete",
        observed_completion_posture="execution completed",
        target_effect_posture="artifact exists but target result is still uncertain",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Finish the bounded objective",
        outcome=outcome,
        evidence_quality_posture="strong",
        mandatory_target_reached=False,
    )

    assert evaluation.evaluation_verdict == "partial"
    assert evaluation.recommended_next_step == "terminate_and_replan"


def test_evaluation_recommendation_is_not_permission() -> None:
    outcome = normalize_outcome(
        execution_result=_execution_result(),
        outcome_state="failed",
        observed_completion_posture="execution failed",
        target_effect_posture="target unchanged",
        artifact_posture="artifact missing",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Finish the bounded objective",
        outcome=outcome,
        evidence_quality_posture="weak",
    )

    with pytest.raises(TypeError, match="ActionEntryDecision"):
        may_start_now(evaluation)  # type: ignore[arg-type]
