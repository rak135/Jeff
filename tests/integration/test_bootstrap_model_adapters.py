from jeff.bootstrap import build_infrastructure_runtime
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    FakeModelAdapter,
    ModelAdapterRuntimeConfig,
)


def test_bootstrap_can_assemble_infrastructure_services_from_explicit_config() -> None:
    services = build_infrastructure_runtime(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response="demo",
                ),
            ),
        )
    )

    adapter = services.get_default_model_adapter()

    assert isinstance(adapter, FakeModelAdapter)
    assert adapter.default_text_response == "demo"


def test_bootstrap_infrastructure_runtime_stays_explicit_and_local() -> None:
    services = build_infrastructure_runtime(
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

    assert services.default_model_adapter_id == "fake-default"
    assert services.get_default_model_adapter().provider_name == "fake"
