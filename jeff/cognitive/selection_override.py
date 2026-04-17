"""Explicit downstream operator override contracts for Selection outcomes."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import ProposalId, SelectionId, coerce_proposal_id, coerce_selection_id

from .selection import SelectionDisposition, SelectionResult
from .types import require_text


@dataclass(frozen=True, slots=True)
class OperatorSelectionOverrideValidationIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class OperatorSelectionOverrideValidationError(ValueError):
    """Raised when an operator Selection override request is not lawful."""

    def __init__(self, issues: tuple[OperatorSelectionOverrideValidationIssue, ...]) -> None:
        if not issues:
            raise ValueError("override validation errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"selection override validation failed: {rendered}")


@dataclass(frozen=True, slots=True)
class OperatorSelectionOverrideRequest:
    request_id: str
    selection_result: SelectionResult
    chosen_proposal_id: str
    operator_rationale: str

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.selection_result, SelectionResult):
            raise TypeError("selection_result must be a SelectionResult")
        if not isinstance(self.chosen_proposal_id, str):
            raise TypeError("chosen_proposal_id must be a string")
        if not isinstance(self.operator_rationale, str):
            raise TypeError("operator_rationale must be a string")


@dataclass(frozen=True, slots=True)
class OperatorSelectionOverride:
    override_id: str
    selection_id: SelectionId
    considered_proposal_ids: tuple[ProposalId, ...]
    original_selection_disposition: SelectionDisposition
    original_selected_proposal_id: ProposalId | None
    chosen_proposal_id: ProposalId
    operator_rationale: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "override_id", require_text(self.override_id, field_name="override_id"))
        object.__setattr__(self, "selection_id", coerce_selection_id(str(self.selection_id)))
        object.__setattr__(
            self,
            "considered_proposal_ids",
            tuple(coerce_proposal_id(str(proposal_id)) for proposal_id in self.considered_proposal_ids),
        )
        if self.original_selection_disposition not in {"selected", "reject_all", "defer", "escalate"}:
            raise ValueError("original_selection_disposition must remain a lawful Selection disposition")
        if self.original_selected_proposal_id is not None:
            object.__setattr__(
                self,
                "original_selected_proposal_id",
                coerce_proposal_id(str(self.original_selected_proposal_id)),
            )
        object.__setattr__(self, "chosen_proposal_id", coerce_proposal_id(str(self.chosen_proposal_id)))
        object.__setattr__(
            self,
            "operator_rationale",
            require_text(self.operator_rationale, field_name="operator_rationale"),
        )
        if self.chosen_proposal_id not in self.considered_proposal_ids:
            raise ValueError("chosen_proposal_id must come from the original considered proposal set")


def validate_operator_selection_override(request: OperatorSelectionOverrideRequest) -> None:
    issues: list[OperatorSelectionOverrideValidationIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            OperatorSelectionOverrideValidationIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    chosen_proposal_id: ProposalId | None = None
    try:
        chosen_candidate = require_text(request.chosen_proposal_id, field_name="chosen_proposal_id")
    except (TypeError, ValueError):
        issues.append(
            OperatorSelectionOverrideValidationIssue(
                code="missing_chosen_proposal_id",
                message="chosen_proposal_id must be a non-empty proposal id",
                field_name="chosen_proposal_id",
            )
        )
    else:
        if chosen_candidate.upper() == "NONE":
            issues.append(
                OperatorSelectionOverrideValidationIssue(
                    code="chosen_proposal_none",
                    message="chosen_proposal_id must name a real considered proposal",
                    field_name="chosen_proposal_id",
                )
            )
        else:
            chosen_proposal_id = coerce_proposal_id(chosen_candidate)
            if chosen_proposal_id not in request.selection_result.considered_proposal_ids:
                issues.append(
                    OperatorSelectionOverrideValidationIssue(
                        code="chosen_proposal_out_of_set",
                        message="chosen_proposal_id must come from the original considered proposal set",
                        field_name="chosen_proposal_id",
                    )
                )

    try:
        require_text(request.operator_rationale, field_name="operator_rationale")
    except (TypeError, ValueError):
        issues.append(
            OperatorSelectionOverrideValidationIssue(
                code="blank_operator_rationale",
                message="operator_rationale must contain explicit bounded text",
                field_name="operator_rationale",
            )
        )

    if not request.selection_result.considered_proposal_ids:
        issues.append(
            OperatorSelectionOverrideValidationIssue(
                code="empty_considered_proposals",
                message="selection_result must preserve at least one considered proposal id",
                field_name="selection_result",
            )
        )

    if issues:
        raise OperatorSelectionOverrideValidationError(tuple(issues))


def build_operator_selection_override(
    request: OperatorSelectionOverrideRequest,
) -> OperatorSelectionOverride:
    validate_operator_selection_override(request)
    return OperatorSelectionOverride(
        override_id=f"selection-override:{require_text(request.request_id, field_name='request_id')}",
        selection_id=request.selection_result.selection_id,
        considered_proposal_ids=request.selection_result.considered_proposal_ids,
        original_selection_disposition=request.selection_result.disposition,
        original_selected_proposal_id=request.selection_result.selected_proposal_id,
        chosen_proposal_id=coerce_proposal_id(
            require_text(request.chosen_proposal_id, field_name="chosen_proposal_id")
        ),
        operator_rationale=require_text(request.operator_rationale, field_name="operator_rationale"),
    )
