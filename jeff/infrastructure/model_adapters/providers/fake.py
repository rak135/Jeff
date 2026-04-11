"""Deterministic fake model adapter for contract-focused tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..errors import ModelMalformedOutputError, ModelTimeoutError
from ..types import (
    ModelInvocationStatus,
    ModelRequest,
    ModelResponse,
    ModelResponseMode,
    ModelUsage,
)


@dataclass(frozen=True, slots=True)
class FakeModelAdapter:
    adapter_id: str = "fake-default"
    provider_name: str = "fake"
    model_name: str = "fake-model"
    default_text_response: str = "fake text response"
    default_json_response: dict[str, Any] | None = None
    forced_status: ModelInvocationStatus | None = None
    forced_exception: Exception | None = None
    warnings: tuple[str, ...] = ()

    def invoke(self, request: ModelRequest) -> ModelResponse:
        if self.forced_exception is not None:
            raise self.forced_exception

        if self.forced_status is ModelInvocationStatus.TIMED_OUT:
            raise ModelTimeoutError(f"model invocation timed out for adapter {self.adapter_id}")

        if request.response_mode is ModelResponseMode.JSON:
            if self.default_json_response is None:
                raise ModelMalformedOutputError(
                    f"adapter {self.adapter_id} has no JSON payload for JSON response_mode",
                )
            output_json = dict(self.default_json_response)
            output_text = None
        else:
            output_json = None
            output_text = self.default_text_response

        status = self.forced_status or ModelInvocationStatus.COMPLETED

        if status is ModelInvocationStatus.MALFORMED_OUTPUT:
            raise ModelMalformedOutputError(f"adapter {self.adapter_id} returned malformed output")

        return ModelResponse(
            request_id=request.request_id,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            status=status,
            output_text=output_text,
            output_json=output_json,
            usage=ModelUsage(
                input_tokens=max(len(request.prompt.split()), 1),
                output_tokens=max(
                    len((output_text or "").split()) + len((output_json or {}).keys()),
                    1,
                ),
                total_tokens=max(len(request.prompt.split()), 1)
                + max(len((output_text or "").split()) + len((output_json or {}).keys()), 1),
                estimated_cost=0.0,
                latency_ms=1,
            ),
            warnings=tuple(self.warnings),
            raw_response_ref=f"fake://{self.adapter_id}/{request.request_id}",
        )
