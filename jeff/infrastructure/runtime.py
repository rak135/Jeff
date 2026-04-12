"""Explicit runtime assembly for infrastructure-owned services."""

from __future__ import annotations

from dataclasses import dataclass, field

from .config import JeffRuntimeConfig, PurposeOverrides
from .model_adapters import AdapterFactoryConfig, AdapterProviderKind, AdapterRegistry, ModelAdapter, create_model_adapter


@dataclass(frozen=True, slots=True)
class ModelAdapterRuntimeConfig:
    default_adapter_id: str
    adapters: tuple[AdapterFactoryConfig, ...]
    purpose_overrides: PurposeOverrides = field(default_factory=PurposeOverrides)


@dataclass(slots=True)
class InfrastructureServices:
    model_adapter_registry: AdapterRegistry
    default_model_adapter_id: str
    purpose_overrides: PurposeOverrides = field(default_factory=PurposeOverrides)

    def get_default_model_adapter(self) -> ModelAdapter:
        return self.get_model_adapter(self.default_model_adapter_id)

    def get_model_adapter(self, adapter_id: str) -> ModelAdapter:
        return self.model_adapter_registry.get(adapter_id)

    def get_adapter_for_purpose(self, purpose: str, *, fallback_adapter_id: str | None = None) -> ModelAdapter:
        override_adapter_id = self.purpose_overrides.for_purpose(purpose)
        if override_adapter_id is None:
            if purpose == "research_repair":
                if fallback_adapter_id is not None:
                    return self.get_model_adapter(fallback_adapter_id)
                return self.get_adapter_for_purpose("research")
            return self.get_default_model_adapter()
        return self.get_model_adapter(override_adapter_id)


def build_infrastructure_services(config: ModelAdapterRuntimeConfig) -> InfrastructureServices:
    registry = AdapterRegistry()

    for adapter_config in config.adapters:
        registry.register(create_model_adapter(adapter_config))

    services = InfrastructureServices(
        model_adapter_registry=registry,
        default_model_adapter_id=config.default_adapter_id,
        purpose_overrides=config.purpose_overrides,
    )

    services.get_default_model_adapter()
    for purpose in ("research", "research_repair", "proposal", "planning", "evaluation"):
        override_adapter_id = config.purpose_overrides.for_purpose(purpose)
        if override_adapter_id is not None:
            services.get_model_adapter(override_adapter_id)
    return services


def build_model_adapter_runtime_config(config: JeffRuntimeConfig) -> ModelAdapterRuntimeConfig:
    return ModelAdapterRuntimeConfig(
        default_adapter_id=config.defaults.default_adapter_id,
        adapters=tuple(_factory_config_from_adapter_config(adapter) for adapter in config.adapters),
        purpose_overrides=config.purpose_overrides,
    )


def _factory_config_from_adapter_config(adapter_config) -> AdapterFactoryConfig:
    provider_kind_map = {
        "fake": AdapterProviderKind.FAKE,
        "ollama": AdapterProviderKind.OLLAMA,
    }
    return AdapterFactoryConfig(
        provider_kind=provider_kind_map[adapter_config.provider_kind],
        adapter_id=adapter_config.adapter_id,
        model_name=adapter_config.model_name,
        provider_name=adapter_config.provider_name,
        base_url=adapter_config.base_url,
        timeout_seconds=adapter_config.timeout_seconds,
        provider_options={"context_length": adapter_config.provider_options.context_length}
        if adapter_config.provider_options.context_length is not None
        else None,
    )
