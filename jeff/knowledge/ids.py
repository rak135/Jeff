"""Opaque identifiers for compiled knowledge artifacts and retrieval events."""

from __future__ import annotations

import secrets
from typing import NewType

from jeff.cognitive.types import require_text

KnowledgeArtifactId = NewType("KnowledgeArtifactId", str)
KnowledgeRetrievalEventId = NewType("KnowledgeRetrievalEventId", str)


def _allocate_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def allocate_knowledge_artifact_id() -> KnowledgeArtifactId:
    return KnowledgeArtifactId(_allocate_id("know"))


def allocate_knowledge_retrieval_event_id() -> KnowledgeRetrievalEventId:
    return KnowledgeRetrievalEventId(_allocate_id("knowretr"))


def coerce_knowledge_artifact_id(value: str) -> KnowledgeArtifactId:
    return KnowledgeArtifactId(require_text(value, field_name="knowledge_artifact_id"))


def coerce_knowledge_retrieval_event_id(value: str) -> KnowledgeRetrievalEventId:
    return KnowledgeRetrievalEventId(require_text(value, field_name="knowledge_retrieval_event_id"))