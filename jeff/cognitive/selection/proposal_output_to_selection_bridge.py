"""Deterministic fail-closed bridge from preserved proposal output into selection."""

from __future__ import annotations

from dataclasses import dataclass

from ..proposal import ProposalResult
from ..types import require_text
from .contracts import SelectionRequest, SelectionResult
from .decision import run_selection


@dataclass(frozen=True, slots=True)
class SelectionBridgeIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class SelectionBridgeError(ValueError):
    """Raised when preserved proposal output is not lawful enough to attempt selection."""

    def __init__(self, issues: tuple[SelectionBridgeIssue, ...]) -> None:
        if not issues:
            raise ValueError("selection bridge errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"selection bridge failed: {rendered}")


@dataclass(frozen=True, slots=True)
class SelectionBridgeRequest:
    request_id: str
    proposal_result: ProposalResult | None
    selection_id: str | None

    def __post_init__(self) -> None:
        if not isinstance(self.request_id, str):
            raise TypeError("request_id must be a string")
        if self.proposal_result is not None and not isinstance(self.proposal_result, ProposalResult):
            raise TypeError("proposal_result must be a ProposalResult when provided")
        if self.selection_id is not None and not isinstance(self.selection_id, str):
            raise TypeError("selection_id must be a string when provided")


@dataclass(frozen=True, slots=True)
class SelectionBridgeResult:
    bridge_id: str
    proposal_result_id: str
    selection_request_built: bool
    selection_ran: bool
    selection_request: SelectionRequest | None = None
    selection_result: SelectionResult | None = None
    selected_proposal_id: str | None = None
    selection_disposition: str | None = None
    no_selection_reason: str | None = None
    summary: str = ""

    def __post_init__(self) -> None:
        object.__setattr__(self, "bridge_id", require_text(self.bridge_id, field_name="bridge_id"))
        object.__setattr__(
            self,
            "proposal_result_id",
            require_text(self.proposal_result_id, field_name="proposal_result_id"),
        )
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        if self.selected_proposal_id is not None:
            object.__setattr__(
                self,
                "selected_proposal_id",
                require_text(self.selected_proposal_id, field_name="selected_proposal_id"),
            )
        if self.selection_disposition is not None:
            object.__setattr__(
                self,
                "selection_disposition",
                require_text(self.selection_disposition, field_name="selection_disposition"),
            )
        if self.no_selection_reason is not None:
            object.__setattr__(
                self,
                "no_selection_reason",
                require_text(self.no_selection_reason, field_name="no_selection_reason"),
            )

        if self.selection_request is None and self.selection_request_built:
            raise ValueError("selection_request_built requires a preserved selection_request")
        if self.selection_ran and self.selection_result is None:
            raise ValueError("selection_ran requires a preserved selection_result")
        if self.selection_result is not None and not self.selection_ran:
            raise ValueError("selection_result requires selection_ran")
        if self.selection_ran and self.no_selection_reason is not None:
            raise ValueError("selection_ran must not carry no_selection_reason")
        if not self.selection_ran and self.no_selection_reason is None:
            raise ValueError("non-running bridge results must preserve no_selection_reason")
        if self.selection_result is not None:
            if self.selection_request is None:
                raise ValueError("selection_result requires preserved selection_request")
            if self.selection_request.proposal_result.request_id != self.proposal_result_id:
                raise ValueError("selection_request must preserve proposal_result_id linkage")
            if self.selection_result.considered_proposal_ids != self.selection_request.considered_proposal_ids:
                raise ValueError("selection_result must preserve considered proposal ids")
            if self.selection_disposition != self.selection_result.disposition:
                raise ValueError("selection_disposition must match selection_result.disposition")
            if self.selected_proposal_id != self.selection_result.selected_proposal_id:
                raise ValueError("selected_proposal_id must match selection_result.selected_proposal_id")


def build_and_run_selection(request: SelectionBridgeRequest) -> SelectionBridgeResult:
    issues = _collect_request_issues(request)
    if issues:
        raise SelectionBridgeError(tuple(issues))

    proposal_result = request.proposal_result
    assert proposal_result is not None
    assert request.selection_id is not None

    selection_request = SelectionRequest(
        request_id=request.request_id,
        proposal_result=proposal_result,
    )
    selection_result = run_selection(
        request=selection_request,
        selection_id=request.selection_id,
    )
    disposition = selection_result.disposition
    selected_proposal_id = selection_result.selected_proposal_id
    selection_summary = (
        f"selected proposal {selected_proposal_id}"
        if selected_proposal_id is not None
        else f"returned explicit non-selection outcome {disposition}"
    )

    return SelectionBridgeResult(
        bridge_id=f"proposal-output-to-selection:{request.request_id}",
        proposal_result_id=proposal_result.request_id,
        selection_request_built=True,
        selection_ran=True,
        selection_request=selection_request,
        selection_result=selection_result,
        selected_proposal_id=selected_proposal_id,
        selection_disposition=disposition,
        no_selection_reason=None,
        summary=(
            "Selection bridge built a bounded selection request from preserved proposal output, ran selection, "
            f"and preserved selection output that {selection_summary}. Selection output remains selection-only; "
            "it is not action, not permission, not governance, and not execution."
        ),
    )


def _collect_request_issues(request: SelectionBridgeRequest) -> tuple[SelectionBridgeIssue, ...]:
    issues: list[SelectionBridgeIssue] = []

    try:
        require_text(request.request_id, field_name="request_id")
    except (TypeError, ValueError):
        issues.append(
            SelectionBridgeIssue(
                code="invalid_request_id",
                message="request_id must be a non-empty string",
                field_name="request_id",
            )
        )

    if request.proposal_result is None:
        issues.append(
            SelectionBridgeIssue(
                code="missing_proposal_output",
                message="selection bridge requires preserved lawful proposal output",
                field_name="proposal_result",
            )
        )

    try:
        require_text(request.selection_id, field_name="selection_id")
    except (TypeError, ValueError):
        issues.append(
            SelectionBridgeIssue(
                code="missing_selection_id",
                message="selection bridge requires an explicit non-empty selection_id",
                field_name="selection_id",
            )
        )

    return tuple(issues)