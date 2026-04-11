"""Provider-neutral model adapter contract."""

from __future__ import annotations

from typing import Protocol

from .types import ModelRequest, ModelResponse


class ModelAdapter(Protocol):
    adapter_id: str
    provider_name: str
    model_name: str

    def invoke(self, request: ModelRequest) -> ModelResponse:
        ...
