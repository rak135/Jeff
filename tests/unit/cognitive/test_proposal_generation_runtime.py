from dataclasses import dataclass, field

import pytest

from jeff.cognitive.proposal import (
    ProposalGenerationPromptBundle,
    ProposalGenerationRawResult,
    ProposalGenerationRuntimeError,
    invoke_proposal_generation_with_runtime,
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


def test_runtime_handoff_routes_through_existing_runtime_pattern_for_proposal() -> None:
    bundle = _bundle()
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
                    adapter_id="fake-proposal",
                    model_name="proposal-model",
                    fake_text_response="PROPOSAL_COUNT: 0\nSCARCITY_REASON: No honest option is currently supported.",
                ),
            ),
            purpose_overrides=PurposeOverrides(proposal="fake-proposal"),
        )
    )

    result = invoke_proposal_generation_with_runtime(
        bundle,
        infrastructure_services=services,
    )

    assert isinstance(result, ProposalGenerationRawResult)
    assert result.request_id == bundle.request_id
    assert result.adapter_id == "fake-proposal"
    assert result.raw_output_text.startswith("PROPOSAL_COUNT: 0")


def test_runtime_handoff_consumes_rendered_prompt_bundle_without_parsing_or_repair_path() -> None:
    bundle = _bundle()
    runtime = _TrackingContractRuntime(
        response=ModelResponse(
            request_id=bundle.request_id,
            adapter_id="tracking-adapter",
            provider_name="fake",
            model_name="tracking-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text="PROPOSAL_COUNT: 1\nSCARCITY_REASON: Only one path remains.",
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
    )

    result = invoke_proposal_generation_with_runtime(
        bundle,
        infrastructure_services=_FakeServices(runtime),
    )

    assert runtime.invoke_with_request_calls == []
    assert len(runtime.invoke_calls) == 1
    call = runtime.invoke_calls[0]
    assert call.prompt == bundle.prompt
    assert call.system_instructions == bundle.system_instructions
    assert call.request_id == bundle.request_id
    assert call.purpose == "proposal_generation_step1"
    assert call.routing_purpose == Purpose.PROPOSAL
    assert call.output_strategy is OutputStrategy.BOUNDED_TEXT_THEN_PARSE
    assert call.response_mode is ModelResponseMode.TEXT
    assert result.raw_output_text == "PROPOSAL_COUNT: 1\nSCARCITY_REASON: Only one path remains."
    assert not hasattr(result, "options")


def test_runtime_failures_are_surfaced_explicitly() -> None:
    bundle = _bundle()
    runtime = _TrackingContractRuntime(raised_exception=ModelTimeoutError("timed out"))

    with pytest.raises(ProposalGenerationRuntimeError, match="runtime handoff failed"):
        invoke_proposal_generation_with_runtime(
            bundle,
            infrastructure_services=_FakeServices(runtime),
        )


def test_runtime_rejects_non_text_completed_response() -> None:
    bundle = _bundle()
    runtime = _TrackingContractRuntime(
        response=ModelResponse(
            request_id=bundle.request_id,
            adapter_id="tracking-adapter",
            provider_name="fake",
            model_name="tracking-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text=None,
            output_json={"unexpected": "json"},
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )
    )

    with pytest.raises(ProposalGenerationRuntimeError, match="requires raw text output"):
        invoke_proposal_generation_with_runtime(
            bundle,
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
        raise AssertionError("proposal slice D should not use invoke_with_request")


@dataclass
class _FakeServices:
    runtime: _TrackingContractRuntime

    @property
    def contract_runtime(self) -> _TrackingContractRuntime:
        return self.runtime


def _bundle() -> ProposalGenerationPromptBundle:
    return ProposalGenerationPromptBundle(
        request_id="proposal-generation:project-1:wu-1:run-1:test-objective",
        scope=_scope(),
        objective="Frame bounded proposal options",
        system_instructions="Proposal generates possibilities, not authority.",
        prompt="TASK: bounded proposal generation\nOBJECTIVE:\nFrame bounded proposal options",
    )


def _scope():
    from jeff.core.schemas import Scope

    return Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
