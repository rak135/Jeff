"""Planning validation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from .models import PlanArtifact


@dataclass(frozen=True, slots=True)
class PlanningValidationResult:
    valid: bool
    code: str | None = None
    reason: str | None = None


def validate_plan_artifact(plan: PlanArtifact) -> PlanningValidationResult:
    if plan.selected_proposal_id is None:
        return PlanningValidationResult(
            valid=False,
            code="missing_selected_proposal_id",
            reason="plan artifacts must preserve selected proposal linkage",
        )
    if plan.active_step is None and plan.plan_status == "active":
        return PlanningValidationResult(
            valid=False,
            code="missing_active_step",
            reason="active plans must expose one active step",
        )
    if any(step.step_order <= 0 for step in plan.intended_steps):
        return PlanningValidationResult(
            valid=False,
            code="invalid_step_order",
            reason="plan steps must keep positive step order values",
        )
    return PlanningValidationResult(valid=True)