from dataclasses import dataclass, field

from jeff.cognitive import ProposalResult, ProposalResultOption, SelectionResult, assemble_context_package
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


def test_orchestrator_keeps_deterministic_selection_path_available() -> None:
    scope = _scope()
    result = run_flow(
        flow_id="flow-deterministic-selection",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_deterministic_handlers(scope),
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.selection_failure is None
    assert isinstance(result.outputs["selection"], SelectionResult)
    assert result.outputs["selection"].selected_proposal_id == "proposal-1"
    assert any(event.summary == "entered selection via deterministic path" for event in result.events)
    assert any(event.summary == "exited selection via deterministic path" for event in result.events)


def test_orchestrator_can_run_hybrid_selection_success_path() -> None:
    scope = _scope()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-request-1:selection",
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

    result = run_flow(
        flow_id="flow-hybrid-selection-success",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_hybrid_handlers(scope, runtime),
    )

    assert result.lifecycle.lifecycle_state == "completed"
    assert result.selection_failure is None
    assert isinstance(result.outputs["selection"], SelectionResult)
    assert result.outputs["selection"].selected_proposal_id == "proposal-1"
    assert result.outputs["selection"].considered_proposal_ids == ("proposal-1", "proposal-2")
    assert runtime.invoke_calls and runtime.invoke_calls[0].request_id == "proposal-request-1:selection"
    assert any(event.summary == "entered selection via hybrid path" for event in result.events)
    assert any(event.summary == "exited selection via hybrid path" for event in result.events)


def test_hybrid_runtime_failure_stays_stage_specific_without_fallback() -> None:
    import jeff.cognitive.selection.decision as decision_module

    scope = _scope()
    runtime = _TrackingContractRuntime(raised_exception=ModelTimeoutError("timed out"))

    original = decision_module.run_selection
    decision_module.run_selection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fallback used"))
    try:
        result = run_flow(
            flow_id="flow-hybrid-selection-runtime-failure",
            flow_family="blocked_or_escalation",
            scope=scope,
            stage_handlers=_hybrid_handlers(scope, runtime),
        )
    finally:
        decision_module.run_selection = original

    assert result.lifecycle.lifecycle_state == "failed"
    assert result.lifecycle.current_stage == "selection"
    assert result.selection_failure is not None
    assert result.selection_failure.failure_stage == "runtime"
    assert "selection" not in result.outputs
    assert "action" not in result.outputs
    assert result.events[-1].summary.startswith("selection hybrid runtime failure:")


def test_hybrid_parse_failure_stays_stage_specific() -> None:
    scope = _scope()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-request-1:selection",
            output_text="NOT_A_VALID_SELECTION_LINE",
        )
    )

    result = run_flow(
        flow_id="flow-hybrid-selection-parse-failure",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_hybrid_handlers(scope, runtime),
    )

    assert result.lifecycle.lifecycle_state == "failed"
    assert result.selection_failure is not None
    assert result.selection_failure.failure_stage == "parse"
    assert result.selection_failure.raw_comparison_result is not None
    assert result.selection_failure.parsed_comparison is None
    assert "action" not in result.outputs
    assert result.events[-1].summary.startswith("selection hybrid parse failure:")


def test_hybrid_validation_failure_stays_stage_specific() -> None:
    scope = _scope()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id="proposal-request-1:selection",
            output_text=(
                "DISPOSITION: selected\n"
                "SELECTED_PROPOSAL_ID: proposal-999\n"
                "PRIMARY_BASIS: This option is approved and safe to execute now.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-2\n"
                "MAIN_LOSING_REASON: It is not authorized.\n"
                "PLANNING_INSERTION_RECOMMENDED: no\n"
                "CAUTIONS: execution approved after planning\n"
            ),
        )
    )

    result = run_flow(
        flow_id="flow-hybrid-selection-validation-failure",
        flow_family="blocked_or_escalation",
        scope=scope,
        stage_handlers=_hybrid_handlers(scope, runtime),
    )

    assert result.lifecycle.lifecycle_state == "failed"
    assert result.selection_failure is not None
    assert result.selection_failure.failure_stage == "validation"
    assert result.selection_failure.parsed_comparison is not None
    assert tuple(issue.code for issue in result.selection_failure.validation_issues) == (
        "selected_proposal_out_of_set",
        "authority_leakage",
        "authority_leakage",
        "authority_leakage",
    )
    assert "action" not in result.outputs
    assert result.events[-1].summary.startswith("selection hybrid validation failure:")


def _deterministic_handlers(scope: Scope) -> dict[str, object]:
    handlers = _base_handlers(scope)

    def selection_stage(proposal_result):
        return SelectionResult(
            selection_id="selection-1",
            considered_proposal_ids=tuple(option.proposal_id for option in proposal_result.options),
            selected_proposal_id="proposal-1",
            rationale="The deterministic path keeps the existing bounded choice behavior.",
        )

    return {
        "context": handlers["context"],
        "proposal": handlers["proposal"],
        "selection": selection_stage,
        "action": handlers["action"],
        "governance": handlers["governance"],
    }


def _hybrid_handlers(scope: Scope, runtime: "_TrackingContractRuntime") -> dict[str, object]:
    handlers = _base_handlers(scope)
    return {
        "context": handlers["context"],
        "proposal": handlers["proposal"],
        "selection": HybridSelectionStageConfig(
            selection_id="selection-hybrid-1",
            infrastructure_services=_FakeServices(runtime),
        ),
        "action": handlers["action"],
        "governance": handlers["governance"],
    }


def _base_handlers(scope: Scope) -> dict[str, object]:
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
