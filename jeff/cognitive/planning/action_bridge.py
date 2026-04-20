"""Explicit bounded bridge from the active plan step into an action candidate."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.contracts import Action
from jeff.core.schemas import Scope

from ..types import require_text
from .models import PlanArtifact


@dataclass(frozen=True, slots=True)
class PlanActionCandidateResult:
    candidate_id: str
    action: Action | None
    action_formed: bool
    plan_id: str
    step_id: str | None
    no_action_reason: str | None
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", require_text(self.candidate_id, field_name="candidate_id"))
        object.__setattr__(self, "plan_id", require_text(self.plan_id, field_name="plan_id"))
        if self.step_id is not None:
            object.__setattr__(self, "step_id", require_text(self.step_id, field_name="step_id"))
        if self.no_action_reason is not None:
            object.__setattr__(self, "no_action_reason", require_text(self.no_action_reason, field_name="no_action_reason"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.action_formed and self.action is None:
            raise ValueError("action_formed candidates must include an Action")
        if not self.action_formed and self.no_action_reason is None:
            raise ValueError("non-formed action candidates must include no_action_reason")


def materialize_active_step_action(
    *,
    plan: PlanArtifact,
    scope: Scope,
    basis_state_version: int = 0,
    require_single_open_step: bool = False,
) -> PlanActionCandidateResult:
    candidate_id = f"plan-action-candidate:{plan.plan_id}"
    step = plan.active_step
    if step is None:
        return PlanActionCandidateResult(
            candidate_id=candidate_id,
            action=None,
            action_formed=False,
            plan_id=plan.plan_id,
            step_id=None,
            no_action_reason="The plan has no active step to materialize.",
            summary="No action candidate formed because the plan has no active step.",
        )
    if plan.selected_proposal_id is None:
        return PlanActionCandidateResult(
            candidate_id=candidate_id,
            action=None,
            action_formed=False,
            plan_id=plan.plan_id,
            step_id=step.step_id,
            no_action_reason="The plan does not preserve selected proposal linkage required for action materialization.",
            summary="No action candidate formed because the plan lacks selected proposal linkage.",
        )
    if plan.plan_status != "active":
        return PlanActionCandidateResult(
            candidate_id=candidate_id,
            action=None,
            action_formed=False,
            plan_id=plan.plan_id,
            step_id=step.step_id,
            no_action_reason=f"The current plan status is {plan.plan_status} and is not action-materializable.",
            summary="No action candidate formed because the plan is not currently active.",
        )
    open_steps = tuple(
        step_entry for step_entry in plan.intended_steps if step_entry.step_status in {"pending", "active", "blocked"}
    )
    if require_single_open_step and len(open_steps) != 1:
        return PlanActionCandidateResult(
            candidate_id=candidate_id,
            action=None,
            action_formed=False,
            plan_id=plan.plan_id,
            step_id=step.step_id,
            no_action_reason=(
                f"The plan still exposes {len(open_steps)} open steps, so orchestration must not guess a single executable next action."
            ),
            summary="No action candidate formed because multiple open steps remain.",
        )
    if step.review_required:
        return PlanActionCandidateResult(
            candidate_id=candidate_id,
            action=None,
            action_formed=False,
            plan_id=plan.plan_id,
            step_id=step.step_id,
            no_action_reason="The active plan step is review-only and does not yet yield an executable action candidate.",
            summary="No action candidate formed because the active step is review-only.",
        )

    action = Action(
        action_id=f"action:planned:{plan.selected_proposal_id}:{step.step_id}",
        scope=scope,
        intent_summary=step.candidate_action_summary or step.summary,
        target_summary=plan.bounded_objective,
        basis_state_version=basis_state_version,
        basis_label=(
            f"planned_action;plan_id={plan.plan_id};proposal_id={plan.selected_proposal_id};step_id={step.step_id}"
        ),
    )
    return PlanActionCandidateResult(
        candidate_id=candidate_id,
        action=action,
        action_formed=True,
        plan_id=plan.plan_id,
        step_id=step.step_id,
        no_action_reason=None,
        summary="Action candidate formed from the active bounded plan step for downstream governance evaluation.",
    )