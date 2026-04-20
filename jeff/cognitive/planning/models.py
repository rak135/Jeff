"""Core bounded planning models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import ProposalId, Scope, coerce_proposal_id

from ..types import PlanStep, normalize_text_list, require_text

PlanStatus = Literal[
    "active",
    "needs_revalidation",
    "needs_replan",
    "escalated",
    "completed",
    "failed",
    "stopped",
]
PlanStepStatus = Literal["pending", "active", "completed", "blocked", "failed", "stopped"]
PlanStepType = Literal["bounded_action", "review", "validation", "analysis", "coordination"]
PlanStepRuntimeState = Literal[
    "not_executable",
    "governance_blocked",
    "governance_allowed",
    "executed",
    "checkpointed",
]
CheckpointDecision = Literal[
    "continue_next_step",
    "revalidate_plan",
    "replan_from_here",
    "escalate",
    "stop_complete",
    "stop_failed",
]


@dataclass(frozen=True, slots=True)
class PlanStepRuntimeRecord:
    step_id: str
    runtime_state: PlanStepRuntimeState
    executability_posture: str
    action_id: str | None = None
    action_intent_summary: str | None = None
    last_governance_outcome: str | None = None
    last_governance_allowed_now: bool | None = None
    last_governance_reason_summary: str | None = None
    last_execution_status: str | None = None
    last_execution_command_id: str | None = None
    last_execution_summary: str | None = None
    last_outcome_state: str | None = None
    last_outcome_summary: str | None = None
    last_evaluation_verdict: str | None = None
    last_evaluation_next_step: str | None = None
    last_evaluation_reason_summary: str | None = None
    latest_checkpoint_decision: CheckpointDecision | None = None
    latest_checkpoint_summary: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", require_text(self.step_id, field_name="step_id"))
        if self.runtime_state not in {
            "not_executable",
            "governance_blocked",
            "governance_allowed",
            "executed",
            "checkpointed",
        }:
            raise ValueError("runtime_state must remain a lawful bounded planning runtime state")
        object.__setattr__(
            self,
            "executability_posture",
            require_text(self.executability_posture, field_name="executability_posture"),
        )
        if self.action_id is not None:
            object.__setattr__(self, "action_id", require_text(self.action_id, field_name="action_id"))
        if self.action_intent_summary is not None:
            object.__setattr__(
                self,
                "action_intent_summary",
                require_text(self.action_intent_summary, field_name="action_intent_summary"),
            )
        if self.last_governance_outcome is not None:
            object.__setattr__(
                self,
                "last_governance_outcome",
                require_text(self.last_governance_outcome, field_name="last_governance_outcome"),
            )
        if self.last_governance_reason_summary is not None:
            object.__setattr__(
                self,
                "last_governance_reason_summary",
                require_text(self.last_governance_reason_summary, field_name="last_governance_reason_summary"),
            )
        if self.last_execution_status is not None:
            object.__setattr__(
                self,
                "last_execution_status",
                require_text(self.last_execution_status, field_name="last_execution_status"),
            )
        if self.last_execution_command_id is not None:
            object.__setattr__(
                self,
                "last_execution_command_id",
                require_text(self.last_execution_command_id, field_name="last_execution_command_id"),
            )
        if self.last_execution_summary is not None:
            object.__setattr__(
                self,
                "last_execution_summary",
                require_text(self.last_execution_summary, field_name="last_execution_summary"),
            )
        if self.last_outcome_state is not None:
            object.__setattr__(
                self,
                "last_outcome_state",
                require_text(self.last_outcome_state, field_name="last_outcome_state"),
            )
        if self.last_outcome_summary is not None:
            object.__setattr__(
                self,
                "last_outcome_summary",
                require_text(self.last_outcome_summary, field_name="last_outcome_summary"),
            )
        if self.last_evaluation_verdict is not None:
            object.__setattr__(
                self,
                "last_evaluation_verdict",
                require_text(self.last_evaluation_verdict, field_name="last_evaluation_verdict"),
            )
        if self.last_evaluation_next_step is not None:
            object.__setattr__(
                self,
                "last_evaluation_next_step",
                require_text(self.last_evaluation_next_step, field_name="last_evaluation_next_step"),
            )
        if self.last_evaluation_reason_summary is not None:
            object.__setattr__(
                self,
                "last_evaluation_reason_summary",
                require_text(self.last_evaluation_reason_summary, field_name="last_evaluation_reason_summary"),
            )
        if self.latest_checkpoint_summary is not None:
            object.__setattr__(
                self,
                "latest_checkpoint_summary",
                require_text(self.latest_checkpoint_summary, field_name="latest_checkpoint_summary"),
            )
        if self.latest_checkpoint_decision is not None and self.latest_checkpoint_decision not in {
            "continue_next_step",
            "revalidate_plan",
            "replan_from_here",
            "escalate",
            "stop_complete",
            "stop_failed",
        }:
            raise ValueError("latest_checkpoint_decision must remain a lawful checkpoint outcome")


@dataclass(frozen=True, slots=True)
class PlanCheckpointResult:
    checkpoint_id: str
    step_id: str
    decision: CheckpointDecision
    summary: str
    previous_plan_status: PlanStatus
    resulting_plan_status: PlanStatus
    next_active_step_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "checkpoint_id", require_text(self.checkpoint_id, field_name="checkpoint_id"))
        object.__setattr__(self, "step_id", require_text(self.step_id, field_name="step_id"))
        if self.decision not in {
            "continue_next_step",
            "revalidate_plan",
            "replan_from_here",
            "escalate",
            "stop_complete",
            "stop_failed",
        }:
            raise ValueError("decision must remain a lawful checkpoint outcome")
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.previous_plan_status not in {
            "active",
            "needs_revalidation",
            "needs_replan",
            "escalated",
            "completed",
            "failed",
            "stopped",
        }:
            raise ValueError("previous_plan_status must remain a lawful plan state")
        if self.resulting_plan_status not in {
            "active",
            "needs_revalidation",
            "needs_replan",
            "escalated",
            "completed",
            "failed",
            "stopped",
        }:
            raise ValueError("resulting_plan_status must remain a lawful plan state")
        if self.next_active_step_id is not None:
            object.__setattr__(
                self,
                "next_active_step_id",
                require_text(self.next_active_step_id, field_name="next_active_step_id"),
            )


@dataclass(frozen=True, slots=True)
class PlanArtifact:
    bounded_objective: str
    intended_steps: tuple[PlanStep, ...]
    assumptions: tuple[str, ...] = ()
    dependencies: tuple[str, ...] = ()
    risks: tuple[str, ...] = ()
    checkpoints: tuple[str, ...] = ()
    stop_conditions: tuple[str, ...] = ()
    invalidation_conditions: tuple[str, ...] = ()
    selected_proposal_id: ProposalId | None = None
    plan_id: str = "plan:bounded"
    scope: Scope | None = None
    blockers: tuple[str, ...] = ()
    support_refs: tuple[str, ...] = ()
    plan_status: PlanStatus = "active"
    active_step_id: str | None = None
    checkpoint_history: tuple[PlanCheckpointResult, ...] = ()
    step_runtime_records: tuple[PlanStepRuntimeRecord, ...] = ()
    origin_basis: str | None = None
    revision_number: int = 1
    parent_plan_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "bounded_objective",
            require_text(self.bounded_objective, field_name="bounded_objective"),
        )
        object.__setattr__(self, "plan_id", require_text(self.plan_id, field_name="plan_id"))
        if not isinstance(self.revision_number, int):
            raise TypeError("revision_number must be an integer")
        if self.revision_number <= 0:
            raise ValueError("revision_number must be greater than zero")
        if not self.intended_steps:
            raise ValueError("plan artifacts require at least one intended step")

        normalized_steps: list[PlanStep] = []
        seen_step_ids: set[str] = set()
        seen_orders: set[int] = set()
        active_step_ids: list[str] = []
        for index, step in enumerate(self.intended_steps, start=1):
            if not isinstance(step, PlanStep):
                raise TypeError("intended_steps must contain PlanStep instances")
            step_id = step.step_id or f"{self.plan_id}:step-{index}"
            if step.step_id != step_id or step.step_order != index:
                step = PlanStep(
                    summary=step.summary,
                    review_required=step.review_required,
                    step_id=step_id,
                    step_order=index,
                    title=step.title,
                    step_objective=step.step_objective,
                    step_type=step.step_type,
                    step_inputs_summary=step.step_inputs_summary,
                    assumptions=step.assumptions,
                    risks=step.risks,
                    dependencies=step.dependencies,
                    entry_conditions=step.entry_conditions,
                    success_criteria=step.success_criteria,
                    checkpoint_required=step.checkpoint_required,
                    revalidation_required_on_resume=step.revalidation_required_on_resume,
                    candidate_action_summary=step.candidate_action_summary,
                    step_status=step.step_status,
                    support_refs=step.support_refs,
                )
            if step.step_id in seen_step_ids:
                raise ValueError("plan step ids must be unique")
            if step.step_order in seen_orders:
                raise ValueError("plan step order must be unique")
            seen_step_ids.add(step.step_id)
            seen_orders.add(step.step_order)
            if step.step_status == "active":
                active_step_ids.append(step.step_id)
            normalized_steps.append(step)

        object.__setattr__(self, "intended_steps", tuple(normalized_steps))
        object.__setattr__(self, "assumptions", normalize_text_list(self.assumptions, field_name="assumptions"))
        object.__setattr__(self, "dependencies", normalize_text_list(self.dependencies, field_name="dependencies"))
        object.__setattr__(self, "risks", normalize_text_list(self.risks, field_name="risks"))
        object.__setattr__(self, "checkpoints", normalize_text_list(self.checkpoints, field_name="checkpoints"))
        object.__setattr__(
            self,
            "stop_conditions",
            normalize_text_list(self.stop_conditions, field_name="stop_conditions"),
        )
        object.__setattr__(
            self,
            "invalidation_conditions",
            normalize_text_list(self.invalidation_conditions, field_name="invalidation_conditions"),
        )
        object.__setattr__(self, "blockers", normalize_text_list(self.blockers, field_name="blockers"))
        object.__setattr__(self, "support_refs", normalize_text_list(self.support_refs, field_name="support_refs"))
        if self.selected_proposal_id is not None:
            object.__setattr__(
                self,
                "selected_proposal_id",
                coerce_proposal_id(str(self.selected_proposal_id)),
            )
        if self.origin_basis is not None:
            object.__setattr__(self, "origin_basis", require_text(self.origin_basis, field_name="origin_basis"))
        if self.parent_plan_id is not None:
            object.__setattr__(self, "parent_plan_id", require_text(self.parent_plan_id, field_name="parent_plan_id"))
        if self.plan_status not in {
            "active",
            "needs_revalidation",
            "needs_replan",
            "escalated",
            "completed",
            "failed",
            "stopped",
        }:
            raise ValueError("plan_status must remain a lawful bounded planning state")
        if len(active_step_ids) > 1:
            raise ValueError("plan artifacts may expose at most one active step")

        resolved_active_step_id = self.active_step_id
        if resolved_active_step_id is not None:
            resolved_active_step_id = require_text(resolved_active_step_id, field_name="active_step_id")
            if resolved_active_step_id not in seen_step_ids:
                raise ValueError("active_step_id must refer to a known plan step")
        elif active_step_ids:
            resolved_active_step_id = active_step_ids[0]
        else:
            resolved_active_step_id = _first_open_step_id(tuple(normalized_steps))
        object.__setattr__(self, "active_step_id", resolved_active_step_id)

        if self.checkpoint_history:
            for checkpoint in self.checkpoint_history:
                if not isinstance(checkpoint, PlanCheckpointResult):
                    raise TypeError("checkpoint_history must contain PlanCheckpointResult entries")
        if self.step_runtime_records:
            seen_runtime_steps: set[str] = set()
            for runtime_record in self.step_runtime_records:
                if not isinstance(runtime_record, PlanStepRuntimeRecord):
                    raise TypeError("step_runtime_records must contain PlanStepRuntimeRecord entries")
                if runtime_record.step_id not in seen_step_ids:
                    raise ValueError("step runtime records must refer to known plan steps")
                if runtime_record.step_id in seen_runtime_steps:
                    raise ValueError("step runtime records may contain at most one record per step")
                seen_runtime_steps.add(runtime_record.step_id)

    @property
    def ordered_steps(self) -> tuple[PlanStep, ...]:
        return self.intended_steps

    @property
    def global_assumptions(self) -> tuple[str, ...]:
        return self.assumptions

    @property
    def global_dependencies(self) -> tuple[str, ...]:
        return self.dependencies

    @property
    def global_risks(self) -> tuple[str, ...]:
        return self.risks

    @property
    def global_blockers(self) -> tuple[str, ...]:
        return self.blockers

    @property
    def review_points(self) -> tuple[str, ...]:
        return self.checkpoints

    @property
    def active_step(self) -> PlanStep | None:
        if self.active_step_id is None:
            return None
        for step in self.intended_steps:
            if step.step_id == self.active_step_id:
                return step
        return None

    def runtime_for_step(self, step_id: str) -> PlanStepRuntimeRecord | None:
        for runtime_record in self.step_runtime_records:
            if runtime_record.step_id == step_id:
                return runtime_record
        return None

    @property
    def active_step_runtime(self) -> PlanStepRuntimeRecord | None:
        if self.active_step_id is None:
            return None
        return self.runtime_for_step(self.active_step_id)

    @property
    def latest_runtime_record(self) -> PlanStepRuntimeRecord | None:
        if not self.step_runtime_records:
            return None
        return self.step_runtime_records[-1]


def _first_open_step_id(steps: tuple[PlanStep, ...]) -> str | None:
    for step in steps:
        if step.step_status in {"pending", "active", "blocked"}:
            return step.step_id
    return None