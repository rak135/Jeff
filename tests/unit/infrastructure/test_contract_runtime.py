"""Unit tests for jeff.infrastructure.contract_runtime."""

from dataclasses import dataclass, field

import pytest

from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    ModelRequest,
    ModelResponse,
    ModelUsage,
    build_infrastructure_services,
)
from jeff.infrastructure.contract_runtime import (
    ContractCallRequest,
    ContractRuntime,
    _resolve_purpose_string,
    _strategy_to_response_mode,
)
from jeff.infrastructure.model_adapters.types import ModelInvocationStatus, ModelResponseMode
from jeff.infrastructure.output_strategies import OutputStrategy
from jeff.infrastructure.purposes import Purpose


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fake_services(adapter_id: str = "fake-default"):
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id=adapter_id,
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id=adapter_id,
                    model_name="fake-model",
                ),
            ),
        )
    )


def _fake_services_two(default_id: str = "fake-default", second_id: str = "fake-repair"):
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id=default_id,
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id=default_id,
                    model_name="fake-model",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id=second_id,
                    model_name="fake-repair-model",
                ),
            ),
        )
    )


@dataclass
class _TrackingAdapter:
    adapter_id: str = "tracking-adapter"
    provider_name: str = "fake"
    model_name: str = "tracking-model"
    requests: list[ModelRequest] = field(default_factory=list)

    def invoke(self, request: ModelRequest) -> ModelResponse:
        self.requests.append(request)
        if request.response_mode is ModelResponseMode.JSON:
            return ModelResponse(
                request_id=request.request_id,
                adapter_id=self.adapter_id,
                provider_name=self.provider_name,
                model_name=self.model_name,
                status=ModelInvocationStatus.COMPLETED,
                output_text=None,
                output_json={"answer": "ok"},
                usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
            )
        return ModelResponse(
            request_id=request.request_id,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            status=ModelInvocationStatus.COMPLETED,
            output_text="tracking response",
            output_json=None,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2),
        )


@dataclass
class _TrackingServices:
    adapter: _TrackingAdapter
    routed_purposes: list[str] = field(default_factory=list)
    adapter_lookups: list[str] = field(default_factory=list)

    def get_adapter_for_purpose(self, purpose: str):  # type: ignore[no-untyped-def]
        self.routed_purposes.append(purpose)
        return self.adapter

    def get_model_adapter(self, adapter_id: str):  # type: ignore[no-untyped-def]
        self.adapter_lookups.append(adapter_id)
        assert adapter_id == self.adapter.adapter_id
        return self.adapter


# ---------------------------------------------------------------------------
# _resolve_purpose_string
# ---------------------------------------------------------------------------

def test_resolve_purpose_string_returns_value_for_enum() -> None:
    assert _resolve_purpose_string(Purpose.RESEARCH) == "research"
    assert _resolve_purpose_string(Purpose.FORMATTER_BRIDGE) == "formatter_bridge"
    assert _resolve_purpose_string(Purpose.PROPOSAL) == "proposal"


def test_resolve_purpose_string_returns_raw_string_unchanged() -> None:
    assert _resolve_purpose_string("research") == "research"
    assert _resolve_purpose_string("custom_purpose") == "custom_purpose"


# ---------------------------------------------------------------------------
# _strategy_to_response_mode
# ---------------------------------------------------------------------------

def test_all_strategies_map_to_text_mode() -> None:
    for strategy in OutputStrategy:
        assert _strategy_to_response_mode(strategy) is ModelResponseMode.TEXT


# ---------------------------------------------------------------------------
# ContractCallRequest construction
# ---------------------------------------------------------------------------

def test_call_request_constructs_with_minimal_fields() -> None:
    req = ContractCallRequest(
        purpose=Purpose.RESEARCH,
        output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER,
        prompt="tell me about X",
    )
    assert req.purpose is Purpose.RESEARCH
    assert req.output_strategy is OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER
    assert req.prompt == "tell me about X"
    assert req.request_id is None
    assert req.response_mode is None
    assert req.reasoning_effort is None
    assert req.metadata == {}


def test_call_request_accepts_raw_string_purpose() -> None:
    req = ContractCallRequest(
        purpose="research",
        output_strategy=OutputStrategy.PLAIN_TEXT,
        prompt="prompt text",
    )
    assert req.purpose == "research"


def test_call_request_accepts_runtime_level_fields() -> None:
    req = ContractCallRequest(
        purpose="research_synthesis",
        routing_purpose=Purpose.RESEARCH,
        output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
        prompt="prompt text",
        response_mode=ModelResponseMode.JSON,
        json_schema={"type": "object"},
        reasoning_effort="medium",
    )

    assert req.routing_purpose is Purpose.RESEARCH
    assert req.response_mode is ModelResponseMode.JSON
    assert req.json_schema == {"type": "object"}
    assert req.reasoning_effort == "medium"


def test_call_request_rejects_empty_prompt() -> None:
    with pytest.raises(ValueError, match="prompt must be a non-empty string"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="   ",
        )


def test_call_request_rejects_invalid_output_strategy() -> None:
    with pytest.raises(TypeError, match="output_strategy must be an OutputStrategy"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy="plain_text",  # type: ignore[arg-type]
            prompt="prompt",
        )


def test_call_request_rejects_invalid_response_mode() -> None:
    with pytest.raises(TypeError, match="response_mode must be a ModelResponseMode"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="prompt",
            response_mode="TEXT",  # type: ignore[arg-type]
        )


def test_call_request_rejects_zero_timeout() -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be greater than zero"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="prompt",
            timeout_seconds=0,
        )


def test_call_request_rejects_zero_max_output_tokens() -> None:
    with pytest.raises(ValueError, match="max_output_tokens must be greater than zero"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="prompt",
            max_output_tokens=0,
        )


def test_call_request_rejects_blank_reasoning_effort() -> None:
    with pytest.raises(ValueError, match="reasoning_effort must be a non-empty string"):
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="prompt",
            reasoning_effort="   ",
        )


# ---------------------------------------------------------------------------
# ContractRuntime.invoke
# ---------------------------------------------------------------------------

def test_invoke_returns_completed_response() -> None:
    services = _fake_services()
    runtime = ContractRuntime(services)

    response = runtime.invoke(
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER,
            prompt="research prompt",
        )
    )

    assert response.status is ModelInvocationStatus.COMPLETED
    assert response.output_text == "fake text response"
    assert response.adapter_id == "fake-default"


def test_invoke_generates_request_id_when_not_supplied() -> None:
    services = _fake_services()
    runtime = ContractRuntime(services)

    r1 = runtime.invoke(ContractCallRequest(
        purpose=Purpose.RESEARCH,
        output_strategy=OutputStrategy.PLAIN_TEXT,
        prompt="prompt a",
    ))
    r2 = runtime.invoke(ContractCallRequest(
        purpose=Purpose.RESEARCH,
        output_strategy=OutputStrategy.PLAIN_TEXT,
        prompt="prompt b",
    ))

    assert r1.request_id
    assert r2.request_id
    assert r1.request_id != r2.request_id


def test_invoke_preserves_caller_supplied_request_id() -> None:
    services = _fake_services()
    runtime = ContractRuntime(services)

    response = runtime.invoke(
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="prompt",
            request_id="my-stable-id",
        )
    )

    assert response.request_id == "my-stable-id"


def test_invoke_with_purpose_enum_routes_via_default_when_no_override() -> None:
    services = _fake_services()
    runtime = ContractRuntime(services)

    response = runtime.invoke(
        ContractCallRequest(
            purpose=Purpose.PROPOSAL,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="proposal prompt",
        )
    )

    assert response.adapter_id == "fake-default"


def test_invoke_with_raw_string_purpose_works() -> None:
    services = _fake_services()
    runtime = ContractRuntime(services)

    response = runtime.invoke(
        ContractCallRequest(
            purpose="research",
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
            prompt="prompt",
        )
    )

    assert response.status is ModelInvocationStatus.COMPLETED


def test_invoke_forwards_explicit_runtime_fields_and_routes_by_routing_purpose() -> None:
    adapter = _TrackingAdapter()
    services = _TrackingServices(adapter)
    runtime = ContractRuntime(services)  # type: ignore[arg-type]

    response = runtime.invoke(
        ContractCallRequest(
            purpose="research_synthesis",
            routing_purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
            prompt="prompt",
            system_instructions="system",
            request_id="req-1",
            response_mode=ModelResponseMode.JSON,
            json_schema={"type": "object"},
            reasoning_effort="medium",
            metadata={"stage": "step1"},
        )
    )

    assert response.output_json == {"answer": "ok"}
    assert services.routed_purposes == ["research"]
    assert adapter.requests[0].purpose == "research_synthesis"
    assert adapter.requests[0].response_mode is ModelResponseMode.JSON
    assert adapter.requests[0].json_schema == {"type": "object"}
    assert adapter.requests[0].reasoning_effort == "medium"
    assert adapter.requests[0].metadata == {"stage": "step1"}


def test_invoke_uses_explicit_adapter_id_when_provided() -> None:
    adapter = _TrackingAdapter()
    services = _TrackingServices(adapter)
    runtime = ContractRuntime(services)  # type: ignore[arg-type]

    runtime.invoke(
        ContractCallRequest(
            purpose="research_synthesis",
            adapter_id="tracking-adapter",
            routing_purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_PARSE,
            prompt="prompt",
        )
    )

    assert services.adapter_lookups == ["tracking-adapter"]
    assert services.routed_purposes == []


# ---------------------------------------------------------------------------
# ContractRuntime.invoke_with_adapter
# ---------------------------------------------------------------------------

def test_invoke_with_adapter_uses_specified_adapter() -> None:
    services = _fake_services_two()
    runtime = ContractRuntime(services)

    response = runtime.invoke_with_adapter(
        ContractCallRequest(
            purpose=Purpose.FORMATTER_BRIDGE,
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER,
            prompt="repair prompt",
        ),
        adapter_id="fake-repair",
    )

    assert response.adapter_id == "fake-repair"


def test_invoke_with_adapter_preserves_purpose_in_response_request_id() -> None:
    services = _fake_services_two()
    runtime = ContractRuntime(services)

    response = runtime.invoke_with_adapter(
        ContractCallRequest(
            purpose=Purpose.FORMATTER_BRIDGE,
            output_strategy=OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER,
            prompt="repair prompt",
            request_id="trace-id-123",
        ),
        adapter_id="fake-repair",
    )

    assert response.request_id == "trace-id-123"


# ---------------------------------------------------------------------------
# InfrastructureServices.contract_runtime property
# ---------------------------------------------------------------------------

def test_services_contract_runtime_property_returns_contract_runtime() -> None:
    services = _fake_services()
    cr = services.contract_runtime
    assert isinstance(cr, ContractRuntime)


def test_services_contract_runtime_property_is_bound_to_services() -> None:
    services = _fake_services()
    cr = services.contract_runtime

    response = cr.invoke(
        ContractCallRequest(
            purpose=Purpose.RESEARCH,
            output_strategy=OutputStrategy.PLAIN_TEXT,
            prompt="bound call",
        )
    )

    assert response.status is ModelInvocationStatus.COMPLETED
