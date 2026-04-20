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
from jeff.cognitive.post_selection.override import (
    OperatorSelectionOverrideRequest,
    build_operator_selection_override,
)
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord
from jeff.cognitive.post_selection.selection_review import (
    materialize_selection_review_from_available_data,
    recompute_selection_review_record,
    selection_review_basis_state_version,
)
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionResult
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy


def test_materialize_selection_review_reconstructs_downstream_chain_without_interface_context() -> None:
    selection_result, proposal_result, operator_override, truth = _selection_inputs()
    existing_review = SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        proposal_result=proposal_result,
        action_scope=truth.scope,
        basis_state_version=truth.state_version,
        governance_policy=Policy(approval_required=True),
        governance_truth=truth,
    )

    materialized = materialize_selection_review_from_available_data(
        existing_review=existing_review,
        flow_run=None,
    )

    assert materialized is not None
    assert materialized.operator_override == operator_override
    assert materialized.resolved_basis is not None
    assert materialized.resolved_basis.effective_proposal_id == "proposal-2"
    assert materialized.materialized_effective_proposal is not None
    assert materialized.materialized_effective_proposal.effective_proposal_id == "proposal-2"
    assert materialized.formed_action_result is not None
    assert materialized.formed_action_result.action_formed is True
    assert materialized.governance_handoff_result is not None
    assert materialized.governance_handoff_result.governance_result is not None
    assert materialized.governance_handoff_result.governance_result.governance_outcome == "approval_required"


def test_recompute_selection_review_record_rebases_effective_choice_without_widening_truth() -> None:
    selection_result, proposal_result, _operator_override, truth = _selection_inputs()
    original_review = _full_review(
        selection_result=selection_result,
        proposal_result=proposal_result,
        truth=truth,
        chosen_proposal_id="proposal-1",
    )
    override = build_operator_selection_override(
        OperatorSelectionOverrideRequest(
            request_id="override-recompute",
            selection_result=selection_result,
            chosen_proposal_id="proposal-2",
            operator_rationale="Operator prefers the bounded alternative.",
        )
    )

    updated = recompute_selection_review_record(
        existing_review=original_review,
        selection_result=selection_result,
        operator_override=override,
    )

    assert updated.operator_override == override
    assert updated.resolved_basis is not None
    assert updated.resolved_basis.effective_proposal_id == "proposal-2"
    assert updated.materialized_effective_proposal is not None
    assert updated.materialized_effective_proposal.effective_proposal_id == "proposal-2"
    assert updated.formed_action_result is not None
    assert updated.formed_action_result.action is not None
    assert updated.formed_action_result.action.basis_state_version == truth.state_version
    assert updated.governance_policy == original_review.governance_policy
    assert updated.governance_truth == original_review.governance_truth
    assert selection_review_basis_state_version(updated) == truth.state_version


def test_selection_review_basis_state_version_falls_back_to_zero_when_absent() -> None:
    assert selection_review_basis_state_version(SelectionReviewRecord()) == 0


def _selection_inputs() -> tuple[SelectionResult, ProposalResult, object, CurrentTruthSnapshot]:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    proposal_result = ProposalResult(
        request_id="proposal-request-1",
        scope=scope,
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Primary bounded change",
                why_now="The default bounded path is ready.",
                summary="Primary bounded change",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="direct_action",
                title="Alternate bounded change",
                why_now="The operator may prefer the alternate bounded path.",
                summary="Alternate bounded change",
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
    truth = CurrentTruthSnapshot(scope=scope, state_version=3)
    return selection_result, proposal_result, operator_override, truth


def _full_review(*, selection_result: SelectionResult, proposal_result: ProposalResult, truth: CurrentTruthSnapshot, chosen_proposal_id: str) -> SelectionReviewRecord:
    operator_override = None
    if chosen_proposal_id != selection_result.selected_proposal_id:
        operator_override = build_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id=f"override:{chosen_proposal_id}",
                selection_result=selection_result,
                chosen_proposal_id=chosen_proposal_id,
                operator_rationale="Override for review recomputation coverage.",
            )
        )
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id=f"resolution:{chosen_proposal_id}",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id=f"materialization:{chosen_proposal_id}",
            proposal_result=proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id=f"formation:{chosen_proposal_id}",
            materialized_effective_proposal=materialized,
            scope=truth.scope,
            basis_state_version=truth.state_version,
        )
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id=f"governance:{chosen_proposal_id}",
            formed_action_result=formed_action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=truth,
        )
    )
    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized,
        formed_action_result=formed_action,
        governance_handoff_result=governance_handoff,
        proposal_result=proposal_result,
        action_scope=truth.scope,
        basis_state_version=truth.state_version,
        governance_policy=Policy(approval_required=True),
        governance_approval=None,
        governance_truth=truth,
    )