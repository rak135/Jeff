"""Deterministic plan-step progression and resume rules."""

from __future__ import annotations

from dataclasses import dataclass, replace

from jeff.cognitive.evaluation import EvaluationResult

from .models import (
    CheckpointDecision,
    PlanArtifact,
    PlanCheckpointResult,
    PlanStatus,
    PlanStep,
    PlanStepRuntimeRecord,
    PlanStepStatus,
)


@dataclass(frozen=True, slots=True)
class DeterministicCheckpointOutcome:
    decision: CheckpointDecision
    summary: str


def active_step(plan: PlanArtifact) -> PlanStep | None:
    return plan.active_step


def resume_posture(plan: PlanArtifact) -> str:
    step = plan.active_step
    if step is None:
        return "no_active_step"
    if step.revalidation_required_on_resume:
        return "revalidation_required"
    return "resume_allowed"


def apply_checkpoint_decision(
    *,
    plan: PlanArtifact,
    decision: CheckpointDecision,
    summary: str,
) -> PlanArtifact:
    step = plan.active_step
    if step is None:
        raise ValueError("checkpoint progression requires an active plan step")

    next_status, next_active_step_id, current_step_status = _decision_resolution(plan=plan, decision=decision)
    updated_steps: list[PlanStep] = []
    next_step_activated = False
    for existing in plan.intended_steps:
        if existing.step_id == step.step_id:
            updated_steps.append(_replace_step_status(existing, current_step_status))
            continue
        if not next_step_activated and next_active_step_id is not None and existing.step_id == next_active_step_id:
            updated_steps.append(_replace_step_status(existing, "active"))
            next_step_activated = True
            continue
        if existing.step_status == "active" and existing.step_id != step.step_id:
            updated_steps.append(_replace_step_status(existing, "pending"))
            continue
        updated_steps.append(existing)

    checkpoint = PlanCheckpointResult(
        checkpoint_id=f"{plan.plan_id}:checkpoint-{len(plan.checkpoint_history) + 1}",
        step_id=step.step_id,
        decision=decision,
        summary=summary,
        previous_plan_status=plan.plan_status,
        resulting_plan_status=next_status,
        next_active_step_id=next_active_step_id,
    )
    return PlanArtifact(
        plan_id=plan.plan_id,
        scope=plan.scope,
        bounded_objective=plan.bounded_objective,
        intended_steps=tuple(updated_steps),
        assumptions=plan.assumptions,
        dependencies=plan.dependencies,
        risks=plan.risks,
        checkpoints=plan.checkpoints,
        stop_conditions=plan.stop_conditions,
        invalidation_conditions=plan.invalidation_conditions,
        selected_proposal_id=plan.selected_proposal_id,
        blockers=plan.blockers,
        support_refs=plan.support_refs,
        plan_status=next_status,
        active_step_id=next_active_step_id,
        checkpoint_history=(*plan.checkpoint_history, checkpoint),
        step_runtime_records=plan.step_runtime_records,
        origin_basis=plan.origin_basis,
        revision_number=plan.revision_number,
        parent_plan_id=plan.parent_plan_id,
    )


def checkpoint_from_evaluation(*, plan: PlanArtifact, evaluation: EvaluationResult) -> DeterministicCheckpointOutcome:
    if evaluation.recommended_next_step == "accept_as_complete":
        next_step = _next_pending_step(plan, after_step_id=plan.active_step_id)
        if next_step is None:
            return DeterministicCheckpointOutcome(
                decision="stop_complete",
                summary=(
                    f"evaluation verdict {evaluation.evaluation_verdict} accepted the executed step as complete and no downstream step remains"
                ),
            )
        return DeterministicCheckpointOutcome(
            decision="continue_next_step",
            summary=(
                f"evaluation verdict {evaluation.evaluation_verdict} accepted the executed step and the next bounded step is ready"
            ),
        )
    if evaluation.recommended_next_step == "continue":
        return DeterministicCheckpointOutcome(
            decision="continue_next_step",
            summary=f"evaluation verdict {evaluation.evaluation_verdict} supports continuing to the next bounded step",
        )
    if evaluation.recommended_next_step == "revalidate":
        return DeterministicCheckpointOutcome(
            decision="revalidate_plan",
            summary=f"evaluation verdict {evaluation.evaluation_verdict} requires bounded plan revalidation before continuation",
        )
    if evaluation.recommended_next_step in {"recover", "terminate_and_replan"}:
        return DeterministicCheckpointOutcome(
            decision="replan_from_here",
            summary=f"evaluation verdict {evaluation.evaluation_verdict} requires replanning from the current bounded step",
        )
    if evaluation.recommended_next_step in {"escalate", "request_clarification"}:
        return DeterministicCheckpointOutcome(
            decision="escalate",
            summary=f"evaluation verdict {evaluation.evaluation_verdict} requires operator escalation before further planning progress",
        )
    if evaluation.recommended_next_step == "retry":
        return DeterministicCheckpointOutcome(
            decision="stop_failed",
            summary=f"evaluation verdict {evaluation.evaluation_verdict} marks the executed bounded step as failed",
        )
    raise ValueError("unsupported evaluation recommended_next_step")


def with_step_runtime_record(*, plan: PlanArtifact, runtime_record: PlanStepRuntimeRecord) -> PlanArtifact:
    updated_records: list[PlanStepRuntimeRecord] = []
    replaced_existing = False
    for existing in plan.step_runtime_records:
        if existing.step_id == runtime_record.step_id:
            updated_records.append(runtime_record)
            replaced_existing = True
            continue
        updated_records.append(existing)
    if not replaced_existing:
        updated_records.append(runtime_record)

    return PlanArtifact(
        plan_id=plan.plan_id,
        scope=plan.scope,
        bounded_objective=plan.bounded_objective,
        intended_steps=plan.intended_steps,
        assumptions=plan.assumptions,
        dependencies=plan.dependencies,
        risks=plan.risks,
        checkpoints=plan.checkpoints,
        stop_conditions=plan.stop_conditions,
        invalidation_conditions=plan.invalidation_conditions,
        selected_proposal_id=plan.selected_proposal_id,
        blockers=plan.blockers,
        support_refs=plan.support_refs,
        plan_status=plan.plan_status,
        active_step_id=plan.active_step_id,
        checkpoint_history=plan.checkpoint_history,
        step_runtime_records=tuple(updated_records),
        origin_basis=plan.origin_basis,
        revision_number=plan.revision_number,
        parent_plan_id=plan.parent_plan_id,
    )


def _decision_resolution(
    *,
    plan: PlanArtifact,
    decision: CheckpointDecision,
) -> tuple[PlanStatus, str | None, PlanStepStatus]:
    if decision == "continue_next_step":
        next_step = _next_pending_step(plan, after_step_id=plan.active_step_id)
        if next_step is None:
            return "completed", None, "completed"
        return "active", next_step.step_id, "completed"
    if decision == "revalidate_plan":
        return "needs_revalidation", plan.active_step_id, "blocked"
    if decision == "replan_from_here":
        return "needs_replan", plan.active_step_id, "blocked"
    if decision == "escalate":
        return "escalated", None, "blocked"
    if decision == "stop_complete":
        return "completed", None, "completed"
    if decision == "stop_failed":
        return "failed", None, "failed"
    raise ValueError("unknown checkpoint decision")


def _next_pending_step(plan: PlanArtifact, *, after_step_id: str | None) -> PlanStep | None:
    found_current = after_step_id is None
    for step in plan.intended_steps:
        if not found_current:
            if step.step_id == after_step_id:
                found_current = True
            continue
        if step.step_id == after_step_id:
            continue
        if step.step_status == "pending":
            return step
    return None


def _replace_step_status(step: PlanStep, status: PlanStepStatus) -> PlanStep:
    return replace(step, step_status=status)