"""Bounded compiled knowledge support layer."""

from .api import (
    build_memory_handoff_signal,
    create_source_digest_from_archive_artifact,
    create_source_digest_from_research_record,
    create_topic_note,
    detect_duplicate_topic_note_artifact,
    get_knowledge_artifact_by_id,
    relabel_artifact,
    retrieve_project_knowledge,
    save_knowledge_artifact,
    supersede_artifact,
)
from .ids import (
    KnowledgeArtifactId,
    KnowledgeRetrievalEventId,
    allocate_knowledge_artifact_id,
    allocate_knowledge_retrieval_event_id,
    coerce_knowledge_artifact_id,
    coerce_knowledge_retrieval_event_id,
)
from .lineage import refresh_knowledge_artifact
from .models import (
    ARTIFACT_FAMILIES,
    ARTIFACT_STATUSES,
    CONTEXT_PRIORITY,
    CompiledKnowledgeArtifact,
    KnowledgeProvenance,
    MemoryHandoffSignal,
)
from .registry import KnowledgeRegistry, KnowledgeRegistryEntry, KnowledgeStore
from .retrieval import KnowledgeRetrievalRequest, KnowledgeRetrievalResult
from .telemetry import KnowledgeCounters, get_counters

__all__ = [
    "ARTIFACT_FAMILIES",
    "ARTIFACT_STATUSES",
    "CONTEXT_PRIORITY",
    "CompiledKnowledgeArtifact",
    "KnowledgeArtifactId",
    "KnowledgeCounters",
    "KnowledgeProvenance",
    "KnowledgeRegistry",
    "KnowledgeRegistryEntry",
    "KnowledgeRetrievalEventId",
    "KnowledgeRetrievalRequest",
    "KnowledgeRetrievalResult",
    "KnowledgeStore",
    "MemoryHandoffSignal",
    "allocate_knowledge_artifact_id",
    "allocate_knowledge_retrieval_event_id",
    "build_memory_handoff_signal",
    "coerce_knowledge_artifact_id",
    "coerce_knowledge_retrieval_event_id",
    "create_source_digest_from_archive_artifact",
    "create_source_digest_from_research_record",
    "create_topic_note",
    "detect_duplicate_topic_note_artifact",
    "get_counters",
    "get_knowledge_artifact_by_id",
    "refresh_knowledge_artifact",
    "relabel_artifact",
    "retrieve_project_knowledge",
    "save_knowledge_artifact",
    "supersede_artifact",
]