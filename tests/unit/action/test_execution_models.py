import pytest
import sys

from jeff.action.execution import ExecutionResult, GovernedExecutionRequest, RepoLocalValidationPlan, execute_governed_action
from jeff.action.types import SupportRef
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry


def _action() -> Action:
    return Action(
        action_id="action-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        intent_summary="Apply a bounded code edit",
        target_summary="repo:jeff",
        protected_surface="core backbone",
        basis_state_version=3,
    )


def _allowed_decision():
    action = _action()
    return action, evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=None,
        truth=CurrentTruthSnapshot(
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            state_version=3,
        ),
    )


def test_execution_requires_governance_pass_for_lawful_start() -> None:
    action, decision = _allowed_decision()
    request = GovernedExecutionRequest(action=action, governance_decision=decision)

    result = ExecutionResult(
        governed_request=request,
        execution_status="completed",
        output_summary="Tool call finished",
        artifact_refs=(
            SupportRef(
                ref_type="artifact",
                ref_id="artifact-1",
                scope=action.scope,
                summary="Generated patch",
            ),
        ),
    )

    assert result.action_id == "action-1"
    assert result.scope.project_id == "project-1"


def test_execution_rejects_ungoverned_or_blocked_start() -> None:
    action = _action()
    with pytest.raises(TypeError, match="ActionEntryDecision governance pass"):
        GovernedExecutionRequest(action=action, governance_decision=action)  # type: ignore[arg-type]

    blocked_decision = evaluate_action_entry(
        action=action,
        policy=Policy(),
        approval=None,
        truth=CurrentTruthSnapshot(
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            state_version=3,
            blocked_reasons=("target unavailable",),
        ),
    )
    with pytest.raises(ValueError, match="allowed_now"):
        GovernedExecutionRequest(action=action, governance_decision=blocked_decision)


def test_execution_rejects_mismatched_governed_action() -> None:
    action, decision = _allowed_decision()
    changed_action = Action(
        action_id="action-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        intent_summary="Apply a materially different code edit",
        target_summary="repo:jeff",
        protected_surface="core backbone",
        basis_state_version=3,
    )

    with pytest.raises(ValueError, match="exact bounded action"):
        GovernedExecutionRequest(action=changed_action, governance_decision=decision)


def test_execute_governed_action_runs_repo_local_validation_plan_and_captures_evidence(tmp_path) -> None:
    action, decision = _allowed_decision()

    plan = RepoLocalValidationPlan(
        command_id="validation-smoke",
        argv=(sys.executable, "-c", "print('validation ok')"),
        working_directory=str(tmp_path),
        description="Run a bounded validation probe.",
        timeout_seconds=30,
    )

    result = execute_governed_action(
        GovernedExecutionRequest(action=action, governance_decision=decision),
        execution_plan=plan,
    )

    assert result.execution_status == "completed"
    assert result.execution_family == "repo_local_validation"
    assert result.execution_command_id == "validation-smoke"
    assert result.exit_code == 0
    assert result.working_directory == str(tmp_path)
    assert "validation ok" in (result.stdout_excerpt or "")
    assert "-c" in (result.executed_command or "")
