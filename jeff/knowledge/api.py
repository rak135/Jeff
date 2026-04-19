"""Public API for compiled knowledge creation, persistence, and retrieval."""

from __future__ import annotations

import secrets

from jeff.cognitive.research import ResearchArtifactRecord
from jeff.cognitive.research.archive import ResearchArchiveArtifact

from .compiler import support_from_archive_artifact, support_from_research_record
from .digests import build_source_digest
from .maintenance import detect_duplicate_topic_note, relabel_persisted_artifact, supersede_knowledge_artifact
from .models import CompiledKnowledgeArtifact, MemoryHandoffSignal
from .registry import KnowledgeStore
from .retrieval import KnowledgeRetrievalRequest, KnowledgeRetrievalResult, retrieve_knowledge
from .telemetry import get_counters
from .topics import build_topic_note


def create_source_digest_from_research_record(
    record: ResearchArtifactRecord,
) -> CompiledKnowledgeArtifact:
    return build_source_digest(support_from_research_record(record))


def create_source_digest_from_archive_artifact(
    artifact: ResearchArchiveArtifact,
) -> CompiledKnowledgeArtifact:
    return build_source_digest(support_from_archive_artifact(artifact))


def create_topic_note(
    *,
    topic: str,
    supports: tuple[CompiledKnowledgeArtifact, ...],
    major_supported_points: tuple[str, ...],
    contested_points: tuple[str, ...] = (),
    unresolved_items: tuple[str, ...] = (),
    topic_framing: str | None = None,
) -> CompiledKnowledgeArtifact:
    return build_topic_note(
        topic=topic,
        supports=supports,
        major_supported_points=major_supported_points,
        contested_points=contested_points,
        unresolved_items=unresolved_items,
        topic_framing=topic_framing,
    )


def build_memory_handoff_signal(
    artifact: CompiledKnowledgeArtifact,
    *,
    signal_summary: str | None = None,
) -> MemoryHandoffSignal:
    summary = signal_summary or f"Compiled knowledge artifact {artifact.artifact_id} may be relevant for later memory review."
    return MemoryHandoffSignal(
        signal_id=f"knowhandoff_{secrets.token_hex(6)}",
        signal_summary=summary,
        support_refs=(str(artifact.artifact_id),),
    )


def save_knowledge_artifact(
    artifact: CompiledKnowledgeArtifact,
    *,
    store: KnowledgeStore,
) -> str:
    path = store.save(artifact)
    get_counters().artifacts_saved += 1
    return str(path)


def get_knowledge_artifact_by_id(
    *,
    project_id: str,
    artifact_id: str,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact | None:
    return store.get_by_id(project_id, artifact_id)


def retrieve_project_knowledge(
    request: KnowledgeRetrievalRequest,
    *,
    store: KnowledgeStore,
) -> KnowledgeRetrievalResult:
    result = retrieve_knowledge(request, store=store)
    get_counters().retrievals += 1
    if result.stale_artifact_ids:
        get_counters().stale_reads += 1
    return result


def detect_duplicate_topic_note_artifact(
    artifact: CompiledKnowledgeArtifact,
    *,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact | None:
    duplicate = detect_duplicate_topic_note(
        project_id=artifact.project_id,
        topic_key=artifact.topic_key,
        supporting_artifact_ids=artifact.supporting_artifact_ids,
        store=store,
    )
    if duplicate is not None:
        get_counters().duplicate_topic_note_rejections += 1
    return duplicate


def supersede_artifact(
    *,
    project_id: str,
    superseded_artifact_id: str,
    replacement: CompiledKnowledgeArtifact,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact:
    updated = supersede_knowledge_artifact(
        project_id=project_id,
        superseded_artifact_id=superseded_artifact_id,
        replacement=replacement,
        store=store,
    )
    get_counters().supersessions += 1
    return updated


def relabel_artifact(
    *,
    project_id: str,
    artifact_id: str,
    status: str,
    store: KnowledgeStore,
) -> CompiledKnowledgeArtifact:
    return relabel_persisted_artifact(project_id=project_id, artifact_id=artifact_id, status=status, store=store)