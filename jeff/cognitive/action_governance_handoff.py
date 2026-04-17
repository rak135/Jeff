"""Deterministic governance handoff from formed Action results."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.contracts import Action
from jeff.governance import ActionEntryDecision, Approval, CurrentTruthSnapshot, Policy, evaluate_action_entry

from .action_formation import FormedActionResult
from .types import require_text


@dataclass(frozen=True, slots=True)
class ActionGovernanceHandoffIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ActionGovernanceHandoffError(ValueError):
    """Raised when Action should be handoff-capable but lawful governance handoff cannot proceed."""

    def __init__(self, issues: tuple[ActionGovernanceHandoffIssue, ...]) -> None:
        if not issues:
            raise ValueError("governance handoff errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"action governance handoff failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ActionGovernanceHandoffRequest:
    request_id: str
    formed_action_result: FormedActionResult
    policy: Policy
    approval: Approval | None
    truth: CurrentTruthSnapshot

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.formed_action_result, FormedActionResult):
            raise TypeError("formed_action_result must be a FormedActionResult")
        if not isinstance(self.policy, Policy):
            raise TypeError("policy must be a Policy")
        if self.approval is not None and not isinstance(self.approval, Approval):
            raise TypeError("approval must be an Approval or None")
        if not isinstance(self.truth, CurrentTruthSnapshot):
            raise TypeError("truth must be a CurrentTruthSnapshot")


@dataclass(frozen=True, slots=True)
class GovernedActionHandoffResult:
    handoff_id: str
    selection_id: str
    effective_source: str
    effective_proposal_id: str | None
    action_formed: bool
    action: Action | None
    governance_result: ActionEntryDecision | None
    governance_evaluated: bool
    no_governance_reason: str | None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "handoff_id", require_text(self.handoff_id, field_name="handoff_id"))
        object.__setattr__(self, "selection_id", require_text(self.selection_id, field_name="selection_id"))
        if self.effective_source not in {"selection", "operator_override", "none"}:
            raise ValueError("effective_source must be selection, operator_override, or none")
        if self.effective_proposal_id is not None:
            object.__setattr__(
                self,
                "effective_proposal_id",
                require_text(self.effective_proposal_id, field_name="effective_proposal_id"),
            )
        if self.no_governance_reason is not None:
            object.__setattr__(
                self,
                "no_governance_reason",
                require_text(self.no_governance_reason, field_name="no_governance_reason"),
            )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.governance_evaluated:
            if self.action is None or self.governance_result is None:
                raise ValueError("evaluated governance handoffs must preserve action and governance_result")
            if self.no_governance_reason is not None:
                raise ValueError("evaluated governance handoffs must not include no_governance_reason")
        else:
            if self.governance_result is not None:
                raise ValueError("non-evaluated governance handoffs must not include governance_result")
            if self.no_governance_reason is None:
                raise ValueError("non-evaluated governance handoffs must include no_governance_reason")


def handoff_action_to_governance(
    request: ActionGovernanceHandoffRequest,
) -> GovernedActionHandoffResult:
    formed = request.formed_action_result

    if not formed.action_formed:
        return GovernedActionHandoffResult(
            handoff_id=f"action-governance-handoff:{require_text(request.request_id, field_name='request_id')}",
            selection_id=formed.selection_id,
            effective_source=formed.effective_source,
            effective_proposal_id=formed.effective_proposal_id,
            action_formed=False,
            action=None,
            governance_result=None,
            governance_evaluated=False,
            no_governance_reason="No governance evaluation occurred because no Action was formed.",
            summary="No governance evaluation occurred because there was no formed Action.",
        )

    issues: list[ActionGovernanceHandoffIssue] = []
    if formed.action is None:
        issues.append(
            ActionGovernanceHandoffIssue(
                code="missing_action",
                message="formed Action handoff requires a real Action contract",
                field_name="formed_action_result.action",
            )
        )

    if issues:
        raise ActionGovernanceHandoffError(tuple(issues))

    governance_result = evaluate_action_entry(
        action=formed.action,
        policy=request.policy,
        approval=request.approval,
        truth=request.truth,
    )
    return GovernedActionHandoffResult(
        handoff_id=f"action-governance-handoff:{require_text(request.request_id, field_name='request_id')}",
        selection_id=formed.selection_id,
        effective_source=formed.effective_source,
        effective_proposal_id=formed.effective_proposal_id,
        action_formed=True,
        action=formed.action,
        governance_result=governance_result,
        governance_evaluated=True,
        no_governance_reason=None,
        summary=(
            f"Governance evaluated Action from {formed.effective_source} basis with outcome "
            f"{governance_result.governance_outcome}."
        ),
    )
