from jeff.infrastructure import (
    ModelInvocationStatus,
    ModelRequest,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
    telemetry_from_response,
)


def test_telemetry_preserves_identity_fields() -> None:
    request = _request()
    response = _response(request_id=request.request_id)

    event = telemetry_from_response(request, response)

    assert event.request_id == "request-1"
    assert event.adapter_id == "adapter-1"
    assert event.provider_name == "ollama"
    assert event.model_name == "llama3.2"
    assert event.purpose == "draft answer"


def test_telemetry_normalizes_usage_fields() -> None:
    request = _request()
    response = _response(
        request_id=request.request_id,
        usage=ModelUsage(
            input_tokens=10,
            output_tokens=25,
            total_tokens=35,
            estimated_cost=None,
            latency_ms=87,
        ),
    )

    event = telemetry_from_response(request, response)

    assert event.status is ModelInvocationStatus.COMPLETED
    assert event.input_tokens == 10
    assert event.output_tokens == 25
    assert event.total_tokens == 35
    assert event.latency_ms == 87


def test_telemetry_counts_warnings() -> None:
    request = _request()
    response = _response(
        request_id=request.request_id,
        warnings=("warn-1", "warn-2", "warn-3"),
    )

    event = telemetry_from_response(request, response)

    assert event.warning_count == 3
    assert event.metadata == {"origin": "test"}


def _request() -> ModelRequest:
    return ModelRequest(
        request_id="request-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        purpose="draft answer",
        prompt="Tell me something bounded.",
        system_instructions=None,
        response_mode=ModelResponseMode.TEXT,
        json_schema=None,
        timeout_seconds=10,
        max_output_tokens=100,
        reasoning_effort="medium",
        metadata={"origin": "test"},
    )


def _response(
    *,
    request_id: str,
    usage: ModelUsage | None = None,
    warnings: tuple[str, ...] = (),
) -> ModelResponse:
    return ModelResponse(
        request_id=request_id,
        adapter_id="adapter-1",
        provider_name="ollama",
        model_name="llama3.2",
        status=ModelInvocationStatus.COMPLETED,
        output_text="ok",
        output_json=None,
        usage=usage or ModelUsage(),
        warnings=warnings,
    )
