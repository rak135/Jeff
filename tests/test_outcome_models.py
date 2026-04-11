import pytest

from jeff.action.execution import ExecutionResult, GovernedExecutionRequest
from jeff.action.outcome import normalize_outcome
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry


def _execution_result() -> ExecutionResult:
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
    return ExecutionResult(
        governed_request=GovernedExecutionRequest(action=action, governance_decision=decision),
        execution_status="completed",
        output_summary="Execution completed",
    )


def test_outcome_requires_explicit_normalization_step() -> None:
    result = _execution_result()
    assert not hasattr(result, "outcome_state")

    outcome = normalize_outcome(
        execution_result=result,
        outcome_state="complete",
        observed_completion_posture="execution completed cleanly",
        target_effect_posture="target changed as intended",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )

    assert outcome.outcome_state == "complete"


def test_outcome_does_not_carry_evaluation_verdict_fields() -> None:
    outcome = normalize_outcome(
        execution_result=_execution_result(),
        outcome_state="inconclusive",
        observed_completion_posture="execution finished with gaps",
        target_effect_posture="target effect uncertain",
        artifact_posture="artifact missing",
        side_effect_posture="unknown",
        uncertainty_markers=("verification missing",),
    )

    assert not hasattr(outcome, "evaluation_verdict")

    with pytest.raises(ValueError, match="mismatch markers"):
        normalize_outcome(
            execution_result=_execution_result(),
            outcome_state="mismatch_affected",
            observed_completion_posture="result hit mismatch",
            target_effect_posture="uncertain",
            artifact_posture="artifact present",
            side_effect_posture="unknown",
        )
