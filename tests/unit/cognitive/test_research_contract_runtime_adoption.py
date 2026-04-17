"""Focused tests verifying ContractRuntime adoption in the research synthesis path.

These tests verify that:
- invoke_with_request on ContractRuntime correctly dispatches pre-built ModelRequests
- synthesize_research_with_runtime routes Step 1 and formatter calls through ContractRuntime
- synthesize_research without contract_runtime still works (direct adapter path remains intact)
- No behavior change in either path
"""

from dataclasses import dataclass, field

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    SourceItem,
    synthesize_research,
    synthesize_research_with_runtime,
)
from jeff.cognitive.research import synthesis as research_synthesis_module
from jeff.cognitive.research.errors import ResearchSynthesisValidationError
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ContractCallRequest,
    ModelAdapterRuntimeConfig,
    ModelInvocationStatus,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    OutputStrategy,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.infrastructure.contract_runtime import ContractRuntime


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@dataclass
class _TrackingAdapter:
    """Fake adapter that records every invoke call made through it."""

    adapter_id: str = "tracking-adapter"
    provider_name: str = "fake"
    model_name: str = "fake-model"
    text_response: str = ""
    json_response: dict | None = None
    requests: list[ModelRequest] = field(default_factory=list)

    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        from jeff.infrastructure.model_adapters.types import ModelResponseMode
        if request.response_mode is ModelResponseMode.JSON and self.json_response is not None:
            return ModelResponse(
                request_id=request.request_id,
                adapter_id=self.adapter_id,
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ModelInvocationStatus.COMPLETED,
                output_text=None,
                output_json=dict(self.json_response),
                usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        return ModelResponse(
            request_id=request.request_id,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            status=ModelInvocationStatus.COMPLETED,
            output_text=self.text_response,
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )


@dataclass
class _TrackingContractRuntime:
    step1_text_response: str
    formatter_json_response: dict | None = None
    invoke_calls: list[ContractCallRequest] = field(default_factory=list)
    invoke_with_request_calls: list[tuple[ModelRequest, str]] = field(default_factory=list)

    def invoke(self, call: ContractCallRequest) -> ModelResponse:
        self.invoke_calls.append(call)
        return ModelResponse(
            request_id=call.request_id or "generated-request",
            adapter_id="runtime-research",
            provider_name="fake",
            model_name="runtime-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text=self.step1_text_response,
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )

    def invoke_with_request(self, request: ModelRequest, *, adapter_id: str) -> ModelResponse:
        self.invoke_with_request_calls.append((request, adapter_id))
        if request.response_mode is research_synthesis_module.ModelResponseMode.JSON:
            return ModelResponse(
                request_id=request.request_id,
                adapter_id=adapter_id,
                provider_name="fake",
                model_name="formatter-model",
                status=ModelInvocationStatus.COMPLETED,
                output_text=None,
                output_json=dict(self.formatter_json_response or {}),
                usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        return ModelResponse(
            request_id=request.request_id,
            adapter_id=adapter_id,
            provider_name="fake",
            model_name="runtime-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text=self.step1_text_response,
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )


def _services(primary_adapter, *, formatter_adapter=None, purpose_overrides=None):
    adapters = [
        AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.FAKE,
            adapter_id=primary_adapter.adapter_id,
            model_name=primary_adapter.model_name,
            fake_text_response=primary_adapter.text_response,
        ),
    ]
    if formatter_adapter is not None:
        adapters.append(
            AdapterFactoryConfig(
                provider_kind=AdapterProviderKind.FAKE,
                adapter_id=formatter_adapter.adapter_id,
                model_name=formatter_adapter.model_name,
                fake_text_response=formatter_adapter.text_response or "{}",
            )
        )
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id=primary_adapter.adapter_id,
            adapters=tuple(adapters),
            purpose_overrides=purpose_overrides or PurposeOverrides(),
        )
    )


def _request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the prepared evidence support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the prepared evidence support?",
        sources=(SourceItem(source_id="source-a", source_type="document", title="A", locator="doc://a", snippet="A"),),
        evidence_items=(EvidenceItem(text="Fact from A.", source_refs=("source-a",)),),
    )


def _valid_step1_text() -> str:
    return "\n".join([
        "SUMMARY:",
        "Bounded conclusion.",
        "",
        "FINDINGS:",
        "- text: A fact about source A.",
        "  cites: S1",
        "",
        "INFERENCES:",
        "- A minimal inference.",
        "",
        "UNCERTAINTIES:",
        "- One uncertainty.",
        "",
        "RECOMMENDATION:",
        "Remain bounded.",
    ])


def _valid_formatter_json() -> dict:
    return {
        "summary": "Formatter summary.",
        "findings": [{"text": "Formatter finding.", "source_refs": ["S1"]}],
        "inferences": ["Formatter inference."],
        "uncertainties": ["Formatter uncertainty."],
        "recommendation": "Formatter recommendation.",
    }


# ---------------------------------------------------------------------------
# ContractRuntime.invoke_with_request tests
# ---------------------------------------------------------------------------

def test_invoke_with_request_dispatches_pre_built_request_to_correct_adapter() -> None:
    from jeff.infrastructure.model_adapters.types import ModelResponseMode

    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response="hello from fake",
                ),
            ),
        )
    )
    cr = services.contract_runtime
    request = ModelRequest(
        request_id="test-req-1",
        project_id=None,
        work_unit_id=None,
        run_id=None,
        purpose="research_synthesis",
        prompt="test prompt",
        system_instructions=None,
        response_mode=ModelResponseMode.TEXT,
        json_schema=None,
        timeout_seconds=None,
        max_output_tokens=None,
        reasoning_effort=None,
        metadata={},
    )

    response = cr.invoke_with_request(request, adapter_id="fake-default")

    assert response.status is ModelInvocationStatus.COMPLETED
    assert response.output_text == "hello from fake"
    assert response.request_id == "test-req-1"


def test_invoke_with_request_preserves_json_mode_request() -> None:
    """Verifies that invoke_with_request passes the ModelRequest as-is, including JSON mode."""
    from jeff.infrastructure.model_adapters.types import ModelResponseMode
    from jeff.infrastructure import FakeModelAdapter

    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-json",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-json",
                    model_name="fake-model",
                    fake_json_response={"key": "value"},
                ),
            ),
        )
    )
    cr = services.contract_runtime
    request = ModelRequest(
        request_id="json-req-1",
        project_id=None,
        work_unit_id=None,
        run_id=None,
        purpose="research_synthesis_repair",
        prompt="format this",
        system_instructions=None,
        response_mode=ModelResponseMode.JSON,
        json_schema={"type": "object"},
        timeout_seconds=None,
        max_output_tokens=None,
        reasoning_effort=None,
        metadata={},
    )

    response = cr.invoke_with_request(request, adapter_id="fake-json")

    assert response.output_json == {"key": "value"}


# ---------------------------------------------------------------------------
# synthesize_research — direct adapter path unchanged
# ---------------------------------------------------------------------------

def test_synthesize_research_without_contract_runtime_still_uses_direct_adapter() -> None:
    """Passing no contract_runtime preserves the original direct adapter.invoke() path."""
    from jeff.infrastructure import FakeModelAdapter

    adapter = FakeModelAdapter(adapter_id="direct", default_text_response=_valid_step1_text())

    artifact = synthesize_research(
        research_request=_request(),
        evidence_pack=_evidence_pack(),
        adapter=adapter,
    )

    assert artifact.summary == "Bounded conclusion."
    assert artifact.findings[0].source_refs == ("source-a",)


# ---------------------------------------------------------------------------
# synthesize_research_with_runtime — routes through ContractRuntime
# ---------------------------------------------------------------------------

def test_runtime_path_routes_step1_call_through_contract_runtime() -> None:
    """End-to-end: synthesize_research_with_runtime produces same result as direct path."""
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-research",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-research",
                    model_name="fake-model",
                    fake_text_response=_valid_step1_text(),
                ),
            ),
        )
    )

    artifact = synthesize_research_with_runtime(
        research_request=_request(),
        evidence_pack=_evidence_pack(),
        infrastructure_services=services,
    )

    assert artifact.summary == "Bounded conclusion."
    assert artifact.findings[0].source_refs == ("source-a",)


def test_runtime_path_formatter_fallback_also_routes_through_contract_runtime() -> None:
    """Formatter fallback in the runtime path goes through ContractRuntime.invoke_with_request."""
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-research",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-research",
                    model_name="fake-model",
                    fake_text_response=_valid_step1_text(),
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-formatter",
                    model_name="formatter-model",
                    fake_json_response=_valid_formatter_json(),
                ),
            ),
            purpose_overrides=PurposeOverrides(
                research="fake-research",
                formatter_bridge="fake-formatter",
            ),
        )
    )
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict:
        raise ResearchSynthesisValidationError("forced transform failure")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        artifact = synthesize_research_with_runtime(
            research_request=_request(),
            evidence_pack=_evidence_pack(),
            infrastructure_services=services,
        )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    assert artifact.summary == "Formatter summary."
    assert artifact.findings[0].source_refs == ("source-a",)


def test_contract_runtime_is_obtained_from_services_in_runtime_path() -> None:
    """Verify that contract_runtime property is used — services.contract_runtime is a ContractRuntime."""
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response=_valid_step1_text(),
                ),
            ),
        )
    )

    assert isinstance(services.contract_runtime, ContractRuntime)


def test_step1_uses_clean_invoke_path_when_contract_runtime_is_supplied() -> None:
    adapter = _TrackingAdapter(adapter_id="direct-adapter", text_response="should not be used directly")
    formatter_adapter = _TrackingAdapter(adapter_id="formatter-adapter", json_response=_valid_formatter_json())
    runtime = _TrackingContractRuntime(step1_text_response=_valid_step1_text())

    artifact = synthesize_research(
        research_request=_request(),
        evidence_pack=_evidence_pack(),
        adapter=adapter,
        formatter_adapter=formatter_adapter,
        contract_runtime=runtime,  # type: ignore[arg-type]
    )

    assert artifact.summary == "Bounded conclusion."
    assert len(runtime.invoke_calls) == 1
    assert runtime.invoke_with_request_calls == []
    assert runtime.invoke_calls[0].purpose == "research_synthesis"
    assert runtime.invoke_calls[0].adapter_id == "direct-adapter"
    assert runtime.invoke_calls[0].routing_purpose == "research"
    assert runtime.invoke_calls[0].output_strategy is OutputStrategy.BOUNDED_TEXT_THEN_PARSE
    assert runtime.invoke_calls[0].response_mode is research_synthesis_module.ModelResponseMode.TEXT
    assert runtime.invoke_calls[0].reasoning_effort == "medium"
    assert adapter.requests == []


def test_step3_intentionally_stays_on_invoke_with_request() -> None:
    adapter = _TrackingAdapter(adapter_id="direct-adapter", text_response="should not be used directly")
    formatter_adapter = _TrackingAdapter(adapter_id="formatter-adapter", json_response=_valid_formatter_json())
    runtime = _TrackingContractRuntime(
        step1_text_response=_valid_step1_text(),
        formatter_json_response=_valid_formatter_json(),
    )
    original_transform = research_synthesis_module.transform_step1_bounded_text_to_candidate_payload

    def failing_transform(_: str) -> dict:
        raise ResearchSynthesisValidationError("forced transform failure")

    research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = failing_transform
    try:
        artifact = synthesize_research(
            research_request=_request(),
            evidence_pack=_evidence_pack(),
            adapter=adapter,
            formatter_adapter=formatter_adapter,
            contract_runtime=runtime,  # type: ignore[arg-type]
        )
    finally:
        research_synthesis_module.transform_step1_bounded_text_to_candidate_payload = original_transform

    assert artifact.summary == "Formatter summary."
    assert len(runtime.invoke_calls) == 1
    assert len(runtime.invoke_with_request_calls) == 1
    formatter_request, formatter_adapter_id = runtime.invoke_with_request_calls[0]
    assert formatter_request.purpose == "research_synthesis_formatter"
    assert formatter_adapter_id == "formatter-adapter"
