import pytest

from jeff.cognitive.selection.prompt_files import (
    PromptFileMalformedError,
    PromptFileNotFoundError,
    PromptRenderError,
    load_prompt_file,
    render_prompt,
)


def test_load_comparison_file_returns_both_sections() -> None:
    system_instructions, prompt_template = load_prompt_file("COMPARISON.md")

    assert system_instructions.strip()
    assert prompt_template.strip()


def test_comparison_prompt_requires_expected_output_contract_fields() -> None:
    _, template = load_prompt_file("COMPARISON.md")

    assert "DISPOSITION: <selected|reject_all|defer|escalate>" in template
    assert "SELECTED_PROPOSAL_ID: <proposal id or NONE>" in template
    assert "PRIMARY_BASIS: <short bounded text>" in template
    assert "MAIN_LOSING_ALTERNATIVE_ID: <proposal id or NONE>" in template
    assert "MAIN_LOSING_REASON: <short bounded text or NONE>" in template
    assert "PLANNING_INSERTION_RECOMMENDED: <yes|no>" in template
    assert "CAUTIONS: <semicolon-separated items or NONE>" in template


def test_comparison_prompt_includes_explicit_anti_authority_language() -> None:
    system_instructions, template = load_prompt_file("COMPARISON.md")

    assert "Selection is bounded choice, not permission." in system_instructions
    assert "Do not emit approval, readiness, permission, authorization, governance, or execution-authority language." in system_instructions
    assert "Selection does not authorize execution." in template
    assert "Selection does not decide approval." in template
    assert "Selection does not decide readiness." in template
    assert "Do not invent a proposal option that was not provided." in template
    assert "Do not return more than one winner." in template


def test_render_prompt_substitutes_comparison_placeholders() -> None:
    _, template = load_prompt_file("COMPARISON.md")

    rendered = render_prompt(
        template,
        REQUEST_ID="selection-request-1",
        SCOPE="project-1 / wu-1 / run-1",
        CONSIDERED_PROPOSAL_IDS="proposal-1,proposal-2",
        SCARCITY_REASON="NONE",
        PROPOSAL_OPTIONS="proposal-1|type=direct_action|summary=Do the bounded change",
    )

    assert "{{REQUEST_ID}}" not in rendered
    assert "REQUEST_ID:\nselection-request-1" in rendered
    assert "CONSIDERED_PROPOSAL_IDS:\nproposal-1,proposal-2" in rendered
    assert "PROPOSAL_OPTIONS:\nproposal-1|type=direct_action|summary=Do the bounded change" in rendered


def test_render_prompt_fails_for_unresolved_placeholder() -> None:
    _, template = load_prompt_file("COMPARISON.md")

    with pytest.raises(PromptRenderError) as exc_info:
        render_prompt(template, REQUEST_ID="Only one field")

    assert "{{SCOPE}}" in str(exc_info.value)


def test_load_missing_file_raises_clear_error() -> None:
    with pytest.raises(PromptFileNotFoundError) as exc_info:
        load_prompt_file("DOES_NOT_EXIST.md")

    assert "DOES_NOT_EXIST.md" in str(exc_info.value)


def test_parse_sections_rejects_missing_markers() -> None:
    from jeff.cognitive.selection.prompt_files import _parse_sections

    with pytest.raises(PromptFileMalformedError, match="---SYSTEM---"):
        _parse_sections("---PROMPT---\nOnly prompt\n", path_hint="bad.md")

    with pytest.raises(PromptFileMalformedError, match="---PROMPT---"):
        _parse_sections("---SYSTEM---\nOnly system\n", path_hint="bad.md")
