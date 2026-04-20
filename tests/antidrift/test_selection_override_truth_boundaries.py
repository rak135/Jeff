import json

import pytest

from jeff.cognitive.post_selection.action_formation import (
    ActionFormationRequest,
    form_action_from_materialized_proposal,
)
from jeff.cognitive.post_selection.action_resolution import (
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.post_selection.effective_proposal import (
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.cognitive.post_selection.governance_handoff import (
    ActionGovernanceHandoffRequest,
    handoff_action_to_governance,
)
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext

from tests.fixtures.cli import build_state_with_run


def test_override_entry_preserves_original_selection_truth_and_json_blocks() -> None:
    selection_result = _selection_result()
    cli = JeffCLI(context=_context_with_review_chain(selection_result=selection_result))

    result = cli.execute(
        '/selection override proposal-2 --why "Operator prefers the second bounded option." run-1',
        json_output=True,
    )
    updated_review = result.context.selection_reviews["run-1"]
    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert updated_review.selection_result == selection_result
    assert updated_review.selection_result.selected_proposal_id == "proposal-1"
    assert updated_review.operator_override is not None
    assert updated_review.operator_override.chosen_proposal_id == "proposal-2"
    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert payload["resolved_choice"]["effective_source"] == "operator_override"
    assert payload["resolved_choice"]["effective_proposal_id"] == "proposal-2"


def test_invalid_override_fails_closed_without_mutating_existing_review_chain() -> None:
    context = _context_with_review_chain(selection_result=_selection_result())
    cli = JeffCLI(context=context)

    before_payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))
    before_review = context.selection_reviews["run-1"]

    with pytest.raises(ValueError, match="chosen_proposal_id"):
        cli.run_one_shot('/selection override proposal-999 --why "This proposal is out of set." run-1')

    after_payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))
    after_review = cli.execute("/selection show run-1").context.selection_reviews["run-1"]

    assert after_review == before_review
    assert after_payload == before_payload
    assert after_payload["override"]["exists"] is False
    assert after_payload["resolved_choice"]["effective_proposal_id"] == "proposal-1"


def test_override_recomputes_governance_for_new_action_basis_without_reusing_old_result() -> None:
    selection_result = _selection_result()
    context = _context_with_review_chain(selection_result=selection_result)
    original_review = context.selection_reviews["run-1"]
    original_action_id = original_review.formed_action_result.action.action_id
    original_governance_action_id = original_review.governance_handoff_result.action.action_id

    cli = JeffCLI(context=context)
    result = cli.execute(
        '/selection override proposal-2 --why "Operator wants the alternate bounded path." run-1'
    )
    updated_review = result.context.selection_reviews["run-1"]

    assert updated_review.operator_override is not None
    assert updated_review.operator_override.chosen_proposal_id == "proposal-2"
    assert updated_review.formed_action_result.action is not None
    assert updated_review.formed_action_result.action.action_id != original_action_id
    assert updated_review.formed_action_result.action.action_id.endswith(":proposal-2")
    assert updated_review.governance_handoff_result is not None
    assert updated_review.governance_handoff_result.governance_evaluated is True
    assert updated_review.governance_handoff_result.action is not None
    assert updated_review.governance_handoff_result.action.action_id != original_governance_action_id
    assert updated_review.governance_handoff_result.action.action_id.endswith(":proposal-2")
    assert updated_review.governance_handoff_result.governance_result is not None
    assert updated_review.governance_handoff_result.governance_result.allowed_now is False


def test_selection_surfaces_do_not_drift_into_authority_or_execution_language() -> None:
    cli = JeffCLI(context=_context_with_review_chain(selection_result=_selection_result()))

    receipt_text = cli.run_one_shot(
        '/selection override proposal-2 --why "Use the second bounded option." run-1'
    )
    review_text = cli.run_one_shot("/selection show run-1")
    receipt_payload = json.loads(
        cli.run_one_shot(
            '/selection override proposal-2 --why "Use the second bounded option again." run-1',
            json_output=True,
        )
    )

    assert "original_selected_proposal_id=proposal-1" in receipt_text
    assert "chosen_proposal_id=proposal-2" in receipt_text
    assert "execution_started=False" in receipt_text
    assert "ready to execute" not in receipt_text.lower()
    assert "execution complete" not in receipt_text.lower()
    assert "[selection] disposition=selected selected_proposal_id=proposal-1" in review_text
    assert "[override] exists=True chosen_proposal_id=proposal-2" in review_text
    assert "execution complete" not in review_text.lower()
    assert receipt_payload["truth"]["original_selected_proposal_id"] == "proposal-1"
    assert receipt_payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert "status" not in receipt_payload


def test_missing_review_chain_objects_are_reported_honestly() -> None:
    state, scope = build_state_with_run()
    selection_result = _selection_result()
    cli = JeffCLI(
        context=InterfaceContext(
            state=state,
            selection_reviews={
                str(scope.run_id): SelectionReviewRecord(selection_result=selection_result),
            },
        )
    )

    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["override"]["missing_reason"] == "no override recorded"
    assert payload["resolved_choice"]["missing_reason"] == "no resolved downstream basis available"
    assert payload["action_formation"]["missing_reason"] == "no Action formation result available"
    assert payload["governance_handoff"]["missing_reason"] == "governance handoff has not been recorded"


def _context_with_review_chain(*, selection_result: SelectionResult) -> InterfaceContext:
    state, scope = build_state_with_run()
    action_scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=action_scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Implement the first bounded change",
                why_now="The first bounded path is the current Selection choice.",
                summary="Implement the first bounded change",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="direct_action",
                title="Implement the alternate bounded change",
                why_now="The operator may prefer the alternate bounded path.",
                summary="Implement the alternate bounded change",
            ),
        ),
    )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-1",
            selection_result=selection_result,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-1",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-1",
            materialized_effective_proposal=materialized,
            scope=action_scope,
            basis_state_version=3,
        )
    )
    policy = Policy(approval_required=True)
    truth = CurrentTruthSnapshot(scope=action_scope, state_version=3)
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-1",
            formed_action_result=formed_action,
            policy=policy,
            approval=None,
            truth=truth,
        )
    )
    return InterfaceContext(
        state=state,
        selection_reviews={
            str(scope.run_id): SelectionReviewRecord(
                selection_result=selection_result,
                operator_override=None,
                resolved_basis=resolved_basis,
                materialized_effective_proposal=materialized,
                formed_action_result=formed_action,
                governance_handoff_result=governance_handoff,
                proposal_result=proposal_result,
                action_scope=action_scope,
                basis_state_version=3,
                governance_policy=policy,
                governance_approval=None,
                governance_truth=truth,
            )
        },
    )


def _selection_result() -> SelectionResult:
    return SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )
