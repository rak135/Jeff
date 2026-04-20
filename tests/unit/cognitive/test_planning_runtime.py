import pytest

from jeff.cognitive.planning import (
    PlanArtifact,
    PlanStep,
    apply_checkpoint_decision,
    create_plan,
    materialize_active_step_action,
    resume_posture,
)
from jeff.cognitive.proposal import ProposalResultOption
from jeff.core.schemas import Scope


def test_invalid_plan_rejects_multiple_active_steps() -> None:
    with pytest.raises(ValueError, match="at most one active step"):
        PlanArtifact(
            bounded_objective="Ship the bounded change",
            intended_steps=(
                PlanStep(summary="Review bounded scope", step_status="active"),
                PlanStep(summary="Apply bounded change", step_status="active"),
            ),
            selected_proposal_id="proposal-1",
        )


def test_checkpoint_continue_advances_to_next_step() -> None:
    plan = create_plan(
        selected_option=_selected_option(),
        multi_step=True,
        review_heavy=True,
        time_spanning=True,
    )

    progressed = apply_checkpoint_decision(
        plan=plan,
        decision="continue_next_step",
        summary="Initial review is complete.",
    )

    assert progressed.plan_status == "active"
    assert progressed.active_step_id == progressed.intended_steps[1].step_id
    assert progressed.intended_steps[0].step_status == "completed"
    assert progressed.intended_steps[1].step_status == "active"
    assert progressed.checkpoint_history[-1].decision == "continue_next_step"


def test_action_candidate_forms_from_active_non_review_step() -> None:
    plan = create_plan(
        selected_option=_selected_option(),
        multi_step=True,
        review_heavy=True,
        time_spanning=True,
        scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
    )
    progressed = apply_checkpoint_decision(
        plan=plan,
        decision="continue_next_step",
        summary="Initial review is complete.",
    )

    candidate = materialize_active_step_action(
        plan=progressed,
        scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
        basis_state_version=3,
        require_single_open_step=False,
    )

    assert candidate.action_formed is True
    assert candidate.action is not None
    assert candidate.action.intent_summary == _selected_option().summary
    assert candidate.step_id == progressed.active_step_id


def test_resume_posture_requires_revalidation_for_review_step() -> None:
    plan = create_plan(
        selected_option=_selected_option(),
        multi_step=True,
        review_heavy=True,
        time_spanning=True,
    )

    assert resume_posture(plan) == "revalidation_required"


def _selected_option() -> ProposalResultOption:
    return ProposalResultOption(
        option_index=1,
        proposal_id="proposal-1",
        proposal_type="planning_insertion",
        title="Implement the bounded multi-step path",
        why_now="The bounded path is ready for downstream planning judgment.",
        summary="Implement the bounded multi-step path",
        constraints=("Stay inside current scope",),
        main_risks=("Bounded rollout may still fail validation",),
        planning_needed=True,
    )