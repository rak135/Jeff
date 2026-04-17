from dataclasses import dataclass, field

import pytest

from jeff.cognitive import ProposalResult, ProposalResultOption, SelectionResult, assemble_context_package
from jeff.cognitive.selection import SelectionRequest
from jeff.cognitive.selection.api import SelectionRunFailure, run_selection_hybrid
from jeff.cognitive.types import TriggerInput
from jeff.contracts import Action
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.governance import CurrentTruthSnapshot, Policy, evaluate_action_entry
from jeff.infrastructure import ModelInvocationStatus, ModelResponse, ModelUsage
from jeff.infrastructure.contract_runtime import ContractCallRequest
from jeff.infrastructure.model_adapters.errors import ModelTimeoutError
from jeff.orchestrator import HybridSelectionStageConfig, run_flow


@pytest.mark.parametrize(
    ("failure_stage", "response_text", "raised_exception"),
    (
        ("runtime", None, ModelTimeoutError("timed out")),
        ("parse", "NOT_A_VALID_SELECTION_LINE", None),
        (
            "validation",
            (
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-999\n"
                "PRIMARY_BASIS: This option is approved and safe to execute now.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It is not authorized.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: execution approved after planning\n"
            ),
            None,
        ),
    ),
)
def test_hybrid_selection_api_failures_remain_stage_specific(
    failure_stage: str,
    response_text: str | None,
    raised_exception: Exception | None,
) -> None:
    request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=None if response_text is None else _response(request_id=request.request_id, output_text=response_text),
        raised_exception=raised_exception,
    )

    result = run_selection_hybrid(
        request,
        selection_id="selection-hybrid-1",
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, SelectionRunFailure)
    assert result.failure_stage == failure_stage
    assert result.status == f"{failure_stage}_failure"
    if failure_stage == "runtime":
        assert result.raw_comparison_result is None
        assert result.parsed_comparison is None
        assert result.validation_issues == ()
    elif failure_stage == "parse":
        assert result.raw_comparison_result is not None
        assert result.parsed_comparison is None
        assert result.validation_issues == ()
    else:
        assert result.raw_comparison_result is not None
        assert result.parsed_comparison is not None
        assert tuple(issue.code for issue in result.validation_issues) == (
            "selected_proposal_out_of_set",
            "authority_leakage",
            "authority_leakage",
            "authority_leakage",
        )


@pytest.mark.parametrize(
    ("failure_stage", "response_text", "raised_exception"),
    (
        ("runtime", None, ModelTimeoutError("timed out")),
        ("parse", "NOT_A_VALID_SELECTION_LINE", None),
        (
            "validation",
            (
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-999\n"
                "PRIMARY_BASIS: This option is approved and safe to execute now.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It is not authorized.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: execution approved after planning\n"
            ),
            None,
        ),
    ),
)
def test_orchestrator_preserves_hybrid_failure_stage_without_flattening(
    failure_stage: str,
    response_text: str | None,
    raised_exception: Exception | None,
) -> None:
    scope = _scope()
    runtime = _TrackingContractRuntime(
        response=None if response_text is None else _response(request_id="proposal-request-1:selection", output_text=response_text),
        raised_exception=raised_exception,
    )

    result = run_flow(
        flow_id=f"flow-selection-{failure_stage}-failure",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_hybrid_handlers(scope, runtime),
    )

    assert result.lifecycle.lifecycle_state == "failed"
    assert result.lifecycle.current_stage == "selection"
    assert result.selection_failure is not None
    assert result.selection_failure.failure_stage == failure_stage
    assert result.selection_failure.status == f"{failure_stage}_failure"
    assert "selection" not in result.outputs
    assert "action" not in result.outputs
    assert result.events[-1].summary.startswith(f"selection hybrid {failure_stage} failure:")
    assert "success" not in result.events[-1].summary


def _selection_request() -> SelectionRequest:
    return SelectionRequest(
        request_id="proposal-request-1:selection",
        proposal_result=ProposalResult(
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
                    proposal_type="clarify",
                    title="Clarify the missing edge case first",
                    why_now="Open ambiguity still matters.",
                    summary="Clarify the missing edge case first",
                ),
            ),
        ),
    )


def _hybrid_handlers(scope: Scope, runtime: "_TrackingContractRuntime") -> dict[str, object]:
    state = _state(scope)

    def context_stage(_):
        return assemble_context_package(
            trigger=TriggerInput(trigger_summary="Run the bounded hybrid selection path"),
            purpose="proposal support",
            scope=scope,
            state=state,
        )

    def proposal_stage(_context):
        return ProposalResult(
            request_id="proposal-request-1",
            scope=scope,
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
                    proposal_type="clarify",
                    title="Clarify the missing edge case first",
                    why_now="Open ambiguity still matters.",
                    summary="Clarify the missing edge case first",
                ),
            ),
        )

    def action_stage(_selection):
        return Action(
            action_id="action-1",
            scope=scope,
            intent_summary="Apply the bounded selection result",
            basis_state_version=3,
        )

    def governance_stage(action):
        return evaluate_action_entry(
            action=action,
            policy=Policy(),
            approval=None,
            truth=CurrentTruthSnapshot(scope=scope, state_version=3),
        )

    return {
        "context": context_stage,
        "proposal": proposal_stage,
        "selection": HybridSelectionStageConfig(
            selection_id="selection-hybrid-1",
            infrastructure_services=_FakeServices(runtime),
        ),
        "action": action_stage,
        "governance": governance_stage,
    }


def _scope() -> Scope:
    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")


def _state(scope: Scope):
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=str(scope.project_id)),
            payload={"work_unit_id": str(scope.work_unit_id), "objective": "Exercise Selection hybrid orchestration"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=str(scope.project_id), work_unit_id=str(scope.work_unit_id)),
            payload={"run_id": str(scope.run_id)},
        ),
    ).state
    return state


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
