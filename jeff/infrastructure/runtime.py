"""Explicit runtime assembly for infrastructure-owned services."""

from __future__ import annotations

from dataclasses import dataclass

from .model_adapters import AdapterFactoryConfig, AdapterRegistry, ModelAdapter, create_model_adapter


@dataclass(frozen=True, slots=True)
class ModelAdapterRuntimeConfig:
    default_adapter_id: str
    adapters: tuple[AdapterFactoryConfig, ...]


@dataclass(slots=True)
class InfrastructureServices:
    model_adapter_registry: AdapterRegistry
    default_model_adapter_id: str

    def get_default_model_adapter(self) -> ModelAdapter:
        return self.get_model_adapter(self.default_model_adapter_id)

    def get_model_adapter(self, adapter_id: str) -> ModelAdapter:
        return self.model_adapter_registry.get(adapter_id)


def build_infrastructure_services(config: ModelAdapterRuntimeConfig) -> InfrastructureServices:
    registry = AdapterRegistry()

    for adapter_config in config.adapters:
        registry.register(create_model_adapter(adapter_config))

    services = InfrastructureServices(
        model_adapter_registry=registry,
        default_model_adapter_id=config.default_adapter_id,
    )

    services.get_default_model_adapter()
    return services
