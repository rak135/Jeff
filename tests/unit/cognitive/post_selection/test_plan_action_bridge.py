import pytest

from jeff.cognitive import PlanArtifact
from jeff.cognitive.post_selection.plan_action_bridge import (
    PlanActionBridgeError,
    PlanActionBridgeRequest,
    bridge_plan_to_action,
)
from jeff.cognitive.types import PlanStep
from jeff.core.schemas import Scope


def test_single_bounded_non_review_step_forms_action() -> None:
    result = bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id="plan-bridge-1",
            plan_artifact=_single_step_plan(),
            scope=_scope(),
            basis_state_version=3,
        )
    )

    assert result.action_formed is True
    assert result.action is not None
    assert result.action.intent_summary == "Apply the bounded implementation"
    assert result.action.target_summary == "Ship the bounded change"
    assert result.action.scope == _scope()
    assert result.action.basis_state_version == 3
    assert result.plan_selected_proposal_id == "proposal-1"


def test_single_review_required_step_does_not_form_action() -> None:
    result = bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id="plan-bridge-2",
            plan_artifact=PlanArtifact(
                bounded_objective="Ship the bounded change",
                intended_steps=(PlanStep(summary="Review the bounded implementation", review_required=True),),
                selected_proposal_id="proposal-1",
            ),
            scope=_scope(),
        )
    )

    assert result.action_formed is False
    assert result.action is None
    assert "review-only" in result.no_action_reason


def test_missing_plan_output_fails_closed() -> None:
    with pytest.raises(TypeError, match="plan_artifact must be a PlanArtifact"):
        PlanActionBridgeRequest(
            request_id="plan-bridge-3",
            plan_artifact=None,  # type: ignore[arg-type]
            scope=_scope(),
        )


def test_blank_request_id_raises_typed_bridge_error() -> None:
    with pytest.raises(PlanActionBridgeError) as exc_info:
        bridge_plan_to_action(
            PlanActionBridgeRequest(
                request_id="   ",
                plan_artifact=_single_step_plan(),
                scope=_scope(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("invalid_request_id",)


def test_multi_step_plan_does_not_guess_action() -> None:
    result = bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id="plan-bridge-4",
            plan_artifact=PlanArtifact(
                bounded_objective="Ship the bounded change",
                intended_steps=(
                    PlanStep(summary="Prepare the bounded change"),
                    PlanStep(summary="Apply the bounded implementation"),
                ),
                selected_proposal_id="proposal-1",
            ),
            scope=_scope(),
        )
    )

    assert result.action_formed is False
    assert result.action is None
    assert "must not guess a single executable next action" in result.no_action_reason


def test_action_basis_summary_maps_cleanly_to_action_intent_summary() -> None:
    result = bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id="plan-bridge-5",
            plan_artifact=_single_step_plan(),
            scope=_scope(),
        )
    )

    assert result.action_basis_summary == "Apply the bounded implementation"
    assert result.action is not None
    assert result.action.intent_summary == result.action_basis_summary


def test_missing_selected_proposal_linkage_returns_no_action_without_guessing() -> None:
    result = bridge_plan_to_action(
        PlanActionBridgeRequest(
            request_id="plan-bridge-6",
            plan_artifact=PlanArtifact(
                bounded_objective="Ship the bounded change",
                intended_steps=(PlanStep(summary="Apply the bounded implementation"),),
            ),
            scope=_scope(),
        )
    )

    assert result.action_formed is False
    assert result.action is None
    assert "selected proposal linkage" in result.no_action_reason


def test_mutated_empty_intended_steps_raise_typed_bridge_error() -> None:
    plan = _single_step_plan()
    object.__setattr__(plan, "intended_steps", ())

    with pytest.raises(PlanActionBridgeError) as exc_info:
        bridge_plan_to_action(
            PlanActionBridgeRequest(
                request_id="plan-bridge-7",
                plan_artifact=plan,
                scope=_scope(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_intended_steps",)


def _single_step_plan() -> PlanArtifact:
    return PlanArtifact(
        bounded_objective="Ship the bounded change",
        intended_steps=(PlanStep(summary="Apply the bounded implementation"),),
        selected_proposal_id="proposal-1",
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
