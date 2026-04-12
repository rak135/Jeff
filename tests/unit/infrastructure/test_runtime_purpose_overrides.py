import pytest

from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterNotFoundError,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)


def test_research_repair_override_resolves_when_configured() -> None:
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
                    adapter_id="fake-repair",
                    model_name="repair-model",
                ),
            ),
            purpose_overrides=PurposeOverrides(research="fake-research", research_repair="fake-repair"),
        )
    )

    assert services.get_adapter_for_purpose("research").adapter_id == "fake-research"
    assert services.get_adapter_for_purpose("research_repair").adapter_id == "fake-repair"


def test_research_repair_falls_back_to_research_when_absent() -> None:
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

    assert services.get_adapter_for_purpose("research_repair").adapter_id == "fake-research"


def test_unknown_configured_research_repair_adapter_fails_closed() -> None:
    with pytest.raises(ModelAdapterNotFoundError, match="adapter not found: missing-repair"):
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
                purpose_overrides=PurposeOverrides(research_repair="missing-repair"),
            )
        )
