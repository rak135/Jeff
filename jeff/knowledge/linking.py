"""Project-safe linking helpers for compiled knowledge artifacts."""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from .models import CompiledKnowledgeArtifact


class _ProjectArtifact(Protocol):
    artifact_id: str
    project_id: str


def add_related_artifacts(
    artifact: CompiledKnowledgeArtifact,
    *related_artifacts: _ProjectArtifact,
) -> CompiledKnowledgeArtifact:
    related_ids = list(artifact.related_artifact_ids)
    for related in related_artifacts:
        if related.project_id != artifact.project_id:
            raise ValueError("compiled knowledge related-artifact links must stay project-scoped")
        if str(related.artifact_id) == str(artifact.artifact_id):
            continue
        related_ids.append(str(related.artifact_id))
    return replace(artifact, related_artifact_ids=tuple(dict.fromkeys(related_ids)))