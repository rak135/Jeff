"""Deterministic semantic validation for parsed Selection comparison output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import cast

from jeff.core.schemas import ProposalId, coerce_proposal_id

from ..types import normalized_identity, require_text
from .comparison import SelectionComparisonRequest
from .contracts import SelectionDisposition
from .parsing import ParsedSelectionComparison

_ALLOWED_DISPOSITIONS = {"selected", "reject_all", "defer", "escalate"}
_TEXT_FILLER_VALUES = {"none", "n a", "na", "not applicable", "not available", "no caution"}

_FORBIDDEN_AUTHORITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("approved", re.compile(r"\bapproved\b|\bapprove(?:s|d|ing)?\b")),
    ("permission_granted", re.compile(r"\bpermission granted\b")),
    ("authorized", re.compile(r"\bauthoriz(?:ed|e|es|ing|ation)\b")),
    ("ready_to_execute", re.compile(r"\bready to execute\b")),
    ("safe_to_execute", re.compile(r"\bsafe to execute\b")),
    ("can_proceed_now", re.compile(r"\bcan proceed now\b")),
    ("execution_approved", re.compile(r"\bexecution approved\b")),
)

_SECOND_WINNER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("multiple_selected_ids", re.compile(r"\bproposal-[a-z0-9_-]+\b\s+(?:and|&)\s+\bproposal-[a-z0-9_-]+\b")),
    ("multiple_winner_language", re.compile(r"\bboth winners\b|\btwo winners\b|\bmultiple winners\b")),
)


@dataclass(frozen=True, slots=True)
class SelectionComparisonValidationIssue:
    code: str
    message: str
    field_name: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.field_name is not None:
            object.__setattr__(self, "field_name", require_text(self.field_name, field_name="field_name"))


class SelectionComparisonValidationError(ValueError):
    """Raised when parsed Selection comparison output breaks Selection law."""

    def __init__(self, issues: tuple[SelectionComparisonValidationIssue, ...]) -> None:
        if not issues:
            raise ValueError("validation errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.field_name is None else f"{issue.field_name}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"selection validation failed: {rendered}")


@dataclass(frozen=True, slots=True)
class ValidatedSelectionComparison:
    request_id: str
    considered_proposal_ids: tuple[ProposalId, ...]
    disposition: SelectionDisposition
    selected_proposal_id: ProposalId | None
    primary_basis: str
    main_losing_alternative_id: ProposalId | None
    main_losing_reason: str | None
    planning_insertion_recommended: bool
    cautions: str
    parsed_comparison: ParsedSelectionComparison

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(
            self,
            "considered_proposal_ids",
            tuple(coerce_proposal_id(str(proposal_id)) for proposal_id in self.considered_proposal_ids),
        )
        if self.selected_proposal_id is not None:
            object.__setattr__(
                self,
                "selected_proposal_id",
                coerce_proposal_id(str(self.selected_proposal_id)),
            )
        if self.main_losing_alternative_id is not None:
            object.__setattr__(
                self,
                "main_losing_alternative_id",
                coerce_proposal_id(str(self.main_losing_alternative_id)),
            )
        object.__setattr__(self, "primary_basis", require_text(self.primary_basis, field_name="primary_basis"))
        object.__setattr__(self, "cautions", require_text(self.cautions, field_name="cautions"))
        if self.main_losing_reason is not None:
            object.__setattr__(
                self,
                "main_losing_reason",
                require_text(self.main_losing_reason, field_name="main_losing_reason"),
            )


def validate_selection_comparison(
    parsed_comparison: ParsedSelectionComparison,
    *,
    request: SelectionComparisonRequest,
) -> ValidatedSelectionComparison:
    issues: list[SelectionComparisonValidationIssue] = []
    considered_ids = request.considered_proposal_ids
    considered_id_texts = {str(proposal_id) for proposal_id in considered_ids}

    if parsed_comparison.request_id != request.request_id:
        issues.append(
            SelectionComparisonValidationIssue(
                code="request_id_mismatch",
                message="parsed comparison request_id must match the authoritative Selection comparison request",
                field_name="request_id",
            )
        )

    disposition = parsed_comparison.disposition
    if disposition not in _ALLOWED_DISPOSITIONS:
        issues.append(
            SelectionComparisonValidationIssue(
                code="unsupported_disposition",
                message=f"disposition must be one of {sorted(_ALLOWED_DISPOSITIONS)}",
                field_name="disposition",
            )
        )

    if disposition == "selected":
        if parsed_comparison.selected_proposal_id is None:
            issues.append(
                SelectionComparisonValidationIssue(
                    code="missing_selected_proposal_id",
                    message="selected disposition requires selected_proposal_id",
                    field_name="selected_proposal_id",
                )
            )
        elif str(parsed_comparison.selected_proposal_id) not in considered_id_texts:
            issues.append(
                SelectionComparisonValidationIssue(
                    code="selected_proposal_out_of_set",
                    message="selected_proposal_id must come from the considered proposal set",
                    field_name="selected_proposal_id",
                )
            )
    elif parsed_comparison.selected_proposal_id is not None:
        issues.append(
            SelectionComparisonValidationIssue(
                code="non_selected_disposition_with_selected_id",
                message="non-selected dispositions must not carry selected_proposal_id",
                field_name="selected_proposal_id",
            )
        )

    if (
        parsed_comparison.main_losing_alternative_id is not None
        and str(parsed_comparison.main_losing_alternative_id) not in considered_id_texts
    ):
        issues.append(
            SelectionComparisonValidationIssue(
                code="losing_alternative_out_of_set",
                message="main_losing_alternative_id must come from the considered proposal set",
                field_name="main_losing_alternative_id",
            )
        )

    issues.extend(_validate_required_text_field("primary_basis", parsed_comparison.primary_basis))
    issues.extend(
        _validate_required_text_field(
            "main_losing_reason",
            parsed_comparison.main_losing_reason,
            required=parsed_comparison.main_losing_alternative_id is not None,
        )
    )
    issues.extend(_validate_required_text_field("cautions", parsed_comparison.cautions, required=True))

    issues.extend(_collect_authority_issues(parsed_comparison))
    issues.extend(_collect_second_winner_issues(parsed_comparison))

    if issues:
        raise SelectionComparisonValidationError(tuple(issues))

    return ValidatedSelectionComparison(
        request_id=request.request_id,
        considered_proposal_ids=considered_ids,
        disposition=cast(SelectionDisposition, disposition),
        selected_proposal_id=parsed_comparison.selected_proposal_id,
        primary_basis=parsed_comparison.primary_basis,
        main_losing_alternative_id=parsed_comparison.main_losing_alternative_id,
        main_losing_reason=parsed_comparison.main_losing_reason,
        planning_insertion_recommended=parsed_comparison.planning_insertion_recommended,
        cautions=cast(str, parsed_comparison.cautions),
        parsed_comparison=parsed_comparison,
    )


def _validate_required_text_field(
    field_name: str,
    value: str | None,
    *,
    required: bool = True,
) -> tuple[SelectionComparisonValidationIssue, ...]:
    if value is None:
        if required:
            return (
                SelectionComparisonValidationIssue(
                    code=f"missing_{field_name}",
                    message=f"{field_name} must contain explicit bounded text",
                    field_name=field_name,
                ),
            )
        return ()

    normalized = normalized_identity(value)
    if normalized in _TEXT_FILLER_VALUES:
        return (
            SelectionComparisonValidationIssue(
                code=f"blank_{field_name}",
                message=f"{field_name} must not use blank filler text",
                field_name=field_name,
            ),
        )
    return ()


def _collect_authority_issues(
    parsed_comparison: ParsedSelectionComparison,
) -> tuple[SelectionComparisonValidationIssue, ...]:
    issues: list[SelectionComparisonValidationIssue] = []
    for field_name, value in _iter_text_fields(parsed_comparison):
        normalized = normalized_identity(value)
        for marker, pattern in _FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(normalized):
                issues.append(
                    SelectionComparisonValidationIssue(
                        code="authority_leakage",
                        message=f"{field_name} contains forbidden authority language: {marker}",
                        field_name=field_name,
                    )
                )
                break
    return tuple(issues)


def _collect_second_winner_issues(
    parsed_comparison: ParsedSelectionComparison,
) -> tuple[SelectionComparisonValidationIssue, ...]:
    issues: list[SelectionComparisonValidationIssue] = []
    for field_name, value in _iter_text_fields(parsed_comparison):
        normalized = normalized_identity(value)
        for marker, pattern in _SECOND_WINNER_PATTERNS:
            if pattern.search(normalized):
                issues.append(
                    SelectionComparisonValidationIssue(
                        code="multiple_winner_implication",
                        message=f"{field_name} implies multiple selected winners: {marker}",
                        field_name=field_name,
                    )
                )
                break
    return tuple(issues)


def _iter_text_fields(
    parsed_comparison: ParsedSelectionComparison,
) -> tuple[tuple[str, str], ...]:
    text_fields = [("primary_basis", parsed_comparison.primary_basis)]
    if parsed_comparison.main_losing_reason is not None:
        text_fields.append(("main_losing_reason", parsed_comparison.main_losing_reason))
    if parsed_comparison.cautions is not None:
        text_fields.append(("cautions", parsed_comparison.cautions))
    return tuple(text_fields)
