import pytest

import jeff.cognitive.action_governance_handoff as handoff_module
from jeff.cognitive.action_formation import ActionFormationRequest, FormedActionResult, form_action_from_materialized_proposal
from jeff.cognitive.action_governance_handoff import (
    ActionGovernanceHandoffRequest,
    handoff_action_to_governance,
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
from jeff.cognitive.selection_override import OperatorSelectionOverrideRequest, build_operator_selection_override
from jeff.core.schemas import Scope
from jeff.governance import Approval, CurrentTruthSnapshot, Policy


def test_selection_source_formed_action_is_handed_to_real_governance() -> None:
    formed_action = _formed_action_result()

    result = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-1",
            formed_action_result=formed_action,
            policy=Policy(protected_surface=True),
            approval=None,
            truth=_truth(),
        )
    )

    assert result.governance_evaluated is True
    assert result.governance_result is not None
    assert result.governance_result.governance_outcome == "allowed_now"
    assert result.effective_source == "selection"
    assert result.action is formed_action.action


def test_override_source_formed_action_is_handed_to_real_governance() -> None:
    formed_action = _formed_action_result(effective_source="operator_override")

    result = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-2",
            formed_action_result=formed_action,
            policy=Policy(),
            approval=None,
            truth=_truth(),
        )
    )

    assert result.governance_evaluated is True
    assert result.governance_result is not None
    assert result.governance_result.action_id == str(formed_action.action.action_id)  # type: ignore[union-attr]
    assert result.effective_source == "operator_override"


def test_no_action_result_returns_no_governance_outcome_without_error() -> None:
    formed_action = _formed_action_result(proposal_type="planning_insertion")

    result = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-3",
            formed_action_result=formed_action,
            policy=Policy(),
            approval=None,
            truth=_truth(),
        )
    )

    assert result.governance_evaluated is False
    assert result.governance_result is None
    assert result.no_governance_reason == "No governance evaluation occurred because no Action was formed."


def test_governance_is_invoked_for_override_derived_formed_action_and_does_not_reuse_old_approval() -> None:
    selection_formed_action = _formed_action_result()
    prior_approval = Approval.granted_for(
        action_id=str(selection_formed_action.action.action_id),  # type: ignore[union-attr]
        action_binding_key=selection_formed_action.action.binding_key,  # type: ignore[union-attr]
        basis_state_version=3,
    )
    override_formed_action = _formed_action_result(effective_source="operator_override")

    call_count = {"count": 0}
    original = handoff_module.evaluate_action_entry

    def _counting_evaluate_action_entry(*, action, policy, approval, truth):
        call_count["count"] += 1
        return original(action=action, policy=policy, approval=approval, truth=truth)

    handoff_module.evaluate_action_entry = _counting_evaluate_action_entry
    try:
        result = handoff_action_to_governance(
            ActionGovernanceHandoffRequest(
                request_id="governance-handoff-4",
                formed_action_result=override_formed_action,
                policy=Policy(approval_required=True),
                approval=prior_approval,
                truth=_truth(),
            )
        )
    finally:
        handoff_module.evaluate_action_entry = original

    assert call_count["count"] == 1
    assert result.governance_evaluated is True
    assert result.governance_result is not None
    assert result.governance_result.approval_verdict == "mismatched"
    assert result.governance_result.governance_outcome == "invalidated"
    assert result.governance_result.allowed_now is False


def test_handoff_preserves_truthful_linkage_and_upstream_object() -> None:
    formed_action = _formed_action_result()
    original_snapshot = FormedActionResult(
        formation_id=formed_action.formation_id,
        selection_id=formed_action.selection_id,
        effective_source=formed_action.effective_source,
        effective_proposal_id=formed_action.effective_proposal_id,
        action=formed_action.action,
        action_formed=formed_action.action_formed,
        no_action_reason=formed_action.no_action_reason,
        proposal_type=formed_action.proposal_type,
        summary=formed_action.summary,
    )

    result = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-5",
            formed_action_result=formed_action,
            policy=Policy(),
            approval=None,
            truth=_truth(),
        )
    )

    assert result.selection_id == formed_action.selection_id
    assert result.effective_proposal_id == formed_action.effective_proposal_id
    assert formed_action == original_snapshot


def _formed_action_result(
    *,
    effective_source: str = "selection",
    proposal_type: str = "direct_action",
) -> FormedActionResult:
    selection_result = SelectionResult(
        selection_id="selection-1",
        considered_proposal_ids=("proposal-1", "proposal-2"),
        selected_proposal_id="proposal-1",
        rationale="The original Selection result chose the first bounded option.",
    )
    proposal_result = _proposal_result(second_direct_action=True, first_proposal_type=proposal_type)

    if effective_source == "operator_override":
        operator_override = build_operator_selection_override(
            OperatorSelectionOverrideRequest(
                request_id="override-request-1",
                selection_result=selection_result,
                chosen_proposal_id="proposal-2",
                operator_rationale="Carry a separate downstream operator choice.",
            )
        )
    else:
        operator_override = None

    resolved = resolve_selection_action_basis(
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
            resolved_basis=resolved,
        )
    )
    return form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-1",
            materialized_effective_proposal=materialized,
            scope=_scope(),
            basis_state_version=3,
        )
    )


def _proposal_result(*, second_direct_action: bool, first_proposal_type: str = "direct_action") -> ProposalResult:
    second_type = "direct_action" if second_direct_action else "clarify"
    return ProposalResult(
        request_id="proposal-request-1",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type=first_proposal_type,  # type: ignore[arg-type]
                title="Implement the bounded change",
                why_now="The bounded path is ready.",
                summary="Implement the bounded change",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type=second_type,  # type: ignore[arg-type]
                title="Implement the second bounded change",
                why_now="The operator wants the alternate bounded path.",
                summary="Implement the second bounded change",
            ),
        ),
    )


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")


def _truth() -> CurrentTruthSnapshot:
    return CurrentTruthSnapshot(scope=_scope(), state_version=3)
