"""Local filesystem-backed memory store implementing MemoryStoreProtocol.

This backend is the durable local-runtime path for normal one-shot CLI usage.
It keeps committed memory support-only and persists records, links, embeddings,
and audit events under the workspace runtime home so fresh `python -m jeff`
processes can retrieve the same committed memory.
"""

from __future__ import annotations

import contextlib
import copy
import json
import math
from pathlib import Path

from jeff.core.schemas import MemoryId, Scope, coerce_memory_id, coerce_project_id

from .ids import (
    coerce_link_id,
    coerce_maintenance_job_id,
    coerce_retrieval_event_id,
    coerce_write_event_id,
)
from .models import CommittedMemoryRecord, MemorySupportRef
from .schemas import MaintenanceJobRecord, MemoryLink, MemoryRetrievalEvent, MemoryWriteEvent
from .types import normalized_identity

_SCHEMA_VERSION = "1.0"


class LocalFileMemoryStore:
    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)
        self._store_path = self.root_dir / "memory_store.json"
        self._counter = 0
        self._records: dict[MemoryId, CommittedMemoryRecord] = {}
        self._links: list[MemoryLink] = []
        self._links_by_target: dict[str, list[MemoryLink]] = {}
        self._links_by_memory: dict[str, list[MemoryLink]] = {}
        self._write_events: list[MemoryWriteEvent] = []
        self._retrieval_events: list[MemoryRetrievalEvent] = []
        self._maintenance_jobs: list[MaintenanceJobRecord] = []
        self._embeddings: dict[str, list[float]] = {}
        self._atomic_depth = 0
        self._load()

    # --- Record operations ---

    def allocate_memory_id(self) -> MemoryId:
        self._counter += 1
        self._persist_if_auto()
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
        self._records[record.memory_id] = record
        self._persist_if_auto()

    def _mark_superseded(
        self,
        *,
        superseded_memory_id: MemoryId,
        new_memory_id: MemoryId,
    ) -> None:
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
        self._persist_if_auto()

    # --- Link operations ---

    def store_link(self, link: MemoryLink) -> None:
        self._links.append(link)
        self._rebuild_link_indexes()
        self._persist_if_auto()

    def get_links_for_target(self, target_id: str, project_id: str) -> tuple[MemoryLink, ...]:
        links = self._links_by_target.get(target_id, [])
        result = []
        for link in links:
            record = self.get_committed(str(link.memory_id))
            if record is not None and str(record.scope.project_id) == project_id:
                result.append(link)
        return tuple(result)

    def get_links_for_memory(self, memory_id: str) -> tuple[MemoryLink, ...]:
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
        scored.sort(key=lambda item: item[0], reverse=True)
        return tuple(record for _, record in scored[:limit])

    def store_embedding(self, memory_id: str, embedding: list[float]) -> None:
        self._embeddings[memory_id] = embedding
        self._persist_if_auto()

    # --- Audit / event operations ---

    def store_write_event(self, event: MemoryWriteEvent) -> None:
        self._write_events.append(event)
        self._persist_if_auto()

    def store_retrieval_event(self, event: MemoryRetrievalEvent) -> None:
        self._retrieval_events.append(event)
        self._persist_if_auto()

    def store_maintenance_job(self, job: MaintenanceJobRecord) -> None:
        self._maintenance_jobs.append(job)
        self._persist_if_auto()

    # --- Transaction control ---

    @contextlib.contextmanager
    def atomic(self):
        if self._atomic_depth > 0:
            self._atomic_depth += 1
            try:
                yield
            finally:
                self._atomic_depth -= 1
            return

        snapshot = self._snapshot()
        self._atomic_depth = 1
        try:
            yield
            self._persist()
        except Exception:
            self._restore(snapshot)
            raise
        finally:
            self._atomic_depth = 0

    # --- Persistence helpers ---

    def _persist_if_auto(self) -> None:
        if self._atomic_depth == 0:
            self._persist()

    def _snapshot(self) -> dict[str, object]:
        return {
            "counter": self._counter,
            "records": copy.deepcopy(self._records),
            "links": copy.deepcopy(self._links),
            "write_events": copy.deepcopy(self._write_events),
            "retrieval_events": copy.deepcopy(self._retrieval_events),
            "maintenance_jobs": copy.deepcopy(self._maintenance_jobs),
            "embeddings": copy.deepcopy(self._embeddings),
        }

    def _restore(self, snapshot: dict[str, object]) -> None:
        self._counter = int(snapshot["counter"])
        self._records = snapshot["records"]  # type: ignore[assignment]
        self._links = snapshot["links"]  # type: ignore[assignment]
        self._write_events = snapshot["write_events"]  # type: ignore[assignment]
        self._retrieval_events = snapshot["retrieval_events"]  # type: ignore[assignment]
        self._maintenance_jobs = snapshot["maintenance_jobs"]  # type: ignore[assignment]
        self._embeddings = snapshot["embeddings"]  # type: ignore[assignment]
        self._rebuild_link_indexes()

    def _load(self) -> None:
        if not self._store_path.exists():
            self._persist()
            return
        payload = json.loads(self._store_path.read_text(encoding="utf-8"))
        self._counter = int(payload.get("counter", 0))
        self._records = {
            coerce_memory_id(record_payload["memory_id"]): _record_from_payload(record_payload)
            for record_payload in payload.get("records", [])
        }
        self._links = [_link_from_payload(link_payload) for link_payload in payload.get("links", [])]
        self._write_events = [
            _write_event_from_payload(event_payload) for event_payload in payload.get("write_events", [])
        ]
        self._retrieval_events = [
            _retrieval_event_from_payload(event_payload)
            for event_payload in payload.get("retrieval_events", [])
        ]
        self._maintenance_jobs = [
            _maintenance_job_from_payload(job_payload) for job_payload in payload.get("maintenance_jobs", [])
        ]
        self._embeddings = {
            str(memory_id): [float(value) for value in embedding]
            for memory_id, embedding in payload.get("embeddings", {}).items()
        }
        self._rebuild_link_indexes()

    def _persist(self) -> None:
        payload = {
            "schema_version": _SCHEMA_VERSION,
            "counter": self._counter,
            "records": [_record_to_payload(record) for record in self.list_all_records()],
            "links": [_link_to_payload(link) for link in self._links],
            "write_events": [_write_event_to_payload(event) for event in self._write_events],
            "retrieval_events": [_retrieval_event_to_payload(event) for event in self._retrieval_events],
            "maintenance_jobs": [_maintenance_job_to_payload(job) for job in self._maintenance_jobs],
            "embeddings": self._embeddings,
        }
        temp_path = self._store_path.with_name(f"{self._store_path.name}.tmp")
        temp_path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        temp_path.replace(self._store_path)

    def list_all_records(self) -> tuple[CommittedMemoryRecord, ...]:
        records = list(self._records.values())
        records.sort(key=lambda record: str(record.memory_id))
        return tuple(records)

    def _rebuild_link_indexes(self) -> None:
        self._links_by_target = {}
        self._links_by_memory = {}
        for link in self._links:
            self._links_by_target.setdefault(link.target_id, []).append(link)
            self._links_by_memory.setdefault(str(link.memory_id), []).append(link)


def _scope_to_payload(scope: Scope) -> dict[str, str | None]:
    return {
        "project_id": str(scope.project_id),
        "work_unit_id": None if scope.work_unit_id is None else str(scope.work_unit_id),
        "run_id": None if scope.run_id is None else str(scope.run_id),
    }


def _scope_from_payload(payload: dict[str, str | None]) -> Scope:
    return Scope(
        project_id=payload["project_id"],
        work_unit_id=payload.get("work_unit_id"),
        run_id=payload.get("run_id"),
    )


def _support_ref_to_payload(ref: MemorySupportRef) -> dict[str, str]:
    return {
        "ref_kind": ref.ref_kind,
        "ref_id": ref.ref_id,
        "summary": ref.summary,
    }


def _support_ref_from_payload(payload: dict[str, str]) -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind=payload["ref_kind"],
        ref_id=payload["ref_id"],
        summary=payload["summary"],
    )


def _record_to_payload(record: CommittedMemoryRecord) -> dict[str, object]:
    return {
        "memory_id": str(record.memory_id),
        "memory_type": record.memory_type,
        "scope": _scope_to_payload(record.scope),
        "summary": record.summary,
        "remembered_points": list(record.remembered_points),
        "why_it_matters": record.why_it_matters,
        "support_quality": record.support_quality,
        "stability": record.stability,
        "record_status": record.record_status,
        "conflict_posture": record.conflict_posture,
        "created_at": record.created_at,
        "updated_at": record.updated_at,
        "support_refs": [_support_ref_to_payload(ref) for ref in record.support_refs],
        "freshness_sensitivity": record.freshness_sensitivity,
        "created_from_run_id": record.created_from_run_id,
        "schema_version": record.schema_version,
        "supersedes_memory_id": record.supersedes_memory_id,
        "superseded_by_memory_id": record.superseded_by_memory_id,
        "merged_into_memory_id": record.merged_into_memory_id,
    }


def _record_from_payload(payload: dict[str, object]) -> CommittedMemoryRecord:
    return CommittedMemoryRecord(
        memory_id=str(payload["memory_id"]),
        memory_type=str(payload["memory_type"]),
        scope=_scope_from_payload(payload["scope"]),  # type: ignore[arg-type]
        summary=str(payload["summary"]),
        remembered_points=tuple(payload.get("remembered_points", ())),
        why_it_matters=str(payload["why_it_matters"]),
        support_quality=str(payload["support_quality"]),
        stability=str(payload["stability"]),
        record_status=str(payload.get("record_status", "active")),
        conflict_posture=str(payload.get("conflict_posture", "none")),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        support_refs=tuple(_support_ref_from_payload(item) for item in payload.get("support_refs", ())),
        freshness_sensitivity=str(payload.get("freshness_sensitivity", "low")),
        created_from_run_id=payload.get("created_from_run_id"),  # type: ignore[arg-type]
        schema_version=str(payload.get("schema_version", "1.0")),
        supersedes_memory_id=payload.get("supersedes_memory_id"),  # type: ignore[arg-type]
        superseded_by_memory_id=payload.get("superseded_by_memory_id"),  # type: ignore[arg-type]
        merged_into_memory_id=payload.get("merged_into_memory_id"),  # type: ignore[arg-type]
    )


def _link_to_payload(link: MemoryLink) -> dict[str, object]:
    return {
        "memory_link_id": str(link.memory_link_id),
        "memory_id": str(link.memory_id),
        "link_type": link.link_type,
        "target_id": link.target_id,
        "target_family": link.target_family,
        "metadata": dict(link.metadata),
    }


def _link_from_payload(payload: dict[str, object]) -> MemoryLink:
    return MemoryLink(
        memory_link_id=coerce_link_id(str(payload["memory_link_id"])),
        memory_id=str(payload["memory_id"]),
        link_type=str(payload["link_type"]),
        target_id=str(payload["target_id"]),
        target_family=str(payload["target_family"]),
        metadata=dict(payload.get("metadata", {})),
    )


def _write_event_to_payload(event: MemoryWriteEvent) -> dict[str, object]:
    return {
        "write_event_id": str(event.write_event_id),
        "candidate_id": str(event.candidate_id),
        "project_id": event.project_id,
        "write_outcome": event.write_outcome,
        "decision_summary": event.decision_summary,
        "created_at": event.created_at,
        "defer_reason_code": event.defer_reason_code,
        "related_memory_id": event.related_memory_id,
    }


def _write_event_from_payload(payload: dict[str, object]) -> MemoryWriteEvent:
    return MemoryWriteEvent(
        write_event_id=coerce_write_event_id(str(payload["write_event_id"])),
        candidate_id=str(payload["candidate_id"]),
        project_id=str(payload["project_id"]),
        write_outcome=str(payload["write_outcome"]),
        decision_summary=str(payload["decision_summary"]),
        created_at=str(payload["created_at"]),
        defer_reason_code=payload.get("defer_reason_code"),  # type: ignore[arg-type]
        related_memory_id=payload.get("related_memory_id"),  # type: ignore[arg-type]
    )


def _retrieval_event_to_payload(event: MemoryRetrievalEvent) -> dict[str, object]:
    return {
        "retrieval_event_id": str(event.retrieval_event_id),
        "project_id": event.project_id,
        "purpose": event.purpose,
        "returned_count": event.returned_count,
        "explicit_hit_count": event.explicit_hit_count,
        "lexical_hit_count": event.lexical_hit_count,
        "semantic_hit_count": event.semantic_hit_count,
        "contradiction_count": event.contradiction_count,
        "created_at": event.created_at,
    }


def _retrieval_event_from_payload(payload: dict[str, object]) -> MemoryRetrievalEvent:
    return MemoryRetrievalEvent(
        retrieval_event_id=coerce_retrieval_event_id(str(payload["retrieval_event_id"])),
        project_id=str(payload["project_id"]),
        purpose=str(payload["purpose"]),
        returned_count=int(payload["returned_count"]),
        explicit_hit_count=int(payload["explicit_hit_count"]),
        lexical_hit_count=int(payload["lexical_hit_count"]),
        semantic_hit_count=int(payload["semantic_hit_count"]),
        contradiction_count=int(payload["contradiction_count"]),
        created_at=str(payload["created_at"]),
    )


def _maintenance_job_to_payload(job: MaintenanceJobRecord) -> dict[str, object]:
    return {
        "job_id": str(job.job_id),
        "job_type": job.job_type,
        "project_id": job.project_id,
        "job_status": job.job_status,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
        "details": dict(job.details),
    }


def _maintenance_job_from_payload(payload: dict[str, object]) -> MaintenanceJobRecord:
    return MaintenanceJobRecord(
        job_id=coerce_maintenance_job_id(str(payload["job_id"])),
        job_type=str(payload["job_type"]),
        project_id=str(payload["project_id"]),
        job_status=str(payload["job_status"]),
        created_at=str(payload["created_at"]),
        updated_at=str(payload["updated_at"]),
        details=dict(payload.get("details", {})),
    )


def _vec_norm(vector: list[float]) -> float:
    return math.sqrt(sum(value * value for value in vector))


def _cosine_similarity(a: list[float], a_norm: float, b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    b_norm = _vec_norm(b)
    if b_norm == 0.0:
        return 0.0
    dot = sum(left * right for left, right in zip(a, b))
    return dot / (a_norm * b_norm)