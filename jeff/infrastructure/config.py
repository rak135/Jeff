"""Explicit local runtime config loading for infrastructure-owned services."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import Any


def _require_text(value: Any, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return normalized


def _optional_text(value: Any, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name=field_name)


def _optional_positive_int(value: Any, *, field_name: str) -> int | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an integer when provided")
    if value <= 0:
        raise ValueError(f"{field_name} must be greater than zero when provided")
    return value


def _optional_bool(value: Any, *, field_name: str, default: bool) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field_name} must be a boolean when provided")
    return value


def _require_table(payload: dict[str, Any], field_name: str) -> dict[str, Any]:
    value = payload.get(field_name)
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} table is required in runtime config")
    return value


@dataclass(frozen=True, slots=True)
class AdapterRuntimeOptions:
    context_length: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "context_length",
            _optional_positive_int(self.context_length, field_name="provider_options.context_length"),
        )


@dataclass(frozen=True, slots=True)
class AdapterConfig:
    adapter_id: str
    provider_kind: str
    model_name: str
    provider_name: str | None = None
    base_url: str | None = None
    timeout_seconds: int | None = None
    provider_options: AdapterRuntimeOptions = field(default_factory=AdapterRuntimeOptions)

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapter_id", _require_text(self.adapter_id, field_name="adapters.adapter_id"))
        object.__setattr__(
            self,
            "provider_kind",
            _normalize_provider_kind(self.provider_kind),
        )
        object.__setattr__(self, "model_name", _require_text(self.model_name, field_name="adapters.model_name"))
        object.__setattr__(
            self,
            "provider_name",
            _optional_text(self.provider_name, field_name="adapters.provider_name"),
        )
        object.__setattr__(self, "base_url", _optional_text(self.base_url, field_name="adapters.base_url"))
        object.__setattr__(
            self,
            "timeout_seconds",
            _optional_positive_int(self.timeout_seconds, field_name="adapters.timeout_seconds"),
        )


@dataclass(frozen=True, slots=True)
class RuntimeDefaults:
    default_adapter_id: str

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "default_adapter_id",
            _require_text(self.default_adapter_id, field_name="runtime.default_adapter_id"),
        )


@dataclass(frozen=True, slots=True)
class PurposeOverrides:
    research: str | None = None
    research_repair: str | None = None
    proposal: str | None = None
    planning: str | None = None
    evaluation: str | None = None

    def __post_init__(self) -> None:
        for field_name in ("research", "research_repair", "proposal", "planning", "evaluation"):
            object.__setattr__(
                self,
                field_name,
                _optional_text(getattr(self, field_name), field_name=f"purpose_overrides.{field_name}"),
            )

    def for_purpose(self, purpose: str) -> str | None:
        if purpose not in {"research", "research_repair", "proposal", "planning", "evaluation"}:
            return None
        return getattr(self, purpose)


@dataclass(frozen=True, slots=True)
class ResearchRuntimeConfig:
    artifact_store_root: str
    enable_memory_handoff: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "artifact_store_root",
            _require_text(self.artifact_store_root, field_name="research.artifact_store_root"),
        )
        object.__setattr__(
            self,
            "enable_memory_handoff",
            _optional_bool(self.enable_memory_handoff, field_name="research.enable_memory_handoff", default=True),
        )


@dataclass(frozen=True, slots=True)
class JeffRuntimeConfig:
    defaults: RuntimeDefaults
    adapters: tuple[AdapterConfig, ...]
    purpose_overrides: PurposeOverrides = field(default_factory=PurposeOverrides)
    research: ResearchRuntimeConfig = field(default_factory=lambda: ResearchRuntimeConfig(artifact_store_root=".jeff_runtime"))

    def __post_init__(self) -> None:
        if not self.adapters:
            raise ValueError("runtime config requires at least one adapter")
        adapter_ids = [adapter.adapter_id for adapter in self.adapters]
        duplicates = {adapter_id for adapter_id in adapter_ids if adapter_ids.count(adapter_id) > 1}
        if duplicates:
            duplicate = sorted(duplicates)[0]
            raise ValueError(f"duplicate adapter_id in runtime config: {duplicate}")


def load_runtime_config(path: str | Path) -> JeffRuntimeConfig:
    config_path = Path(path)
    try:
        with config_path.open("rb") as handle:
            payload = tomllib.load(handle)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"runtime config file not found: {config_path}") from exc
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"malformed runtime config TOML in {config_path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"runtime config root must be a TOML table: {config_path}")

    runtime_table = _require_table(payload, "runtime")
    research_table = _require_table(payload, "research")
    purpose_overrides_table = payload.get("purpose_overrides", {})
    if not isinstance(purpose_overrides_table, dict):
        raise ValueError("purpose_overrides must be a TOML table when provided")

    adapters_payload = payload.get("adapters")
    if not isinstance(adapters_payload, list) or not adapters_payload:
        raise ValueError("runtime config requires at least one [[adapters]] entry")

    adapters = tuple(_load_adapter_config(item) for item in adapters_payload)
    return JeffRuntimeConfig(
        defaults=RuntimeDefaults(default_adapter_id=runtime_table.get("default_adapter_id")),
        adapters=adapters,
        purpose_overrides=PurposeOverrides(
            research=purpose_overrides_table.get("research"),
            research_repair=purpose_overrides_table.get("research_repair"),
            proposal=purpose_overrides_table.get("proposal"),
            planning=purpose_overrides_table.get("planning"),
            evaluation=purpose_overrides_table.get("evaluation"),
        ),
        research=ResearchRuntimeConfig(
            artifact_store_root=research_table.get("artifact_store_root"),
            enable_memory_handoff=research_table.get("enable_memory_handoff", True),
        ),
    )


def _load_adapter_config(payload: Any) -> AdapterConfig:
    if not isinstance(payload, dict):
        raise ValueError("each [[adapters]] entry must be a TOML table")
    provider_options_payload = payload.get("provider_options", {})
    if not isinstance(provider_options_payload, dict):
        raise ValueError("adapters.provider_options must be a TOML table when provided")
    return AdapterConfig(
        adapter_id=payload.get("adapter_id"),
        provider_kind=payload.get("provider_kind"),
        provider_name=payload.get("provider_name"),
        model_name=payload.get("model_name"),
        base_url=payload.get("base_url"),
        timeout_seconds=payload.get("timeout_seconds"),
        provider_options=AdapterRuntimeOptions(
            context_length=provider_options_payload.get("context_length"),
        ),
    )


def _normalize_provider_kind(value: Any) -> str:
    normalized = _require_text(value, field_name="adapters.provider_kind").lower()
    if normalized not in {"fake", "ollama"}:
        raise ValueError(f"unsupported provider_kind in runtime config: {normalized}")
    return normalized
