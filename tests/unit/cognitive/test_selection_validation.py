import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionRequest
from jeff.cognitive.selection.comparison import SelectionComparisonRequest, build_selection_comparison_prompt_bundle
from jeff.cognitive.selection.comparison_runtime import SelectionRawComparisonResult
from jeff.cognitive.selection.parsing import parse_selection_comparison_result
from jeff.cognitive.selection.validation import (
    SelectionComparisonValidationError,
    ValidatedSelectionComparison,
    validate_selection_comparison,
)
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelUsage


def test_lawful_selected_parsed_comparison_validates_successfully() -> None:
    request = _comparison_request()
    validated = validate_selection_comparison(
        _parsed_comparison(
            "DISPOSITION: selected\n"
            "SELECTED_PROPOSAL_ID: proposal-1\n"
            "PRIMARY_BASIS: This option has the strongest bounded support.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
            "MAIN_LOSING_REASON: It still depends on unresolved clarification.\n"
            "PLANNING_INSERTION_RECOMMENDED: no\n"
            "CAUTIONS: keep scope tight and preserve bounded review\n",
            request=request,
        ),
        request=request,
    )

    assert isinstance(validated, ValidatedSelectionComparison)
    assert validated.disposition == "selected"
    assert validated.selected_proposal_id == "proposal-1"
    assert validated.cautions == "keep scope tight and preserve bounded review"


@pytest.mark.parametrize("disposition", ["reject_all", "defer", "escalate"])
def test_lawful_non_selection_parsed_comparison_validates_successfully(disposition: str) -> None:
    request = _comparison_request()
    validated = validate_selection_comparison(
        _parsed_comparison(
            f"DISPOSITION: {disposition}\n"
            "SELECTED_PROPOSAL_ID: NONE\n"
            "PRIMARY_BASIS: A non-selection outcome is more honest under current visible limits.\n"
            "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
            "MAIN_LOSING_REASON: The strongest option still remains materially blocked.\n"
            "PLANNING_INSERTION_RECOMMENDED: yes\n"
            "CAUTIONS: preserve bounded choice and keep governance separate\n",
            request=request,
        ),
        request=request,
    )

    assert validated.disposition == disposition
    assert validated.selected_proposal_id is None
    assert validated.planning_insertion_recommended is True


def test_unsupported_disposition_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="disposition must be one of") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: maybe_later\n"
                "SELECTED_PROPOSAL_ID: NONE\n"
                "PRIMARY_BASIS: Shape is valid but semantics are not.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
                "MAIN_LOSING_REASON: It still loses.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep this bounded\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("unsupported_disposition",)


def test_invented_selected_proposal_id_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="considered proposal set") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-999\n"
                "PRIMARY_BASIS: The parser accepted the id, but validation should not.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It still loses.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep this bounded\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("selected_proposal_out_of_set",)


def test_non_selected_disposition_with_selected_proposal_id_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="must not carry selected_proposal_id") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: defer\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: Deferral is more honest.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It still loses.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep this bounded\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("non_selected_disposition_with_selected_id",)


def test_selected_disposition_without_selected_proposal_id_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="requires selected_proposal_id") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: NONE\n"
                "PRIMARY_BASIS: The output claims selection without a winner.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It still loses.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep this bounded\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("missing_selected_proposal_id",)


def test_invalid_main_losing_alternative_id_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="main_losing_alternative_id") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: This path wins.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-404\n"
                "MAIN_LOSING_REASON: It still loses.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep this bounded\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("losing_alternative_out_of_set",)


def test_blank_rationale_bearing_fields_fail_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError) as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: NONE\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: NONE\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: NONE\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == ("blank_primary_basis", "missing_main_losing_reason", "missing_cautions")


def test_authority_language_leakage_fails_closed() -> None:
    request = _comparison_request()

    with pytest.raises(SelectionComparisonValidationError, match="authority language") as exc_info:
        validate_selection_comparison(
            _parsed_comparison(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: This option is approved and safe to execute now.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It is not authorized.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: execution approved after planning\n",
                request=request,
            ),
            request=request,
        )

    assert _issue_codes(exc_info.value) == (
        "authority_leakage",
        "authority_leakage",
        "authority_leakage",
    )


def test_parsing_and_validation_remain_separate_concerns() -> None:
    request = _comparison_request()
    parsed = _parsed_comparison(
        "DISPOSITION: maybe_later\n"
        "SELECTED_PROPOSAL_ID: proposal-999\n"
        "PRIMARY_BASIS: Parsed shape is fine.\n"
        "MAIN_LOSING_ALTERNATIVE_ID: NONE\n"
        "MAIN_LOSING_REASON: NONE\n"
        "PLANNING_INSERTION_RECOMMENDED: no\n"
        "CAUTIONS: keep this bounded\n",
        request=request,
    )

    assert parsed.disposition == "maybe_later"

    with pytest.raises(SelectionComparisonValidationError):
        validate_selection_comparison(parsed, request=request)


def _comparison_request() -> SelectionComparisonRequest:
    return SelectionComparisonRequest.from_selection_request(
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


def _parsed_comparison(raw_text: str, *, request: SelectionComparisonRequest):
    return parse_selection_comparison_result(_raw_result(raw_text, request=request))


def _raw_result(raw_text: str, *, request: SelectionComparisonRequest) -> SelectionRawComparisonResult:
    return SelectionRawComparisonResult(
        prompt_bundle=build_selection_comparison_prompt_bundle(request),
        request_id=request.request_id,
        model_output_text=raw_text,
        adapter_id="adapter-1",
        provider_name="fake",
        model_name="fake-model",
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )


def _issue_codes(error: SelectionComparisonValidationError) -> tuple[str, ...]:
    return tuple(issue.code for issue in error.issues)
