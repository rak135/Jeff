import pytest

from jeff.cognitive.planning import create_plan, should_plan
from jeff.cognitive.proposal import ProposalResultOption
from jeff.cognitive.types import PlanStep
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry


def _selected_option(*, planning_needed: bool = False) -> ProposalResultOption:
    scope = Scope(project_id="project-1", work_unit_id="wu-1")
    return ProposalResultOption(
        option_index=1,
        proposal_id="proposal-1",
        proposal_type="planning_insertion" if planning_needed else "direct_action",
        title="Implement the bounded multi-step path",
        why_now="The bounded path is ready for downstream planning judgment.",
        summary="Implement the bounded multi-step path",
        constraints=("Stay inside current scope",),
        planning_needed=planning_needed,
    )


def test_planning_is_conditional_not_universal() -> None:
    assert should_plan(selected_option=_selected_option(), operator_requested=False) is False
    assert should_plan(selected_option=_selected_option(planning_needed=True), operator_requested=False) is True
    assert should_plan(selected_option=_selected_option(), operator_requested=True) is True


def test_create_plan_requires_real_justification() -> None:
    with pytest.raises(ValueError, match="conditional and must not run"):
        create_plan(
            selected_option=_selected_option(),
            intended_steps=(PlanStep(summary="Do the single bounded step"),),
        )


def test_plan_artifact_is_not_action() -> None:
    plan = create_plan(
        selected_option=_selected_option(planning_needed=True),
        intended_steps=(
            PlanStep(summary="Prepare the change"),
            PlanStep(summary="Review the change", review_required=True),
        ),
        multi_step=True,
        checkpoints=("review checkpoint",),
        invalidation_conditions=("scope changes materially",),
    )

    assert len(plan.intended_steps) == 2

    with pytest.raises(TypeError, match="bounded Action input"):
        evaluate_action_entry(
            action=plan,  # type: ignore[arg-type]
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(
                scope=Scope(project_id="project-1", work_unit_id="wu-1"),
                state_version=3,
            ),
        )
