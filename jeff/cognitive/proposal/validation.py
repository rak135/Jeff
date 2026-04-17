"""Semantic validation for Proposal Step 1 parsed output."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .contracts import ProposalResult, ProposalResultOption
from .parsing import ParsedProposalGenerationResult, ParsedProposalOption
from ..types import normalized_identity, require_text

_FORBIDDEN_AUTHORITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("approval", re.compile(r"\bapproval\b|\bapprove(?:d|s|ing)?\b")),
    ("permission", re.compile(r"\bpermission\b|\bpermit(?:ted|s|ting)?\b")),
    ("authorization", re.compile(r"\bauthoriz(?:e|ed|es|ing|ation)\b")),
    ("readiness", re.compile(r"\breadiness\b|\bready\b")),
    ("execution", re.compile(r"\bexecution\b|\bexecute(?:d|s|ing)?\b")),
    ("governance", re.compile(r"\bgovernance\b|\bgovern(?:ed|s|ing)?\b")),
    ("selection", re.compile(r"\bselection\b|\bselect(?:ed|s|ing)?\b|\bchoose(?:n|s)?\b")),
    ("allowed", re.compile(r"\ballow(?:ed|s|ing)?\b")),
)


@dataclass(frozen=True, slots=True)
class ProposalValidationIssue:
    code: str
    message: str
    option_index: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "code", require_text(self.code, field_name="code"))
        object.__setattr__(self, "message", require_text(self.message, field_name="message"))
        if self.option_index is not None and self.option_index <= 0:
            raise ValueError("option_index must be greater than zero when present")


class ProposalGenerationValidationError(ValueError):
    """Raised when parsed Proposal output breaks Proposal law."""

    def __init__(self, issues: tuple[ProposalValidationIssue, ...]) -> None:
        if not issues:
            raise ValueError("validation errors must include at least one issue")
        self.issues = issues
        rendered = "; ".join(
            issue.message if issue.option_index is None else f"option {issue.option_index}: {issue.message}"
            for issue in issues
        )
        super().__init__(f"proposal validation failed: {rendered}")


def validate_proposal_generation_result(
    parsed_result: ParsedProposalGenerationResult,
) -> ProposalResult:
    issues: list[ProposalValidationIssue] = []
    proposal_count = parsed_result.proposal_count

    if proposal_count < 0 or proposal_count > 3:
        issues.append(
            ProposalValidationIssue(
                code="proposal_count_out_of_range",
                message="proposal_count must stay inside 0..3",
            )
        )

    if len(parsed_result.options) != proposal_count:
        issues.append(
            ProposalValidationIssue(
                code="option_count_mismatch",
                message="parsed option count must match proposal_count",
            )
        )

    if proposal_count < 2 and parsed_result.scarcity_reason is None:
        issues.append(
            ProposalValidationIssue(
                code="missing_scarcity_reason",
                message="scarcity_reason is required when proposal_count is 0 or 1",
            )
        )

    issues.extend(_collect_duplicate_option_issues(parsed_result.options))

    result_options: list[ProposalResultOption] = []
    for parsed_option in parsed_result.options:
        issues.extend(_collect_option_issues(parsed_option))
        result_options.append(
            ProposalResultOption(
                option_index=parsed_option.option_index,
                proposal_id=f"proposal-{parsed_option.option_index}",
                proposal_type=parsed_option.proposal_type,
                title=parsed_option.title,
                why_now=parsed_option.why_now,
                summary=parsed_option.summary,
                constraints=parsed_option.constraints,
                feasibility=parsed_option.feasibility,
                reversibility=parsed_option.reversibility,
                support_refs=parsed_option.support_refs,
                assumptions=parsed_option.assumptions,
                main_risks=parsed_option.risks,
                blockers=parsed_option.blockers,
                planning_needed=parsed_option.planning_needed,
            )
        )

    if issues:
        raise ProposalGenerationValidationError(tuple(issues))

    return ProposalResult(
        request_id=parsed_result.raw_result.request_id,
        scope=parsed_result.raw_result.scope,
        options=tuple(result_options),
        scarcity_reason=parsed_result.scarcity_reason,
    )


def _collect_option_issues(parsed_option: ParsedProposalOption) -> tuple[ProposalValidationIssue, ...]:
    issues: list[ProposalValidationIssue] = []
    option_index = parsed_option.option_index

    if not parsed_option.assumptions:
        issues.append(
            ProposalValidationIssue(
                code="missing_assumptions",
                message="must include at least one explicit assumption",
                option_index=option_index,
            )
        )

    if not parsed_option.risks:
        issues.append(
            ProposalValidationIssue(
                code="missing_risks",
                message="must include at least one explicit risk",
                option_index=option_index,
            )
        )

    if not parsed_option.constraints and not parsed_option.blockers:
        issues.append(
            ProposalValidationIssue(
                code="missing_constraints_or_blockers",
                message="must include at least one explicit constraint or blocker",
                option_index=option_index,
            )
        )

    for field_name, value in _iter_text_fields(parsed_option):
        normalized_value = normalized_identity(value)
        for marker, pattern in _FORBIDDEN_AUTHORITY_PATTERNS:
            if pattern.search(normalized_value):
                issues.append(
                    ProposalValidationIssue(
                        code="authority_leakage",
                        message=f"{field_name} contains forbidden authority language: {marker}",
                        option_index=option_index,
                    )
                )
                break

    return tuple(issues)


def _collect_duplicate_option_issues(
    options: tuple[ParsedProposalOption, ...],
) -> tuple[ProposalValidationIssue, ...]:
    issues: list[ProposalValidationIssue] = []
    seen_summaries: dict[str, int] = {}
    seen_material_signatures: dict[tuple[str, str, str], int] = {}

    for option in options:
        summary_signature = normalized_identity(option.summary)
        material_signature = (
            normalized_identity(option.title),
            summary_signature,
            normalized_identity(option.why_now),
        )

        duplicate_of = seen_material_signatures.get(material_signature)
        if duplicate_of is None:
            duplicate_of = seen_summaries.get(summary_signature)

        if duplicate_of is not None:
            issues.append(
                ProposalValidationIssue(
                    code="duplicate_option",
                    message=f"is not materially distinct from option {duplicate_of}",
                    option_index=option.option_index,
                )
            )
            continue

        seen_summaries[summary_signature] = option.option_index
        seen_material_signatures[material_signature] = option.option_index

    return tuple(issues)


def _iter_text_fields(parsed_option: ParsedProposalOption) -> tuple[tuple[str, str], ...]:
    text_fields: list[tuple[str, str]] = [
        ("title", parsed_option.title),
        ("summary", parsed_option.summary),
        ("why_now", parsed_option.why_now),
    ]
    text_fields.extend(("assumptions", value) for value in parsed_option.assumptions)
    text_fields.extend(("risks", value) for value in parsed_option.risks)
    text_fields.extend(("constraints", value) for value in parsed_option.constraints)
    text_fields.extend(("blockers", value) for value in parsed_option.blockers)
    if parsed_option.feasibility is not None:
        text_fields.append(("feasibility", parsed_option.feasibility))
    if parsed_option.reversibility is not None:
        text_fields.append(("reversibility", parsed_option.reversibility))
    return tuple(text_fields)

