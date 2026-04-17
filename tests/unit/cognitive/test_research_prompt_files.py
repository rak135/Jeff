"""Tests for file-backed prompt loading, rendering, and research adoption."""

import pytest

from jeff.cognitive import EvidenceItem, EvidencePack, ResearchRequest, SourceItem, build_research_model_request
from jeff.cognitive.research.formatter import build_research_formatter_model_request
from jeff.cognitive.research.prompt_files import (
    PromptFileNotFoundError,
    PromptFileMalformedError,
    PromptRenderError,
    load_prompt_file,
    render_prompt,
)
from jeff.cognitive.research.synthesis import build_research_model_request


# ---------------------------------------------------------------------------
# Loader — happy path
# ---------------------------------------------------------------------------


def test_load_step1_synthesis_file_returns_both_sections() -> None:
    system_instructions, prompt_template = load_prompt_file("research/STEP1_SYNTHESIS.md")

    assert system_instructions.strip()
    assert prompt_template.strip()


def test_load_step3_formatter_file_returns_both_sections() -> None:
    system_instructions, prompt_template = load_prompt_file("research/STEP3_FORMATTER.md")

    assert system_instructions.strip()
    assert prompt_template.strip()


def test_step1_system_instructions_contain_required_constraints() -> None:
    system_instructions, _ = load_prompt_file("research/STEP1_SYNTHESIS.md")

    assert "Use only the provided evidence." in system_instructions
    assert "Return bounded plain text in the declared section syntax." in system_instructions
    assert "Do not return JSON." in system_instructions
    assert "UNCERTAINTIES section is REQUIRED" in system_instructions


def test_step3_system_instructions_contain_required_constraints() -> None:
    system_instructions, _ = load_prompt_file("research/STEP3_FORMATTER.md")

    assert "Format the provided bounded text artifact into exactly one JSON object" in system_instructions
    assert "No markdown, no code fences, no commentary." in system_instructions
    assert "Preserve only content already materially present in the bounded artifact." in system_instructions


def test_step1_prompt_template_contains_required_structure() -> None:
    _, template = load_prompt_file("research/STEP1_SYNTHESIS.md")

    assert "TASK: bounded research synthesis" in template
    assert "Output bounded plain text using the exact section syntax below." in template
    assert "REQUIRED_BOUNDED_SYNTAX:" in template
    assert "{{QUESTION}}" in template
    assert "{{ALLOWED_CITATION_KEYS}}" in template
    assert "{{BOUNDED_SYNTAX}}" in template
    assert "{{CONSTRAINTS}}" in template
    assert "{{SOURCES}}" in template
    assert "{{EVIDENCE}}" in template
    assert "{{CONTRADICTIONS}}" in template
    assert "{{UNCERTAINTIES}}" in template


def test_step3_prompt_template_contains_required_structure() -> None:
    _, template = load_prompt_file("research/STEP3_FORMATTER.md")

    assert "TASK: formatter fallback over bounded research text" in template
    assert "Use only the provided bounded text artifact." in template
    assert "{{QUESTION}}" in template
    assert "{{ALLOWED_CITATION_KEYS}}" in template
    assert "{{TRANSFORM_FAILURE}}" in template
    assert "{{JSON_SCHEMA}}" in template
    assert "{{BOUNDED_CONTENT}}" in template


# ---------------------------------------------------------------------------
# Loader — failure cases
# ---------------------------------------------------------------------------


def test_load_missing_file_raises_prompt_file_not_found_error() -> None:
    with pytest.raises(PromptFileNotFoundError) as exc_info:
        load_prompt_file("research/DOES_NOT_EXIST.md")

    assert "DOES_NOT_EXIST.md" in str(exc_info.value)


def test_load_missing_file_error_includes_full_path() -> None:
    with pytest.raises(PromptFileNotFoundError) as exc_info:
        load_prompt_file("nonexistent/MISSING_PROMPT.md")

    assert "MISSING_PROMPT.md" in str(exc_info.value)


def test_load_malformed_file_missing_system_section_raises_clear_error(tmp_path) -> None:
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("---PROMPT---\nsome prompt\n", encoding="utf-8")

    from jeff.cognitive.research.prompt_files import _parse_sections

    with pytest.raises(PromptFileMalformedError) as exc_info:
        _parse_sections(bad_file.read_text(encoding="utf-8"), path_hint=str(bad_file))

    assert "---SYSTEM---" in str(exc_info.value)


def test_load_malformed_file_missing_prompt_section_raises_clear_error(tmp_path) -> None:
    bad_file = tmp_path / "bad.md"
    bad_file.write_text("---SYSTEM---\nsome instructions\n", encoding="utf-8")

    from jeff.cognitive.research.prompt_files import _parse_sections

    with pytest.raises(PromptFileMalformedError) as exc_info:
        _parse_sections(bad_file.read_text(encoding="utf-8"), path_hint=str(bad_file))

    assert "---PROMPT---" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------


def test_render_prompt_substitutes_all_placeholders() -> None:
    template = "Hello {{NAME}}, you have {{COUNT}} items."

    result = render_prompt(template, NAME="Jeff", COUNT="3")

    assert result == "Hello Jeff, you have 3 items."


def test_render_prompt_handles_multiline_value() -> None:
    template = "SECTION:\n{{CONTENT}}\nEND"
    multiline_value = "line one\nline two\nline three"

    result = render_prompt(template, CONTENT=multiline_value)

    assert result == "SECTION:\nline one\nline two\nline three\nEND"


def test_render_prompt_fails_for_unresolved_placeholder() -> None:
    template = "Hello {{NAME}}, you are {{AGE}} years old."

    with pytest.raises(PromptRenderError) as exc_info:
        render_prompt(template, NAME="Jeff")

    assert "{{AGE}}" in str(exc_info.value)


def test_render_prompt_with_no_placeholders_returns_template_unchanged() -> None:
    template = "No placeholders here."

    result = render_prompt(template)

    assert result == template


# ---------------------------------------------------------------------------
# Research Step 1 — file-backed integration
# ---------------------------------------------------------------------------


def test_step1_model_request_prompt_is_file_backed() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    # Static content that must come from the file
    assert "TASK: bounded research synthesis" in model_request.prompt
    assert "Output bounded plain text using the exact section syntax below." in model_request.prompt
    assert "REQUIRED_BOUNDED_SYNTAX:" in model_request.prompt
    assert "RECOMMENDATION must be plain text or NONE." in model_request.prompt


def test_step1_system_instructions_are_file_backed() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    assert "Return bounded plain text in the declared section syntax." in model_request.system_instructions
    assert "Do not return JSON." in model_request.system_instructions
    assert "UNCERTAINTIES section is REQUIRED" in model_request.system_instructions


def test_step1_prompt_includes_rendered_dynamic_question() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    assert "QUESTION: What does the evidence support?" in model_request.prompt


def test_step1_prompt_includes_rendered_citation_keys() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    assert "ALLOWED_CITATION_KEYS: S1" in model_request.prompt


def test_step1_prompt_includes_rendered_evidence_lines() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    assert "E1|refs=S1|text=The evidence item text." in model_request.prompt


def test_step1_prompt_includes_bounded_syntax_description() -> None:
    from jeff.cognitive.research.bounded_syntax import STEP1_BOUNDED_SYNTAX_DESCRIPTION

    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack)

    # The bounded syntax description is rendered into the prompt via {{BOUNDED_SYNTAX}}
    assert "SUMMARY:" in model_request.prompt
    assert "FINDINGS:" in model_request.prompt
    assert "cites: S1,S2" in model_request.prompt
    assert STEP1_BOUNDED_SYNTAX_DESCRIPTION in model_request.prompt


# ---------------------------------------------------------------------------
# Research Step 3 — file-backed integration
# ---------------------------------------------------------------------------


def test_step3_formatter_prompt_is_file_backed() -> None:
    from jeff.infrastructure import ModelRequest, ModelResponseMode

    request = _research_request()
    evidence_pack = _evidence_pack()
    primary_request = build_research_model_request(request, evidence_pack)
    bounded_text = "SUMMARY:\nThe summary.\n\nFINDINGS:\n- text: A fact.\n  cites: S1\n\nINFERENCES:\n- An inference.\n\nUNCERTAINTIES:\n- No live validation.\n\nRECOMMENDATION:\nProceed."

    formatter_request = build_research_formatter_model_request(
        request,
        evidence_pack,
        bounded_text,
        transform_failure_reason="test transform failure",
        primary_request=primary_request,
    )

    assert "TASK: formatter fallback over bounded research text" in formatter_request.prompt
    assert "Use only the provided bounded text artifact." in formatter_request.prompt
    assert "Output exactly one JSON object matching json_schema." in formatter_request.prompt


def test_step3_system_instructions_are_file_backed() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()
    primary_request = build_research_model_request(request, evidence_pack)
    bounded_text = "SUMMARY:\nThe summary.\n\nFINDINGS:\n- text: A fact.\n  cites: S1\n\nINFERENCES:\n- An inference.\n\nUNCERTAINTIES:\n- No live validation.\n\nRECOMMENDATION:\nProceed."

    formatter_request = build_research_formatter_model_request(
        request,
        evidence_pack,
        bounded_text,
        transform_failure_reason="test transform failure",
        primary_request=primary_request,
    )

    assert "Format the provided bounded text artifact into exactly one JSON object" in formatter_request.system_instructions
    assert "Preserve only content already materially present in the bounded artifact." in formatter_request.system_instructions


def test_step3_prompt_includes_rendered_bounded_content() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()
    primary_request = build_research_model_request(request, evidence_pack)
    bounded_text = "SUMMARY:\nThe summary.\n\nFINDINGS:\n- text: A fact.\n  cites: S1\n\nINFERENCES:\n- An inference.\n\nUNCERTAINTIES:\n- No live validation.\n\nRECOMMENDATION:\nProceed."

    formatter_request = build_research_formatter_model_request(
        request,
        evidence_pack,
        bounded_text,
        transform_failure_reason="structural parse failure",
        primary_request=primary_request,
    )

    assert "BOUNDED_CONTENT:" in formatter_request.prompt
    assert "TRANSFORM_FAILURE: structural parse failure" in formatter_request.prompt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _research_request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the evidence support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the evidence support?",
        sources=(
            SourceItem(
                source_id="source-a",
                source_type="document",
                title="Source A",
                locator="doc://a",
                snippet="Source A snippet.",
            ),
        ),
        evidence_items=(
            EvidenceItem(text="The evidence item text.", source_refs=("source-a",)),
        ),
    )
