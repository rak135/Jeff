"""Provider-neutral request and response models for model adapters."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


def _require_text(value: str, *, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")

    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")

    return normalized


def _normalize_optional_text(value: str | None, *, field_name: str) -> str | None:
    if value is None:
        return None
    return _require_text(value, field_name=field_name)


def _normalize_mapping(
    value: dict[str, Any] | None,
    *,
    field_name: str,
) -> dict[str, Any] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict when provided")
    return dict(value)


def _normalize_required_mapping(value: dict[str, Any], *, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{field_name} must be a dict")
    return dict(value)


def _normalize_warnings(value: tuple[str, ...] | list[str] | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return tuple(_require_text(item, field_name="warnings") for item in value)


class ModelResponseMode(str, Enum):
    TEXT = "TEXT"
    JSON = "JSON"


class ModelInvocationStatus(str, Enum):
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    TIMED_OUT = "TIMED_OUT"
    MALFORMED_OUTPUT = "MALFORMED_OUTPUT"


@dataclass(frozen=True, slots=True)
class ModelRequest:
    request_id: str
    project_id: str | None
    work_unit_id: str | None
    run_id: str | None
    purpose: str
    prompt: str
    system_instructions: str | None
    response_mode: ModelResponseMode
    json_schema: dict[str, Any] | None
    timeout_seconds: int | None
    max_output_tokens: int | None
    reasoning_effort: str | None
    metadata: dict[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "project_id", _normalize_optional_text(self.project_id, field_name="project_id"))
        object.__setattr__(
            self,
            "work_unit_id",
            _normalize_optional_text(self.work_unit_id, field_name="work_unit_id"),
        )
        object.__setattr__(self, "run_id", _normalize_optional_text(self.run_id, field_name="run_id"))
        object.__setattr__(self, "purpose", _require_text(self.purpose, field_name="purpose"))
        object.__setattr__(self, "prompt", _require_text(self.prompt, field_name="prompt"))
        object.__setattr__(
            self,
            "system_instructions",
            _normalize_optional_text(self.system_instructions, field_name="system_instructions"),
        )
        object.__setattr__(self, "json_schema", _normalize_mapping(self.json_schema, field_name="json_schema"))
        object.__setattr__(self, "metadata", _normalize_required_mapping(self.metadata, field_name="metadata"))

        if not isinstance(self.response_mode, ModelResponseMode):
            raise TypeError("response_mode must be a ModelResponseMode")

        if self.response_mode is ModelResponseMode.JSON and self.json_schema is not None and not self.json_schema:
            raise ValueError("json_schema may not be empty when provided")
        if self.response_mode is ModelResponseMode.TEXT and self.json_schema is not None:
            raise ValueError("json_schema is only valid for JSON response_mode")
        if self.timeout_seconds is not None and self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero when provided")
        if self.max_output_tokens is not None and self.max_output_tokens <= 0:
            raise ValueError("max_output_tokens must be greater than zero when provided")
        if self.reasoning_effort is not None:
            object.__setattr__(
                self,
                "reasoning_effort",
                _require_text(self.reasoning_effort, field_name="reasoning_effort"),
            )


@dataclass(frozen=True, slots=True)
class ModelUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: float | None = None
    latency_ms: int | None = None

    def __post_init__(self) -> None:
        for field_name in ("input_tokens", "output_tokens", "total_tokens", "latency_ms"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} must be zero or greater when provided")
        if self.estimated_cost is not None and self.estimated_cost < 0:
            raise ValueError("estimated_cost must be zero or greater when provided")


@dataclass(frozen=True, slots=True)
class ModelResponse:
    request_id: str
    adapter_id: str
    provider_name: str
    model_name: str
    status: ModelInvocationStatus
    output_text: str | None
    output_json: dict[str, Any] | None
    usage: ModelUsage
    warnings: tuple[str, ...] = ()
    raw_response_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_id", _require_text(self.request_id, field_name="request_id"))
        object.__setattr__(self, "adapter_id", _require_text(self.adapter_id, field_name="adapter_id"))
        object.__setattr__(self, "provider_name", _require_text(self.provider_name, field_name="provider_name"))
        object.__setattr__(self, "model_name", _require_text(self.model_name, field_name="model_name"))
        object.__setattr__(self, "output_text", _normalize_optional_text(self.output_text, field_name="output_text"))
        object.__setattr__(self, "output_json", _normalize_mapping(self.output_json, field_name="output_json"))
        object.__setattr__(
            self,
            "raw_response_ref",
            _normalize_optional_text(self.raw_response_ref, field_name="raw_response_ref"),
        )
        object.__setattr__(self, "warnings", _normalize_warnings(self.warnings))

        if not isinstance(self.status, ModelInvocationStatus):
            raise TypeError("status must be a ModelInvocationStatus")
        if not isinstance(self.usage, ModelUsage):
            raise TypeError("usage must be a ModelUsage")

        if self.status is ModelInvocationStatus.COMPLETED:
            if self.output_text is None and self.output_json is None:
                raise ValueError("completed responses must include output_text or output_json")
