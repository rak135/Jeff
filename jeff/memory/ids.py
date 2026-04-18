"""Memory-owned typed IDs and coercion helpers."""

from __future__ import annotations

from typing import NewType

from jeff.core.schemas import MemoryId, coerce_memory_id  # noqa: F401 — re-export

MemoryCandidateId = NewType("MemoryCandidateId", str)
MemoryLinkId = NewType("MemoryLinkId", str)
MemoryWriteEventId = NewType("MemoryWriteEventId", str)
MemoryRetrievalEventId = NewType("MemoryRetrievalEventId", str)
MaintenanceJobId = NewType("MaintenanceJobId", str)


def _coerce(type_fn: type, value: str, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field} must be a non-empty string")
    return type_fn(normalized)


def coerce_candidate_id(value: str) -> MemoryCandidateId:
    return _coerce(MemoryCandidateId, value, "candidate_id")


def coerce_link_id(value: str) -> MemoryLinkId:
    return _coerce(MemoryLinkId, value, "link_id")


def coerce_write_event_id(value: str) -> MemoryWriteEventId:
    return _coerce(MemoryWriteEventId, value, "write_event_id")


def coerce_retrieval_event_id(value: str) -> MemoryRetrievalEventId:
    return _coerce(MemoryRetrievalEventId, value, "retrieval_event_id")


def coerce_maintenance_job_id(value: str) -> MaintenanceJobId:
    return _coerce(MaintenanceJobId, value, "maintenance_job_id")
