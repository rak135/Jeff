"""In-memory repository implementing MemoryStoreProtocol.

Used for tests and non-PostgreSQL environments.  Lexical search uses
token-intersection matching.  Semantic search uses cosine similarity over
in-process embeddings — functionally correct but not indexed for scale.

Global/system memory is hard-forbidden; project_id scoping is enforced by callers.
"""

from __future__ import annotations

import math

from jeff.core.schemas import MemoryId, coerce_memory_id, coerce_project_id

from .models import CommittedMemoryRecord
from .types import normalized_identity


class InMemoryMemoryStore:
    def __init__(self) -> None:
        self._records: dict[MemoryId, CommittedMemoryRecord] = {}
        self._counter = 0
        # Link storage: target_id → [MemoryLink, ...], memory_id → [MemoryLink, ...]
        self._links_by_target: dict[str, list] = {}
        self._links_by_memory: dict[str, list] = {}
        # Audit storage
        self._write_events: list = []
        self._retrieval_events: list = []
        self._maintenance_jobs: list = []
        # Embedding storage: memory_id → list[float]
        self._embeddings: dict[str, list[float]] = {}

    # --- Record operations ---

    def allocate_memory_id(self) -> MemoryId:
        self._counter += 1
        return coerce_memory_id(f"memory-{self._counter}")

    def get_committed(self, memory_id: str) -> CommittedMemoryRecord | None:
        return self._records.get(coerce_memory_id(memory_id))

    def list_project_records(self, project_id: str) -> tuple[CommittedMemoryRecord, ...]:
        normalized_project_id = coerce_project_id(project_id)
        records = [
            record
            for record in self._records.values()
            if record.scope.project_id == normalized_project_id
        ]
        records.sort(key=lambda record: str(record.memory_id))
        return tuple(records)

    def _store_committed_record(self, record: CommittedMemoryRecord) -> None:
        """Internal: write a committed record. Used by write_pipeline and test fixtures."""
        self._records[record.memory_id] = record

    def _mark_superseded(
        self,
        *,
        superseded_memory_id: MemoryId,
        new_memory_id: MemoryId,
    ) -> None:
        """Mark an existing record as superseded by a new one."""
        old = self._records.get(superseded_memory_id)
        if old is None:
            return
        updated = CommittedMemoryRecord(
            memory_id=old.memory_id,
            memory_type=old.memory_type,
            scope=old.scope,
            summary=old.summary,
            remembered_points=old.remembered_points,
            why_it_matters=old.why_it_matters,
            support_quality=old.support_quality,
            stability=old.stability,
            record_status="superseded",
            conflict_posture=old.conflict_posture,
            created_at=old.created_at,
            updated_at=old.updated_at,
            support_refs=old.support_refs,
            freshness_sensitivity=old.freshness_sensitivity,
            created_from_run_id=old.created_from_run_id,
            schema_version=old.schema_version,
            supersedes_memory_id=old.supersedes_memory_id,
            superseded_by_memory_id=str(new_memory_id),
            merged_into_memory_id=old.merged_into_memory_id,
        )
        self._records[superseded_memory_id] = updated

    # --- Link operations ---

    def store_link(self, link) -> None:
        target_key = link.target_id
        memory_key = str(link.memory_id)
        self._links_by_target.setdefault(target_key, []).append(link)
        self._links_by_memory.setdefault(memory_key, []).append(link)

    def get_links_for_target(self, target_id: str, project_id: str) -> tuple:
        """Return links for target_id whose source memory belongs to project_id."""
        links = self._links_by_target.get(target_id, [])
        result = []
        for link in links:
            record = self.get_committed(str(link.memory_id))
            if record is not None and str(record.scope.project_id) == project_id:
                result.append(link)
        return tuple(result)

    def get_links_for_memory(self, memory_id: str) -> tuple:
        return tuple(self._links_by_memory.get(memory_id, []))

    # --- Retrieval search ---

    def search_lexical(
        self,
        project_id: str,
        query: str,
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Token-intersection search over active project records."""
        query_tokens = set(normalized_identity(query).split())
        if not query_tokens:
            return ()
        results = []
        for record in self.list_project_records(project_id):
            if record.record_status != "active":
                continue
            if memory_type_filter is not None and record.memory_type != memory_type_filter:
                continue
            haystack_tokens = set(
                normalized_identity(
                    " ".join([record.summary, record.why_it_matters, *record.remembered_points])
                ).split()
            )
            if query_tokens & haystack_tokens:
                results.append(record)
        return tuple(results[:limit])

    def search_semantic(
        self,
        project_id: str,
        query_embedding: list[float],
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Cosine similarity search using stored embeddings.

        Returns empty when no embeddings are stored (degraded but not broken).
        Records without stored embeddings are silently skipped; the committed
        record remains authoritative regardless.
        """
        if not self._embeddings or not query_embedding:
            return ()
        query_norm = _vec_norm(query_embedding)
        if query_norm == 0.0:
            return ()
        scored: list[tuple[float, CommittedMemoryRecord]] = []
        for record in self.list_project_records(project_id):
            if record.record_status != "active":
                continue
            if memory_type_filter is not None and record.memory_type != memory_type_filter:
                continue
            emb = self._embeddings.get(str(record.memory_id))
            if emb is None:
                continue
            score = _cosine_similarity(query_embedding, query_norm, emb)
            scored.append((score, record))
        scored.sort(key=lambda x: x[0], reverse=True)
        return tuple(record for _, record in scored[:limit])

    def store_embedding(self, memory_id: str, embedding: list[float]) -> None:
        self._embeddings[memory_id] = embedding

    # --- Audit / event operations ---

    def store_write_event(self, event) -> None:
        self._write_events.append(event)

    def store_retrieval_event(self, event) -> None:
        self._retrieval_events.append(event)

    def store_maintenance_job(self, job) -> None:
        self._maintenance_jobs.append(job)


def _vec_norm(v: list[float]) -> float:
    return math.sqrt(sum(x * x for x in v))


def _cosine_similarity(a: list[float], a_norm: float, b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    b_norm = _vec_norm(b)
    if b_norm == 0.0:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    return dot / (a_norm * b_norm)
