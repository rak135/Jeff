"""Normalized invocation telemetry for model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .types import ModelInvocationStatus, ModelRequest, ModelResponse


def _require_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _normalize_metadata(value: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("metadata must be a dict")
    return dict(value)


@dataclass(frozen=True, slots=True)
class ModelTelemetryEvent:
    request_id: str
    adapter_id: str
    provider_name: str
    model_name: str
    status: ModelInvocationStatus
    purpose: str
    latency_ms: int | None
    input_tokens: int | None
    output_tokens: int | None
    total_tokens: int | None
    estimated_cost: float | None
    warning_count: int
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "adapter_id", _require_text(self.adapter_id, field_name="adapter_id"))
        object.__setattr__(self, "provider_name", _require_text(self.provider_name, field_name="provider_name"))
        object.__setattr__(self, "model_name", _require_text(self.model_name, field_name="model_name"))
        object.__setattr__(self, "purpose", _require_text(self.purpose, field_name="purpose"))
        object.__setattr__(self, "metadata", _normalize_metadata(self.metadata))
        if not isinstance(self.status, ModelInvocationStatus):
            raise TypeError("status must be a ModelInvocationStatus")
        if self.warning_count < 0:
            raise ValueError("warning_count must be zero or greater")


def telemetry_from_response(request: ModelRequest, response: ModelResponse) -> ModelTelemetryEvent:
    return ModelTelemetryEvent(
        request_id=response.request_id,
        adapter_id=response.adapter_id,
        provider_name=response.provider_name,
        model_name=response.model_name,
        status=response.status,
        purpose=request.purpose,
        latency_ms=response.usage.latency_ms,
        input_tokens=response.usage.input_tokens,
        output_tokens=response.usage.output_tokens,
        total_tokens=response.usage.total_tokens,
        estimated_cost=response.usage.estimated_cost,
        warning_count=len(response.warnings),
        metadata=request.metadata,
    )
