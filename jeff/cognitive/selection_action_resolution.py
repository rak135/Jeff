"""Deterministic downstream action-basis resolution after Selection and optional override."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from jeff.core.schemas import ProposalId, SelectionId, coerce_proposal_id, coerce_selection_id

from .selection import SelectionDisposition, SelectionResult
from .selection_override import OperatorSelectionOverride
from .types import require_text

SelectionActionResolutionSource = Literal["selection", "operator_override", "none"]


@dataclass(frozen=True, slots=True)
class SelectionActionResolutionIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class SelectionActionResolutionError(ValueError):
    """Raised when Selection-to-action resolution linkage is not lawful."""

    def __init__(self, issues: tuple[SelectionActionResolutionIssue, ...]) -> None:
        if not issues:
            raise ValueError("resolution errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"selection action resolution failed: {rendered}")


@dataclass(frozen=True, slots=True)
class SelectionActionResolutionRequest:
    request_id: str
    selection_result: SelectionResult
    operator_override: OperatorSelectionOverride | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.selection_result, SelectionResult):
            raise TypeError("selection_result must be a SelectionResult")
        if self.operator_override is not None and not isinstance(self.operator_override, OperatorSelectionOverride):
            raise TypeError("operator_override must be an OperatorSelectionOverride or None")


@dataclass(frozen=True, slots=True)
class ResolvedSelectionActionBasis:
    resolution_id: str
    selection_id: SelectionId
    considered_proposal_ids: tuple[ProposalId, ...]
    effective_proposal_id: ProposalId | None
    effective_source: SelectionActionResolutionSource
    original_selection_disposition: SelectionDisposition
    original_selected_proposal_id: ProposalId | None
    operator_override_present: bool
    non_selection_outcome: Literal["reject_all", "defer", "escalate"] | None
    operator_override_chosen_proposal_id: ProposalId | None = None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "resolution_id", require_text(self.resolution_id, field_name="resolution_id"))
        object.__setattr__(self, "selection_id", coerce_selection_id(str(self.selection_id)))
        object.__setattr__(
            self,
            "considered_proposal_ids",
            tuple(coerce_proposal_id(str(proposal_id)) for proposal_id in self.considered_proposal_ids),
        )
        if self.effective_proposal_id is not None:
            object.__setattr__(
                self,
                "effective_proposal_id",
                coerce_proposal_id(str(self.effective_proposal_id)),
            )
        if self.original_selected_proposal_id is not None:
            object.__setattr__(
                self,
                "original_selected_proposal_id",
                coerce_proposal_id(str(self.original_selected_proposal_id)),
            )
        if self.operator_override_chosen_proposal_id is not None:
            object.__setattr__(
                self,
                "operator_override_chosen_proposal_id",
                coerce_proposal_id(str(self.operator_override_chosen_proposal_id)),
            )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.effective_source not in {"selection", "operator_override", "none"}:
            raise ValueError("effective_source must be selection, operator_override, or none")
        if self.original_selection_disposition not in {"selected", "reject_all", "defer", "escalate"}:
            raise ValueError("original_selection_disposition must remain a lawful Selection disposition")
        if self.effective_source == "none" and self.effective_proposal_id is not None:
            raise ValueError("none effective_source must not carry an effective_proposal_id")
        if self.effective_source != "none" and self.effective_proposal_id is None:
            raise ValueError("selection and operator_override sources require an effective_proposal_id")
        if self.effective_proposal_id is not None and self.effective_proposal_id not in self.considered_proposal_ids:
            raise ValueError("effective_proposal_id must come from the considered proposal set")
        if self.operator_override_present != (self.operator_override_chosen_proposal_id is not None):
            raise ValueError("operator override linkage must match operator_override_present")


def resolve_selection_action_basis(
    request: SelectionActionResolutionRequest,
) -> ResolvedSelectionActionBasis:
    issues = _collect_resolution_issues(request)
    if issues:
        raise SelectionActionResolutionError(tuple(issues))

    selection_result = request.selection_result
    operator_override = request.operator_override
    if operator_override is None:
        effective_source: SelectionActionResolutionSource
        effective_proposal_id: ProposalId | None
        if selection_result.selected_proposal_id is not None:
            effective_source = "selection"
            effective_proposal_id = selection_result.selected_proposal_id
        else:
            effective_source = "none"
            effective_proposal_id = None
    else:
        effective_source = "operator_override"
        effective_proposal_id = operator_override.chosen_proposal_id

    return ResolvedSelectionActionBasis(
        resolution_id=f"selection-action-resolution:{require_text(request.request_id, field_name='request_id')}",
        selection_id=selection_result.selection_id,
        considered_proposal_ids=selection_result.considered_proposal_ids,
        effective_proposal_id=effective_proposal_id,
        effective_source=effective_source,
        original_selection_disposition=selection_result.disposition,
        original_selected_proposal_id=selection_result.selected_proposal_id,
        operator_override_present=operator_override is not None,
        non_selection_outcome=selection_result.non_selection_outcome,
        operator_override_chosen_proposal_id=(
            None if operator_override is None else operator_override.chosen_proposal_id
        ),
        summary=_build_resolution_summary(
            effective_source=effective_source,
            selection_result=selection_result,
            effective_proposal_id=effective_proposal_id,
        ),
    )


def _collect_resolution_issues(
    request: SelectionActionResolutionRequest,
) -> tuple[SelectionActionResolutionIssue, ...]:
    issues: list[SelectionActionResolutionIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            SelectionActionResolutionIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    operator_override = request.operator_override
    selection_result = request.selection_result
    if operator_override is None:
        return tuple(issues)

    if operator_override.selection_id != selection_result.selection_id:
        issues.append(
            SelectionActionResolutionIssue(
                code="selection_id_mismatch",
                message="operator override selection_id must match selection_result.selection_id",
                field_name="operator_override.selection_id",
            )
        )

    if operator_override.considered_proposal_ids != selection_result.considered_proposal_ids:
        issues.append(
            SelectionActionResolutionIssue(
                code="considered_proposal_ids_mismatch",
                message="operator override considered_proposal_ids must match the original Selection considered set",
                field_name="operator_override.considered_proposal_ids",
            )
        )

    if operator_override.chosen_proposal_id not in selection_result.considered_proposal_ids:
        issues.append(
            SelectionActionResolutionIssue(
                code="override_choice_out_of_set",
                message="operator override chosen_proposal_id must come from the original Selection considered set",
                field_name="operator_override.chosen_proposal_id",
            )
        )

    return tuple(issues)


def _build_resolution_summary(
    *,
    effective_source: SelectionActionResolutionSource,
    selection_result: SelectionResult,
    effective_proposal_id: ProposalId | None,
) -> str:
    disposition = selection_result.disposition
    if effective_source == "selection":
        return (
            f"Downstream basis follows selection choice {effective_proposal_id}; "
            f"original selection disposition was {disposition}."
        )
    if effective_source == "operator_override":
        return (
            f"Downstream basis follows operator override choice {effective_proposal_id}; "
            f"original selection disposition was {disposition}."
        )
    return f"No downstream proposal basis; original selection disposition was {disposition}."
