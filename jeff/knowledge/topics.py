"""Builders and identity helpers for compiled topic notes."""

from __future__ import annotations

from jeff.memory.types import normalized_identity, utc_now

from .compiler import (
    SourceAwareSupport,
    collect_provenance,
    collect_source_refs,
    collect_supporting_ids,
    derive_locality,
    support_from_knowledge_artifact,
)
from .ids import allocate_knowledge_artifact_id
from .models import CompiledKnowledgeArtifact, MemoryHandoffSignal


def build_topic_identity_key(topic: str, supporting_artifact_ids: tuple[str, ...]) -> str:
    topic_key = normalized_identity(topic)
    support_key = "|".join(sorted(supporting_artifact_ids))
    return f"{topic_key}::{support_key}"


def build_topic_note(
    *,
    topic: str,
    supports: tuple[SourceAwareSupport | CompiledKnowledgeArtifact, ...],
    major_supported_points: tuple[str, ...],
    contested_points: tuple[str, ...] = (),
    unresolved_items: tuple[str, ...] = (),
    topic_framing: str | None = None,
    artifact_id: str | None = None,
    generated_at: str | None = None,
    memory_handoff_signal: MemoryHandoffSignal | None = None,
) -> CompiledKnowledgeArtifact:
    if len(supports) < 2:
        raise ValueError("topic_note requires multiple upstream support objects")
    normalized_supports = tuple(
        support_from_knowledge_artifact(item) if isinstance(item, CompiledKnowledgeArtifact) else item
        for item in supports
    )
    work_unit_id, run_id = derive_locality(normalized_supports)
    supporting_artifact_ids = collect_supporting_ids(normalized_supports)
    timestamp = generated_at or utc_now()
    topic_key = normalized_identity(topic)
    title = f"Topic note: {topic}"
    framing = topic_framing or f"Compiled support for topic '{topic}'."
    source_refs = collect_source_refs(normalized_supports)
    return CompiledKnowledgeArtifact(
        artifact_id=artifact_id or allocate_knowledge_artifact_id(),
        artifact_family="topic_note",
        project_id=normalized_supports[0].project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        title=title,
        generated_at=timestamp,
        updated_at=timestamp,
        derived_from_artifact_ids=supporting_artifact_ids,
        source_refs=source_refs,
        provenance=collect_provenance(normalized_supports),
        related_artifact_ids=supporting_artifact_ids,
        supporting_artifact_ids=supporting_artifact_ids,
        topic_key=topic_key,
        memory_handoff_signal=memory_handoff_signal,
        topic_framing=framing,
        major_supported_points=major_supported_points,
        contested_points=contested_points,
        unresolved_items=unresolved_items,
        relevant_source_refs=source_refs,
    )