"""Staleness and quarantine helpers for compiled knowledge artifacts."""

from __future__ import annotations

from dataclasses import replace

from jeff.memory.types import utc_now

from .models import ARTIFACT_STATUSES, CompiledKnowledgeArtifact


def relabel_artifact_status(
    artifact: CompiledKnowledgeArtifact,
    *,
    status: str,
    updated_at: str | None = None,
) -> CompiledKnowledgeArtifact:
    if status not in ARTIFACT_STATUSES:
        raise ValueError(f"unsupported compiled knowledge status: {status}")
    return replace(artifact, status=status, updated_at=updated_at or utc_now())


def mark_stale_review_needed(artifact: CompiledKnowledgeArtifact) -> CompiledKnowledgeArtifact:
    return relabel_artifact_status(artifact, status="stale_review_needed")


def mark_stale_rebuild_needed(artifact: CompiledKnowledgeArtifact) -> CompiledKnowledgeArtifact:
    return relabel_artifact_status(artifact, status="stale_rebuild_needed")


def quarantine_artifact(artifact: CompiledKnowledgeArtifact) -> CompiledKnowledgeArtifact:
    return relabel_artifact_status(artifact, status="quarantined")