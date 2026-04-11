import pytest

from jeff.infrastructure import (
    FakeModelAdapter,
    ModelInvocationError,
    ModelInvocationStatus,
    ModelMalformedOutputError,
    ModelRequest,
    ModelResponseMode,
    ModelTimeoutError,
)


def test_fake_adapter_returns_text_response() -> None:
    adapter = FakeModelAdapter(
        adapter_id="fake-text",
        default_text_response="deterministic text",
        warnings=("fake warning",),
    )

    response = adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))

    assert response.request_id == "request-1"
    assert response.adapter_id == "fake-text"
    assert response.status is ModelInvocationStatus.COMPLETED
    assert response.output_text == "deterministic text"
    assert response.output_json is None
    assert response.warnings == ("fake warning",)


def test_fake_adapter_returns_json_response() -> None:
    adapter = FakeModelAdapter(
        adapter_id="fake-json",
        default_json_response={"answer": "yes", "confidence": "high"},
    )

    response = adapter.invoke(_request(response_mode=ModelResponseMode.JSON))

    assert response.request_id == "request-1"
    assert response.output_json == {"answer": "yes", "confidence": "high"}
    assert response.output_text is None


def test_fake_adapter_raises_forced_exception() -> None:
    adapter = FakeModelAdapter(forced_exception=ModelInvocationError("forced failure"))

    with pytest.raises(ModelInvocationError, match="forced failure"):
        adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))


def test_fake_adapter_raises_timeout_for_forced_timeout_status() -> None:
    adapter = FakeModelAdapter(forced_status=ModelInvocationStatus.TIMED_OUT)

    with pytest.raises(ModelTimeoutError, match="timed out"):
        adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))


def test_fake_adapter_raises_malformed_output_when_json_requested_without_payload() -> None:
    adapter = FakeModelAdapter(default_json_response=None)

    with pytest.raises(ModelMalformedOutputError, match="has no JSON payload"):
        adapter.invoke(_request(response_mode=ModelResponseMode.JSON))


def _request(*, response_mode: ModelResponseMode) -> ModelRequest:
    return ModelRequest(
        request_id="request-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        purpose="contract test",
        prompt="Return a deterministic answer.",
        system_instructions=None,
        response_mode=response_mode,
        json_schema={"type": "object"} if response_mode is ModelResponseMode.JSON else None,
        timeout_seconds=10,
        max_output_tokens=50,
        reasoning_effort=None,
        metadata={"test": True},
    )
