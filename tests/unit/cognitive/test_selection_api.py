from dataclasses import dataclass, field

import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionRequest
from jeff.cognitive.selection.api import (
    SelectionRunFailure,
    SelectionRunSuccess,
    run_selection_hybrid,
)
from jeff.core.schemas import Scope
from jeff.infrastructure import ModelInvocationStatus, ModelResponse, ModelUsage
from jeff.infrastructure.contract_runtime import ContractCallRequest
from jeff.infrastructure.model_adapters.errors import ModelTimeoutError


def test_successful_hybrid_run_returns_canonical_selection_result() -> None:
    request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=request.request_id,
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

    result = run_selection_hybrid(
        request,
        selection_id="selection-1",
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, SelectionRunSuccess)
    assert result.status == "validated_success"
    assert result.selection_result.selected_proposal_id == "proposal-1"
    assert result.selection_result.non_selection_outcome is None
    assert result.selection_result.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert (
        result.selection_result.rationale
        == "This option has the strongest bounded support. "
        "Main losing alternative proposal-2: It still depends on unresolved clarification. "
        "Cautions: keep scope tight and preserve bounded review"
    )


@pytest.mark.parametrize("disposition", ["reject_all", "defer", "escalate"])
def test_non_selection_outputs_compose_into_selection_result(disposition: str) -> None:
    request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=request.request_id,
            output_text=(
                f"DISPOSITION: {disposition}\n"
                "SELECTED_PROPOSAL_ID: NONE\n"
                "PRIMARY_BASIS: A non-selection outcome is more honest under current visible limits.\n"
                "MAIN_LOSING_ALTERNATIVE_ID: proposal-1\n"
                "MAIN_LOSING_REASON: The strongest option still remains materially blocked.\n"
                "PLANNING_INSERTION_RECOMMENDED: yes\n"
                "CAUTIONS: preserve bounded choice and keep governance separate\n"
            ),
        )
    )

    result = run_selection_hybrid(
        request,
        selection_id="selection-2",
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, SelectionRunSuccess)
    assert result.selection_result.selected_proposal_id is None
    assert result.selection_result.non_selection_outcome == disposition
    assert result.selection_result.considered_proposal_ids == ("proposal-1", "proposal-2")
    assert "Planning insertion may still help later." in result.selection_result.rationale


def test_runtime_failure_returns_runtime_stage_failure_without_fallback() -> None:
    import jeff.cognitive.selection.decision as decision_module

    request = _selection_request()
    runtime = _TrackingContractRuntime(raised_exception=ModelTimeoutError("timed out"))

    original = decision_module.run_selection
    decision_module.run_selection = lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("fallback used"))
    try:
        result = run_selection_hybrid(
            request,
            selection_id="selection-3",
            infrastructure_services=_FakeServices(runtime),
        )
    finally:
        decision_module.run_selection = original

    assert isinstance(result, SelectionRunFailure)
    assert result.failure_stage == "runtime"
    assert result.status == "runtime_failure"
    assert result.raw_comparison_result is None
    assert result.parsed_comparison is None


def test_parse_failure_returns_parsing_stage_failure() -> None:
    request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=request.request_id,
            output_text="NOT_A_VALID_SELECTION_LINE",
        )
    )

    result = run_selection_hybrid(
        request,
        selection_id="selection-4",
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, SelectionRunFailure)
    assert result.failure_stage == "parse"
    assert result.status == "parse_failure"
    assert result.raw_comparison_result is not None
    assert result.parsed_comparison is None


def test_validation_failure_returns_validation_stage_failure() -> None:
    request = _selection_request()
    runtime = _TrackingContractRuntime(
        response=_response(
            request_id=request.request_id,
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

    result = run_selection_hybrid(
        request,
        selection_id="selection-5",
        infrastructure_services=_FakeServices(runtime),
    )

    assert isinstance(result, SelectionRunFailure)
    assert result.failure_stage == "validation"
    assert result.status == "validation_failure"
    assert result.parsed_comparison is not None
    assert tuple(issue.code for issue in result.validation_issues) == (
        "selected_proposal_out_of_set",
        "authority_leakage",
        "authority_leakage",
        "authority_leakage",
    )


@dataclass
class _TrackingContractRuntime:
    response: ModelResponse | None = None
    raised_exception: Exception | None = None
    invoke_calls: list[ContractCallRequest] = field(default_factory=list)
    invoke_with_request_calls: list[tuple[object, str]] = field(default_factory=list)

    def invoke(self, call: ContractCallRequest) -> ModelResponse:
        self.invoke_calls.append(call)
        if self.raised_exception is not None:
            raise self.raised_exception
        assert self.response is not None
        return self.response

    def invoke_with_request(self, request: object, *, adapter_id: str) -> ModelResponse:
        self.invoke_with_request_calls.append((request, adapter_id))
        raise AssertionError("selection slice 6 should not use invoke_with_request")


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


def _selection_request() -> SelectionRequest:
    return SelectionRequest(
        request_id="selection-request-1",
        proposal_result=ProposalResult(
            request_id="proposal-request-1",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
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
                    proposal_type="clarify",
                    title="Clarify the missing edge case first",
                    why_now="Remaining ambiguity matters.",
                    summary="Clarify the missing edge case first",
                ),
            ),
        ),
    )
