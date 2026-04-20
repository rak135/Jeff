"""JSON-friendly planning persistence helpers."""

from __future__ import annotations

from typing import Any

from jeff.core.schemas import Scope

from .models import PlanArtifact, PlanCheckpointResult, PlanStep, PlanStepRuntimeRecord


def plan_step_to_payload(step: PlanStep) -> dict[str, Any]:
    return {
        "summary": step.summary,
        "review_required": step.review_required,
        "step_id": step.step_id,
        "step_order": step.step_order,
        "title": step.title,
        "step_objective": step.step_objective,
        "step_type": step.step_type,
        "step_inputs_summary": list(step.step_inputs_summary),
        "assumptions": list(step.assumptions),
        "risks": list(step.risks),
        "dependencies": list(step.dependencies),
        "entry_conditions": list(step.entry_conditions),
        "success_criteria": list(step.success_criteria),
        "checkpoint_required": step.checkpoint_required,
        "revalidation_required_on_resume": step.revalidation_required_on_resume,
        "candidate_action_summary": step.candidate_action_summary,
        "step_status": step.step_status,
        "support_refs": list(step.support_refs),
    }


def plan_step_from_payload(payload: dict[str, Any]) -> PlanStep:
    return PlanStep(
        summary=payload["summary"],
        review_required=payload.get("review_required", False),
        step_id=payload.get("step_id"),
        step_order=payload.get("step_order", 1),
        title=payload.get("title"),
        step_objective=payload.get("step_objective"),
        step_type=payload.get("step_type", "bounded_action"),
        step_inputs_summary=tuple(payload.get("step_inputs_summary", ())),
        assumptions=tuple(payload.get("assumptions", ())),
        risks=tuple(payload.get("risks", ())),
        dependencies=tuple(payload.get("dependencies", ())),
        entry_conditions=tuple(payload.get("entry_conditions", ())),
        success_criteria=tuple(payload.get("success_criteria", ())),
        checkpoint_required=payload.get("checkpoint_required"),
        revalidation_required_on_resume=payload.get("revalidation_required_on_resume", False),
        candidate_action_summary=payload.get("candidate_action_summary"),
        step_status=payload.get("step_status", "pending"),
        support_refs=tuple(payload.get("support_refs", ())),
    )


def checkpoint_to_payload(checkpoint: PlanCheckpointResult) -> dict[str, Any]:
    return {
        "checkpoint_id": checkpoint.checkpoint_id,
        "step_id": checkpoint.step_id,
        "decision": checkpoint.decision,
        "summary": checkpoint.summary,
        "previous_plan_status": checkpoint.previous_plan_status,
        "resulting_plan_status": checkpoint.resulting_plan_status,
        "next_active_step_id": checkpoint.next_active_step_id,
    }


def checkpoint_from_payload(payload: dict[str, Any]) -> PlanCheckpointResult:
    return PlanCheckpointResult(
        checkpoint_id=payload["checkpoint_id"],
        step_id=payload["step_id"],
        decision=payload["decision"],
        summary=payload["summary"],
        previous_plan_status=payload["previous_plan_status"],
        resulting_plan_status=payload["resulting_plan_status"],
        next_active_step_id=payload.get("next_active_step_id"),
    )


def step_runtime_to_payload(runtime_record: PlanStepRuntimeRecord) -> dict[str, Any]:
    return {
        "step_id": runtime_record.step_id,
        "runtime_state": runtime_record.runtime_state,
        "executability_posture": runtime_record.executability_posture,
        "action_id": runtime_record.action_id,
        "action_intent_summary": runtime_record.action_intent_summary,
        "last_governance_outcome": runtime_record.last_governance_outcome,
        "last_governance_allowed_now": runtime_record.last_governance_allowed_now,
        "last_governance_reason_summary": runtime_record.last_governance_reason_summary,
        "last_execution_status": runtime_record.last_execution_status,
        "last_execution_command_id": runtime_record.last_execution_command_id,
        "last_execution_summary": runtime_record.last_execution_summary,
        "last_outcome_state": runtime_record.last_outcome_state,
        "last_outcome_summary": runtime_record.last_outcome_summary,
        "last_evaluation_verdict": runtime_record.last_evaluation_verdict,
        "last_evaluation_next_step": runtime_record.last_evaluation_next_step,
        "last_evaluation_reason_summary": runtime_record.last_evaluation_reason_summary,
        "latest_checkpoint_decision": runtime_record.latest_checkpoint_decision,
        "latest_checkpoint_summary": runtime_record.latest_checkpoint_summary,
    }


def step_runtime_from_payload(payload: dict[str, Any]) -> PlanStepRuntimeRecord:
    return PlanStepRuntimeRecord(
        step_id=payload["step_id"],
        runtime_state=payload["runtime_state"],
        executability_posture=payload["executability_posture"],
        action_id=payload.get("action_id"),
        action_intent_summary=payload.get("action_intent_summary"),
        last_governance_outcome=payload.get("last_governance_outcome"),
        last_governance_allowed_now=payload.get("last_governance_allowed_now"),
        last_governance_reason_summary=payload.get("last_governance_reason_summary"),
        last_execution_status=payload.get("last_execution_status"),
        last_execution_command_id=payload.get("last_execution_command_id"),
        last_execution_summary=payload.get("last_execution_summary"),
        last_outcome_state=payload.get("last_outcome_state"),
        last_outcome_summary=payload.get("last_outcome_summary"),
        last_evaluation_verdict=payload.get("last_evaluation_verdict"),
        last_evaluation_next_step=payload.get("last_evaluation_next_step"),
        last_evaluation_reason_summary=payload.get("last_evaluation_reason_summary"),
        latest_checkpoint_decision=payload.get("latest_checkpoint_decision"),
        latest_checkpoint_summary=payload.get("latest_checkpoint_summary"),
    )


def plan_artifact_to_payload(plan: PlanArtifact) -> dict[str, Any]:
    return {
        "plan_id": plan.plan_id,
        "scope": None if plan.scope is None else _scope_to_payload(plan.scope),
        "bounded_objective": plan.bounded_objective,
        "intended_steps": [plan_step_to_payload(step) for step in plan.intended_steps],
        "assumptions": list(plan.assumptions),
        "dependencies": list(plan.dependencies),
        "risks": list(plan.risks),
        "checkpoints": list(plan.checkpoints),
        "stop_conditions": list(plan.stop_conditions),
        "invalidation_conditions": list(plan.invalidation_conditions),
        "selected_proposal_id": None if plan.selected_proposal_id is None else str(plan.selected_proposal_id),
        "blockers": list(plan.blockers),
        "support_refs": list(plan.support_refs),
        "plan_status": plan.plan_status,
        "active_step_id": plan.active_step_id,
        "checkpoint_history": [checkpoint_to_payload(checkpoint) for checkpoint in plan.checkpoint_history],
        "step_runtime_records": [step_runtime_to_payload(item) for item in plan.step_runtime_records],
        "origin_basis": plan.origin_basis,
        "revision_number": plan.revision_number,
        "parent_plan_id": plan.parent_plan_id,
    }


def plan_artifact_from_payload(payload: dict[str, Any]) -> PlanArtifact:
    scope_payload = payload.get("scope")
    return PlanArtifact(
        plan_id=payload.get("plan_id", "plan:bounded"),
        scope=None if scope_payload is None else _scope_from_payload(scope_payload),
        bounded_objective=payload["bounded_objective"],
        intended_steps=tuple(plan_step_from_payload(step_payload) for step_payload in payload["intended_steps"]),
        assumptions=tuple(payload.get("assumptions", ())),
        dependencies=tuple(payload.get("dependencies", ())),
        risks=tuple(payload.get("risks", ())),
        checkpoints=tuple(payload.get("checkpoints", ())),
        stop_conditions=tuple(payload.get("stop_conditions", ())),
        invalidation_conditions=tuple(payload.get("invalidation_conditions", ())),
        selected_proposal_id=payload.get("selected_proposal_id"),
        blockers=tuple(payload.get("blockers", ())),
        support_refs=tuple(payload.get("support_refs", ())),
        plan_status=payload.get("plan_status", "active"),
        active_step_id=payload.get("active_step_id"),
        checkpoint_history=tuple(
            checkpoint_from_payload(checkpoint_payload)
            for checkpoint_payload in payload.get("checkpoint_history", ())
        ),
        step_runtime_records=tuple(
            step_runtime_from_payload(runtime_payload)
            for runtime_payload in payload.get("step_runtime_records", ())
        ),
        origin_basis=payload.get("origin_basis"),
        revision_number=payload.get("revision_number", 1),
        parent_plan_id=payload.get("parent_plan_id"),
    )


def _scope_to_payload(scope: Scope) -> dict[str, Any]:
    return {
        "project_id": str(scope.project_id),
        "work_unit_id": None if scope.work_unit_id is None else str(scope.work_unit_id),
        "run_id": None if scope.run_id is None else str(scope.run_id),
    }


def _scope_from_payload(payload: dict[str, Any]) -> Scope:
    return Scope(
        project_id=payload["project_id"],
        work_unit_id=payload.get("work_unit_id"),
        run_id=payload.get("run_id"),
    )