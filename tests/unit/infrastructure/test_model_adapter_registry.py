import pytest

from jeff.infrastructure import AdapterRegistry, FakeModelAdapter, ModelAdapterNotFoundError


def test_registry_registers_and_gets_adapter() -> None:
    registry = AdapterRegistry()
    adapter = FakeModelAdapter(adapter_id="fake-a")

    registry.register(adapter)

    assert registry.has("fake-a") is True
    assert registry.get("fake-a") is adapter


def test_registry_rejects_duplicate_adapter_ids() -> None:
    registry = AdapterRegistry()
    registry.register(FakeModelAdapter(adapter_id="fake-a"))

    with pytest.raises(ValueError, match="already registered"):
        registry.register(FakeModelAdapter(adapter_id="fake-a"))


def test_registry_raises_for_missing_adapter() -> None:
    registry = AdapterRegistry()

    with pytest.raises(ModelAdapterNotFoundError, match="adapter not found: missing"):
        registry.get("missing")


def test_registry_lists_adapter_ids_in_registration_order() -> None:
    registry = AdapterRegistry()
    registry.register(FakeModelAdapter(adapter_id="fake-b"))
    registry.register(FakeModelAdapter(adapter_id="fake-a"))

    assert registry.list_adapter_ids() == ("fake-b", "fake-a")
