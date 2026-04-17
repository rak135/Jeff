import pytest

from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterNotFoundError,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)


def test_formatter_bridge_override_resolves_when_configured() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-research",
                    model_name="research-model",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-formatter",
                    model_name="formatter-model",
                ),
            ),
            purpose_overrides=PurposeOverrides(research="fake-research", formatter_bridge="fake-formatter"),
        )
    )

    assert services.get_adapter_for_purpose("research").adapter_id == "fake-research"
    assert services.get_adapter_for_purpose("formatter_bridge").adapter_id == "fake-formatter"


def test_formatter_bridge_falls_back_to_research_when_absent() -> None:
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="default-model",
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-research",
                    model_name="research-model",
                ),
            ),
            purpose_overrides=PurposeOverrides(research="fake-research"),
        )
    )

    assert services.get_adapter_for_purpose("formatter_bridge").adapter_id == "fake-research"


def test_unknown_configured_formatter_bridge_adapter_fails_closed() -> None:
    with pytest.raises(ModelAdapterNotFoundError, match="adapter not found: missing-formatter"):
        build_infrastructure_services(
            ModelAdapterRuntimeConfig(
                default_adapter_id="fake-default",
                adapters=(
                    AdapterFactoryConfig(
                        provider_kind=AdapterProviderKind.FAKE,
                        adapter_id="fake-default",
                        model_name="default-model",
                    ),
                ),
                purpose_overrides=PurposeOverrides(formatter_bridge="missing-formatter"),
            )
        )
