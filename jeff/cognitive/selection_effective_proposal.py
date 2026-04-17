"""Deterministic effective-proposal materialization after Selection action-basis resolution."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.core.schemas import ProposalId, SelectionId, coerce_proposal_id, coerce_selection_id

from .proposal import ProposalResult, ProposalResultOption
from .selection import SelectionDisposition
from .selection_action_resolution import ResolvedSelectionActionBasis, SelectionActionResolutionSource
from .types import require_text


@dataclass(frozen=True, slots=True)
class SelectionEffectiveProposalMaterializationIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class SelectionEffectiveProposalMaterializationError(ValueError):
    """Raised when effective proposal materialization linkage is not lawful."""

    def __init__(self, issues: tuple[SelectionEffectiveProposalMaterializationIssue, ...]) -> None:
        if not issues:
            raise ValueError("materialization errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"selection effective proposal materialization failed: {rendered}")


@dataclass(frozen=True, slots=True)
class SelectionEffectiveProposalRequest:
    request_id: str
    proposal_result: ProposalResult
    resolved_basis: ResolvedSelectionActionBasis

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if not isinstance(self.proposal_result, ProposalResult):
            raise TypeError("proposal_result must be a ProposalResult")
        if not isinstance(self.resolved_basis, ResolvedSelectionActionBasis):
            raise TypeError("resolved_basis must be a ResolvedSelectionActionBasis")


@dataclass(frozen=True, slots=True)
class MaterializedEffectiveProposal:
    materialization_id: str
    selection_id: SelectionId
    effective_source: SelectionActionResolutionSource
    effective_proposal_id: ProposalId | None
    effective_proposal_option: ProposalResultOption | None
    operator_override_present: bool
    original_selection_disposition: SelectionDisposition
    non_selection_outcome: str | None
    considered_proposal_ids: tuple[ProposalId, ...]
    summary: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "materialization_id", require_text(self.materialization_id, field_name="materialization_id"))
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
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))

        if self.effective_source not in {"selection", "operator_override", "none"}:
            raise ValueError("effective_source must be selection, operator_override, or none")
        if self.original_selection_disposition not in {"selected", "reject_all", "defer", "escalate"}:
            raise ValueError("original_selection_disposition must remain a lawful Selection disposition")
        if self.effective_source == "none":
            if self.effective_proposal_id is not None or self.effective_proposal_option is not None:
                raise ValueError("none effective_source must not carry an effective proposal")
        else:
            if self.effective_proposal_id is None or self.effective_proposal_option is None:
                raise ValueError("selection and operator_override sources require an effective proposal id and option")
            if self.effective_proposal_option.proposal_id != self.effective_proposal_id:
                raise ValueError("effective_proposal_option must match effective_proposal_id")
            if self.effective_proposal_id not in self.considered_proposal_ids:
                raise ValueError("effective_proposal_id must come from the considered proposal set")


def materialize_effective_proposal(
    request: SelectionEffectiveProposalRequest,
) -> MaterializedEffectiveProposal:
    issues = _collect_materialization_issues(request)
    if issues:
        raise SelectionEffectiveProposalMaterializationError(tuple(issues))

    resolved_basis = request.resolved_basis
    effective_option = _find_effective_option(request.proposal_result, resolved_basis.effective_proposal_id)

    return MaterializedEffectiveProposal(
        materialization_id=f"selection-effective-proposal:{require_text(request.request_id, field_name='request_id')}",
        selection_id=resolved_basis.selection_id,
        effective_source=resolved_basis.effective_source,
        effective_proposal_id=resolved_basis.effective_proposal_id,
        effective_proposal_option=effective_option,
        operator_override_present=resolved_basis.operator_override_present,
        original_selection_disposition=resolved_basis.original_selection_disposition,
        non_selection_outcome=resolved_basis.non_selection_outcome,
        considered_proposal_ids=resolved_basis.considered_proposal_ids,
        summary=_build_materialization_summary(resolved_basis),
    )


def _collect_materialization_issues(
    request: SelectionEffectiveProposalRequest,
) -> tuple[SelectionEffectiveProposalMaterializationIssue, ...]:
    issues: list[SelectionEffectiveProposalMaterializationIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            SelectionEffectiveProposalMaterializationIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    proposal_ids = tuple(option.proposal_id for option in request.proposal_result.options)
    if proposal_ids != request.resolved_basis.considered_proposal_ids:
        issues.append(
            SelectionEffectiveProposalMaterializationIssue(
                code="proposal_set_mismatch",
                message="proposal_result option ids must match resolved_basis considered_proposal_ids exactly",
                field_name="proposal_result.options",
            )
        )

    if request.resolved_basis.effective_source == "none":
        if request.resolved_basis.effective_proposal_id is not None:
            issues.append(
                SelectionEffectiveProposalMaterializationIssue(
                    code="none_source_with_effective_proposal_id",
                    message="none effective_source must not carry effective_proposal_id",
                    field_name="resolved_basis.effective_proposal_id",
                )
            )
        return tuple(issues)

    if request.resolved_basis.effective_proposal_id is None:
        issues.append(
            SelectionEffectiveProposalMaterializationIssue(
                code="missing_effective_proposal_id",
                message="selection and operator_override sources require effective_proposal_id",
                field_name="resolved_basis.effective_proposal_id",
            )
        )
    elif request.resolved_basis.effective_proposal_id not in proposal_ids:
        issues.append(
            SelectionEffectiveProposalMaterializationIssue(
                code="effective_proposal_not_found",
                message="effective_proposal_id must match a real proposal_result option",
                field_name="resolved_basis.effective_proposal_id",
            )
        )

    return tuple(issues)


def _find_effective_option(
    proposal_result: ProposalResult,
    effective_proposal_id: ProposalId | None,
) -> ProposalResultOption | None:
    if effective_proposal_id is None:
        return None
    for option in proposal_result.options:
        if option.proposal_id == effective_proposal_id:
            return option
    return None


def _build_materialization_summary(
    resolved_basis: ResolvedSelectionActionBasis,
) -> str:
    if resolved_basis.effective_source == "none":
        return (
            f"No effective proposal option materialized; original selection disposition was "
            f"{resolved_basis.original_selection_disposition}"
            + (
                f" with non-selection outcome {resolved_basis.non_selection_outcome}."
                if resolved_basis.non_selection_outcome is not None
                else "."
            )
        )
    return (
        f"Materialized proposal option {resolved_basis.effective_proposal_id} from "
        f"{resolved_basis.effective_source}; original selection disposition was "
        f"{resolved_basis.original_selection_disposition}."
    )
