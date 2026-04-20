"""Deterministic parsing for Proposal Step 1 bounded text output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import ProposalType
from .generation import ProposalGenerationRawResult
from ..types import normalize_text_list, require_text

_KEY_VALUE_PATTERN = re.compile(r"^(?P<key>[A-Z0-9_]+): (?P<value>.+)$")
_OPTION_KEY_PATTERN = re.compile(r"^OPTION_(?P<index>[1-3])_(?P<field>[A-Z_]+)$")

NO_ADDITIONAL_SCARCITY_REASON = "No additional scarcity explanation identified from the provided support."
NO_EXPLICIT_ASSUMPTIONS = "No explicit assumptions identified from the provided support."
NO_EXPLICIT_RISKS = "No explicit risks identified from the provided support."
NO_EXPLICIT_CONSTRAINTS = "No explicit constraints identified from the provided support."
NO_EXPLICIT_BLOCKERS = "No explicit blockers identified from the provided support."
NO_EXPLICIT_FEASIBILITY = "No explicit feasibility statement identified from the provided support."
NO_EXPLICIT_REVERSIBILITY = "No explicit reversibility statement identified from the provided support."
NO_SUPPORT_REFS = "none"

_REQUIRED_TOP_LEVEL_FIELDS = ("PROPOSAL_COUNT", "SCARCITY_REASON")

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

    key_value_lines = tuple(_parse_key_value_line(line) for line in lines)
    proposal_count = _parse_proposal_count_from_line(key_value_lines)
    if len(key_value_lines) < len(_REQUIRED_TOP_LEVEL_FIELDS):
        raise ProposalGenerationParseError("proposal output is missing SCARCITY_REASON")
    expected_keys = _expected_keys_for_proposal_count(proposal_count)
    if len(key_value_lines) != len(expected_keys):
        raise ProposalGenerationParseError(
            f"proposal output must contain exactly {len(expected_keys)} non-empty lines for PROPOSAL_COUNT {proposal_count}",
        )

    for line_index, ((key, _value), expected_key) in enumerate(zip(key_value_lines, expected_keys, strict=True), start=1):
        if key != expected_key:
            option_match = _OPTION_KEY_PATTERN.fullmatch(key)
            expected_option_match = _OPTION_KEY_PATTERN.fullmatch(expected_key)
            if option_match is not None and expected_option_match is not None and option_match.group("index") == expected_option_match.group("index"):
                raise ProposalGenerationParseError(
                    f"option {option_match.group('index')} field order drifted: expected {expected_option_match.group('field')} but got {option_match.group('field')}",
                )
            raise ProposalGenerationParseError(
                f"proposal output line {line_index} must be '{expected_key}: ...' but got '{key}: ...'",
            )

    scarcity_reason = _parse_scarcity_reason(key_value_lines[1][1], proposal_count=proposal_count)
    parsed_options = tuple(
        _parse_option_from_lines(option_index=index, lines=key_value_lines[2 + ((index - 1) * len(_REQUIRED_OPTION_FIELDS)):2 + (index * len(_REQUIRED_OPTION_FIELDS))])
        for index in range(1, proposal_count + 1)
    )
    return ParsedProposalGenerationResult(
        raw_result=raw_result,
        proposal_count=proposal_count,
        scarcity_reason=scarcity_reason,
        options=parsed_options,
    )


def _normalized_lines(raw_output_text: str) -> tuple[str, ...]:
    return tuple(line.strip() for line in raw_output_text.splitlines() if line.strip())


def _parse_key_value_line(line: str) -> tuple[str, str]:
    match = _KEY_VALUE_PATTERN.fullmatch(line)
    if match is None:
        raise ProposalGenerationParseError(f"malformed proposal output line: {line!r}")
    key = match.group("key")
    value = require_text(match.group("value"), field_name=key.lower())
    if value == "NONE":
        raise ProposalGenerationParseError(
            f"{key} uses legacy NONE; proposal output must use the canonical fallback text or token",
        )
    return key, value


def _parse_proposal_count_from_line(key_value_lines: tuple[tuple[str, str], ...]) -> int:
    if not key_value_lines:
        raise ProposalGenerationParseError("proposal generation output is empty")
    first_key, raw_count = key_value_lines[0]
    if first_key != "PROPOSAL_COUNT":
        raise ProposalGenerationParseError("proposal output is missing PROPOSAL_COUNT")
    if raw_count not in {"0", "1", "2", "3"}:
        raise ProposalGenerationParseError("PROPOSAL_COUNT must be one of 0, 1, 2, or 3")
    return int(raw_count)


def _expected_keys_for_proposal_count(proposal_count: int) -> tuple[str, ...]:
    keys = list(_REQUIRED_TOP_LEVEL_FIELDS)
    for option_index in range(1, proposal_count + 1):
        keys.extend(f"OPTION_{option_index}_{field_name}" for field_name in _REQUIRED_OPTION_FIELDS)
    return tuple(keys)


def _parse_scarcity_reason(value: str, *, proposal_count: int) -> str | None:
    if value == NO_ADDITIONAL_SCARCITY_REASON:
        if proposal_count < 2:
            raise ProposalGenerationParseError(
                "SCARCITY_REASON fallback is not allowed when PROPOSAL_COUNT is 0 or 1",
            )
        return None
    return require_text(value, field_name="scarcity_reason")


def _parse_option_from_lines(*, option_index: int, lines: tuple[tuple[str, str], ...]) -> ParsedProposalOption:
    if len(lines) != len(_REQUIRED_OPTION_FIELDS):
        raise ProposalGenerationParseError(
            f"option {option_index} must contain exactly {len(_REQUIRED_OPTION_FIELDS)} lines",
        )

    fields: dict[str, str] = {}
    for key, value in lines:
        option_match = _OPTION_KEY_PATTERN.fullmatch(key)
        if option_match is None or int(option_match.group("index")) != option_index:
            raise ProposalGenerationParseError(f"option {option_index} has malformed field key: {key}")
        field_name = option_match.group("field")
        expected_field_name = _REQUIRED_OPTION_FIELDS[len(fields)]
        if field_name != expected_field_name:
            raise ProposalGenerationParseError(
                f"option {option_index} field order drifted: expected {expected_field_name} but got {field_name}",
            )
        fields[field_name] = value

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
        assumptions=_parse_semicolon_list(fields["ASSUMPTIONS"], empty_marker=NO_EXPLICIT_ASSUMPTIONS),
        risks=_parse_semicolon_list(fields["RISKS"], empty_marker=NO_EXPLICIT_RISKS),
        constraints=_parse_semicolon_list(fields["CONSTRAINTS"], empty_marker=NO_EXPLICIT_CONSTRAINTS),
        blockers=_parse_semicolon_list(fields["BLOCKERS"], empty_marker=NO_EXPLICIT_BLOCKERS),
        planning_needed=planning_needed_raw == "yes",
        feasibility=_parse_optional_text_value(fields["FEASIBILITY"], empty_marker=NO_EXPLICIT_FEASIBILITY),
        reversibility=_parse_optional_text_value(fields["REVERSIBILITY"], empty_marker=NO_EXPLICIT_REVERSIBILITY),
        support_refs=_parse_comma_list(fields["SUPPORT_REFS"], empty_marker=NO_SUPPORT_REFS),
    )


def _parse_optional_text_value(value: str, *, empty_marker: str) -> str | None:
    if value == empty_marker:
        return None
    return require_text(value, field_name="value")


def _parse_semicolon_list(value: str, *, empty_marker: str) -> tuple[str, ...]:
    if value == empty_marker:
        return ()
    return tuple(require_text(item.strip(), field_name="value") for item in value.split(";"))


def _parse_comma_list(value: str, *, empty_marker: str) -> tuple[str, ...]:
    if value == empty_marker:
        return ()
    return tuple(require_text(item.strip(), field_name="value") for item in value.split(","))
