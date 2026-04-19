"""Operational helpers for duplicate control, supersession, and status updates."""

from __future__ import annotations

from dataclasses import replace

from .models import CompiledKnowledgeArtifact
from .registry import KnowledgeRegistry, KnowledgeStore
from .staleness import relabel_artifact_status


def detect_duplicate_topic_note(
    *,
    project_id: str,
    topic_key: str | None,
    supporting_artifact_ids: tuple[str, ...],
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact | None:
    registry = KnowledgeRegistry(store)
    duplicate = registry.find_duplicate_topic_note(
        project_id=project_id,
        topic_key=topic_key,
        supporting_artifact_ids=supporting_artifact_ids,
    )
    if duplicate is None:
        return None
    return store.get_by_id(project_id, duplicate.artifact_id)


def supersede_knowledge_artifact(
    *,
    project_id: str,
    superseded_artifact_id: str,
    replacement: CompiledKnowledgeArtifact,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact:
    current = store.get_by_id(project_id, superseded_artifact_id)
    if current is None:
        raise ValueError("cannot supersede a compiled knowledge artifact that does not exist")
    if replacement.project_id != current.project_id:
        raise ValueError("compiled knowledge supersession must stay within one project")
    replacement_record = replacement
    if replacement.supersedes_artifact_id is None:
        replacement_record = replace(replacement, supersedes_artifact_id=superseded_artifact_id)
    store.save(replacement_record)
    store.save(
        replace(
            relabel_artifact_status(current, status="superseded", updated_at=replacement_record.updated_at),
            superseded_by_artifact_id=str(replacement_record.artifact_id),
        )
    )
    return replacement_record


def relabel_persisted_artifact(
    *,
    project_id: str,
    artifact_id: str,
    status: str,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact:
    artifact = store.get_by_id(project_id, artifact_id)
    if artifact is None:
        raise ValueError("cannot relabel a compiled knowledge artifact that does not exist")
    updated = relabel_artifact_status(artifact, status=status)
    store.save(updated)
    return updated