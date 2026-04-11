"""Deterministic registry for model adapters."""

from __future__ import annotations

from .base import ModelAdapter
from .errors import ModelAdapterNotFoundError


class AdapterRegistry:
    def __init__(self) -> None:
        self._adapters: dict[str, ModelAdapter] = {}

    def register(self, adapter: ModelAdapter) -> None:
        adapter_id = adapter.adapter_id
        if adapter_id in self._adapters:
            raise ValueError(f"adapter_id already registered: {adapter_id}")
        self._adapters[adapter_id] = adapter

    def get(self, adapter_id: str) -> ModelAdapter:
        try:
            return self._adapters[adapter_id]
        except KeyError as exc:
            raise ModelAdapterNotFoundError(f"adapter not found: {adapter_id}") from exc

    def has(self, adapter_id: str) -> bool:
        return adapter_id in self._adapters

    def list_adapter_ids(self) -> tuple[str, ...]:
        return tuple(self._adapters)
