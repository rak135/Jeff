import pytest

from jeff.cognitive.proposal.prompt_files import (
    PromptFileMalformedError,
    PromptFileNotFoundError,
    PromptRenderError,
    load_prompt_file,
    render_prompt,
)


def test_load_step1_generation_file_returns_both_sections() -> None:
    system_instructions, prompt_template = load_prompt_file("STEP1_GENERATION.md")

    assert system_instructions.strip()
    assert prompt_template.strip()


def test_step1_generation_system_instructions_forbid_authority_leakage_and_padding() -> None:
    system_instructions, _ = load_prompt_file("STEP1_GENERATION.md")

    assert "Proposal generates candidate paths, not authority." in system_instructions
    assert "Do not invent options to satisfy a quota." in system_instructions
    assert (
        "Do not emit permission, approval, authorization, winner, readiness, start-now, or execution-clearance language."
        in system_instructions
    )
    assert "Research may inform proposal but does not replace it." in system_instructions
    assert "Never return more than 3 serious options." in system_instructions


def test_step1_generation_prompt_template_contains_required_output_contract() -> None:
    _, template = load_prompt_file("STEP1_GENERATION.md")

    assert "PROPOSAL_COUNT: <0|1|2|3>" in template
    assert "SCARCITY_REASON: <explicit text or No additional scarcity explanation identified from the provided support.>" in template
    assert "OPTION_n_TYPE:" in template
    assert "OPTION_n_TITLE:" in template
    assert "OPTION_n_SUMMARY:" in template
    assert "OPTION_n_WHY_NOW:" in template
    assert "OPTION_n_ASSUMPTIONS:" in template
    assert "OPTION_n_RISKS:" in template
    assert "OPTION_n_CONSTRAINTS:" in template
    assert "OPTION_n_BLOCKERS:" in template
    assert "OPTION_n_PLANNING_NEEDED:" in template
    assert "OPTION_n_FEASIBILITY:" in template
    assert "OPTION_n_REVERSIBILITY:" in template
    assert "OPTION_n_SUPPORT_REFS:" in template
    assert "Do not invent a second or third option just for variety." in template
    assert "Do not emit approval, permission, authorization, selection, winner, ranking, readiness-to-start, proceed-now, or execution-clearance language." in template
    assert "Use the exact fallback values above instead of NONE." in template
    assert "For PROPOSAL_COUNT 1, make SCARCITY_REASON name the specific narrowing factor" in template
    assert "Do not use fallback text for assumptions, risks, constraints, blockers, feasibility, or reversibility" in template


def test_render_prompt_substitutes_step1_generation_placeholders() -> None:
    _, template = load_prompt_file("STEP1_GENERATION.md")

    rendered = render_prompt(
        template,
        OBJECTIVE="Frame bounded options for the current blocker state.",
        SCOPE="project-1 / wu-1 / run-1",
        TRUTH_SNAPSHOT="Current truth says dependency X is unresolved.",
        CURRENT_CONSTRAINTS="Must stay inside project scope.",
        RESEARCH_SUPPORT="research-1: dependency uncertainty remains open.",
        OTHER_SUPPORT="ctx-1: active blocker is still open.",
        UNCERTAINTIES="Unclear whether dependency X can be resolved today.",
    )

    assert "{{OBJECTIVE}}" not in rendered
    assert "OBJECTIVE:\nFrame bounded options for the current blocker state." in rendered
    assert "RESEARCH_SUPPORT:\nresearch-1: dependency uncertainty remains open." in rendered


def test_render_prompt_fails_for_unresolved_placeholder() -> None:
    _, template = load_prompt_file("STEP1_GENERATION.md")

    with pytest.raises(PromptRenderError) as exc_info:
        render_prompt(template, OBJECTIVE="Only one field")

    assert "{{SCOPE}}" in str(exc_info.value)


def test_load_missing_file_raises_clear_error() -> None:
    with pytest.raises(PromptFileNotFoundError) as exc_info:
        load_prompt_file("DOES_NOT_EXIST.md")

    assert "DOES_NOT_EXIST.md" in str(exc_info.value)


def test_parse_sections_rejects_missing_markers() -> None:
    from jeff.cognitive.proposal.prompt_files import _parse_sections

    with pytest.raises(PromptFileMalformedError, match="---SYSTEM---"):
        _parse_sections("---PROMPT---\nOnly prompt\n", path_hint="bad.md")

    with pytest.raises(PromptFileMalformedError, match="---PROMPT---"):
        _parse_sections("---SYSTEM---\nOnly system\n", path_hint="bad.md")
