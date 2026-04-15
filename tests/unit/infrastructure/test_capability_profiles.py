"""Unit tests for jeff.infrastructure.capability_profiles."""

import pytest

from jeff.infrastructure.capability_profiles import CapabilityProfile, CapabilityProfileRegistry


def test_capability_profile_defaults() -> None:
    profile = CapabilityProfile(adapter_id="fake-default")
    assert profile.supports_structured_output is True
    assert profile.max_context_tokens is None
    assert profile.provider_kind is None


def test_capability_profile_with_all_fields() -> None:
    profile = CapabilityProfile(
        adapter_id="ollama-main",
        supports_structured_output=True,
        max_context_tokens=8192,
        provider_kind="ollama",
    )
    assert profile.adapter_id == "ollama-main"
    assert profile.max_context_tokens == 8192
    assert profile.provider_kind == "ollama"


def test_can_use_strategy_allows_delimiter_when_structured_output_supported() -> None:
    profile = CapabilityProfile(adapter_id="a", supports_structured_output=True)
    assert profile.can_use_strategy(strategy_requires_delimiter=True) is True


def test_can_use_strategy_blocks_delimiter_when_structured_output_not_supported() -> None:
    profile = CapabilityProfile(adapter_id="a", supports_structured_output=False)
    assert profile.can_use_strategy(strategy_requires_delimiter=True) is False


def test_can_use_strategy_plain_text_always_allowed() -> None:
    for supports in (True, False):
        profile = CapabilityProfile(adapter_id="a", supports_structured_output=supports)
        assert profile.can_use_strategy(strategy_requires_delimiter=False) is True


def test_registry_get_returns_none_for_unknown_adapter() -> None:
    registry = CapabilityProfileRegistry()
    assert registry.get("nonexistent") is None


def test_registry_with_profile_adds_profile() -> None:
    profile = CapabilityProfile(adapter_id="fake-default")
    registry = CapabilityProfileRegistry().with_profile(profile)
    assert registry.get("fake-default") is profile


def test_registry_with_profile_replaces_existing() -> None:
    old = CapabilityProfile(adapter_id="fake-default", max_context_tokens=4096)
    new = CapabilityProfile(adapter_id="fake-default", max_context_tokens=8192)
    registry = CapabilityProfileRegistry().with_profile(old).with_profile(new)
    assert registry.get("fake-default").max_context_tokens == 8192


def test_registry_is_immutable_with_profile_returns_new_instance() -> None:
    registry = CapabilityProfileRegistry()
    profile = CapabilityProfile(adapter_id="a")
    updated = registry.with_profile(profile)
    assert registry is not updated
    assert registry.get("a") is None
    assert updated.get("a") is profile


def test_registry_adapter_ids_reflects_registered_profiles() -> None:
    registry = (
        CapabilityProfileRegistry()
        .with_profile(CapabilityProfile(adapter_id="a"))
        .with_profile(CapabilityProfile(adapter_id="b"))
    )
    assert registry.adapter_ids() == {"a", "b"}
