import pytest

from jeff.cognitive.selection import SelectionResult
from jeff.cognitive.selection_override import (
    OperatorSelectionOverrideRequest,
    OperatorSelectionOverrideValidationError,
    build_operator_selection_override,
    validate_operator_selection_override,
)


def test_valid_override_from_selected_selection_result_succeeds() -> None:
    selection_result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The bounded first option won the original Selection pass.",
    )

    override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-1",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="The second option better matches the operator's current bounded judgment.",
        )
    )

    assert override.override_id == "selection-override:override-request-1"
    assert override.selection_id == "selection-1"
    assert override.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert override.original_selection_disposition == "selected"
    assert override.original_selected_proposal_id == "proposal-1"
    assert override.chosen_proposal_id == "proposal-2"


def test_valid_override_from_non_selection_result_succeeds() -> None:
    selection_result = SelectionResult(
        selection_id="selection-2",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome="defer",
        rationale="Selection deferred because the visible uncertainty was still too high.",
    )

    override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-2",
            selection_result=selection_result,
            chosen_proposal_id="proposal-1",
            operator_rationale="The operator wants to force a bounded choice for downstream review.",
        )
    )

    assert override.original_selection_disposition == "defer"
    assert override.original_selected_proposal_id is None
    assert override.chosen_proposal_id == "proposal-1"


def test_chosen_proposal_outside_considered_ids_fails_closed() -> None:
    with pytest.raises(OperatorSelectionOverrideValidationError) as exc_info:
        build_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id="override-request-3",
                selection_result=_selection_result(),
                chosen_proposal_id="proposal-999",
                operator_rationale="This should fail because the operator cannot invent a new proposal.",
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("chosen_proposal_out_of_set",)


def test_override_to_none_fails_closed() -> None:
    with pytest.raises(OperatorSelectionOverrideValidationError) as exc_info:
        build_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id="override-request-4",
                selection_result=_selection_result(),
                chosen_proposal_id="NONE",
                operator_rationale="This should fail because NONE is not a proposal id.",
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("chosen_proposal_none",)


def test_blank_operator_rationale_fails_closed() -> None:
    with pytest.raises(OperatorSelectionOverrideValidationError) as exc_info:
        validate_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id="override-request-5",
                selection_result=_selection_result(),
                chosen_proposal_id="proposal-2",
                operator_rationale="   ",
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("blank_operator_rationale",)


def test_original_selection_linkage_and_result_truth_are_preserved() -> None:
    selection_result = _selection_result()
    original_snapshot = SelectionResult(
        selection_id=selection_result.selection_id,
        considered_proposal_ids=selection_result.considered_proposal_ids,
        selected_proposal_id=selection_result.selected_proposal_id,
        rationale=selection_result.rationale,
    )

    override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-6",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="Preserve the original Selection result and carry the operator choice separately.",
        )
    )

    assert override.selection_id == selection_result.selection_id
    assert override.considered_proposal_ids == selection_result.considered_proposal_ids
    assert override.original_selection_disposition == selection_result.disposition
    assert selection_result == original_snapshot
    assert selection_result.selected_proposal_id == "proposal-1"


def _selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )
