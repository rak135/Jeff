"""Pure post-selection reconstruction and recompute helpers."""

from __future__ import annotations

from jeff.action.execution import ExecutionResult
from jeff.cognitive import SelectionResult
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
from jeff.cognitive.post_selection.override import OperatorSelectionOverride
from jeff.cognitive.proposal import ProposalResult
from jeff.governance import Approval, CurrentTruthSnapshot, Policy
from jeff.orchestrator import FlowRunResult
from jeff.cognitive.post_selection.selection_review_record import SelectionReviewRecord


def materialize_selection_review_from_available_data(
    *,
    existing_review: SelectionReviewRecord | None,
    flow_run: FlowRunResult | None,
) -> SelectionReviewRecord | None:
    selection_result = None if existing_review is None else existing_review.selection_result
    if selection_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("selection")
        if isinstance(candidate, SelectionResult):
            selection_result = candidate

    proposal_result = None if existing_review is None else existing_review.proposal_result
    if proposal_result is None and flow_run is not None:
        candidate = flow_run.outputs.get("proposal")
        if isinstance(candidate, ProposalResult):
            proposal_result = candidate

    if existing_review is None and selection_result is None and proposal_result is None:
        return None

    operator_override = None if existing_review is None else existing_review.operator_override
    resolved_basis = None if existing_review is None else existing_review.resolved_basis
    materialized_effective_proposal = None if existing_review is None else existing_review.materialized_effective_proposal
    formed_action_result = None if existing_review is None else existing_review.formed_action_result
    governance_handoff_result = None if existing_review is None else existing_review.governance_handoff_result

    governance_policy = None if existing_review is None else existing_review.governance_policy
    if governance_policy is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_policy")
        if isinstance(candidate, Policy):
            governance_policy = candidate

    governance_approval = None if existing_review is None else existing_review.governance_approval
    if governance_approval is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_approval")
        if isinstance(candidate, Approval):
            governance_approval = candidate

    governance_truth = None if existing_review is None else existing_review.governance_truth
    if governance_truth is None and flow_run is not None:
        candidate = flow_run.outputs.get("governance_truth")
        if isinstance(candidate, CurrentTruthSnapshot):
            governance_truth = candidate

    action_scope = None if existing_review is None else existing_review.action_scope
    if action_scope is None and proposal_result is not None:
        action_scope = proposal_result.scope
    basis_state_version = None if existing_review is None else existing_review.basis_state_version
    if governance_truth is not None and basis_state_version is None:
        basis_state_version = governance_truth.state_version

    execution_result = None
    if flow_run is not None:
        candidate = flow_run.outputs.get("execution")
        if isinstance(candidate, ExecutionResult):
            execution_result = candidate
    if execution_result is not None:
        if action_scope is None:
            action_scope = execution_result.governed_request.action.scope
        if basis_state_version is None:
            basis_state_version = execution_result.governed_request.action.basis_state_version

    if (
        selection_result is not None
        and resolved_basis is None
        and (flow_run is not None or proposal_result is not None or operator_override is not None)
    ):
        resolved_basis = resolve_selection_action_basis(
            SelectionActionResolutionRequest(
                request_id=f"selection-review-resolution:{selection_result.selection_id}",
                selection_result=selection_result,
                operator_override=operator_override,
            )
        )

    if proposal_result is not None and resolved_basis is not None and materialized_effective_proposal is None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

    if (
        materialized_effective_proposal is not None
        and action_scope is not None
        and basis_state_version is not None
        and formed_action_result is None
    ):
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{materialized_effective_proposal.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=basis_state_version,
            )
        )

    if (
        formed_action_result is not None
        and governance_policy is not None
        and governance_truth is not None
        and governance_handoff_result is None
    ):
        governance_handoff_result = handoff_action_to_governance(
            ActionGovernanceHandoffRequest(
                request_id=f"selection-review-governance-handoff:{formed_action_result.selection_id}",
                formed_action_result=formed_action_result,
                policy=governance_policy,
                approval=governance_approval,
                truth=governance_truth,
            )
        )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=basis_state_version,
        governance_policy=governance_policy,
        governance_approval=governance_approval,
        governance_truth=governance_truth,
    )


def recompute_selection_review_record(
    *,
    existing_review: SelectionReviewRecord,
    selection_result: SelectionResult,
    operator_override: OperatorSelectionOverride,
) -> SelectionReviewRecord:
    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id=f"selection-review-resolution:{selection_result.selection_id}",
            selection_result=selection_result,
            operator_override=operator_override,
        )
    )

    proposal_result = existing_review.proposal_result
    action_scope = existing_review.action_scope
    materialized_effective_proposal = None
    formed_action_result = None
    governance_handoff_result = None

    if proposal_result is not None:
        materialized_effective_proposal = materialize_effective_proposal(
            SelectionEffectiveProposalRequest(
                request_id=f"selection-review-materialization:{selection_result.selection_id}",
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
            )
        )

        action_scope = action_scope or proposal_result.scope
        formed_action_result = form_action_from_materialized_proposal(
            ActionFormationRequest(
                request_id=f"selection-review-action-formation:{selection_result.selection_id}",
                materialized_effective_proposal=materialized_effective_proposal,
                scope=action_scope,
                basis_state_version=selection_review_basis_state_version(existing_review),
            )
        )

        if existing_review.governance_policy is not None and existing_review.governance_truth is not None:
            governance_handoff_result = handoff_action_to_governance(
                ActionGovernanceHandoffRequest(
                    request_id=f"selection-review-governance-handoff:{selection_result.selection_id}",
                    formed_action_result=formed_action_result,
                    policy=existing_review.governance_policy,
                    approval=existing_review.governance_approval,
                    truth=existing_review.governance_truth,
                )
            )

    return SelectionReviewRecord(
        selection_result=selection_result,
        operator_override=operator_override,
        resolved_basis=resolved_basis,
        materialized_effective_proposal=materialized_effective_proposal,
        formed_action_result=formed_action_result,
        governance_handoff_result=governance_handoff_result,
        proposal_result=proposal_result,
        action_scope=action_scope,
        basis_state_version=selection_review_basis_state_version(existing_review),
        governance_policy=existing_review.governance_policy,
        governance_approval=existing_review.governance_approval,
        governance_truth=existing_review.governance_truth,
    )


def selection_review_basis_state_version(selection_review: SelectionReviewRecord) -> int:
    if selection_review.basis_state_version is not None:
        return selection_review.basis_state_version
    if (
        selection_review.formed_action_result is not None
        and selection_review.formed_action_result.action is not None
    ):
        return selection_review.formed_action_result.action.basis_state_version
    if (
        selection_review.governance_handoff_result is not None
        and selection_review.governance_handoff_result.action is not None
    ):
        return selection_review.governance_handoff_result.action.basis_state_version
    return 0