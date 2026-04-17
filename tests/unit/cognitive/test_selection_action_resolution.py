import pytest

from jeff.cognitive.selection import SelectionResult
from jeff.cognitive.selection_action_resolution import (
    SelectionActionResolutionError,
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection_override import OperatorSelectionOverride, OperatorSelectionOverrideRequest
from jeff.cognitive.selection_override import build_operator_selection_override


def test_selected_selection_without_override_resolves_to_selection_source() -> None:
    selection_result = _selected_selection_result()

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-1",
            selection_result=selection_result,
        )
    )

    assert resolved.effective_source == "selection"
    assert resolved.effective_proposal_id == "proposal-1"
    assert resolved.original_selection_disposition == "selected"
    assert resolved.operator_override_present is False
    assert resolved.non_selection_outcome is None


def test_non_selection_without_override_resolves_to_no_actionable_basis() -> None:
    selection_result = SelectionResult(
        selection_id="selection-2",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome="defer",
        rationale="Selection deferred because visible uncertainty remained too high.",
    )

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-2",
            selection_result=selection_result,
        )
    )

    assert resolved.effective_source == "none"
    assert resolved.effective_proposal_id is None
    assert resolved.original_selection_disposition == "defer"
    assert resolved.non_selection_outcome == "defer"
    assert resolved.summary == "No downstream proposal basis; original selection disposition was defer."


def test_valid_override_over_selected_result_resolves_to_operator_override_source() -> None:
    selection_result = _selected_selection_result()
    operator_override = _operator_override(selection_result=selection_result, chosen_proposal_id="proposal-2")

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-3",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    assert resolved.effective_source == "operator_override"
    assert resolved.effective_proposal_id == "proposal-2"
    assert resolved.original_selection_disposition == "selected"
    assert resolved.operator_override_present is True
    assert resolved.operator_override_chosen_proposal_id == "proposal-2"


def test_valid_override_over_non_selection_result_resolves_to_operator_override_source() -> None:
    selection_result = SelectionResult(
        selection_id="selection-3",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome="reject_all",
        rationale="Selection rejected all current options under bounded visible factors.",
    )
    operator_override = _operator_override(selection_result=selection_result, chosen_proposal_id="proposal-1")

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-4",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    assert resolved.effective_source == "operator_override"
    assert resolved.effective_proposal_id == "proposal-1"
    assert resolved.original_selection_disposition == "reject_all"
    assert resolved.non_selection_outcome == "reject_all"


def test_override_with_mismatched_selection_id_fails_closed() -> None:
    selection_result = _selected_selection_result()
    operator_override = OperatorSelectionOverride(
        override_id="selection-override:bad-id",
        selection_id="selection-other",
        considered_proposal_ids=selection_result.considered_proposal_ids,
        original_selection_disposition="selected",
        original_selected_proposal_id="proposal-1",
        chosen_proposal_id="proposal-2",
        operator_rationale="Carry a separate downstream operator choice.",
    )

    with pytest.raises(SelectionActionResolutionError) as exc_info:
        resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id="resolution-request-5",
                selection_result=selection_result,
                operator_override=operator_override,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("selection_id_mismatch",)


def test_override_with_mismatched_considered_ids_fails_closed() -> None:
    selection_result = _selected_selection_result()
    operator_override = OperatorSelectionOverride(
        override_id="selection-override:bad-considered",
        selection_id=selection_result.selection_id,
        considered_proposal_ids=("proposal-1", "proposal-3"),
        original_selection_disposition="selected",
        original_selected_proposal_id="proposal-1",
        chosen_proposal_id="proposal-1",
        operator_rationale="Carry a separate downstream operator choice.",
    )

    with pytest.raises(SelectionActionResolutionError) as exc_info:
        resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id="resolution-request-6",
                selection_result=selection_result,
                operator_override=operator_override,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("considered_proposal_ids_mismatch",)


def test_original_selection_and_override_objects_remain_untouched() -> None:
    selection_result = _selected_selection_result()
    operator_override = _operator_override(selection_result=selection_result, chosen_proposal_id="proposal-2")

    original_selection_snapshot = SelectionResult(
        selection_id=selection_result.selection_id,
        considered_proposal_ids=selection_result.considered_proposal_ids,
        selected_proposal_id=selection_result.selected_proposal_id,
        rationale=selection_result.rationale,
    )
    original_override_snapshot = OperatorSelectionOverride(
        override_id=operator_override.override_id,
        selection_id=operator_override.selection_id,
        considered_proposal_ids=operator_override.considered_proposal_ids,
        original_selection_disposition=operator_override.original_selection_disposition,
        original_selected_proposal_id=operator_override.original_selected_proposal_id,
        chosen_proposal_id=operator_override.chosen_proposal_id,
        operator_rationale=operator_override.operator_rationale,
    )

    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-7",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    assert resolved.effective_source == "operator_override"
    assert selection_result == original_selection_snapshot
    assert operator_override == original_override_snapshot


def _selected_selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )


def _operator_override(
    *,
    selection_result: SelectionResult,
    chosen_proposal_id: str,
):
    return build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id=f"override-for-{selection_result.selection_id}-{chosen_proposal_id}",
            selection_result=selection_result,
            chosen_proposal_id=chosen_proposal_id,
            operator_rationale="Carry a separate downstream operator choice.",
        )
    )
