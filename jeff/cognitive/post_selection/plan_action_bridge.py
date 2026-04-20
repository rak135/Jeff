"""Deterministic fail-closed bridge from bounded planning output into Action."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive import PlanArtifact, materialize_active_step_action
from jeff.contracts import Action
from jeff.core.schemas import Scope

from ..types import PlanStep, require_text


@dataclass(frozen=True, slots=True)
class PlanActionBridgeIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class PlanActionBridgeError(ValueError):
    """Raised when a planning artifact cannot be lawfully evaluated for planned Action formation."""

    def __init__(self, issues: tuple[PlanActionBridgeIssue, ...]) -> None:
        if not issues:
            raise ValueError("plan action bridge errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"plan action bridge failed: {rendered}")


@dataclass(frozen=True, slots=True)
class PlanActionBridgeRequest:
    request_id: str
    plan_artifact: PlanArtifact
    scope: Scope
    basis_state_version: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.plan_artifact, PlanArtifact):
            raise TypeError("plan_artifact must be a PlanArtifact")
        if not isinstance(self.scope, Scope):
            raise TypeError("scope must be a Scope")
        if not isinstance(self.basis_state_version, int):
            raise TypeError("basis_state_version must be an integer")


@dataclass(frozen=True, slots=True)
class PlannedActionBridgeResult:
    bridge_id: str
    action: Action | None
    action_formed: bool
    plan_selected_proposal_id: str | None
    action_basis_summary: str | None
    no_action_reason: str | None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "bridge_id", require_text(self.bridge_id, field_name="bridge_id"))
        if self.plan_selected_proposal_id is not None:
            object.__setattr__(
                self,
                "plan_selected_proposal_id",
                require_text(self.plan_selected_proposal_id, field_name="plan_selected_proposal_id"),
            )
        if self.action_basis_summary is not None:
            object.__setattr__(
                self,
                "action_basis_summary",
                require_text(self.action_basis_summary, field_name="action_basis_summary"),
            )
        if self.no_action_reason is not None:
            object.__setattr__(
                self,
                "no_action_reason",
                require_text(self.no_action_reason, field_name="no_action_reason"),
            )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.action_formed:
            if self.action is None:
                raise ValueError("action_formed bridge results must include action")
            if self.action_basis_summary is None:
                raise ValueError("action_formed bridge results must include action_basis_summary")
            if self.no_action_reason is not None:
                raise ValueError("action_formed bridge results must not include no_action_reason")
        else:
            if self.action is not None:
                raise ValueError("non-formed bridge results must not include action")
            if self.no_action_reason is None:
                raise ValueError("non-formed bridge results must include no_action_reason")


def bridge_plan_to_action(
    request: PlanActionBridgeRequest,
) -> PlannedActionBridgeResult:
    issues: list[PlanActionBridgeIssue] = []

    try:
        request_id = require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        request_id = ""
        issues.append(
            PlanActionBridgeIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    if request.basis_state_version < 0:
        issues.append(
            PlanActionBridgeIssue(
                code="invalid_basis_state_version",
                message="basis_state_version must be zero or greater",
                field_name="basis_state_version",
            )
        )

    plan = request.plan_artifact
    if not plan.intended_steps:
        issues.append(
            PlanActionBridgeIssue(
                code="missing_intended_steps",
                message="plan artifact requires at least one intended step for planned action bridging",
                field_name="plan_artifact.intended_steps",
            )
        )

    if issues:
        raise PlanActionBridgeError(tuple(issues))

    if plan.selected_proposal_id is None:
        return PlannedActionBridgeResult(
            bridge_id=f"plan-action-bridge:{request_id}",
            action=None,
            action_formed=False,
            plan_selected_proposal_id=None,
            action_basis_summary=None,
            no_action_reason=(
                "Plan artifact does not preserve selected proposal linkage required for planned Action formation "
                "in current repo semantics."
            ),
            summary="No Action formed because the plan artifact does not preserve selected proposal linkage.",
        )

    planned_step = plan.active_step or plan.intended_steps[0]
    if not isinstance(planned_step, PlanStep):
        raise PlanActionBridgeError(
            (
                PlanActionBridgeIssue(
                    code="invalid_intended_step",
                    message="plan intended_steps must contain PlanStep instances",
                    field_name="plan_artifact.intended_steps[0]",
                ),
            )
        )

    candidate = materialize_active_step_action(
        plan=plan,
        scope=request.scope,
        basis_state_version=request.basis_state_version,
        require_single_open_step=True,
    )
    if not candidate.action_formed or candidate.action is None:
        return PlannedActionBridgeResult(
            bridge_id=f"plan-action-bridge:{request_id}",
            action=None,
            action_formed=False,
            plan_selected_proposal_id=str(plan.selected_proposal_id),
            action_basis_summary=None,
            no_action_reason=candidate.no_action_reason,
            summary=candidate.summary,
        )

    try:
        action_basis_summary = require_text(
            candidate.action.intent_summary,
            field_name="plan_artifact.intended_steps[0].summary",
        )
    except (TypeError, ValueError) as exc:
        raise PlanActionBridgeError(
            (
                PlanActionBridgeIssue(
                    code="missing_action_basis_summary",
                    message="the single intended step must provide a non-empty summary for Action formation",
                    field_name="plan_artifact.intended_steps[0].summary",
                ),
            )
        ) from exc

    return PlannedActionBridgeResult(
        bridge_id=f"plan-action-bridge:{request_id}",
        action=candidate.action,
        action_formed=True,
        plan_selected_proposal_id=str(plan.selected_proposal_id),
        action_basis_summary=action_basis_summary,
        no_action_reason=None,
        summary=(
            f"Action formed from plan output for proposal {plan.selected_proposal_id} using the active bounded "
            "plan step."
        ),
    )
