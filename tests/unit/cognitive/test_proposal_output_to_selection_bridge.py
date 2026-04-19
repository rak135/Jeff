import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import (
    SelectionBridgeError,
    SelectionBridgeRequest,
    build_and_run_selection,
)
from jeff.core.schemas import Scope


def test_lawful_proposal_output_builds_selection_request_and_runs_selection() -> None:
    result = build_and_run_selection(
        SelectionBridgeRequest(
            request_id="selection-bridge-request-1",
            proposal_result=_direct_action_proposal_result(),
            selection_id="selection-bridge-1",
        )
    )

    assert result.selection_request_built is True
    assert result.selection_ran is True
    assert result.selection_request is not None
    assert result.selection_result is not None
    assert result.selection_result.selected_proposal_id == "proposal-1"
    assert result.selected_proposal_id == "proposal-1"
    assert result.selection_disposition == "selected"


def test_missing_proposal_output_fails_closed() -> None:
    with pytest.raises(SelectionBridgeError, match="preserved lawful proposal output"):
        build_and_run_selection(
            SelectionBridgeRequest(
                request_id="selection-bridge-request-2",
                proposal_result=None,
                selection_id="selection-bridge-2",
            )
        )


def test_blank_request_id_raises_typed_error() -> None:
    with pytest.raises(SelectionBridgeError, match="request_id"):
        build_and_run_selection(
            SelectionBridgeRequest(
                request_id=" ",
                proposal_result=_direct_action_proposal_result(),
                selection_id="selection-bridge-3",
            )
        )


def test_missing_required_additional_selection_inputs_fails_closed() -> None:
    with pytest.raises(SelectionBridgeError, match="selection_id"):
        build_and_run_selection(
            SelectionBridgeRequest(
                request_id="selection-bridge-request-4",
                proposal_result=_direct_action_proposal_result(),
                selection_id=" ",
            )
        )


def test_selection_output_is_preserved_in_bounded_form() -> None:
    result = build_and_run_selection(
        SelectionBridgeRequest(
            request_id="selection-bridge-request-5",
            proposal_result=_direct_action_proposal_result(),
            selection_id="selection-bridge-5",
        )
    )

    assert result.selection_request is not None
    assert result.selection_request.proposal_result.request_id == "proposal-request-1"
    assert result.selection_result is not None
    assert result.selection_result.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert "selection-only" in result.summary


def test_non_selection_outcomes_remain_selection_semantics() -> None:
    result = build_and_run_selection(
        SelectionBridgeRequest(
            request_id="selection-bridge-request-6",
            proposal_result=_clarify_only_proposal_result(),
            selection_id="selection-bridge-6",
        )
    )

    assert result.selection_result is not None
    assert result.selection_result.selected_proposal_id is None
    assert result.selection_result.non_selection_outcome == "defer"
    assert result.selection_disposition == "defer"
    assert "selection-only" in result.summary


def test_zero_option_proposal_output_runs_without_guessing() -> None:
    result = build_and_run_selection(
        SelectionBridgeRequest(
            request_id="selection-bridge-request-7",
            proposal_result=_zero_option_proposal_result(),
            selection_id="selection-bridge-7",
        )
    )

    assert result.selection_result is not None
    assert result.selection_result.selected_proposal_id is None
    assert result.selection_result.non_selection_outcome == "reject_all"
    assert result.selection_disposition == "reject_all"


def _direct_action_proposal_result() -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Implement the bounded change",
                why_now="The bounded direct path is currently strongest.",
                summary="Implement the bounded change",
                support_refs=("source-1",),
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="clarify",
                title="Clarify one remaining uncertainty",
                why_now="A visible uncertainty still exists.",
                summary="Clarify one remaining uncertainty",
            ),
        ),
    )


def _clarify_only_proposal_result() -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-2",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-9",
                proposal_type="clarify",
                title="Clarify the remaining export constraint",
                why_now="One decisive uncertainty remains visible.",
                summary="Clarify the remaining export constraint",
            ),
        ),
        scarcity_reason="Only one serious clarification option is currently grounded.",
    )


def _zero_option_proposal_result() -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-3",
        scope=_scope(),
        options=(),
        scarcity_reason="No serious option is currently grounded by the preserved proposal output.",
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")