"""Fail-closed stage sequence and handoff validation."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.action import EvaluationResult, ExecutionResult, Outcome
from jeff.cognitive import ContextPackage, PlanArtifact, ProposalSet, ResearchResult, SelectionResult
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.transition import TransitionResult
from jeff.governance import ActionEntryDecision
from jeff.memory import MemoryWriteDecision

from .flows import FlowFamily, StageName, stage_order_for_flow


@dataclass(frozen=True, slots=True)
class ValidationResult:
    valid: bool
    code: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if self.valid and (self.code is not None or self.reason is not None):
            raise ValueError("valid validation results must not carry failure code or reason")
        if not self.valid:
            if self.code is None or self.reason is None:
                raise ValueError("invalid validation results require code and reason")


_ALLOWED_PREDECESSORS: dict[StageName, tuple[StageName, ...]] = {
    "context": (),
    "research": ("context",),
    "proposal": ("context", "research"),
    "selection": ("proposal",),
    "planning": ("selection",),
    "action": ("selection", "planning"),
    "governance": ("action",),
    "execution": ("governance",),
    "outcome": ("execution",),
    "evaluation": ("outcome",),
    "memory": ("evaluation",),
    "transition": ("memory",),
}

_EXPECTED_OUTPUT_TYPES: dict[StageName, type[object]] = {
    "context": ContextPackage,
    "research": ResearchResult,
    "proposal": ProposalSet,
    "selection": SelectionResult,
    "planning": PlanArtifact,
    "action": Action,
    "governance": ActionEntryDecision,
    "execution": ExecutionResult,
    "outcome": Outcome,
    "evaluation": EvaluationResult,
    "memory": MemoryWriteDecision,
    "transition": TransitionResult,
}


def validate_stage_sequence(
    *,
    flow_family: FlowFamily,
    stages: tuple[StageName, ...],
) -> ValidationResult:
    expected = stage_order_for_flow(flow_family)
    if stages != expected:
        return ValidationResult(
            valid=False,
            code="illegal_stage_order",
            reason=f"{flow_family} must use the explicit stage order {expected}",
        )
    return ValidationResult(valid=True)


def validate_stage_output(
    *,
    stage: StageName,
    output: object,
    flow_scope: Scope,
) -> ValidationResult:
    expected_type = _EXPECTED_OUTPUT_TYPES[stage]
    if not isinstance(output, expected_type):
        return ValidationResult(
            valid=False,
            code="wrong_stage_output_type",
            reason=f"{stage} must emit {expected_type.__name__}",
        )

    output_scope = _scope_from_output(output)
    if output_scope is not None and output_scope != flow_scope:
        return ValidationResult(
            valid=False,
            code="scope_mismatch",
            reason=f"{stage} emitted scope {output_scope} outside flow scope {flow_scope}",
        )

    return ValidationResult(valid=True)


def validate_handoff(
    *,
    previous_stage: StageName,
    previous_output: object,
    next_stage: StageName,
    flow_scope: Scope,
) -> ValidationResult:
    allowed_predecessors = _ALLOWED_PREDECESSORS[next_stage]
    if previous_stage not in allowed_predecessors:
        return ValidationResult(
            valid=False,
            code="impossible_handoff",
            reason=f"{previous_stage} cannot hand off directly to {next_stage}",
        )

    output_validation = validate_stage_output(
        stage=previous_stage,
        output=previous_output,
        flow_scope=flow_scope,
    )
    if not output_validation.valid:
        return output_validation

    if previous_stage == "proposal" and next_stage == "selection" and not previous_output.options:
        return ValidationResult(
            valid=False,
            code="empty_proposal_set",
            reason="selection cannot run when proposal generation returned no serious options",
        )

    if previous_stage == "selection" and next_stage in {"planning", "action"}:
        if previous_output.selected_proposal_id is None:
            return ValidationResult(
                valid=False,
                code="selection_is_not_permission",
                reason="selection must choose a proposal before planning or action may proceed",
            )

    if previous_stage == "planning" and next_stage == "action" and previous_output.selected_proposal_id is None:
        return ValidationResult(
            valid=False,
            code="plan_missing_selected_proposal",
            reason="action cannot start from a plan artifact that lacks selected proposal linkage",
        )

    if previous_stage == "governance" and next_stage == "execution" and not previous_output.allowed_now:
        return ValidationResult(
            valid=False,
            code="governance_not_forwardable",
            reason="execution may not begin until governance explicitly allows_now",
        )

    if previous_stage == "memory" and next_stage == "transition" and previous_output.write_outcome != "write":
        return ValidationResult(
            valid=False,
            code="memory_not_committed",
            reason="transition may not use rejected or deferred memory writes as lawful basis",
        )

    return ValidationResult(valid=True)


def _scope_from_output(output: object) -> Scope | None:
    if isinstance(output, ContextPackage):
        return output.scope
    if isinstance(output, ResearchResult):
        return output.request.scope
    if isinstance(output, ProposalSet):
        return output.scope
    if isinstance(output, Action):
        return output.scope
    if isinstance(output, ExecutionResult):
        return output.scope
    if isinstance(output, Outcome):
        return output.scope
    if isinstance(output, EvaluationResult):
        return output.outcome.scope
    if isinstance(output, MemoryWriteDecision) and output.committed_record is not None:
        return output.committed_record.scope
    return None
