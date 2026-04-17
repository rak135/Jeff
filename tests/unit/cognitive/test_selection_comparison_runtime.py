from dataclasses import dataclass, field

import pytest

from jeff.cognitive.proposal import ProposalResult, ProposalResultOption
from jeff.cognitive.selection import SelectionRequest
from jeff.cognitive.selection.comparison import SelectionComparisonRequest
from jeff.cognitive.selection.comparison_runtime import (
    SelectionComparisonRuntimeError,
    SelectionRawComparisonResult,
    run_selection_comparison,
)
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    ModelInvocationStatus,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
    OutputStrategy,
    Purpose,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.infrastructure.contract_runtime import ContractCallRequest
from jeff.infrastructure.model_adapters.errors import ModelTimeoutError


def test_runtime_handoff_routes_through_existing_runtime_pattern_for_selection() -> None:
    request = _comparison_request()
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                    fake_text_response="wrong adapter",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-selection",
                    model_name="selection-model",
                    fake_text_response="DISPOSITION: defer\nSELECTED_PROPOSAL_ID: NONE",
                ),
            ),
            purpose_overrides=PurposeOverrides(selection="fake-selection"),
        )
    )

    result = run_selection_comparison(
        request,
        infrastructure_services=services,
    )

    assert isinstance(result, SelectionRawComparisonResult)
    assert result.request_id == request.request_id
    assert result.adapter_id == "fake-selection"
    assert result.model_output_text.startswith("DISPOSITION: defer")


def test_runtime_handoff_uses_prompt_bundle_builder_without_parsing_or_validation() -> None:
    request = _comparison_request()
    runtime = _TrackingContractRuntime(
        response=ModelResponse(
            request_id=request.request_id,
            adapter_id="tracking-adapter",
            provider_name="fake",
            model_name="tracking-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text="DISPOSITION: selected\nSELECTED_PROPOSAL_ID: proposal-1\nPRIMARY_BASIS: Raw model text only.",
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
    )

    result = run_selection_comparison(
        request,
        infrastructure_services=_FakeServices(runtime),
    )

    assert runtime.invoke_with_request_calls == []
    assert len(runtime.invoke_calls) == 1
    call = runtime.invoke_calls[0]
    assert call.request_id == request.request_id
    assert "CONSIDERED_PROPOSAL_IDS:\nproposal-1,proposal-2" in call.prompt
    assert "Selection is bounded choice, not permission." in call.system_instructions
    assert call.purpose == "selection_comparison"
    assert call.routing_purpose == Purpose.SELECTION
    assert call.output_strategy is OutputStrategy.BOUNDED_TEXT_THEN_PARSE
    assert call.response_mode is ModelResponseMode.TEXT
    assert result.model_output_text == "DISPOSITION: selected\nSELECTED_PROPOSAL_ID: proposal-1\nPRIMARY_BASIS: Raw model text only."
    assert not hasattr(result, "disposition")


def test_runtime_failures_are_surfaced_explicitly() -> None:
    request = _comparison_request()
    runtime = _TrackingContractRuntime(raised_exception=ModelTimeoutError("timed out"))

    with pytest.raises(SelectionComparisonRuntimeError, match="runtime handoff failed"):
        run_selection_comparison(
            request,
            infrastructure_services=_FakeServices(runtime),
        )


def test_runtime_rejects_non_text_completed_response() -> None:
    request = _comparison_request()
    runtime = _TrackingContractRuntime(
        response=ModelResponse(
            request_id=request.request_id,
            adapter_id="tracking-adapter",
            provider_name="fake",
            model_name="tracking-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text=None,
            output_json={"unexpected": "json"},
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
    )

    with pytest.raises(SelectionComparisonRuntimeError, match="requires raw text output"):
        run_selection_comparison(
            request,
            infrastructure_services=_FakeServices(runtime),
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
        raise AssertionError("selection slice 3 should not use invoke_with_request")


@dataclass
class _FakeServices:
    runtime: _TrackingContractRuntime

    @property
    def contract_runtime(self) -> _TrackingContractRuntime:
        return self.runtime


def _comparison_request() -> SelectionComparisonRequest:
    return SelectionComparisonRequest.from_selection_request(
        SelectionRequest(
            request_id="selection-request-1",
            proposal_result=ProposalResult(
                request_id="proposal-request-1",
                scope=_scope(),
                options=(
                    ProposalResultOption(
                        option_index=1,
                        proposal_id="proposal-1",
                        proposal_type="direct_action",
                        title="Implement the bounded change",
                        why_now="Current truth keeps this bounded path viable.",
                        summary="Implement the bounded change in the current scope.",
                    ),
                    ProposalResultOption(
                        option_index=2,
                        proposal_id="proposal-2",
                        proposal_type="clarify",
                        title="Clarify the missing boundary first",
                        why_now="Boundary ambiguity still matters.",
                        summary="Clarify the remaining boundary before stronger choice.",
                    ),
                ),
            ),
        )
    )


def _scope():
    from jeff.core.schemas import Scope

    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
