"""Lineage helpers for rebuilds and supersession-friendly compiled knowledge flows."""

from __future__ import annotations

from dataclasses import replace

from jeff.memory.types import utc_now

from .ids import allocate_knowledge_artifact_id
from .models import CompiledKnowledgeArtifact


def refresh_knowledge_artifact(
    artifact: CompiledKnowledgeArtifact,
    *,
    generated_at: str | None = None,
    **changes: object,
) -> CompiledKnowledgeArtifact:
    timestamp = generated_at or utc_now()
    derived_from = tuple(dict.fromkeys((*artifact.derived_from_artifact_ids, str(artifact.artifact_id))))
    return replace(
        artifact,
        artifact_id=allocate_knowledge_artifact_id(),
        generated_at=timestamp,
        updated_at=timestamp,
        derived_from_artifact_ids=derived_from,
        superseded_by_artifact_id=None,
        supersedes_artifact_id=None,
        **changes,
    )