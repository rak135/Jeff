"""Deterministic bounded plan formation."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import Scope

from ..proposal import ProposalResultOption
from .gating import evaluate_planning_gate
from .models import PlanArtifact, PlanStep


@dataclass(frozen=True, slots=True)
class PlanFormationRequest:
    selected_option: ProposalResultOption
    scope: Scope | None = None
    operator_requested: bool = False
    multi_step: bool = False
    review_heavy: bool = False
    high_risk: bool = False
    time_spanning: bool = False
    dependency_heavy: bool = False
    checkpoint_heavy: bool = False
    plan_id: str | None = None


def form_plan(request: PlanFormationRequest) -> PlanArtifact:
    gate = evaluate_planning_gate(
        selected_option=request.selected_option,
        operator_requested=request.operator_requested,
        multi_step=request.multi_step,
        review_heavy=request.review_heavy,
        high_risk=request.high_risk,
        time_spanning=request.time_spanning,
        dependency_heavy=request.dependency_heavy,
        checkpoint_heavy=request.checkpoint_heavy,
    )
    if not gate.should_plan:
        raise ValueError("planning is conditional and must not run for simple unjustified work")

    selected = request.selected_option
    plan_id = request.plan_id or f"plan:{selected.proposal_id}"
    dependencies = tuple(dict.fromkeys((*selected.constraints, *selected.blockers)))
    risks = selected.main_risks
    assumptions = selected.assumptions
    support_refs = selected.support_refs
    review_points = _review_points_for(selected)

    steps = (
        PlanStep(
            summary="Review bounded scope, dependencies, and checkpoints before execution",
            review_required=True,
            step_id=f"{plan_id}:step-1",
            step_order=1,
            title="Review plan basis",
            step_objective="Confirm the selected path still fits current scope and bounded validation intent.",
            step_type="review",
            step_inputs_summary=(selected.summary, *selected.constraints[:2]),
            assumptions=assumptions,
            risks=risks,
            dependencies=dependencies,
            entry_conditions=("A selected proposal exists.",),
            success_criteria=(
                "The selected proposal remains within current scope.",
                "Dependencies and blockers are explicitly acknowledged.",
            ),
            checkpoint_required=True,
            revalidation_required_on_resume=True,
            candidate_action_summary=(
                "Review the selected proposal, active constraints, blockers, and smoke-validation intent before any downstream action."
            ),
            step_status="active",
            support_refs=support_refs,
        ),
        PlanStep(
            summary=selected.summary,
            step_id=f"{plan_id}:step-2",
            step_order=2,
            title="Execute bounded validation step",
            step_objective="Materialize one bounded action candidate for the selected implementation path.",
            step_type="validation",
            step_inputs_summary=(selected.why_now,),
            assumptions=assumptions,
            risks=risks,
            dependencies=dependencies,
            entry_conditions=("Step 1 review checkpoint passed.",),
            success_criteria=("A single bounded action candidate is available for governance review.",),
            checkpoint_required=True,
            revalidation_required_on_resume=False,
            candidate_action_summary=selected.summary,
            step_status="pending",
            support_refs=support_refs,
        ),
        PlanStep(
            summary="Review outcome and decide continue, revalidate, replan, escalate, or stop",
            review_required=True,
            step_id=f"{plan_id}:step-3",
            step_order=3,
            title="Checkpoint outcome review",
            step_objective="Judge the last bounded step without collapsing planning into truth or permission.",
            step_type="review",
            step_inputs_summary=(selected.summary,),
            assumptions=assumptions,
            risks=risks,
            dependencies=dependencies,
            entry_conditions=("The active bounded action candidate has been executed and evaluated.",),
            success_criteria=("A lawful checkpoint decision is recorded.",),
            checkpoint_required=True,
            revalidation_required_on_resume=True,
            candidate_action_summary="Inspect the last bounded result and record the next checkpoint decision.",
            step_status="pending",
            support_refs=support_refs,
        ),
    )

    return PlanArtifact(
        plan_id=plan_id,
        scope=request.scope,
        bounded_objective=selected.summary,
        intended_steps=steps,
        assumptions=assumptions,
        dependencies=dependencies,
        risks=risks,
        blockers=selected.blockers,
        checkpoints=review_points,
        stop_conditions=(
            "The bounded objective is fully satisfied.",
            "Governance or execution reveals the path should stop.",
        ),
        invalidation_conditions=(
            "Scope changes materially.",
            "Dependencies or blockers change the lawful bounded path.",
        ),
        support_refs=support_refs,
        plan_status="active",
        active_step_id=steps[0].step_id,
        selected_proposal_id=selected.proposal_id,
        origin_basis="deterministic_selection_boundaries",
    )


def create_plan(
    *,
    selected_option: ProposalResultOption,
    intended_steps: tuple[PlanStep, ...] | None = None,
    operator_requested: bool = False,
    multi_step: bool = False,
    review_heavy: bool = False,
    high_risk: bool = False,
    time_spanning: bool = False,
    assumptions: tuple[str, ...] = (),
    dependencies: tuple[str, ...] = (),
    risks: tuple[str, ...] = (),
    checkpoints: tuple[str, ...] = (),
    stop_conditions: tuple[str, ...] = (),
    invalidation_conditions: tuple[str, ...] = (),
    blockers: tuple[str, ...] = (),
    support_refs: tuple[str, ...] = (),
    scope: Scope | None = None,
    plan_id: str | None = None,
) -> PlanArtifact:
    if intended_steps is None:
        return form_plan(
            PlanFormationRequest(
                selected_option=selected_option,
                scope=scope,
                operator_requested=operator_requested,
                multi_step=multi_step,
                review_heavy=review_heavy,
                high_risk=high_risk,
                time_spanning=time_spanning,
                dependency_heavy=len(dependencies) > 1 or len(selected_option.blockers) > 0,
                checkpoint_heavy=len(checkpoints) > 1,
                plan_id=plan_id,
            )
        )

    gate = evaluate_planning_gate(
        selected_option=selected_option,
        operator_requested=operator_requested,
        multi_step=multi_step,
        review_heavy=review_heavy,
        high_risk=high_risk,
        time_spanning=time_spanning,
        dependency_heavy=len(dependencies) > 1 or len(blockers) > 0,
        checkpoint_heavy=len(checkpoints) > 1,
    )
    if not gate.should_plan:
        raise ValueError("planning is conditional and must not run for simple unjustified work")

    return PlanArtifact(
        plan_id=plan_id or f"plan:{selected_option.proposal_id}",
        scope=scope,
        bounded_objective=selected_option.summary,
        intended_steps=intended_steps,
        assumptions=assumptions,
        dependencies=dependencies,
        risks=risks,
        blockers=blockers,
        checkpoints=checkpoints,
        stop_conditions=stop_conditions,
        invalidation_conditions=invalidation_conditions,
        support_refs=support_refs,
        selected_proposal_id=selected_option.proposal_id,
        origin_basis="explicit_create_plan",
    )


def _review_points_for(selected_option: ProposalResultOption) -> tuple[str, ...]:
    base = [
        "Confirm current scope and blockers before any downstream action.",
        "Review the outcome after each bounded action step.",
    ]
    if selected_option.main_risks:
        base.append("Explicitly revisit the main risks before continuing.")
    return tuple(base)