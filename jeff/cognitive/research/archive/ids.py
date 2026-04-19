"""Jeff-issued opaque IDs for research archive artifacts and events."""

from __future__ import annotations

import uuid
from typing import NewType

ArchiveArtifactId = NewType("ArchiveArtifactId", str)
ArchiveRetrievalEventId = NewType("ArchiveRetrievalEventId", str)


def _coerce(type_fn: type, value: str, field_name: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    normalized = value.strip()
    if not normalized:
        raise ValueError(f"{field_name} must be a non-empty string")
    return type_fn(normalized)


def coerce_archive_artifact_id(value: str) -> ArchiveArtifactId:
    return _coerce(ArchiveArtifactId, value, "artifact_id")


def coerce_archive_retrieval_event_id(value: str) -> ArchiveRetrievalEventId:
    return _coerce(ArchiveRetrievalEventId, value, "retrieval_event_id")


def allocate_archive_artifact_id() -> ArchiveArtifactId:
    return coerce_archive_artifact_id(f"artifact-{uuid.uuid4().hex[:16]}")


def allocate_archive_retrieval_event_id() -> ArchiveRetrievalEventId:
    return coerce_archive_retrieval_event_id(f"archive-re-{uuid.uuid4().hex[:12]}")