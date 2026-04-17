import json

import pytest

from jeff.cognitive.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.action_governance_handoff import ActionGovernanceHandoffRequest, handoff_action_to_governance
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
from jeff.cognitive.selection_override import OperatorSelectionOverrideRequest, build_operator_selection_override
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext, SelectionReviewRecord

from tests.fixtures.cli import build_flow_run, build_state_with_run


def test_selection_show_renders_original_selection_and_override_separately() -> None:
    context = _context_with_selection_review()
    cli = JeffCLI(context=context)

    text = cli.run_one_shot("/selection show run-1")

    assert "SELECTION REVIEW run_id=run-1" in text
    assert "[selection] disposition=selected selected_proposal_id=proposal-1" in text
    assert "[override] exists=True chosen_proposal_id=proposal-2" in text
    assert "[resolved_choice] effective_source=operator_override effective_proposal_id=proposal-2" in text
    assert "[action_formation] action_formed=True" in text
    assert "[governance_handoff] governance_evaluated=True governance_outcome=approval_required allowed_now=False" in text
    assert "execution" not in text.lower()


def test_selection_show_json_preserves_structured_truth_classes() -> None:
    context = _context_with_selection_review()
    cli = JeffCLI(context=context)

    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert payload["view"] == "selection_review"
    assert payload["selection"]["disposition"] == "selected"
    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["override"]["exists"] is True
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert payload["resolved_choice"]["effective_source"] == "operator_override"
    assert payload["resolved_choice"]["effective_proposal_id"] == "proposal-2"
    assert payload["action_formation"]["action_formed"] is True
    assert payload["action_formation"]["action_id"] is not None
    assert payload["governance_handoff"]["governance_evaluated"] is True
    assert payload["governance_handoff"]["governance_outcome"] == "approval_required"
    assert payload["governance_handoff"]["allowed_now"] is False
    assert "status" not in payload
    assert "execution_status" not in payload["governance_handoff"]


def test_selection_show_reports_missing_downstream_objects_honestly() -> None:
    state, scope = build_state_with_run()
    flow_run = build_flow_run(scope)
    cli = JeffCLI(context=InterfaceContext(state=state, flow_runs={str(scope.run_id): flow_run}))

    text = cli.run_one_shot("/selection show run-1")

    assert "[selection] disposition=selected selected_proposal_id=proposal-1" in text
    assert "[override] missing=no selection review chain is available for this run" in text
    assert "[resolved_choice] missing=no selection review chain is available for this run" in text
    assert "[action_formation] missing=no selection review chain is available for this run" in text
    assert "[governance_handoff] missing=no selection review chain is available for this run" in text


def test_selection_show_is_read_only_and_does_not_add_write_behavior() -> None:
    context = _context_with_selection_review()
    cli = JeffCLI(context=context)

    with pytest.raises(ValueError, match="selection command must be 'selection show \\[run_id\\]' or "):
        cli.run_one_shot("/selection clear-override run-1")


def _context_with_selection_review() -> InterfaceContext:
    state, scope = build_state_with_run()
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
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
                proposal_type="direct_action",
                title="Implement the alternate bounded change",
                why_now="The operator prefers the alternate bounded path.",
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
            request_id="resolution-request-1",
            selection_result=selection_result,
            operator_override=operator_override,
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
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            basis_state_version=3,
        )
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-1",
            formed_action_result=formed_action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(
                scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
                state_version=3,
            ),
        )
    )
    return InterfaceContext(
        state=state,
        selection_reviews={
            str(scope.run_id): SelectionReviewRecord(
                selection_result=selection_result,
                operator_override=operator_override,
                resolved_basis=resolved_basis,
                materialized_effective_proposal=materialized,
                formed_action_result=formed_action,
                governance_handoff_result=governance_handoff,
                proposal_result=proposal_result,
                action_scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
                basis_state_version=3,
                governance_policy=Policy(approval_required=True),
                governance_approval=None,
                governance_truth=CurrentTruthSnapshot(
                    scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
                    state_version=3,
                ),
            )
        },
    )
