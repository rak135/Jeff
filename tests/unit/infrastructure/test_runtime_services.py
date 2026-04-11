import pytest

from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    FakeModelAdapter,
    ModelAdapterNotFoundError,
    ModelAdapterRuntimeConfig,
    OllamaModelAdapter,
    build_infrastructure_services,
)


def test_runtime_builds_services_with_fake_adapter() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                ),
            ),
        )
    )

    adapter = services.get_default_model_adapter()

    assert isinstance(adapter, FakeModelAdapter)
    assert services.default_model_adapter_id == "fake-default"


def test_runtime_builds_services_with_fake_and_ollama_configs() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.OLLAMA,
                    adapter_id="ollama-primary",
                    model_name="llama3.2",
                    base_url="http://localhost:11434",
                ),
            ),
        )
    )

    assert isinstance(services.get_default_model_adapter(), FakeModelAdapter)
    assert isinstance(services.get_model_adapter("ollama-primary"), OllamaModelAdapter)


def test_runtime_rejects_missing_default_adapter() -> None:
    with pytest.raises(ModelAdapterNotFoundError, match="adapter not found: missing-default"):
        build_infrastructure_services(
            ModelAdapterRuntimeConfig(
                default_adapter_id="missing-default",
                adapters=(
                    AdapterFactoryConfig(
                        provider_kind=AdapterProviderKind.FAKE,
                        adapter_id="fake-default",
                        model_name="fake-model",
                    ),
                ),
            )
        )


def test_runtime_rejects_duplicate_adapter_ids() -> None:
    with pytest.raises(ValueError, match="already registered"):
        build_infrastructure_services(
            ModelAdapterRuntimeConfig(
                default_adapter_id="dup",
                adapters=(
                    AdapterFactoryConfig(
                        provider_kind=AdapterProviderKind.FAKE,
                        adapter_id="dup",
                        model_name="fake-model",
                    ),
                    AdapterFactoryConfig(
                        provider_kind=AdapterProviderKind.FAKE,
                        adapter_id="dup",
                        model_name="fake-model-2",
                    ),
                ),
            )
        )


def test_runtime_returns_configured_default_adapter() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-b",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-a",
                    model_name="fake-model-a",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-b",
                    model_name="fake-model-b",
                ),
            ),
        )
    )

    assert services.get_default_model_adapter().adapter_id == "fake-b"


def test_runtime_missing_lookup_fails_closed() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                ),
            ),
        )
    )

    with pytest.raises(ModelAdapterNotFoundError, match="adapter not found: missing"):
        services.get_model_adapter("missing")
