"""Deterministic Action formation from a materialized effective proposal."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.contracts import Action
from jeff.core.schemas import Scope

from .selection_effective_proposal import MaterializedEffectiveProposal
from .types import require_text

_DIRECTLY_ACTIONABLE_PROPOSAL_TYPES = {"direct_action"}


@dataclass(frozen=True, slots=True)
class ActionFormationIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class ActionFormationError(ValueError):
    """Raised when a concrete actionable materialized proposal cannot lawfully form Action."""

    def __init__(self, issues: tuple[ActionFormationIssue, ...]) -> None:
        if not issues:
            raise ValueError("action formation errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"action formation failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ActionFormationRequest:
    request_id: str
    materialized_effective_proposal: MaterializedEffectiveProposal
    scope: Scope
    basis_state_version: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.materialized_effective_proposal, MaterializedEffectiveProposal):
            raise TypeError("materialized_effective_proposal must be a MaterializedEffectiveProposal")
        if not isinstance(self.scope, Scope):
            raise TypeError("scope must be a Scope")
        if not isinstance(self.basis_state_version, int):
            raise TypeError("basis_state_version must be an integer")


@dataclass(frozen=True, slots=True)
class FormedActionResult:
    formation_id: str
    selection_id: str
    effective_source: str
    effective_proposal_id: str | None
    action: Action | None
    action_formed: bool
    no_action_reason: str | None
    proposal_type: str | None = None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "formation_id", require_text(self.formation_id, field_name="formation_id"))
        object.__setattr__(self, "selection_id", require_text(self.selection_id, field_name="selection_id"))
        if self.effective_source not in {"selection", "operator_override", "none"}:
            raise ValueError("effective_source must be selection, operator_override, or none")
        if self.effective_proposal_id is not None:
            object.__setattr__(
                self,
                "effective_proposal_id",
                require_text(self.effective_proposal_id, field_name="effective_proposal_id"),
            )
        if self.no_action_reason is not None:
            object.__setattr__(self, "no_action_reason", require_text(self.no_action_reason, field_name="no_action_reason"))
        if self.proposal_type is not None:
            object.__setattr__(self, "proposal_type", require_text(self.proposal_type, field_name="proposal_type"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.action_formed:
            if self.action is None:
                raise ValueError("action_formed results must include action")
            if self.no_action_reason is not None:
                raise ValueError("action_formed results must not include no_action_reason")
        else:
            if self.action is not None:
                raise ValueError("non-formed action results must not include action")
            if self.no_action_reason is None:
                raise ValueError("non-formed action results must include no_action_reason")


def form_action_from_materialized_proposal(
    request: ActionFormationRequest,
) -> FormedActionResult:
    materialized = request.materialized_effective_proposal

    if materialized.effective_source == "none":
        return FormedActionResult(
            formation_id=f"action-formation:{require_text(request.request_id, field_name='request_id')}",
            selection_id=str(materialized.selection_id),
            effective_source=materialized.effective_source,
            effective_proposal_id=None,
            action=None,
            action_formed=False,
            no_action_reason="No actionable proposal basis is available from the resolved selection outcome.",
            summary="No Action formed because there is no effective proposal basis.",
        )

    option = materialized.effective_proposal_option
    if option is None:
        raise ActionFormationError(
            (
                ActionFormationIssue(
                    code="missing_effective_proposal_option",
                    message="effective proposal option is required when materialized source is actionable",
                    field_name="materialized_effective_proposal.effective_proposal_option",
                ),
            )
        )

    if option.proposal_type not in _DIRECTLY_ACTIONABLE_PROPOSAL_TYPES:
        return FormedActionResult(
            formation_id=f"action-formation:{require_text(request.request_id, field_name='request_id')}",
            selection_id=str(materialized.selection_id),
            effective_source=materialized.effective_source,
            effective_proposal_id=str(materialized.effective_proposal_id),
            action=None,
            action_formed=False,
            no_action_reason=(
                f"Proposal type {option.proposal_type} does not directly form Action in current repo semantics."
            ),
            proposal_type=option.proposal_type,
            summary=(
                f"No Action formed for proposal {materialized.effective_proposal_id} because "
                f"{option.proposal_type} is not directly actionable."
            ),
        )

    issues: list[ActionFormationIssue] = []
    try:
        intent_summary = require_text(option.summary, field_name="effective_proposal_option.summary")
    except (TypeError, ValueError):
        intent_summary = ""
        issues.append(
            ActionFormationIssue(
                code="missing_intent_summary",
                message="effective proposal summary is required for direct Action formation",
                field_name="materialized_effective_proposal.effective_proposal_option.summary",
            )
        )

    if issues:
        raise ActionFormationError(tuple(issues))

    action = Action(
        action_id=f"action:{materialized.selection_id}:{materialized.effective_proposal_id}",
        scope=request.scope,
        intent_summary=intent_summary,
        basis_state_version=request.basis_state_version,
        basis_label=(
            f"selection_source={materialized.effective_source};"
            f"selection_id={materialized.selection_id};"
            f"proposal_id={materialized.effective_proposal_id}"
        ),
    )
    return FormedActionResult(
        formation_id=f"action-formation:{require_text(request.request_id, field_name='request_id')}",
        selection_id=str(materialized.selection_id),
        effective_source=materialized.effective_source,
        effective_proposal_id=str(materialized.effective_proposal_id),
        action=action,
        action_formed=True,
        no_action_reason=None,
        proposal_type=option.proposal_type,
        summary=(
            f"Action formed from {materialized.effective_source} basis for proposal "
            f"{materialized.effective_proposal_id} with proposal type {option.proposal_type}."
        ),
    )
