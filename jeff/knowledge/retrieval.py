"""Bounded retrieval for compiled knowledge support."""

from __future__ import annotations

from dataclasses import dataclass

from jeff.cognitive.types import require_text
from jeff.memory.types import normalized_identity

from .ids import allocate_knowledge_retrieval_event_id
from .models import CONTEXT_PRIORITY, CompiledKnowledgeArtifact
from .registry import KnowledgeRegistry, KnowledgeStore


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalRequest:
    project_id: str
    purpose: str
    artifact_id: str | None = None
    artifact_family: str | None = None
    work_unit_id: str | None = None
    run_id: str | None = None
    topic_query: str | None = None
    limit: int = 5
    include_stale: bool = True
    include_quarantined: bool = False
    include_superseded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "project_id", require_text(self.project_id, field_name="project_id"))
        object.__setattr__(self, "purpose", require_text(self.purpose, field_name="purpose"))
        if self.artifact_id is not None:
            object.__setattr__(self, "artifact_id", require_text(self.artifact_id, field_name="artifact_id"))
        if self.artifact_family is not None:
            object.__setattr__(self, "artifact_family", require_text(self.artifact_family, field_name="artifact_family"))
        if self.topic_query is not None:
            object.__setattr__(self, "topic_query", require_text(self.topic_query, field_name="topic_query"))
        if self.limit < 1 or self.limit > 25:
            raise ValueError("knowledge retrieval limit must stay between 1 and 25")


@dataclass(frozen=True, slots=True)
class KnowledgeRetrievalResult:
    retrieval_event_id: str
    request: KnowledgeRetrievalRequest
    artifacts: tuple[CompiledKnowledgeArtifact, ...]
    support_only: bool
    context_priority: str
    intended_context_order: tuple[str, ...]
    notes: tuple[str, ...]
    stale_artifact_ids: tuple[str, ...]


def retrieve_knowledge(
    request: KnowledgeRetrievalRequest,
    *,
    store: KnowledgeStore,
) -> KnowledgeRetrievalResult:
    notes = [
        "Compiled knowledge is support-only and must stay below truth and committed memory during context assembly.",
        "Artifacts remain project-scoped and preserve visible provenance back to lawful upstream support objects.",
    ]
    if request.artifact_id is not None:
        artifact = store.get_by_id(request.project_id, request.artifact_id)
        artifacts = (artifact,) if artifact is not None else ()
    else:
        registry = KnowledgeRegistry(store)
        entries = registry.list_entries(
            project_id=request.project_id,
            artifact_family=request.artifact_family,
        )
        artifacts = tuple(
            artifact
            for artifact in (
                store.get_by_id(request.project_id, entry.artifact_id)
                for entry in entries
            )
            if artifact is not None and _matches_scope(artifact, request)
        )
        if request.topic_query is not None:
            query = normalized_identity(request.topic_query)
            artifacts = tuple(
                artifact
                for artifact in artifacts
                if query in normalized_identity(artifact.title)
                or (artifact.topic_key is not None and query in artifact.topic_key)
                or (artifact.topic_framing is not None and query in normalized_identity(artifact.topic_framing))
            )
        artifacts = _filter_statuses(artifacts, request)
        artifacts = _dedupe_overlapping_topic_notes(artifacts)
        artifacts = artifacts[: request.limit]

    stale_artifact_ids = tuple(
        str(artifact.artifact_id)
        for artifact in artifacts
        if artifact.status in {"stale_review_needed", "stale_rebuild_needed", "superseded", "quarantined"}
    )
    if stale_artifact_ids:
        notes.append(f"Stale or non-current artifacts were labeled explicitly: {', '.join(stale_artifact_ids)}")
    return KnowledgeRetrievalResult(
        retrieval_event_id=allocate_knowledge_retrieval_event_id(),
        request=request,
        artifacts=artifacts,
        support_only=True,
        context_priority="after_committed_memory",
        intended_context_order=CONTEXT_PRIORITY,
        notes=tuple(notes),
        stale_artifact_ids=stale_artifact_ids,
    )


def _matches_scope(artifact: CompiledKnowledgeArtifact, request: KnowledgeRetrievalRequest) -> bool:
    if artifact.project_id != request.project_id:
        return False
    if request.run_id is not None:
        return (
            artifact.work_unit_id in {None, request.work_unit_id}
            and artifact.run_id in {None, request.run_id}
        )
    if request.work_unit_id is not None:
        return artifact.run_id is None and artifact.work_unit_id in {None, request.work_unit_id}
    return artifact.work_unit_id is None and artifact.run_id is None


def _filter_statuses(
    artifacts: tuple[CompiledKnowledgeArtifact, ...],
    request: KnowledgeRetrievalRequest,
) -> tuple[CompiledKnowledgeArtifact, ...]:
    filtered: list[CompiledKnowledgeArtifact] = []
    for artifact in artifacts:
        if artifact.status == "quarantined" and not request.include_quarantined:
            continue
        if artifact.status == "superseded" and not request.include_superseded:
            continue
        if artifact.status in {"stale_review_needed", "stale_rebuild_needed"} and not request.include_stale:
            continue
        filtered.append(artifact)
    return tuple(filtered)


def _dedupe_overlapping_topic_notes(
    artifacts: tuple[CompiledKnowledgeArtifact, ...],
) -> tuple[CompiledKnowledgeArtifact, ...]:
    deduped: list[CompiledKnowledgeArtifact] = []
    seen_topic_keys: set[str] = set()
    for artifact in artifacts:
        if artifact.artifact_family != "topic_note" or artifact.topic_key is None:
            deduped.append(artifact)
            continue
        if artifact.topic_key in seen_topic_keys:
            continue
        seen_topic_keys.add(artifact.topic_key)
        deduped.append(artifact)
    return tuple(deduped)