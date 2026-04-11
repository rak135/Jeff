import json
import socket
from urllib import error

import pytest

from jeff.infrastructure import (
    ModelInvocationError,
    ModelMalformedOutputError,
    ModelRequest,
    ModelResponseMode,
    ModelTimeoutError,
    OllamaModelAdapter,
)
from jeff.infrastructure.model_adapters.providers import ollama as ollama_module


def test_ollama_adapter_returns_text_response(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-a", model_name="llama3.2")
    _install_urlopen_stub(
        monkeypatch,
        payload={"response": "Hello from Ollama", "prompt_eval_count": 4, "eval_count": 7},
    )
    _install_monotonic_stub(monkeypatch, start=100.0, end=100.05)

    response = adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))

    assert response.request_id == "request-1"
    assert response.output_text == "Hello from Ollama"
    assert response.output_json is None
    assert response.usage.input_tokens == 4
    assert response.usage.output_tokens == 7
    assert response.usage.total_tokens == 11
    assert response.usage.latency_ms == 50


def test_ollama_adapter_returns_json_response_when_text_is_valid_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-b", model_name="llama3.2")
    _install_urlopen_stub(
        monkeypatch,
        payload={"response": '{"answer":"yes","confidence":"high"}'},
    )
    _install_monotonic_stub(monkeypatch, start=200.0, end=200.01)

    response = adapter.invoke(_request(response_mode=ModelResponseMode.JSON))

    assert response.request_id == "request-1"
    assert response.output_text == '{"answer":"yes","confidence":"high"}'
    assert response.output_json == {"answer": "yes", "confidence": "high"}
    assert response.usage.latency_ms == 10


def test_ollama_adapter_raises_for_malformed_json_mode_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-c", model_name="llama3.2")
    _install_urlopen_stub(monkeypatch, payload={"response": "not valid json"})
    _install_monotonic_stub(monkeypatch, start=300.0, end=300.02)

    with pytest.raises(ModelMalformedOutputError, match="not valid JSON"):
        adapter.invoke(_request(response_mode=ModelResponseMode.JSON))


def test_ollama_adapter_maps_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-d", model_name="llama3.2", timeout_seconds=5)
    monkeypatch.setattr(
        ollama_module.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(socket.timeout("timed out")),
    )
    _install_monotonic_stub(monkeypatch, start=400.0, end=400.02)

    with pytest.raises(ModelTimeoutError, match="timed out"):
        adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))


def test_ollama_adapter_maps_transport_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-e", model_name="llama3.2")
    monkeypatch.setattr(
        ollama_module.request,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(error.URLError("connection refused")),
    )
    _install_monotonic_stub(monkeypatch, start=500.0, end=500.02)

    with pytest.raises(ModelInvocationError, match="transport failed"):
        adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))


def test_ollama_adapter_round_trips_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    adapter = OllamaModelAdapter(adapter_id="ollama-f", model_name="llama3.2")
    _install_urlopen_stub(monkeypatch, payload={"response": "ok"})
    _install_monotonic_stub(monkeypatch, start=600.0, end=600.03)

    response = adapter.invoke(_request(response_mode=ModelResponseMode.TEXT))

    assert response.request_id == "request-1"
    assert response.usage.latency_ms == 30


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _install_urlopen_stub(monkeypatch: pytest.MonkeyPatch, *, payload: dict[str, object]) -> None:
    monkeypatch.setattr(
        ollama_module.request,
        "urlopen",
        lambda *_args, **_kwargs: _FakeHttpResponse(payload),
    )


def _install_monotonic_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    start: float,
    end: float,
) -> None:
    values = iter((start, end))
    monkeypatch.setattr(ollama_module.time, "monotonic", lambda: next(values))


def _request(*, response_mode: ModelResponseMode) -> ModelRequest:
    return ModelRequest(
        request_id="request-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        purpose="adapter test",
        prompt="Return a bounded answer.",
        system_instructions="Keep it short.",
        response_mode=response_mode,
        json_schema={"type": "object"} if response_mode is ModelResponseMode.JSON else None,
        timeout_seconds=10,
        max_output_tokens=200,
        reasoning_effort=None,
        metadata={},
    )
