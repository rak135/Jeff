"""Deterministic parsing for Proposal Step 1 bounded text output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import ProposalType
from .generation import ProposalGenerationRawResult
from ..types import normalize_text_list, require_text

_KEY_VALUE_PATTERN = re.compile(r"^(?P<key>[A-Z0-9_]+): (?P<value>.+)$")
_OPTION_KEY_PATTERN = re.compile(r"^OPTION_(?P<index>[1-3])_(?P<field>[A-Z_]+)$")

_REQUIRED_OPTION_FIELDS = (
    "TYPE",
    "TITLE",
    "SUMMARY",
    "WHY_NOW",
    "ASSUMPTIONS",
    "RISKS",
    "CONSTRAINTS",
    "BLOCKERS",
    "PLANNING_NEEDED",
    "FEASIBILITY",
    "REVERSIBILITY",
    "SUPPORT_REFS",
)
_ALLOWED_PROPOSAL_TYPES = {
    "direct_action",
    "investigate",
    "clarify",
    "defer",
    "escalate",
    "planning_insertion",
}


class ProposalGenerationParseError(ValueError):
    """Raised when Proposal Step 1 raw output does not match the bounded syntax."""


@dataclass(frozen=True, slots=True)
class ParsedProposalOption:
    option_index: int
    proposal_type: ProposalType
    title: str
    summary: str
    why_now: str
    assumptions: tuple[str, ...]
    risks: tuple[str, ...]
    constraints: tuple[str, ...]
    blockers: tuple[str, ...]
    planning_needed: bool
    feasibility: str | None
    reversibility: str | None
    support_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.option_index <= 0:
            raise ValueError("option_index must be greater than zero")
        object.__setattr__(self, "title", require_text(self.title, field_name="title"))
        object.__setattr__(self, "summary", require_text(self.summary, field_name="summary"))
        object.__setattr__(self, "why_now", require_text(self.why_now, field_name="why_now"))
        object.__setattr__(self, "assumptions", normalize_text_list(self.assumptions, field_name="assumptions"))
        object.__setattr__(self, "risks", normalize_text_list(self.risks, field_name="risks"))
        object.__setattr__(self, "constraints", normalize_text_list(self.constraints, field_name="constraints"))
        object.__setattr__(self, "blockers", normalize_text_list(self.blockers, field_name="blockers"))
        object.__setattr__(self, "support_refs", normalize_text_list(self.support_refs, field_name="support_refs"))
        if self.feasibility is not None:
            object.__setattr__(self, "feasibility", require_text(self.feasibility, field_name="feasibility"))
        if self.reversibility is not None:
            object.__setattr__(
                self,
                "reversibility",
                require_text(self.reversibility, field_name="reversibility"),
            )


@dataclass(frozen=True, slots=True)
class ParsedProposalGenerationResult:
    raw_result: ProposalGenerationRawResult
    proposal_count: int
    scarcity_reason: str | None
    options: tuple[ParsedProposalOption, ...]

    def __post_init__(self) -> None:
        if self.proposal_count < 0 or self.proposal_count > 3:
            raise ValueError("proposal_count must stay inside 0..3")
        if len(self.options) != self.proposal_count:
            raise ValueError("parsed option count must match proposal_count")
        if self.scarcity_reason is not None:
            object.__setattr__(
                self,
                "scarcity_reason",
                require_text(self.scarcity_reason, field_name="scarcity_reason"),
            )


def parse_proposal_generation_result(
    raw_result: ProposalGenerationRawResult,
) -> ParsedProposalGenerationResult:
    lines = _normalized_lines(raw_result.raw_output_text)
    if not lines:
        raise ProposalGenerationParseError("proposal generation output is empty")

    top_level_values: dict[str, str] = {}
    option_values: dict[int, dict[str, str]] = {}

    for line in lines:
        match = _KEY_VALUE_PATTERN.fullmatch(line)
        if match is None:
            raise ProposalGenerationParseError(f"malformed proposal output line: {line!r}")

        key = match.group("key")
        value = require_text(match.group("value"), field_name=key.lower())

        option_match = _OPTION_KEY_PATTERN.fullmatch(key)
        if option_match is not None:
            option_index = int(option_match.group("index"))
            field_name = option_match.group("field")
            option_fields = option_values.setdefault(option_index, {})
            if field_name in option_fields:
                raise ProposalGenerationParseError(f"duplicate proposal option field: {key}")
            option_fields[field_name] = value
            continue

        if key in top_level_values:
            raise ProposalGenerationParseError(f"duplicate proposal top-level field: {key}")
        top_level_values[key] = value

    proposal_count = _parse_proposal_count(top_level_values)
    scarcity_reason = _parse_optional_text(
        top_level_values,
        field_name="SCARCITY_REASON",
        required=True,
    )
    if proposal_count == 0 and option_values:
        raise ProposalGenerationParseError("0-option proposal output must not include OPTION_n fields")

    expected_option_indexes = tuple(range(1, proposal_count + 1))
    if tuple(sorted(option_values.keys())) != expected_option_indexes:
        raise ProposalGenerationParseError(
            f"proposal option indexes must be exactly {expected_option_indexes or ()}",
        )

    parsed_options = tuple(
        _parse_option(option_index=index, fields=option_values[index])
        for index in expected_option_indexes
    )
    return ParsedProposalGenerationResult(
        raw_result=raw_result,
        proposal_count=proposal_count,
        scarcity_reason=scarcity_reason,
        options=parsed_options,
    )


def _normalized_lines(raw_output_text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in raw_output_text.splitlines() if line.strip())


def _parse_proposal_count(top_level_values: dict[str, str]) -> int:
    raw_count = top_level_values.get("PROPOSAL_COUNT")
    if raw_count is None:
        raise ProposalGenerationParseError("proposal output is missing PROPOSAL_COUNT")
    if raw_count not in {"0", "1", "2", "3"}:
        raise ProposalGenerationParseError("PROPOSAL_COUNT must be one of 0, 1, 2, or 3")
    return int(raw_count)


def _parse_option(*, option_index: int, fields: dict[str, str]) -> ParsedProposalOption:
    missing_fields = [field_name for field_name in _REQUIRED_OPTION_FIELDS if field_name not in fields]
    if missing_fields:
        raise ProposalGenerationParseError(
            f"option {option_index} is missing required fields: {missing_fields}",
        )
    unexpected_fields = [field_name for field_name in fields if field_name not in _REQUIRED_OPTION_FIELDS]
    if unexpected_fields:
        raise ProposalGenerationParseError(
            f"option {option_index} has unexpected fields: {unexpected_fields}",
        )

    proposal_type = fields["TYPE"]
    if proposal_type not in _ALLOWED_PROPOSAL_TYPES:
        raise ProposalGenerationParseError(f"option {option_index} has unsupported TYPE: {proposal_type}")

    planning_needed_raw = fields["PLANNING_NEEDED"]
    if planning_needed_raw not in {"yes", "no"}:
        raise ProposalGenerationParseError(
            f"option {option_index} PLANNING_NEEDED must be 'yes' or 'no'",
        )

    return ParsedProposalOption(
        option_index=option_index,
        proposal_type=proposal_type,  # type: ignore[arg-type]
        title=fields["TITLE"],
        summary=fields["SUMMARY"],
        why_now=fields["WHY_NOW"],
        assumptions=_parse_semicolon_list(fields["ASSUMPTIONS"]),
        risks=_parse_semicolon_list(fields["RISKS"]),
        constraints=_parse_semicolon_list(fields["CONSTRAINTS"]),
        blockers=_parse_semicolon_list(fields["BLOCKERS"]),
        planning_needed=planning_needed_raw == "yes",
        feasibility=_parse_none_or_text(fields["FEASIBILITY"]),
        reversibility=_parse_none_or_text(fields["REVERSIBILITY"]),
        support_refs=_parse_comma_list(fields["SUPPORT_REFS"]),
    )


def _parse_optional_text(
    values: dict[str, str],
    *,
    field_name: str,
    required: bool,
) -> str | None:
    raw_value = values.get(field_name)
    if raw_value is None:
        if required:
            raise ProposalGenerationParseError(f"proposal output is missing {field_name}")
        return None
    return _parse_none_or_text(raw_value)


def _parse_none_or_text(value: str) -> str | None:
    if value == "NONE":
        return None
    return require_text(value, field_name="value")


def _parse_semicolon_list(value: str) -> tuple[str, ...]:
    if value == "NONE":
        return ()
    return tuple(require_text(item.strip(), field_name="value") for item in value.split(";"))


def _parse_comma_list(value: str) -> tuple[str, ...]:
    if value == "NONE":
        return ()
    return tuple(require_text(item.strip(), field_name="value") for item in value.split(","))
