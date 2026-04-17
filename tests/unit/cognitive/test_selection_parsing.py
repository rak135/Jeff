import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionRequest
from jeff.cognitive.selection.comparison import (
    SelectionComparisonRequest,
    build_selection_comparison_prompt_bundle,
)
from jeff.cognitive.selection.comparison_runtime import SelectionRawComparisonResult
from jeff.cognitive.selection.parsing import (
    ParsedSelectionComparison,
    SelectionComparisonParseError,
    parse_selection_comparison_result,
)
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelUsage


def test_valid_raw_selection_comparison_output_parses_successfully() -> None:
    parsed = parse_selection_comparison_result(
        _raw_result(
            "DISPOSITION: selected\n"
            "SELECTED_PROPOSAL_ID: proposal-1\n"
            "PRIMARY_BASIS: This option has the strongest bounded support.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
            "MAIN_LOSING_REASON: It still depends on unresolved clarification.\n"
            "PLANNING_INSERTION_RECOMMENDED: no\n"
            "CAUTIONS: keep scope tight; recheck blocker drift\n",
        )
    )

    assert isinstance(parsed, ParsedSelectionComparison)
    assert parsed.request_id == "selection-request-1"
    assert parsed.disposition == "selected"
    assert parsed.selected_proposal_id == "proposal-1"
    assert parsed.main_losing_alternative_id == "proposal-2"
    assert parsed.planning_insertion_recommended is False
    assert parsed.cautions == "keep scope tight; recheck blocker drift"


def test_all_required_top_level_fields_are_required() -> None:
    with pytest.raises(SelectionComparisonParseError, match="missing required fields"):
        parse_selection_comparison_result(
            _raw_result(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: Basis only.\n",
            )
        )


def test_duplicate_fields_fail_closed() -> None:
    with pytest.raises(SelectionComparisonParseError, match="duplicate selection comparison field"):
        parse_selection_comparison_result(
            _raw_result(
                "DISPOSITION: selected\n"
                "DISPOSITION: defer\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: Basis.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: Loss.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: NONE\n",
            )
        )


def test_malformed_label_structure_fails_closed() -> None:
    with pytest.raises(SelectionComparisonParseError, match="malformed selection comparison output line"):
        parse_selection_comparison_result(
            _raw_result(
                "DISPOSITION selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: Basis.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: Loss.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: NONE\n",
            )
        )


def test_planning_insertion_recommendation_parses_from_yes_no() -> None:
    parsed_yes = parse_selection_comparison_result(
        _raw_result(
            "DISPOSITION: defer\n"
            "SELECTED_PROPOSAL_ID: NONE\n"
            "PRIMARY_BASIS: More structure is needed.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
            "MAIN_LOSING_REASON: It still has open blockers.\n"
            "PLANNING_INSERTION_RECOMMENDED: yes\n"
            "CAUTIONS: NONE\n",
        )
    )
    parsed_no = parse_selection_comparison_result(
        _raw_result(
            "DISPOSITION: reject_all\n"
            "SELECTED_PROPOSAL_ID: NONE\n"
            "PRIMARY_BASIS: No option is currently honest.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: NONE\n"
            "MAIN_LOSING_REASON: NONE\n"
            "PLANNING_INSERTION_RECOMMENDED: no\n"
            "CAUTIONS: NONE\n",
        )
    )

    assert parsed_yes.planning_insertion_recommended is True
    assert parsed_no.planning_insertion_recommended is False


def test_none_sentinel_handling_is_preserved() -> None:
    parsed = parse_selection_comparison_result(
        _raw_result(
            "DISPOSITION: defer\n"
            "SELECTED_PROPOSAL_ID: NONE\n"
            "PRIMARY_BASIS: More clarification is needed.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: NONE\n"
            "MAIN_LOSING_REASON: NONE\n"
            "PLANNING_INSERTION_RECOMMENDED: no\n"
            "CAUTIONS: NONE\n",
        )
    )

    assert parsed.selected_proposal_id is None
    assert parsed.main_losing_alternative_id is None
    assert parsed.main_losing_reason is None
    assert parsed.cautions is None


def test_parser_does_not_perform_semantic_validation_yet() -> None:
    parsed = parse_selection_comparison_result(
        _raw_result(
            "DISPOSITION: maybe_later\n"
            "SELECTED_PROPOSAL_ID: invented-proposal\n"
            "PRIMARY_BASIS: Raw text still matches the output shape.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: NONE\n"
            "MAIN_LOSING_REASON: NONE\n"
            "PLANNING_INSERTION_RECOMMENDED: no\n"
            "CAUTIONS: approval-like words are still parser-shape content only\n",
        )
    )

    assert parsed.disposition == "maybe_later"
    assert parsed.selected_proposal_id == "invented-proposal"
    assert parsed.cautions == "approval-like words are still parser-shape content only"


def test_parser_consumes_raw_runtime_surface_without_changing_runtime_behavior() -> None:
    raw_result = _raw_result(
        "DISPOSITION: escalate\n"
        "SELECTED_PROPOSAL_ID: NONE\n"
        "PRIMARY_BASIS: The comparison crosses a judgment boundary.\n"
        "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
        "MAIN_LOSING_REASON: It does not resolve the same boundary honestly.\n"
        "PLANNING_INSERTION_RECOMMENDED: no\n"
        "CAUTIONS: preserve operator review context\n",
    )

    parsed = parse_selection_comparison_result(raw_result)

    assert parsed.request_id == raw_result.request_id
    assert parsed.raw_model_output_text == raw_result.model_output_text
    assert raw_result.adapter_id == "adapter-1"


def _raw_result(raw_text: str) -> SelectionRawComparisonResult:
    request = SelectionComparisonRequest.from_selection_request(
        SelectionRequest(
            request_id="selection-request-1",
            proposal_result=ProposalResult(
                request_id="proposal-request-1",
                scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
                options=(
                    ProposalResultOption(
                        option_index=1,
                        proposal_id="proposal-1",
                        proposal_type="direct_action",
                        title="Implement the bounded change",
                        why_now="The bounded path is ready.",
                        summary="Implement the bounded change",
                    ),
                    ProposalResultOption(
                        option_index=2,
                        proposal_id="proposal-2",
                        proposal_type="clarify",
                        title="Clarify the missing edge case first",
                        why_now="Remaining ambiguity matters.",
                        summary="Clarify the missing edge case first",
                    ),
                ),
            ),
        )
    )
    return SelectionRawComparisonResult(
        prompt_bundle=build_selection_comparison_prompt_bundle(request),
        request_id=request.request_id,
        model_output_text=raw_text,
        adapter_id="adapter-1",
        provider_name="fake",
        model_name="fake-model",
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )
