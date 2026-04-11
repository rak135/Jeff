import pytest

from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    FakeModelAdapter,
    ModelAdapterError,
    OllamaModelAdapter,
    create_model_adapter,
)


def test_factory_creates_fake_adapter() -> None:
    adapter = create_model_adapter(
        AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.FAKE,
            adapter_id="fake-1",
            model_name="fake-model",
            fake_text_response="hello",
            fake_json_response={"ok": True},
        )
    )

    assert isinstance(adapter, FakeModelAdapter)
    assert adapter.adapter_id == "fake-1"
    assert adapter.default_text_response == "hello"
    assert adapter.default_json_response == {"ok": True}


def test_factory_creates_ollama_adapter() -> None:
    adapter = create_model_adapter(
        AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.OLLAMA,
            adapter_id="ollama-1",
            model_name="llama3.2",
            base_url="http://localhost:11434",
            timeout_seconds=12,
        )
    )

    assert isinstance(adapter, OllamaModelAdapter)
    assert adapter.adapter_id == "ollama-1"
    assert adapter.model_name == "llama3.2"
    assert adapter.base_url == "http://localhost:11434"
    assert adapter.timeout_seconds == 12


def test_factory_rejects_unsupported_provider_kind() -> None:
    config = AdapterFactoryConfig(
        provider_kind="UNSUPPORTED",  # type: ignore[arg-type]
        adapter_id="bad-1",
        model_name="bad-model",
    )

    with pytest.raises(ModelAdapterError, match="unsupported adapter provider kind"):
        create_model_adapter(config)
