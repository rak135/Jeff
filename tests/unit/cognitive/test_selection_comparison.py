import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection.comparison import (
    SelectionComparisonPromptBundle,
    SelectionComparisonRequest,
    build_selection_comparison_prompt_bundle,
)
from jeff.cognitive.selection.prompt_files import PromptRenderError
from jeff.core.schemas import Scope


def _selection_request(*, include_second_option: bool = True) -> SelectionComparisonRequest:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    options = [
        ProposalResultOption(
            option_index=1,
            proposal_id="proposal-1",
            proposal_type="direct_action",
            title="Implement the bounded change",
            why_now="Current truth keeps this bounded path viable.",
            summary="Implement the bounded change in the current scope.",
            support_refs=("support-1", "support-2"),
            assumptions=("Dependency Y stays stable.",),
            main_risks=("Regression risk remains bounded.",),
            blockers=(),
            constraints=("Stay inside project scope.",),
            reversibility="Reversible with rollback.",
            planning_needed=False,
        ),
    ]
    if include_second_option:
        options.append(
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="clarify",
                title="Clarify the missing boundary first",
                why_now="Boundary ambiguity still matters.",
                summary="Clarify the remaining boundary before stronger choice.",
                support_refs=(),
                assumptions=(),
                main_risks=(),
                blockers=("Boundary is still unclear.",),
                constraints=(),
                reversibility=None,
                planning_needed=True,
            ),
        )

    selection_request = SelectionComparisonRequest.from_selection_request(
        selection_request=_base_selection_request(
            scope=scope,
            options=tuple(options),
            scarcity_reason=None if include_second_option else "Only one serious option remains.",
        )
    )
    return selection_request


def _base_selection_request(
    *,
    scope: Scope,
    options: tuple[ProposalResultOption, ...],
    scarcity_reason: str | None,
):
    from jeff.cognitive.selection import SelectionRequest

    return SelectionRequest(
        request_id="selection-request-1",
        proposal_result=ProposalResult(
            request_id="proposal-request-1",
            scope=scope,
            options=options,
            scarcity_reason=scarcity_reason,
        ),
    )


def test_selection_comparison_request_can_be_built_from_selection_request() -> None:
    request = _selection_request()

    assert request.request_id == "selection-request-1"
    assert request.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert request.scope.run_id == "run-1"


def test_build_selection_comparison_prompt_bundle_returns_bounded_bundle() -> None:
    request = _selection_request()

    bundle = build_selection_comparison_prompt_bundle(request)

    assert isinstance(bundle, SelectionComparisonPromptBundle)
    assert bundle.request_id == "selection-request-1"
    assert bundle.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert "Selection is bounded choice, not permission." in bundle.system_prompt


def test_prompt_text_includes_expected_proposal_ids_and_stable_option_blocks() -> None:
    request = _selection_request()

    bundle = build_selection_comparison_prompt_bundle(request)

    assert "CONSIDERED_PROPOSAL_IDS:\nproposal-1,proposal-2" in bundle.prompt_text
    assert "SCARCITY_REASON:\nNONE" in bundle.prompt_text
    assert "OPTION_1:" in bundle.prompt_text
    assert "proposal_id=proposal-1" in bundle.prompt_text
    assert "proposal_type=direct_action" in bundle.prompt_text
    assert "OPTION_2:" in bundle.prompt_text
    assert "proposal_id=proposal-2" in bundle.prompt_text
    assert "planning_needed=yes" in bundle.prompt_text


def test_empty_optional_fields_are_rendered_explicitly() -> None:
    request = _selection_request()

    bundle = build_selection_comparison_prompt_bundle(request)

    assert "constraints=NONE" in bundle.prompt_text
    assert "feasibility=NONE" in bundle.prompt_text
    assert "reversibility=NONE" in bundle.prompt_text
    assert "support_refs=NONE" in bundle.prompt_text
    assert "assumptions=NONE" in bundle.prompt_text
    assert "main_risks=NONE" in bundle.prompt_text


def test_unresolved_placeholders_fail_closed_in_prompt_bundle_builder(monkeypatch: pytest.MonkeyPatch) -> None:
    request = _selection_request(include_second_option=False)

    def _bad_load_prompt_file(_file_name: str) -> tuple[str, str]:
        return "system", "REQUEST_ID={{REQUEST_ID}}\nBROKEN={{UNUSED_PLACEHOLDER}}"

    monkeypatch.setattr(
        "jeff.cognitive.selection.comparison.load_prompt_file",
        _bad_load_prompt_file,
    )

    with pytest.raises(PromptRenderError) as exc_info:
        build_selection_comparison_prompt_bundle(request)

    assert "{{UNUSED_PLACEHOLDER}}" in str(exc_info.value)
