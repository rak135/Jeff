"""Minimal internal envelopes for module I/O."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from types import MappingProxyType
from typing import Mapping

from .scope import Scope


def _freeze_mapping(
    value: Mapping[str, object] | None,
) -> Mapping[str, object]:
    return MappingProxyType(dict(value or {}))


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    code: str
    message: str
    field_path: str | None = None
    related_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.code, str) or not self.code.strip():
            raise ValueError("code must be a non-empty string")
        if not isinstance(self.message, str) or not self.message.strip():
            raise ValueError("message must be a non-empty string")


@dataclass(frozen=True, slots=True)
class EnvelopeMetadata:
    schema_version: str = "1.0"
    produced_at: str = field(default_factory=_utc_now_iso)
    correlation_id: str | None = None
    trace_id: str | None = None
    producer: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.schema_version, str) or not self.schema_version.strip():
            raise ValueError("schema_version must be a non-empty string")
        if not isinstance(self.produced_at, str) or not self.produced_at.strip():
            raise ValueError("produced_at must be a non-empty string")


@dataclass(frozen=True, slots=True)
class InternalEnvelope:
    module: str
    scope: Scope
    metadata: EnvelopeMetadata = field(default_factory=EnvelopeMetadata)
    payload: Mapping[str, object] | None = None
    result: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or not self.module.strip():
            raise ValueError("module must be a non-empty string")

        has_payload = self.payload is not None
        has_result = self.result is not None
        if has_payload == has_result:
            raise ValueError("exactly one of payload or result must be provided")

        if has_payload:
            object.__setattr__(self, "payload", _freeze_mapping(self.payload))
        if has_result:
            object.__setattr__(self, "result", _freeze_mapping(self.result))
