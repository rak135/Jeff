import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.cognitive.selection_action_resolution import (
    ResolvedSelectionActionBasis,
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection_effective_proposal import (
    SelectionEffectiveProposalMaterializationError,
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.cognitive.selection_override import OperatorSelectionOverrideRequest, build_operator_selection_override
from jeff.core.schemas import Scope


def test_selection_source_materializes_matching_proposal_option() -> None:
    proposal_result = _proposal_result()
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-1",
            selection_result=_selected_selection_result(),
        )
    )

    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-1",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )

    assert materialized.effective_source == "selection"
    assert materialized.effective_proposal_id == "proposal-1"
    assert materialized.effective_proposal_option is not None
    assert materialized.effective_proposal_option.proposal_id == "proposal-1"


def test_operator_override_source_materializes_matching_proposal_option() -> None:
    proposal_result = _proposal_result()
    selection_result = _selected_selection_result()
    operator_override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-request-1",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="Carry a separate downstream operator choice.",
        )
    )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-2",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-2",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )

    assert materialized.effective_source == "operator_override"
    assert materialized.effective_proposal_id == "proposal-2"
    assert materialized.effective_proposal_option is not None
    assert materialized.effective_proposal_option.proposal_id == "proposal-2"


def test_none_source_materializes_explicit_no_proposal_basis() -> None:
    proposal_result = _proposal_result()
    selection_result = SelectionResult(
        selection_id="selection-2",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome="defer",
        rationale="Selection deferred because visible uncertainty remained too high.",
    )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-3",
            selection_result=selection_result,
        )
    )

    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-3",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )

    assert materialized.effective_source == "none"
    assert materialized.effective_proposal_id is None
    assert materialized.effective_proposal_option is None
    assert materialized.non_selection_outcome == "defer"


def test_missing_effective_proposal_id_when_source_requires_it_fails_closed() -> None:
    proposal_result = _proposal_result()
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-4",
            selection_result=_selected_selection_result(),
        )
    )
    object.__setattr__(resolved_basis, "effective_proposal_id", None)

    with pytest.raises(SelectionEffectiveProposalMaterializationError) as exc_info:
        materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id="materialization-request-4",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_effective_proposal_id",)


def test_effective_proposal_id_not_found_in_proposal_result_fails_closed() -> None:
    proposal_result = _proposal_result()
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-5",
            selection_result=_selected_selection_result(),
        )
    )
    object.__setattr__(resolved_basis, "effective_proposal_id", "proposal-999")

    with pytest.raises(SelectionEffectiveProposalMaterializationError) as exc_info:
        materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id="materialization-request-5",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("effective_proposal_not_found",)


def test_mismatch_between_resolved_considered_ids_and_proposal_result_fails_closed() -> None:
    proposal_result = ProposalResult(
        request_id="proposal-request-2",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
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
                proposal_id="proposal-3",
                proposal_type="clarify",
                title="Clarify a different edge case",
                why_now="A different ambiguity matters.",
                summary="Clarify a different edge case",
            ),
        ),
    )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-6",
            selection_result=_selected_selection_result(),
        )
    )

    with pytest.raises(SelectionEffectiveProposalMaterializationError) as exc_info:
        materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id="materialization-request-6",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("proposal_set_mismatch",)


def test_original_proposal_result_and_resolved_basis_remain_untouched() -> None:
    proposal_result = _proposal_result()
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-7",
            selection_result=_selected_selection_result(),
        )
    )

    original_proposal_snapshot = ProposalResult(
        request_id=proposal_result.request_id,
        scope=proposal_result.scope,
        options=proposal_result.options,
    )
    original_resolution_snapshot = ResolvedSelectionActionBasis(
        resolution_id=resolved_basis.resolution_id,
        selection_id=resolved_basis.selection_id,
        considered_proposal_ids=resolved_basis.considered_proposal_ids,
        effective_proposal_id=resolved_basis.effective_proposal_id,
        effective_source=resolved_basis.effective_source,
        original_selection_disposition=resolved_basis.original_selection_disposition,
        original_selected_proposal_id=resolved_basis.original_selected_proposal_id,
        operator_override_present=resolved_basis.operator_override_present,
        non_selection_outcome=resolved_basis.non_selection_outcome,
        operator_override_chosen_proposal_id=resolved_basis.operator_override_chosen_proposal_id,
        summary=resolved_basis.summary,
    )

    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-7",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )

    assert materialized.effective_proposal_option is not None
    assert proposal_result == original_proposal_snapshot
    assert resolved_basis == original_resolution_snapshot


def _proposal_result() -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
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
                why_now="Remaining uncertainty matters.",
                summary="Clarify the missing edge case first",
            ),
        ),
    )


def _selected_selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )
