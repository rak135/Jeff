import pytest

from jeff.cognitive.action_formation import (
    ActionFormationError,
    ActionFormationRequest,
    form_action_from_materialized_proposal,
)
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.cognitive.selection_action_resolution import (
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection_effective_proposal import (
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.core.schemas import Scope


def test_directly_actionable_materialized_proposal_forms_action() -> None:
    materialized = _materialized_effective_proposal()

    result = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-1",
            materialized_effective_proposal=materialized,
            scope=_scope(),
            basis_state_version=3,
        )
    )

    assert result.action_formed is True
    assert result.action is not None
    assert result.action.intent_summary == "Implement the bounded change"
    assert result.action.scope == _scope()
    assert result.action.basis_state_version == 3
    assert result.effective_source == "selection"
    assert result.effective_proposal_id == "proposal-1"


def test_none_source_materialized_basis_returns_no_action_without_error() -> None:
    materialized = _materialized_none_basis()

    result = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-2",
            materialized_effective_proposal=materialized,
            scope=_scope(),
        )
    )

    assert result.action_formed is False
    assert result.action is None
    assert result.no_action_reason == "No actionable proposal basis is available from the resolved selection outcome."


def test_planning_insertion_returns_no_action_without_error() -> None:
    materialized = _materialized_effective_proposal(proposal_type="planning_insertion")

    result = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-3",
            materialized_effective_proposal=materialized,
            scope=_scope(),
        )
    )

    assert result.action_formed is False
    assert result.action is None
    assert result.proposal_type == "planning_insertion"
    assert "does not directly form Action" in result.no_action_reason


def test_missing_data_for_actionable_proposal_fails_closed() -> None:
    materialized = _materialized_effective_proposal()
    object.__setattr__(materialized.effective_proposal_option, "summary", "   ")

    with pytest.raises(ActionFormationError) as exc_info:
        form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id="formation-request-4",
                materialized_effective_proposal=materialized,
                scope=_scope(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_intent_summary",)


def test_missing_effective_option_for_actionable_basis_fails_closed() -> None:
    materialized = _materialized_effective_proposal()
    object.__setattr__(materialized, "effective_proposal_option", None)

    with pytest.raises(ActionFormationError) as exc_info:
        form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id="formation-request-5",
                materialized_effective_proposal=materialized,
                scope=_scope(),
            )
        )

    assert tuple(issue.code for issue in exc_info.value.issues) == ("missing_effective_proposal_option",)


def test_formed_action_preserves_truthful_linkage_and_upstream_object() -> None:
    materialized = _materialized_effective_proposal()
    original_snapshot = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request",
            proposal_result=_proposal_result(),
            resolved_basis=resolve_selection_action_basis(
                SelectionActionResolutionRequest(
                    request_id="resolution-request",
                    selection_result=_selection_result(),
                )
            ),
        )
    )

    result = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-6",
            materialized_effective_proposal=materialized,
            scope=_scope(),
            basis_state_version=5,
        )
    )

    assert result.action is not None
    assert result.action.basis_label == "selection_source=selection;selection_id=selection-1;proposal_id=proposal-1"
    assert materialized == original_snapshot


def _materialized_effective_proposal(*, proposal_type: str = "direct_action"):
    proposal_result = _proposal_result(proposal_type=proposal_type)
    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request",
            selection_result=_selection_result(),
        )
    )
    return materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request",
            proposal_result=proposal_result,
            resolved_basis=resolved,
        )
    )


def _materialized_none_basis():
    selection_result = SelectionResult(
        selection_id="selection-2",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        non_selection_outcome="defer",
        rationale="Selection deferred because uncertainty remained too high.",
    )
    resolved = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-none",
            selection_result=selection_result,
        )
    )
    return materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-none",
            proposal_result=_proposal_result(),
            resolved_basis=resolved,
        )
    )


def _proposal_result(*, proposal_type: str = "direct_action") -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type=proposal_type,  # type: ignore[arg-type]
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


def _selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
