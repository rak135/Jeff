"""Store contract tests: verifies MemoryStoreProtocol compliance for InMemoryMemoryStore.

These tests define the behaviour contract that every MemoryStoreProtocol implementation
must satisfy.  The same assertions run against PostgresMemoryStore in the integration
test suite; keeping them here ensures the in-memory store never diverges from the contract.
"""

from __future__ import annotations

import pytest

from jeff.core.schemas import Scope
from jeff.memory import (
    CommittedMemoryRecord,
    HashEmbedder,
    InMemoryMemoryStore,
    MemoryLink,
    MemoryRetrievalEvent,
    MemoryStoreProtocol,
    MemoryWriteEvent,
    MaintenanceJobRecord,
)
from jeff.memory.ids import (
    coerce_link_id,
    coerce_retrieval_event_id,
    coerce_write_event_id,
    coerce_maintenance_job_id,
)
from jeff.memory.types import utc_now


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _make_record(
    memory_id: str = "memory-1",
    project_id: str = "project-alpha",
    summary: str = "Selection never implies governance permission",
    memory_type: str = "semantic",
    record_status: str = "active",
) -> CommittedMemoryRecord:
    from jeff.memory.models import MemorySupportRef
    now = utc_now()
    return CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type=memory_type,
        scope=Scope(project_id=project_id),
        summary=summary,
        remembered_points=("Selection can choose a path without allowing action start.",),
        why_it_matters="This boundary protects execution from choice-as-permission drift.",
        support_quality="strong",
        stability="stable",
        record_status=record_status,
        created_at=now,
        updated_at=now,
        support_refs=(
            MemorySupportRef(
                ref_kind="research",
                ref_id="research-1",
                summary="Research support for this memory.",
            ),
        ),
    )


def _make_link(
    memory_id: str = "memory-1",
    target_id: str = "artifact-99",
) -> MemoryLink:
    return MemoryLink(
        memory_link_id=coerce_link_id("mlink-1"),
        memory_id=memory_id,
        link_type="research_artifact_ref",
        target_id=target_id,
        target_family="research_artifact",
    )


# ---------------------------------------------------------------------------
# Protocol membership
# ---------------------------------------------------------------------------

def test_in_memory_store_satisfies_protocol() -> None:
    store = InMemoryMemoryStore()
    assert isinstance(store, MemoryStoreProtocol)


# ---------------------------------------------------------------------------
# Record round-trip
# ---------------------------------------------------------------------------

def test_store_and_retrieve_record() -> None:
    store = InMemoryMemoryStore()
    record = _make_record()
    store._store_committed_record(record)
    result = store.get_committed("memory-1")
    assert result is not None
    assert result.summary == record.summary
    assert result.memory_type == "semantic"


def test_get_committed_returns_none_for_missing() -> None:
    store = InMemoryMemoryStore()
    assert store.get_committed("memory-999") is None


def test_list_project_records_scoped() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", "project-A"))
    store._store_committed_record(_make_record("memory-2", "project-B"))
    records = store.list_project_records("project-A")
    assert len(records) == 1
    assert str(records[0].memory_id) == "memory-1"


def test_list_project_records_sorted_by_id() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-10", "project-X"))
    store._store_committed_record(_make_record("memory-2", "project-X"))
    ids = [str(r.memory_id) for r in store.list_project_records("project-X")]
    assert ids == sorted(ids)


def test_allocate_memory_id_is_unique() -> None:
    store = InMemoryMemoryStore()
    ids = {str(store.allocate_memory_id()) for _ in range(10)}
    assert len(ids) == 10


def test_mark_superseded_sets_status() -> None:
    store = InMemoryMemoryStore()
    old = _make_record("memory-1")
    new = _make_record("memory-2")
    store._store_committed_record(old)
    store._store_committed_record(new)

    from jeff.core.schemas import coerce_memory_id
    store._mark_superseded(
        superseded_memory_id=coerce_memory_id("memory-1"),
        new_memory_id=coerce_memory_id("memory-2"),
    )
    updated = store.get_committed("memory-1")
    assert updated is not None
    assert updated.record_status == "superseded"
    assert updated.superseded_by_memory_id == "memory-2"


# ---------------------------------------------------------------------------
# Link persistence
# ---------------------------------------------------------------------------

def test_store_and_get_links_for_target() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", "project-alpha"))
    link = _make_link("memory-1", "artifact-99")
    store.store_link(link)

    links = store.get_links_for_target("artifact-99", "project-alpha")
    assert len(links) == 1
    assert links[0].target_id == "artifact-99"


def test_get_links_for_target_wrong_project_excluded() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", "project-A"))
    store.store_link(_make_link("memory-1", "artifact-1"))

    links = store.get_links_for_target("artifact-1", "project-B")
    assert len(links) == 0


def test_get_links_for_memory() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", "project-alpha"))
    link = _make_link("memory-1", "artifact-99")
    store.store_link(link)

    links = store.get_links_for_memory("memory-1")
    assert len(links) == 1


# ---------------------------------------------------------------------------
# Lexical search
# ---------------------------------------------------------------------------

def test_search_lexical_returns_matching_records() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record(
        "memory-1", summary="Selection never implies governance permission"
    ))
    results = store.search_lexical(
        "project-alpha", "governance permission",
        memory_type_filter=None, limit=5,
    )
    assert len(results) == 1
    assert str(results[0].memory_id) == "memory-1"


def test_search_lexical_excludes_wrong_project() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record(
        "memory-1", project_id="project-A",
        summary="governance token boundary",
    ))
    results = store.search_lexical(
        "project-B", "governance", memory_type_filter=None, limit=5,
    )
    assert len(results) == 0


def test_search_lexical_excludes_superseded() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record(
        "memory-1", record_status="superseded",
        summary="governance boundary rule",
    ))
    results = store.search_lexical(
        "project-alpha", "governance", memory_type_filter=None, limit=5,
    )
    assert len(results) == 0


def test_search_lexical_memory_type_filter() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", memory_type="semantic"))
    store._store_committed_record(_make_record("memory-2", memory_type="episodic", summary="governance boundary"))
    results = store.search_lexical(
        "project-alpha", "governance", memory_type_filter="episodic", limit=5,
    )
    assert all(r.memory_type == "episodic" for r in results)


# ---------------------------------------------------------------------------
# Semantic search
# ---------------------------------------------------------------------------

def test_search_semantic_returns_similar_records() -> None:
    store = InMemoryMemoryStore()
    record = _make_record("memory-1")
    store._store_committed_record(record)

    embedder = HashEmbedder()
    text = "Selection never implies governance permission"
    emb = embedder.embed(text)
    store.store_embedding("memory-1", emb)

    query_emb = embedder.embed("governance permission boundary")
    results = store.search_semantic(
        "project-alpha", query_emb, memory_type_filter=None, limit=3,
    )
    assert len(results) >= 1
    assert str(results[0].memory_id) == "memory-1"


def test_search_semantic_no_embeddings_returns_empty() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1"))
    # No embeddings stored — should degrade safely
    results = store.search_semantic(
        "project-alpha", [0.1] * 64, memory_type_filter=None, limit=3,
    )
    assert results == ()


def test_search_semantic_wrong_project_excluded() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(_make_record("memory-1", project_id="project-A"))
    embedder = HashEmbedder()
    emb = embedder.embed("governance boundary")
    store.store_embedding("memory-1", emb)

    results = store.search_semantic(
        "project-B", emb, memory_type_filter=None, limit=3,
    )
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Audit event persistence
# ---------------------------------------------------------------------------

def _make_write_event() -> MemoryWriteEvent:
    return MemoryWriteEvent(
        write_event_id=coerce_write_event_id("we-test-1"),
        candidate_id="cand-1",
        project_id="project-alpha",
        write_outcome="write",
        decision_summary="write for candidate cand-1",
        created_at=utc_now(),
    )


def _make_retrieval_event() -> MemoryRetrievalEvent:
    return MemoryRetrievalEvent(
        retrieval_event_id=coerce_retrieval_event_id("re-test-1"),
        project_id="project-alpha",
        purpose="proposal support",
        returned_count=1,
        explicit_hit_count=0,
        lexical_hit_count=1,
        semantic_hit_count=0,
        contradiction_count=0,
        created_at=utc_now(),
    )


def _make_maintenance_job() -> MaintenanceJobRecord:
    return MaintenanceJobRecord(
        job_id=coerce_maintenance_job_id("maint-test-1"),
        job_type="dedupe_audit",
        project_id="project-alpha",
        job_status="completed",
        created_at=utc_now(),
        updated_at=utc_now(),
    )


def test_store_write_event_persisted() -> None:
    store = InMemoryMemoryStore()
    event = _make_write_event()
    store.store_write_event(event)
    assert len(store._write_events) == 1
    assert store._write_events[0].write_outcome == "write"


def test_store_retrieval_event_persisted() -> None:
    store = InMemoryMemoryStore()
    event = _make_retrieval_event()
    store.store_retrieval_event(event)
    assert len(store._retrieval_events) == 1
    assert store._retrieval_events[0].purpose == "proposal support"


def test_store_maintenance_job_persisted() -> None:
    store = InMemoryMemoryStore()
    job = _make_maintenance_job()
    store.store_maintenance_job(job)
    assert len(store._maintenance_jobs) == 1
    assert store._maintenance_jobs[0].job_type == "dedupe_audit"
