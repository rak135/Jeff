"""Explicit construction boundary for model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

from .base import ModelAdapter
from .errors import ModelAdapterError
from .providers import FakeModelAdapter, OllamaModelAdapter


class AdapterProviderKind(str, Enum):
    FAKE = "FAKE"
    OLLAMA = "OLLAMA"


@dataclass(frozen=True, slots=True)
class AdapterFactoryConfig:
    provider_kind: AdapterProviderKind
    adapter_id: str
    model_name: str
    provider_name: str | None = None
    base_url: str | None = None
    timeout_seconds: int | None = None
    fake_text_response: str | None = None
    fake_json_response: dict[str, Any] | None = None


def create_model_adapter(config: AdapterFactoryConfig) -> ModelAdapter:
    if config.provider_kind is AdapterProviderKind.FAKE:
        return FakeModelAdapter(
            adapter_id=config.adapter_id,
            provider_name=config.provider_name or "fake",
            model_name=config.model_name,
            default_text_response=config.fake_text_response or "fake text response",
            default_json_response=dict(config.fake_json_response) if config.fake_json_response else None,
        )

    if config.provider_kind is AdapterProviderKind.OLLAMA:
        return OllamaModelAdapter(
            adapter_id=config.adapter_id,
            model_name=config.model_name,
            base_url=config.base_url or "http://127.0.0.1:11434",
            timeout_seconds=config.timeout_seconds,
            provider_name=config.provider_name or "ollama",
        )

    raise ModelAdapterError(f"unsupported adapter provider kind: {config.provider_kind}")
