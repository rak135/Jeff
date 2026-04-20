import pytest

from jeff.cognitive.planning import create_plan, evaluate_planning_gate, should_plan
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


def test_planning_gate_collects_deterministic_reasons() -> None:
    decision = evaluate_planning_gate(
        selected_option=_selected_option(planning_needed=True),
        multi_step=True,
        dependency_heavy=True,
        checkpoint_heavy=True,
    )

    assert decision.should_plan is True
    assert decision.reasons == (
        "selected_option_planning_needed",
        "selected_option_is_planning_insertion",
        "multi_step",
        "dependency_heavy",
        "checkpoint_heavy",
    )


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


def test_create_plan_without_explicit_steps_uses_deterministic_defaults() -> None:
    plan = create_plan(
        selected_option=_selected_option(planning_needed=True),
        multi_step=True,
        review_heavy=True,
        time_spanning=True,
        scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
    )

    assert plan.plan_status == "active"
    assert plan.active_step_id == plan.intended_steps[0].step_id
    assert plan.intended_steps[0].review_required is True
    assert plan.scope == Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
