import json
from dataclasses import dataclass, field

import pytest

from jeff.cognitive.action_formation import ActionFormationRequest, form_action_from_materialized_proposal
from jeff.cognitive.action_governance_handoff import ActionGovernanceHandoffRequest, handoff_action_to_governance
from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionRequest, SelectionResult
from jeff.cognitive.selection.api import SelectionRunSuccess, run_selection_hybrid
from jeff.cognitive.selection_action_resolution import (
    SelectionActionResolutionRequest,
    resolve_selection_action_basis,
)
from jeff.cognitive.selection_effective_proposal import (
    SelectionEffectiveProposalRequest,
    materialize_effective_proposal,
)
from jeff.core.schemas import Scope
from jeff.governance import CurrentTruthSnapshot, Policy
from jeff.infrastructure import ModelInvocationStatus, ModelResponse, ModelUsage
from jeff.infrastructure.contract_runtime import ContractCallRequest
from jeff.interface import JeffCLI
from jeff.interface.commands import InterfaceContext, SelectionReviewRecord

from tests.fixtures.cli import build_state_with_run


def test_acceptance_hybrid_selected_chain_stays_truthful() -> None:
    selection_request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=selection_request.request_id,
            output_text=(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-1\n"
                "PRIMARY_BASIS: This option has the strongest bounded support.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It still depends on unresolved clarification.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: keep scope tight and preserve bounded review\n"
            ),
        )
    )

    hybrid_result = run_selection_hybrid(
        selection_request,
        selection_id="selection-1",
        infrastructure_services=_FakeServices(runtime),
    )
    assert isinstance(hybrid_result, SelectionRunSuccess)

    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-1",
            selection_result=hybrid_result.selection_result,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-1",
            proposal_result=selection_request.proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-1",
            materialized_effective_proposal=materialized,
            scope=_scope(),
            basis_state_version=3,
        )
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-1",
            formed_action_result=formed_action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=_scope(), state_version=3),
        )
    )

    assert hybrid_result.selection_result.selected_proposal_id == "proposal-1"
    assert resolved_basis.effective_source == "selection"
    assert materialized.effective_proposal_option is not None
    assert formed_action.action_formed is True
    assert governance_handoff.governance_evaluated is True
    assert governance_handoff.governance_result is not None
    assert governance_handoff.governance_result.allowed_now is False


def test_acceptance_hybrid_non_selection_case_forms_no_actionable_basis() -> None:
    selection_request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=selection_request.request_id,
            output_text=(
                "DISPOSITION: defer\n"
                "SELECTED_PROPOSAL_ID: NONE\n"
                "PRIMARY_BASIS: More bounded clarification is still needed.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
                "MAIN_LOSING_REASON: The strongest option still has unresolved assumptions.\n"
                "PLANNING_INSERTION_RECOMMENDED: yes\n"
                "CAUTIONS: keep governance separate and avoid fake decisiveness\n"
            ),
        )
    )

    hybrid_result = run_selection_hybrid(
        selection_request,
        selection_id="selection-2",
        infrastructure_services=_FakeServices(runtime),
    )
    assert isinstance(hybrid_result, SelectionRunSuccess)

    resolved_basis = resolve_selection_action_basis(
        SelectionActionResolutionRequest(
            request_id="resolution-request-2",
            selection_result=hybrid_result.selection_result,
        )
    )
    materialized = materialize_effective_proposal(
        SelectionEffectiveProposalRequest(
            request_id="materialization-request-2",
            proposal_result=selection_request.proposal_result,
            resolved_basis=resolved_basis,
        )
    )
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-2",
            materialized_effective_proposal=materialized,
            scope=_scope(),
            basis_state_version=3,
        )
    )
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-2",
            formed_action_result=formed_action,
            policy=Policy(approval_required=True),
            approval=None,
            truth=CurrentTruthSnapshot(scope=_scope(), state_version=3),
        )
    )

    assert hybrid_result.selection_result.selected_proposal_id is None
    assert hybrid_result.selection_result.non_selection_outcome == "defer"
    assert resolved_basis.effective_source == "none"
    assert materialized.effective_proposal_option is None
    assert formed_action.action_formed is False
    assert governance_handoff.governance_evaluated is False
    assert governance_handoff.governance_result is None


def test_acceptance_override_case_keeps_original_selection_visible_and_updates_downstream_choice() -> None:
    cli = JeffCLI(context=_context_with_selection_review(selection_result=_selection_result()))

    cli.run_one_shot('/selection override proposal-2 --why "Operator wants the alternate bounded option." run-1')
    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["override"]["exists"] is True
    assert payload["override"]["chosen_proposal_id"] == "proposal-2"
    assert payload["resolved_choice"]["effective_source"] == "operator_override"
    assert payload["resolved_choice"]["effective_proposal_id"] == "proposal-2"
    assert payload["action_formation"]["action_formed"] is True
    assert payload["governance_handoff"]["governance_evaluated"] is True
    assert payload["governance_handoff"]["allowed_now"] is False


def test_acceptance_invalid_override_attempt_leaves_existing_chain_unchanged() -> None:
    cli = JeffCLI(context=_context_with_selection_review(selection_result=_selection_result()))

    before_payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    with pytest.raises(ValueError, match="chosen_proposal_id"):
        cli.run_one_shot('/selection override proposal-999 --why "Out-of-set override." run-1')

    after_payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert after_payload == before_payload
    assert after_payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert after_payload["override"]["exists"] is False


def test_acceptance_review_surface_is_honest_when_downstream_artifacts_are_missing() -> None:
    state, scope = build_state_with_run()
    cli = JeffCLI(
        context=InterfaceContext(
            state=state,
            selection_reviews={
                str(scope.run_id): SelectionReviewRecord(selection_result=_selection_result()),
            },
        )
    )

    payload = json.loads(cli.run_one_shot("/selection show run-1", json_output=True))

    assert payload["selection"]["selected_proposal_id"] == "proposal-1"
    assert payload["override"]["missing_reason"] == "no override recorded"
    assert payload["resolved_choice"]["missing_reason"] == "no resolved downstream basis available"
    assert payload["action_formation"]["missing_reason"] == "no Action formation result available"
    assert payload["governance_handoff"]["missing_reason"] == "governance handoff has not been recorded"


def _context_with_selection_review(*, selection_result: SelectionResult) -> InterfaceContext:
    state, scope = build_state_with_run()
    action_scope = _scope()
    proposal_result = selection_result.proposal_result if hasattr(selection_result, "proposal_result") else None
    proposal_result = proposal_result or _proposal_result()
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
    formed_action = form_action_from_materialized_proposal(
        ActionFormationRequest(
            request_id="formation-request-3",
            materialized_effective_proposal=materialized,
            scope=action_scope,
            basis_state_version=3,
        )
    )
    policy = Policy(approval_required=True)
    truth = CurrentTruthSnapshot(scope=action_scope, state_version=3)
    governance_handoff = handoff_action_to_governance(
        ActionGovernanceHandoffRequest(
            request_id="governance-handoff-3",
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
                proposal_result=proposal_result,
                resolved_basis=resolved_basis,
                materialized_effective_proposal=materialized,
                formed_action_result=formed_action,
                governance_handoff_result=governance_handoff,
                action_scope=action_scope,
                basis_state_version=3,
                governance_policy=policy,
                governance_approval=None,
                governance_truth=truth,
            )
        },
    )


def _selection_request() -> SelectionRequest:
    return SelectionRequest(request_id="proposal-request-1:selection", proposal_result=_proposal_result())


def _proposal_result() -> ProposalResult:
    return ProposalResult(
        request_id="proposal-request-1",
        scope=_scope(),
        options=(
            ProposalResultOption(
                option_index=1,
                proposal_id="proposal-1",
                proposal_type="direct_action",
                title="Implement the bounded option",
                why_now="This option has the strongest bounded fit.",
                summary="Implement the bounded option",
            ),
            ProposalResultOption(
                option_index=2,
                proposal_id="proposal-2",
                proposal_type="direct_action",
                title="Implement the alternate bounded option",
                why_now="The alternate bounded option is still viable.",
                summary="Implement the alternate bounded option",
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


@dataclass
class _TrackingContractRuntime:
    response: ModelResponse | None = None
    raised_exception: Exception | None = None
    invoke_calls: list[ContractCallRequest] = field(default_factory=list)

    def invoke(self, call: ContractCallRequest) -> ModelResponse:
        self.invoke_calls.append(call)
        if self.raised_exception is not None:
            raise self.raised_exception
        assert self.response is not None
        return self.response


@dataclass
class _FakeServices:
    runtime: _TrackingContractRuntime

    @property
    def contract_runtime(self) -> _TrackingContractRuntime:
        return self.runtime


def _response(*, request_id: str, output_text: str) -> ModelResponse:
    return ModelResponse(
        request_id=request_id,
        adapter_id="tracking-adapter",
        provider_name="fake",
        model_name="tracking-model",
        status=ModelInvocationStatus.COMPLETED,
        output_text=output_text,
        output_json=None,
        usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
    )
