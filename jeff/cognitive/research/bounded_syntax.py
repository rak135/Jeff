"""Hard syntax contract for Step 1 bounded research text."""

from __future__ import annotations

import re

from ..types import normalize_text_list, require_text
from .errors import ResearchSynthesisValidationError

STEP1_SUMMARY_SECTION = "SUMMARY"
STEP1_FINDINGS_SECTION = "FINDINGS"
STEP1_INFERENCES_SECTION = "INFERENCES"
STEP1_UNCERTAINTIES_SECTION = "UNCERTAINTIES"
STEP1_RECOMMENDATION_SECTION = "RECOMMENDATION"

STEP1_REQUIRED_SECTION_NAMES = (
    STEP1_SUMMARY_SECTION,
    STEP1_FINDINGS_SECTION,
    STEP1_INFERENCES_SECTION,
    STEP1_UNCERTAINTIES_SECTION,
    STEP1_RECOMMENDATION_SECTION,
)
STEP1_REQUIRED_HEADERS = tuple(f"{section_name}:" for section_name in STEP1_REQUIRED_SECTION_NAMES)

STEP1_FINDING_TEXT_PREFIX = "- text: "
STEP1_FINDING_CITES_PREFIX = "  cites: "
STEP1_BULLET_PREFIX = "- "
STEP1_NONE_LITERAL = "NONE"
STEP1_CITATION_KEY_PATTERN = re.compile(r"^S[1-9][0-9]*$")

STEP1_BOUNDED_SYNTAX_DESCRIPTION = "\n".join(
    [
        "SUMMARY:",
        "<one bounded paragraph>",
        "",
        "FINDINGS:",
        "- text: <finding 1>",
        "  cites: S1,S2",
        "",
        "INFERENCES:",
        "- <inference 1>",
        "",
        "UNCERTAINTIES:",
        "- <uncertainty 1>",
        "- or if no uncertainties identified: No explicit uncertainties identified from the provided evidence.",
        "",
        "RECOMMENDATION:",
        "<text or NONE>",
    ]
)


def validate_step1_bounded_text(artifact_text: str) -> None:
    sections = _split_step1_sections(artifact_text)
    validate_step1_summary_text(sections[STEP1_SUMMARY_SECTION])
    _validate_findings_section_text(sections[STEP1_FINDINGS_SECTION])
    _validate_bullet_section_text(sections[STEP1_INFERENCES_SECTION], section_name="inferences")
    _validate_bullet_section_text(sections[STEP1_UNCERTAINTIES_SECTION], section_name="uncertainties")
    _validate_recommendation_section_text(sections[STEP1_RECOMMENDATION_SECTION])


def validate_step1_summary_text(summary: str) -> str:
    try:
        return require_text(summary, field_name="summary")
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc


def validate_step1_bullet_items(items: tuple[str, ...], *, section_name: str) -> tuple[str, ...]:
    try:
        normalized_items = normalize_text_list(items, field_name=section_name)
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc
    if not normalized_items:
        raise ResearchSynthesisValidationError(f"{section_name} must contain at least one item")
    return normalized_items


def validate_step1_recommendation_text(recommendation: str | None) -> str | None:
    if recommendation is None:
        return None
    try:
        normalized_recommendation = require_text(recommendation, field_name="recommendation")
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc
    if normalized_recommendation == STEP1_NONE_LITERAL:
        return None
    return normalized_recommendation


def validate_step1_citation_keys(citation_keys: tuple[str, ...], *, field_name: str = "citation_keys") -> tuple[str, ...]:
    try:
        normalized_keys = normalize_text_list(citation_keys, field_name=field_name)
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc
    if not normalized_keys:
        raise ResearchSynthesisValidationError(f"{field_name} must contain at least one citation key")

    duplicates: list[str] = []
    seen: set[str] = set()
    for citation_key in normalized_keys:
        if not STEP1_CITATION_KEY_PATTERN.fullmatch(citation_key):
            raise ResearchSynthesisValidationError(f"{field_name} entries must match S<number>: {citation_key}")
        if citation_key in seen and citation_key not in duplicates:
            duplicates.append(citation_key)
        seen.add(citation_key)

    if duplicates:
        raise ResearchSynthesisValidationError(f"{field_name} must not repeat citation keys: {duplicates}")
    return normalized_keys


def _split_step1_sections(artifact_text: str) -> dict[str, str]:
    try:
        normalized_text = require_text(artifact_text, field_name="artifact_text")
    except (TypeError, ValueError) as exc:
        raise ResearchSynthesisValidationError(str(exc)) from exc
    stripped_text = normalized_text.strip()
    if "```" in normalized_text:
        raise ResearchSynthesisValidationError("step1 bounded text must not include fenced code blocks")
    if stripped_text.startswith("{"):
        raise ResearchSynthesisValidationError("step1 bounded text must not be JSON")

    parsed_sections: dict[str, str] = {}
    current_section: str | None = None
    current_lines: list[str] = []
    expected_headers = list(STEP1_REQUIRED_HEADERS)

    for raw_line in normalized_text.splitlines():
        line = raw_line.rstrip()
        stripped_line = line.strip()
        if stripped_line in STEP1_REQUIRED_HEADERS:
            if not expected_headers:
                raise ResearchSynthesisValidationError(f"unexpected extra section header: {stripped_line}")
            expected_header = expected_headers.pop(0)
            if stripped_line != expected_header:
                expected_name = expected_header.removesuffix(":")
                raise ResearchSynthesisValidationError(
                    f"step1 bounded text requires {expected_name} section in canonical order",
                )
            if current_section is not None:
                parsed_sections[current_section] = "\n".join(current_lines).strip()
            current_section = stripped_line.removesuffix(":")
            current_lines = []
            continue

        if current_section is None:
            if stripped_line:
                raise ResearchSynthesisValidationError("step1 bounded text must start with SUMMARY:")
            continue
        current_lines.append(line)

    if current_section is not None:
        parsed_sections[current_section] = "\n".join(current_lines).strip()

    missing_sections = [section_name for section_name in STEP1_REQUIRED_SECTION_NAMES if section_name not in parsed_sections]
    if missing_sections:
        raise ResearchSynthesisValidationError(f"step1 bounded text is missing required sections: {missing_sections}")
    return parsed_sections


def _validate_findings_section_text(section_text: str) -> None:
    lines = [line.rstrip() for line in section_text.splitlines() if line.strip()]
    if not lines:
        raise ResearchSynthesisValidationError("findings must contain at least one entry")
    if len(lines) % 2 != 0:
        raise ResearchSynthesisValidationError("findings entries must use paired text and cites lines")

    for index in range(0, len(lines), 2):
        text_line = lines[index]
        cites_line = lines[index + 1]
        if not text_line.startswith(STEP1_FINDING_TEXT_PREFIX):
            raise ResearchSynthesisValidationError("findings entries must start with '- text: '")
        if not cites_line.startswith(STEP1_FINDING_CITES_PREFIX):
            raise ResearchSynthesisValidationError("findings entries must keep a following '  cites: ' line")
        try:
            require_text(
                text_line[len(STEP1_FINDING_TEXT_PREFIX) :],
                field_name="findings.text",
            )
        except (TypeError, ValueError) as exc:
            raise ResearchSynthesisValidationError(str(exc)) from exc
        citation_keys = tuple(
            item.strip()
            for item in cites_line[len(STEP1_FINDING_CITES_PREFIX) :].split(",")
        )
        validate_step1_citation_keys(citation_keys, field_name="findings.citation_keys")


def _validate_bullet_section_text(section_text: str, *, section_name: str) -> None:
    lines = [line.rstrip() for line in section_text.splitlines() if line.strip()]
    if not lines:
        raise ResearchSynthesisValidationError(f"{section_name} must contain at least one item")
    for line in lines:
        if not line.startswith(STEP1_BULLET_PREFIX):
            raise ResearchSynthesisValidationError(
                f"{section_name} entries must start with '{STEP1_BULLET_PREFIX}'",
            )
        try:
            require_text(line[len(STEP1_BULLET_PREFIX) :], field_name=section_name)
        except (TypeError, ValueError) as exc:
            raise ResearchSynthesisValidationError(str(exc)) from exc


def _validate_recommendation_section_text(section_text: str) -> None:
    validate_step1_recommendation_text(section_text)
