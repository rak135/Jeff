import pytest

from jeff.infrastructure import (
    ModelInvocationStatus,
    ModelRequest,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
)


def test_text_mode_request_and_response_construct_cleanly() -> None:
    request = ModelRequest(
        request_id="request-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        purpose="draft summary",
        prompt="Summarize the current bounded state.",
        system_instructions="Be concise and truthful.",
        response_mode=ModelResponseMode.TEXT,
        json_schema=None,
        timeout_seconds=30,
        max_output_tokens=300,
        reasoning_effort="medium",
        metadata={"source": "test"},
    )

    response = ModelResponse(
        request_id=request.request_id,
        adapter_id="fake-text",
        provider_name="fake",
        model_name="fake-model",
        status=ModelInvocationStatus.COMPLETED,
        output_text="A short truthful summary.",
        output_json=None,
        usage=ModelUsage(input_tokens=4, output_tokens=5, total_tokens=9, estimated_cost=0.0),
        warnings=("bounded",),
        raw_response_ref="fake://fake-text/request-1",
    )

    assert request.response_mode is ModelResponseMode.TEXT
    assert response.request_id == request.request_id
    assert response.output_text == "A short truthful summary."
    assert response.output_json is None


def test_json_mode_request_and_response_allow_json_payload() -> None:
    request = ModelRequest(
        request_id="request-2",
        project_id=None,
        work_unit_id=None,
        run_id=None,
        purpose="structured result",
        prompt="Return a structured decision-support object.",
        system_instructions=None,
        response_mode=ModelResponseMode.JSON,
        json_schema={"type": "object", "properties": {"answer": {"type": "string"}}},
        timeout_seconds=None,
        max_output_tokens=None,
        reasoning_effort=None,
        metadata={},
    )

    response = ModelResponse(
        request_id=request.request_id,
        adapter_id="fake-json",
        provider_name="fake",
        model_name="fake-model",
        status=ModelInvocationStatus.COMPLETED,
        output_text='{"answer": "yes"}',
        output_json={"answer": "yes"},
        usage=ModelUsage(),
    )

    assert request.json_schema == {"type": "object", "properties": {"answer": {"type": "string"}}}
    assert response.output_json == {"answer": "yes"}
    assert response.output_text == '{"answer": "yes"}'


def test_text_mode_rejects_json_schema() -> None:
    with pytest.raises(ValueError, match="json_schema is only valid"):
        ModelRequest(
            request_id="request-3",
            project_id=None,
            work_unit_id=None,
            run_id=None,
            purpose="text only",
            prompt="Say hello.",
            system_instructions=None,
            response_mode=ModelResponseMode.TEXT,
            json_schema={"type": "object"},
            timeout_seconds=None,
            max_output_tokens=None,
            reasoning_effort=None,
            metadata={},
        )


def test_completed_response_requires_some_output() -> None:
    with pytest.raises(ValueError, match="must include output_text or output_json"):
        ModelResponse(
            request_id="request-4",
            adapter_id="fake-empty",
            provider_name="fake",
            model_name="fake-model",
            status=ModelInvocationStatus.COMPLETED,
            output_text=None,
            output_json=None,
            usage=ModelUsage(),
        )
