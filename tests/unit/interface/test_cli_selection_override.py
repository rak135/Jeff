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
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext

from tests.fixtures.cli import build_flow_run, build_state_with_run


def test_selection_override_command_creates_override_and_truthful_receipt() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    payload = json.loads(
        cli.run_one_shot(
            '/selection override proposal-2 --why "Operator prefers the second bounded option." run-1',
            json_output=True,
        )
    )

    assert payload["view"] == "selection_override_receipt"
    assert payload["truth"]["original_selection_disposition"] == "selected"
    assert payload["truth"]["original_selected_proposal_id"] == "proposal-1"
    assert payload["truth"]["original_selection_unchanged"] is True
    assert payload["derived"]["override_created"] is True
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert payload["resolved_choice"]["effective_source"] == "operator_override"
    assert payload["resolved_choice"]["effective_proposal_id"] == "proposal-2"
    assert payload["action_formation"]["action_formed"] is True
    assert payload["governance_handoff"]["governance_evaluated"] is True
    assert payload["governance_handoff"]["governance_outcome"] == "approval_required"
    assert payload["governance_handoff"]["allowed_now"] is False
    assert "status" not in payload


def test_selection_override_command_requires_explicit_rationale() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    with pytest.raises(ValueError, match="operator_rationale must be a non-empty string"):
        cli.run_one_shot('/selection override proposal-2 --why "" run-1')


def test_selection_override_command_rejects_proposal_outside_considered_set() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    with pytest.raises(ValueError, match="chosen_proposal_id"):
        cli.run_one_shot(
            '/selection override proposal-999 --why "This should fail because it is out of set." run-1'
        )


def test_selection_show_after_override_keeps_original_selection_and_override_separate() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    cli.run_one_shot('/selection override proposal-2 --why "Use the second bounded option." run-1')
    text = cli.run_one_shot("/selection show run-1")

    assert "[selection] disposition=selected selected_proposal_id=proposal-1" in text
    assert "[override] exists=True chosen_proposal_id=proposal-2" in text
    assert "[resolved_choice] effective_source=operator_override effective_proposal_id=proposal-2" in text
    assert "[action_formation] action_formed=True" in text
    assert "[governance_handoff] governance_evaluated=True governance_outcome=approval_required allowed_now=False" in text


def test_selection_override_receipt_does_not_imply_approval_or_execution_start() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    text = cli.run_one_shot('/selection override proposal-2 --why "Operator wants the alternate option." run-1')

    assert "original_selection_unchanged=True" in text
    assert "execution_started=False" in text
    assert "SELECTION OVERRIDE RECORDED" in text


def test_selection_override_requires_existing_selection_review_data() -> None:
    state, scope = build_state_with_run()
    cli = JeffCLI(context=InterfaceContext(state=state))

    with pytest.raises(ValueError, match=f"no selection review data is available for run {scope.run_id}"):
        cli.run_one_shot('/selection override proposal-2 --why "No review chain exists." run-1')


def test_selection_override_works_when_review_chain_is_materialized_from_lawful_flow_data() -> None:
    state, scope = build_state_with_run()
    context = InterfaceContext(state=state, flow_runs={str(scope.run_id): build_flow_run(scope)})
    cli = JeffCLI(context=context)

    payload = json.loads(
        cli.run_one_shot(
            '/selection override proposal-2 --why "Use the lawful alternate proposal." run-1',
            json_output=True,
        )
    )

    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert payload["resolved_choice"]["effective_source"] == "operator_override"
    assert payload["action_formation"]["action_formed"] is False
    assert payload["action_formation"]["no_action_reason"] is not None


def test_selection_clear_override_behavior_is_not_added() -> None:
    cli = JeffCLI(context=_context_with_selection_review_chain())

    with pytest.raises(ValueError, match="selection command must be 'selection show \\[run_id\\]' or "):
        cli.run_one_shot("/selection clear-override run-1")


def _context_with_selection_review_chain() -> InterfaceContext:
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
    selection_result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
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
