"""Deterministic parsing for Selection comparison bounded text output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from jeff.core.schemas import ProposalId, coerce_proposal_id

from ..types import require_text
from .comparison_runtime import SelectionRawComparisonResult

_KEY_VALUE_PATTERN = re.compile(r"^(?P<key>[A-Z_]+): (?P<value>.+)$")

_REQUIRED_FIELDS = (
    "DISPOSITION",
    "SELECTED_PROPOSAL_ID",
    "PRIMARY_BASIS",
    "MAIN_LOSING_ALTERNATIVE_ID",
    "MAIN_LOSING_REASON",
    "PLANNING_INSERTION_RECOMMENDED",
    "CAUTIONS",
)


class SelectionComparisonParseError(ValueError):
    """Raised when Selection comparison raw output does not match the bounded syntax."""


@dataclass(frozen=True, slots=True)
class ParsedSelectionComparison:
    request_id: str
    disposition: str
    selected_proposal_id: ProposalId | None
    primary_basis: str
    main_losing_alternative_id: ProposalId | None
    main_losing_reason: str | None
    planning_insertion_recommended: bool
    cautions: str | None
    raw_model_output_text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "disposition", require_text(self.disposition, field_name="disposition"))
        object.__setattr__(self, "primary_basis", require_text(self.primary_basis, field_name="primary_basis"))
        object.__setattr__(
            self,
            "raw_model_output_text",
            require_text(self.raw_model_output_text, field_name="raw_model_output_text"),
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
        if self.main_losing_reason is not None:
            object.__setattr__(
                self,
                "main_losing_reason",
                require_text(self.main_losing_reason, field_name="main_losing_reason"),
            )
        if self.cautions is not None:
            object.__setattr__(self, "cautions", require_text(self.cautions, field_name="cautions"))


def parse_selection_comparison_result(
    raw_result: SelectionRawComparisonResult,
) -> ParsedSelectionComparison:
    lines = _normalized_lines(raw_result.model_output_text)
    if not lines:
        raise SelectionComparisonParseError("selection comparison output is empty")

    values: dict[str, str] = {}
    for line in lines:
        match = _KEY_VALUE_PATTERN.fullmatch(line)
        if match is None:
            raise SelectionComparisonParseError(f"malformed selection comparison output line: {line!r}")

        key = match.group("key")
        value = require_text(match.group("value"), field_name=key.lower())

        if key not in _REQUIRED_FIELDS:
            raise SelectionComparisonParseError(f"unexpected selection comparison field: {key}")
        if key in values:
            raise SelectionComparisonParseError(f"duplicate selection comparison field: {key}")
        values[key] = value

    missing_fields = [field_name for field_name in _REQUIRED_FIELDS if field_name not in values]
    if missing_fields:
        raise SelectionComparisonParseError(
            f"selection comparison output is missing required fields: {missing_fields}",
        )

    planning_insertion_recommended = _parse_yes_no(
        values["PLANNING_INSERTION_RECOMMENDED"],
        field_name="PLANNING_INSERTION_RECOMMENDED",
    )

    return ParsedSelectionComparison(
        request_id=raw_result.request_id,
        disposition=values["DISPOSITION"],
        selected_proposal_id=_parse_none_or_proposal_id(values["SELECTED_PROPOSAL_ID"]),
        primary_basis=values["PRIMARY_BASIS"],
        main_losing_alternative_id=_parse_none_or_proposal_id(values["MAIN_LOSING_ALTERNATIVE_ID"]),
        main_losing_reason=_parse_none_or_text(values["MAIN_LOSING_REASON"]),
        planning_insertion_recommended=planning_insertion_recommended,
        cautions=_parse_none_or_text(values["CAUTIONS"]),
        raw_model_output_text=raw_result.model_output_text,
    )


def _normalized_lines(raw_output_text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in raw_output_text.splitlines() if line.strip())


def _parse_yes_no(value: str, *, field_name: str) -> bool:
    if value == "yes":
        return True
    if value == "no":
        return False
    raise SelectionComparisonParseError(f"{field_name} must be 'yes' or 'no'")


def _parse_none_or_text(value: str) -> str | None:
    if value == "NONE":
        return None
    return require_text(value, field_name="value")


def _parse_none_or_proposal_id(value: str) -> ProposalId | None:
    if value == "NONE":
        return None
    return coerce_proposal_id(value)
