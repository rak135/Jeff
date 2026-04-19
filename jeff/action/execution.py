"""Governed execution entry and execution result contracts."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.contracts import Action
from jeff.governance import ActionEntryDecision

from .types import ExecutionStatus, SupportRef, normalize_text_list, require_text


@dataclass(frozen=True, slots=True)
class GovernedExecutionRequest:
    action: Action
    governance_decision: ActionEntryDecision

    def __post_init__(self) -> None:
        if not isinstance(self.action, Action):
            raise TypeError("execution requires a bounded Action")
        if not isinstance(self.governance_decision, ActionEntryDecision):
            raise TypeError("execution requires an ActionEntryDecision governance pass")
        if not self.governance_decision.allowed_now:
            raise ValueError("execution may begin only when governance allowed_now is true")
        if self.governance_decision.governance_outcome != "allowed_now":
            raise ValueError("execution requires an allowed_now governance outcome")
        if self.governance_decision.action_id != str(self.action.action_id):
            raise ValueError("governance decision does not match the action_id being executed")
        if self.governance_decision.action_binding_key != self.action.binding_key:
            raise ValueError("governance decision does not bind to this exact bounded action")


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    governed_request: GovernedExecutionRequest
    execution_status: ExecutionStatus
    output_summary: str | None = None
    artifact_refs: tuple[SupportRef, ...] = ()
    trace_refs: tuple[SupportRef, ...] = ()
    observed_side_effect_notes: tuple[str, ...] = ()
    execution_errors: tuple[str, ...] = ()
    execution_warnings: tuple[str, ...] = ()
    started_at: str | None = None
    ended_at: str | None = None

    def __post_init__(self) -> None:
        if self.output_summary is not None:
            object.__setattr__(
                self,
                "output_summary",
                require_text(self.output_summary, field_name="output_summary"),
            )
        object.__setattr__(
            self,
            "observed_side_effect_notes",
            normalize_text_list(
                self.observed_side_effect_notes,
                field_name="observed_side_effect_notes",
            ),
        )
        object.__setattr__(
            self,
            "execution_errors",
            normalize_text_list(self.execution_errors, field_name="execution_errors"),
        )
        object.__setattr__(
            self,
            "execution_warnings",
            normalize_text_list(self.execution_warnings, field_name="execution_warnings"),
        )

        for ref in self.artifact_refs:
            if ref.ref_type != "artifact":
                raise ValueError("artifact_refs may contain only artifact support refs")
        for ref in self.trace_refs:
            if ref.ref_type != "trace":
                raise ValueError("trace_refs may contain only trace support refs")

    @property
    def action_id(self) -> str:
        return str(self.governed_request.action.action_id)

    @property
    def scope(self):
        return self.governed_request.action.scope


def execute_governed_action(
    request: GovernedExecutionRequest,
    *,
    output_summary: str | None = None,
    execution_status: ExecutionStatus = "completed",
) -> ExecutionResult:
    """Record the current repo-local execution result for a governed bounded action."""

    if not isinstance(request, GovernedExecutionRequest):
        raise TypeError("execution requires a GovernedExecutionRequest")

    return ExecutionResult(
        governed_request=request,
        execution_status=execution_status,
        output_summary=output_summary,
    )
