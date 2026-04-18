"""Deterministic next-stage routing from a materialized effective proposal."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from ..types import require_text
from .action_resolution import SelectionActionResolutionSource
from .effective_proposal import MaterializedEffectiveProposal

NextStageTarget = Literal[
    "governance",
    "planning",
    "research_followup",
    "terminal_non_selection",
    "escalation_surface",
]
_NonSelectionOutcome = Literal["reject_all", "defer", "escalate"]

_ACTIONABLE_PROPOSAL_TYPE_TO_TARGET: dict[str, NextStageTarget] = {
    "direct_action": "governance",
    "planning_insertion": "planning",
    "investigate": "research_followup",
    "clarify": "research_followup",
    "defer": "terminal_non_selection",
    "escalate": "escalation_surface",
}


@dataclass(frozen=True, slots=True)
class NextStageResolutionIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class NextStageResolutionError(ValueError):
    """Raised when deterministic downstream stage resolution is not lawful."""

    def __init__(self, issues: tuple[NextStageResolutionIssue, ...]) -> None:
        if not issues:
            raise ValueError("next-stage resolution errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"next-stage resolution failed: {rendered}")


@dataclass(frozen=True, slots=True)
class NextStageResolutionRequest:
    request_id: str
    materialized_effective_proposal: MaterializedEffectiveProposal

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.materialized_effective_proposal, MaterializedEffectiveProposal):
            raise TypeError("materialized_effective_proposal must be a MaterializedEffectiveProposal")


@dataclass(frozen=True, slots=True)
class NextStageResolutionResult:
    resolution_id: str
    selection_id: str
    effective_source: SelectionActionResolutionSource
    effective_proposal_id: str | None
    next_stage_target: NextStageTarget
    route_reason: str
    proposal_type: str | None
    non_selection_outcome: _NonSelectionOutcome | None
    action_permitted_to_form: bool
    terminal: bool
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolution_id", require_text(self.resolution_id, field_name="resolution_id"))
        object.__setattr__(self, "selection_id", require_text(self.selection_id, field_name="selection_id"))
        if self.effective_source not in {"selection", "operator_override", "none"}:
            raise ValueError("effective_source must be selection, operator_override, or none")
        if self.effective_proposal_id is not None:
            object.__setattr__(
                self,
                "effective_proposal_id",
                require_text(self.effective_proposal_id, field_name="effective_proposal_id"),
            )
        if self.next_stage_target not in {
            "governance",
            "planning",
            "research_followup",
            "terminal_non_selection",
            "escalation_surface",
        }:
            raise ValueError("next_stage_target must remain a lawful deterministic downstream target")
        object.__setattr__(self, "route_reason", require_text(self.route_reason, field_name="route_reason"))
        if self.proposal_type is not None:
            object.__setattr__(self, "proposal_type", require_text(self.proposal_type, field_name="proposal_type"))
        if self.non_selection_outcome is not None and self.non_selection_outcome not in {"reject_all", "defer", "escalate"}:
            raise ValueError("non_selection_outcome must remain a lawful Selection non-selection outcome")
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.action_permitted_to_form != (self.next_stage_target == "governance"):
            raise ValueError("action_permitted_to_form must only be true for governance next stage")
        if self.terminal != (self.next_stage_target in {"terminal_non_selection", "escalation_surface"}):
            raise ValueError("terminal must only be true for terminal or escalation stop surfaces")
        if self.effective_source == "none":
            if self.effective_proposal_id is not None or self.proposal_type is not None:
                raise ValueError("none effective_source must not carry effective proposal identity or proposal_type")
        elif self.effective_proposal_id is None or self.proposal_type is None:
            raise ValueError("selection and operator_override sources require effective_proposal_id and proposal_type")


def resolve_next_stage(
    request: NextStageResolutionRequest,
) -> NextStageResolutionResult:
    issues = _collect_resolution_issues(request)
    if issues:
        raise NextStageResolutionError(tuple(issues))

    materialized = request.materialized_effective_proposal
    resolution_id = f"next-stage-resolution:{require_text(request.request_id, field_name='request_id')}"
    selection_id = str(materialized.selection_id)
    effective_source = materialized.effective_source

    if effective_source == "none":
        non_selection_outcome = materialized.non_selection_outcome
        next_stage_target = _resolve_none_source_target(non_selection_outcome)
        route_reason = _build_none_source_route_reason(non_selection_outcome)
        summary = _build_none_source_summary(non_selection_outcome)
        return NextStageResolutionResult(
            resolution_id=resolution_id,
            selection_id=selection_id,
            effective_source=effective_source,
            effective_proposal_id=None,
            next_stage_target=next_stage_target,
            route_reason=route_reason,
            proposal_type=None,
            non_selection_outcome=non_selection_outcome,
            action_permitted_to_form=False,
            terminal=next_stage_target in {"terminal_non_selection", "escalation_surface"},
            summary=summary,
        )

    option = materialized.effective_proposal_option
    if option is None:
        raise NextStageResolutionError(
            (
                NextStageResolutionIssue(
                    code="missing_effective_proposal_option",
                    message="effective proposal option is required when effective_source is selection or operator_override",
                    field_name="materialized_effective_proposal.effective_proposal_option",
                ),
            )
        )

    proposal_type = require_text(
        option.proposal_type,
        field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
    )
    next_stage_target = _ACTIONABLE_PROPOSAL_TYPE_TO_TARGET.get(proposal_type)
    if next_stage_target is None:
        raise NextStageResolutionError(
            (
                NextStageResolutionIssue(
                    code="unknown_proposal_type",
                    message="proposal_type does not map to a lawful downstream stage target",
                    field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
                ),
            )
        )

    effective_proposal_id = str(materialized.effective_proposal_id)
    return NextStageResolutionResult(
        resolution_id=resolution_id,
        selection_id=selection_id,
        effective_source=effective_source,
        effective_proposal_id=effective_proposal_id,
        next_stage_target=next_stage_target,
        route_reason=_build_actionable_route_reason(proposal_type),
        proposal_type=proposal_type,
        non_selection_outcome=materialized.non_selection_outcome,
        action_permitted_to_form=next_stage_target == "governance",
        terminal=next_stage_target in {"terminal_non_selection", "escalation_surface"},
        summary=_build_actionable_summary(
            effective_proposal_id=effective_proposal_id,
            proposal_type=proposal_type,
            next_stage_target=next_stage_target,
        ),
    )


def _collect_resolution_issues(
    request: NextStageResolutionRequest,
) -> tuple[NextStageResolutionIssue, ...]:
    issues: list[NextStageResolutionIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            NextStageResolutionIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    materialized = request.materialized_effective_proposal
    if materialized.effective_source not in {"selection", "operator_override", "none"}:
        issues.append(
            NextStageResolutionIssue(
                code="invalid_effective_source",
                message="effective_source must remain selection, operator_override, or none",
                field_name="materialized_effective_proposal.effective_source",
            )
        )
        return tuple(issues)

    if materialized.effective_source == "none":
        if materialized.effective_proposal_id is not None:
            issues.append(
                NextStageResolutionIssue(
                    code="none_source_with_effective_proposal_id",
                    message="none effective_source must not carry effective_proposal_id",
                    field_name="materialized_effective_proposal.effective_proposal_id",
                )
            )
        if materialized.effective_proposal_option is not None:
            issues.append(
                NextStageResolutionIssue(
                    code="none_source_with_effective_proposal_option",
                    message="none effective_source must not carry effective_proposal_option",
                    field_name="materialized_effective_proposal.effective_proposal_option",
                )
            )
        if materialized.non_selection_outcome not in {"reject_all", "defer", "escalate"}:
            issues.append(
                NextStageResolutionIssue(
                    code="unknown_non_selection_outcome",
                    message="none effective_source requires a lawful non_selection_outcome",
                    field_name="materialized_effective_proposal.non_selection_outcome",
                )
            )
        return tuple(issues)

    if materialized.effective_proposal_id is None:
        issues.append(
            NextStageResolutionIssue(
                code="missing_effective_proposal_id",
                message="selection and operator_override sources require effective_proposal_id",
                field_name="materialized_effective_proposal.effective_proposal_id",
            )
        )

    option = materialized.effective_proposal_option
    if option is None:
        issues.append(
            NextStageResolutionIssue(
                code="missing_effective_proposal_option",
                message="selection and operator_override sources require effective_proposal_option",
                field_name="materialized_effective_proposal.effective_proposal_option",
            )
        )
        return tuple(issues)

    if materialized.effective_proposal_id is not None and option.proposal_id != materialized.effective_proposal_id:
        issues.append(
            NextStageResolutionIssue(
                code="effective_proposal_option_mismatch",
                message="effective_proposal_option must match effective_proposal_id",
                field_name="materialized_effective_proposal.effective_proposal_option",
            )
        )

    proposal_type = getattr(option, "proposal_type", None)
    try:
        normalized_proposal_type = require_text(
            proposal_type,
            field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
        )
    except (TypeError, ValueError):
        issues.append(
            NextStageResolutionIssue(
                code="invalid_proposal_type",
                message="effective_proposal_option.proposal_type must be a non-empty string",
                field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
            )
        )
    else:
        if normalized_proposal_type not in _ACTIONABLE_PROPOSAL_TYPE_TO_TARGET:
            issues.append(
                NextStageResolutionIssue(
                    code="unknown_proposal_type",
                    message="proposal_type does not map to a lawful downstream stage target",
                    field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
                )
            )

    return tuple(issues)


def _resolve_none_source_target(non_selection_outcome: _NonSelectionOutcome | None) -> NextStageTarget:
    if non_selection_outcome == "escalate":
        return "escalation_surface"
    if non_selection_outcome in {"reject_all", "defer"}:
        return "terminal_non_selection"
    raise NextStageResolutionError(
        (
            NextStageResolutionIssue(
                code="unknown_non_selection_outcome",
                message="none effective_source requires a lawful non_selection_outcome",
                field_name="materialized_effective_proposal.non_selection_outcome",
            ),
        )
    )


def _build_none_source_route_reason(non_selection_outcome: _NonSelectionOutcome | None) -> str:
    if non_selection_outcome == "reject_all":
        return "Selection returned reject_all with no effective proposal."
    if non_selection_outcome == "defer":
        return "Selection returned defer with no effective proposal."
    if non_selection_outcome == "escalate":
        return "Selection returned escalate with no effective proposal."
    raise NextStageResolutionError(
        (
            NextStageResolutionIssue(
                code="unknown_non_selection_outcome",
                message="none effective_source requires a lawful non_selection_outcome",
                field_name="materialized_effective_proposal.non_selection_outcome",
            ),
        )
    )


def _build_none_source_summary(non_selection_outcome: _NonSelectionOutcome | None) -> str:
    if non_selection_outcome == "reject_all":
        return "Next stage is terminal_non_selection because selection returned reject_all."
    if non_selection_outcome == "defer":
        return "Next stage is terminal_non_selection because selection returned defer."
    if non_selection_outcome == "escalate":
        return "Next stage is escalation_surface because selection returned escalate."
    raise NextStageResolutionError(
        (
            NextStageResolutionIssue(
                code="unknown_non_selection_outcome",
                message="none effective_source requires a lawful non_selection_outcome",
                field_name="materialized_effective_proposal.non_selection_outcome",
            ),
        )
    )


def _build_actionable_route_reason(proposal_type: str) -> str:
    if proposal_type == "direct_action":
        return "Effective proposal is direct_action."
    if proposal_type == "planning_insertion":
        return "Effective proposal requires planning insertion."
    if proposal_type == "investigate":
        return "Effective proposal is investigate and requires research follow-up."
    if proposal_type == "clarify":
        return "Effective proposal is clarify and requires research follow-up."
    if proposal_type == "defer":
        return "Effective proposal is defer."
    if proposal_type == "escalate":
        return "Effective proposal is escalate."
    raise NextStageResolutionError(
        (
            NextStageResolutionIssue(
                code="unknown_proposal_type",
                message="proposal_type does not map to a lawful downstream stage target",
                field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
            ),
        )
    )


def _build_actionable_summary(
    *,
    effective_proposal_id: str,
    proposal_type: str,
    next_stage_target: NextStageTarget,
) -> str:
    if proposal_type == "direct_action":
        return f"Next stage is governance because proposal {effective_proposal_id} is direct_action."
    if proposal_type == "planning_insertion":
        return (
            f"Next stage is planning because proposal {effective_proposal_id} requires planning insertion."
        )
    if proposal_type in {"investigate", "clarify", "defer", "escalate"}:
        return (
            f"Next stage is {next_stage_target} because proposal {effective_proposal_id} is {proposal_type}."
        )
    raise NextStageResolutionError(
        (
            NextStageResolutionIssue(
                code="unknown_proposal_type",
                message="proposal_type does not map to a lawful downstream stage target",
                field_name="materialized_effective_proposal.effective_proposal_option.proposal_type",
            ),
        )
    )
