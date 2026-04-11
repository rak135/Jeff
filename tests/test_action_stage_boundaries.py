from jeff.action.execution import ExecutionResult, GovernedExecutionRequest
from jeff.action.outcome import normalize_outcome
from jeff.cognitive.evaluation import evaluate_outcome
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


def test_execution_completion_does_not_imply_objective_completion() -> None:
    outcome = normalize_outcome(
        execution_result=_execution_result(),
        outcome_state="partial",
        observed_completion_posture="execution completed but target only moved partially",
        target_effect_posture="partial target effect",
        artifact_posture="artifact present",
        side_effect_posture="contained",
    )
    evaluation = evaluate_outcome(
        objective_summary="Finish the bounded objective",
        outcome=outcome,
        evidence_quality_posture="strong",
    )

    assert evaluation.evaluation_verdict == "partial"
    assert evaluation.recommended_next_step == "continue"
