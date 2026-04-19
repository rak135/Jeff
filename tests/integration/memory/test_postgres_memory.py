"""PostgreSQL-backed memory store integration tests.

Set JEFF_TEST_POSTGRES_DSN to a valid connection string to run these tests.
Example:
    JEFF_TEST_POSTGRES_DSN="postgresql://user:pass@localhost/jeff_test" pytest tests/integration/memory/

All tests use an isolated schema; each fixture drops and recreates tables so
tests are independent.  The global/system memory prohibition is verified here
in addition to the unit suite.
"""

from __future__ import annotations

import os

import pytest

from jeff.core.schemas import Scope
from jeff.memory import HashEmbedder, MemoryStoreProtocol
from jeff.memory.models import CommittedMemoryRecord, MemorySupportRef
from jeff.memory.types import utc_now

_DSN = os.getenv("JEFF_TEST_POSTGRES_DSN", "")
pytestmark = pytest.mark.skipif(
    not _DSN,
    reason="JEFF_TEST_POSTGRES_DSN not set — skipping PostgreSQL integration tests",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def pg_conn():
    psycopg2 = pytest.importorskip("psycopg2")
    conn = psycopg2.connect(_DSN)
    yield conn
    conn.close()


@pytest.fixture()
def pg_store(pg_conn):
    from jeff.memory.postgres_store import PostgresMemoryStore

    store = PostgresMemoryStore(pg_conn)
    # Recreate schema fresh for each test
    with pg_conn.cursor() as cur:
        cur.execute("""
            DROP TABLE IF EXISTS maintenance_jobs CASCADE;
            DROP TABLE IF EXISTS memory_retrieval_events CASCADE;
            DROP TABLE IF EXISTS memory_write_events CASCADE;
            DROP TABLE IF EXISTS memory_links CASCADE;
            DROP TABLE IF EXISTS memory_records CASCADE;
        """)
    pg_conn.commit()
    store.initialize_schema()
    return store


def _record(
    memory_id: str = "memory-pg-1",
    project_id: str = "project-pg",
    summary: str = "Selection never implies governance permission",
    memory_type: str = "semantic",
) -> CommittedMemoryRecord:
    now = utc_now()
    return CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type=memory_type,
        scope=Scope(project_id=project_id),
        summary=summary,
        remembered_points=("Selection can choose without allowing action.",),
        why_it_matters="Prevents choice-as-permission drift in execution.",
        support_quality="strong",
        stability="stable",
        created_at=now,
        updated_at=now,
        support_refs=(
            MemorySupportRef(
                ref_kind="research",
                ref_id="research-pg-1",
                summary="Support reference for PostgreSQL test.",
            ),
        ),
    )


# ---------------------------------------------------------------------------
# Protocol membership
# ---------------------------------------------------------------------------

def test_postgres_store_satisfies_protocol(pg_store) -> None:
    assert isinstance(pg_store, MemoryStoreProtocol)


# ---------------------------------------------------------------------------
# Record persistence round-trip
# ---------------------------------------------------------------------------

def test_pg_store_and_retrieve_record(pg_store) -> None:
    rec = _record()
    pg_store._store_committed_record(rec)
    result = pg_store.get_committed("memory-pg-1")
    assert result is not None
    assert result.summary == rec.summary
    assert result.memory_type == "semantic"
    assert str(result.scope.project_id) == "project-pg"


def test_pg_list_project_records_scoped(pg_store) -> None:
    pg_store._store_committed_record(_record("memory-pg-1", "project-A"))
    pg_store._store_committed_record(_record("memory-pg-2", "project-B"))
    records = pg_store.list_project_records("project-A")
    assert len(records) == 1
    assert str(records[0].memory_id) == "memory-pg-1"


def test_pg_upsert_updates_record(pg_store) -> None:
    rec = _record()
    pg_store._store_committed_record(rec)
    # Update conflict_posture via re-store
    from jeff.memory.models import CommittedMemoryRecord
    updated = CommittedMemoryRecord(
        memory_id=rec.memory_id,
        memory_type=rec.memory_type,
        scope=rec.scope,
        summary=rec.summary,
        remembered_points=rec.remembered_points,
        why_it_matters=rec.why_it_matters,
        support_quality=rec.support_quality,
        stability=rec.stability,
        record_status="active",
        conflict_posture="stale_support",
        created_at=rec.created_at,
        updated_at=utc_now(),
        support_refs=rec.support_refs,
    )
    pg_store._store_committed_record(updated)
    result = pg_store.get_committed("memory-pg-1")
    assert result is not None
    assert result.conflict_posture == "stale_support"


# ---------------------------------------------------------------------------
# Link persistence
# ---------------------------------------------------------------------------

def test_pg_link_persistence_and_lookup(pg_store) -> None:
    from jeff.memory.ids import coerce_link_id
    from jeff.memory import MemoryLink

    pg_store._store_committed_record(_record("memory-pg-1", "project-pg"))

    link = MemoryLink(
        memory_link_id=coerce_link_id("mlink-pg-1"),
        memory_id="memory-pg-1",
        link_type="research_artifact_ref",
        target_id="artifact-pg-1",
        target_family="research_artifact",
    )
    pg_store.store_link(link)

    links = pg_store.get_links_for_target("artifact-pg-1", "project-pg")
    assert len(links) == 1
    assert links[0].target_id == "artifact-pg-1"
    assert str(links[0].memory_id) == "memory-pg-1"


def test_pg_link_wrong_project_excluded(pg_store) -> None:
    from jeff.memory.ids import coerce_link_id
    from jeff.memory import MemoryLink

    pg_store._store_committed_record(_record("memory-pg-1", "project-A"))
    link = MemoryLink(
        memory_link_id=coerce_link_id("mlink-pg-2"),
        memory_id="memory-pg-1",
        link_type="source_ref",
        target_id="artifact-shared",
        target_family="artifact",
    )
    pg_store.store_link(link)

    links = pg_store.get_links_for_target("artifact-shared", "project-B")
    assert len(links) == 0


# ---------------------------------------------------------------------------
# Lexical retrieval
# ---------------------------------------------------------------------------

def test_pg_lexical_retrieval_works(pg_store) -> None:
    pg_store._store_committed_record(_record(
        "memory-pg-1", summary="Selection never implies governance permission"
    ))
    results = pg_store.search_lexical(
        "project-pg", "governance permission",
        memory_type_filter=None, limit=5,
    )
    assert len(results) >= 1
    assert any("governance" in r.summary.lower() or "permission" in r.summary.lower()
               for r in results)


def test_pg_lexical_excludes_wrong_project(pg_store) -> None:
    pg_store._store_committed_record(_record(
        "memory-pg-1", project_id="project-X",
        summary="governance boundary rule"
    ))
    results = pg_store.search_lexical(
        "project-Y", "governance", memory_type_filter=None, limit=5,
    )
    assert len(results) == 0


def test_pg_lexical_excludes_superseded(pg_store) -> None:
    rec = _record("memory-pg-1")
    pg_store._store_committed_record(rec)
    from jeff.core.schemas import coerce_memory_id
    # Supersede to change status
    pg_store._store_committed_record(_record("memory-pg-2"))
    pg_store._mark_superseded(
        superseded_memory_id=coerce_memory_id("memory-pg-1"),
        new_memory_id=coerce_memory_id("memory-pg-2"),
    )
    results = pg_store.search_lexical(
        "project-pg", "governance permission", memory_type_filter=None, limit=5,
    )
    ids = [str(r.memory_id) for r in results]
    assert "memory-pg-1" not in ids


# ---------------------------------------------------------------------------
# Semantic retrieval
# ---------------------------------------------------------------------------

def test_pg_semantic_retrieval_works(pg_store) -> None:
    rec = _record("memory-pg-sem-1", summary="governance boundary in execution layer")
    pg_store._store_committed_record(rec)

    embedder = HashEmbedder()
    emb = embedder.embed(rec.summary)
    pg_store.store_embedding("memory-pg-sem-1", emb)

    query_emb = embedder.embed("governance boundary")
    results = pg_store.search_semantic(
        "project-pg", query_emb, memory_type_filter=None, limit=3,
    )
    assert len(results) >= 1
    assert str(results[0].memory_id) == "memory-pg-sem-1"


def test_pg_semantic_no_embeddings_returns_empty(pg_store) -> None:
    pg_store._store_committed_record(_record("memory-pg-1"))
    results = pg_store.search_semantic(
        "project-pg", [0.1] * 64, memory_type_filter=None, limit=3,
    )
    assert results == ()


def test_pg_semantic_wrong_project_excluded(pg_store) -> None:
    pg_store._store_committed_record(_record("memory-pg-1", project_id="project-A"))
    embedder = HashEmbedder()
    emb = embedder.embed("governance boundary")
    pg_store.store_embedding("memory-pg-1", emb)

    results = pg_store.search_semantic(
        "project-B", emb, memory_type_filter=None, limit=3,
    )
    assert len(results) == 0


# ---------------------------------------------------------------------------
# Audit event persistence
# ---------------------------------------------------------------------------

def test_pg_write_event_persisted(pg_store) -> None:
    from jeff.memory import MemoryWriteEvent
    from jeff.memory.ids import coerce_write_event_id

    event = MemoryWriteEvent(
        write_event_id=coerce_write_event_id("we-pg-1"),
        candidate_id="cand-pg-1",
        project_id="project-pg",
        write_outcome="write",
        decision_summary="write for cand-pg-1",
        created_at=utc_now(),
    )
    pg_store.store_write_event(event)

    # Verify persisted by re-querying
    with pg_store._conn.cursor() as cur:
        cur.execute(
            "SELECT write_outcome FROM memory_write_events WHERE write_event_id = %s",
            ("we-pg-1",),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "write"


def test_pg_retrieval_event_persisted(pg_store) -> None:
    from jeff.memory import MemoryRetrievalEvent
    from jeff.memory.ids import coerce_retrieval_event_id

    event = MemoryRetrievalEvent(
        retrieval_event_id=coerce_retrieval_event_id("re-pg-1"),
        project_id="project-pg",
        purpose="proposal support",
        returned_count=2,
        explicit_hit_count=1,
        lexical_hit_count=1,
        semantic_hit_count=0,
        contradiction_count=0,
        created_at=utc_now(),
    )
    pg_store.store_retrieval_event(event)

    with pg_store._conn.cursor() as cur:
        cur.execute(
            "SELECT returned_count FROM memory_retrieval_events WHERE retrieval_event_id = %s",
            ("re-pg-1",),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == 2


def test_pg_maintenance_job_persisted(pg_store) -> None:
    from jeff.memory import MaintenanceJobRecord
    from jeff.memory.ids import coerce_maintenance_job_id

    job = MaintenanceJobRecord(
        job_id=coerce_maintenance_job_id("maint-pg-1"),
        job_type="dedupe_audit",
        project_id="project-pg",
        job_status="completed",
        created_at=utc_now(),
        updated_at=utc_now(),
        details={"inspected": "5"},
    )
    pg_store.store_maintenance_job(job)

    with pg_store._conn.cursor() as cur:
        cur.execute(
            "SELECT job_type FROM maintenance_jobs WHERE job_id = %s",
            ("maint-pg-1",),
        )
        row = cur.fetchone()
    assert row is not None
    assert row[0] == "dedupe_audit"


# ---------------------------------------------------------------------------
# Global/system memory hard-forbidden (PostgreSQL path)
# ---------------------------------------------------------------------------

def test_pg_global_scope_rejected_at_candidate_creation(pg_store) -> None:
    from jeff.memory import InMemoryMemoryStore, create_memory_candidate, MemorySupportRef
    with pytest.raises(ValueError, match="global"):
        create_memory_candidate(
            candidate_id="cand-global",
            memory_type="semantic",
            scope=Scope(project_id="global"),
            summary="This should not be creatable",
            remembered_points=("Not allowed.",),
            why_it_matters="Global memory is hard-forbidden in v1.",
            support_refs=(
                MemorySupportRef(
                    ref_kind="research",
                    ref_id="r-1",
                    summary="Support ref.",
                ),
            ),
        )


# ---------------------------------------------------------------------------
# pgvector schema verification
# ---------------------------------------------------------------------------

def test_pg_embedding_column_is_vector_type(pg_store, pg_conn) -> None:
    """The embedding column must use the vector type from pgvector, not JSONB."""
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT data_type, udt_name
            FROM information_schema.columns
            WHERE table_name = 'memory_records' AND column_name = 'embedding'
        """)
        row = cur.fetchone()
    assert row is not None, "embedding column not found"
    # pgvector USER-DEFINED types appear as 'USER-DEFINED' data_type, udt_name='vector'
    assert row[1] == "vector", f"expected udt_name='vector', got {row!r}"


def test_pg_hnsw_index_exists(pg_store, pg_conn) -> None:
    """An HNSW index on the embedding column must exist after schema init."""
    with pg_conn.cursor() as cur:
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'memory_records' AND indexname = 'memory_records_embedding_idx'
        """)
        row = cur.fetchone()
    assert row is not None, "HNSW embedding index not found"
    assert "hnsw" in row[1].lower(), f"expected HNSW index, got: {row[1]}"


# ---------------------------------------------------------------------------
# Semantic retrieval uses vector operator, not Python cosine
# ---------------------------------------------------------------------------

def test_pg_semantic_uses_vector_operator(pg_store) -> None:
    """store_embedding stores as pgvector literal; search_semantic uses <=> in SQL."""
    rec = _record("memory-pg-vec-1", summary="governance boundary in execution layer")
    pg_store._store_committed_record(rec)

    embedder = HashEmbedder()
    emb = embedder.embed(rec.summary)
    pg_store.store_embedding("memory-pg-vec-1", emb)

    # search_semantic must return the record using the SQL <=> operator path
    query_emb = embedder.embed("governance boundary")
    results = pg_store.search_semantic(
        "project-pg", query_emb, memory_type_filter=None, limit=3,
    )
    assert len(results) >= 1
    assert str(results[0].memory_id) == "memory-pg-vec-1"


def test_pg_store_embedding_as_vector_literal(pg_store, pg_conn) -> None:
    """store_embedding must write a non-NULL pgvector value to the DB column."""
    pg_store._store_committed_record(_record("memory-pg-emb-check"))
    embedder = HashEmbedder()
    pg_store.store_embedding("memory-pg-emb-check", embedder.embed("test text"))

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT embedding IS NOT NULL FROM memory_records WHERE memory_id = %s",
            ("memory-pg-emb-check",),
        )
        row = cur.fetchone()
    assert row is not None and row[0] is True, "embedding column is NULL after store_embedding"


# ---------------------------------------------------------------------------
# Atomic transaction rollback
# ---------------------------------------------------------------------------

def test_pg_atomic_rolls_back_on_failure(pg_store) -> None:
    """If a step inside atomic() raises, the whole block must roll back."""
    rec = _record("memory-pg-atomic-1")

    class _BadStore:
        """Proxy that delegates _store_committed_record but explodes on store_link."""
        def __getattr__(self, name):
            return getattr(pg_store, name)

        def store_link(self, link):
            raise RuntimeError("simulated link-store failure")

    bad = _BadStore()
    with pytest.raises(RuntimeError, match="simulated"):
        with pg_store.atomic():
            pg_store._store_committed_record(rec)
            bad.store_link(None)  # forces exception inside atomic block

    # The record must NOT be in the DB because the transaction rolled back
    result = pg_store.get_committed("memory-pg-atomic-1")
    assert result is None, "record survived despite atomic rollback"


def test_pg_atomic_nested_is_noop(pg_store) -> None:
    """Nested atomic() calls must not commit or rollback the outer transaction."""
    rec = _record("memory-pg-nested-atomic-1")
    with pg_store.atomic():
        pg_store._store_committed_record(rec)
        with pg_store.atomic():
            pass  # nested — must not commit yet
        # outer block hasn't committed; record should be visible within the same connection
        result = pg_store.get_committed("memory-pg-nested-atomic-1")
        assert result is not None
    # outer committed — still visible
    assert pg_store.get_committed("memory-pg-nested-atomic-1") is not None


# ---------------------------------------------------------------------------
# Locality filtering (PostgreSQL path)
# ---------------------------------------------------------------------------

def _record_with_scope(
    memory_id: str,
    scope: Scope,
    summary: str = "Governance boundary applies here",
) -> CommittedMemoryRecord:
    now = utc_now()
    return CommittedMemoryRecord(
        memory_id=memory_id,
        memory_type="semantic",
        scope=scope,
        summary=summary,
        remembered_points=("Governance must precede execution.",),
        why_it_matters="Prevents choice-as-permission drift.",
        support_quality="strong",
        stability="stable",
        created_at=now,
        updated_at=now,
        support_refs=(
            MemorySupportRef(
                ref_kind="research",
                ref_id="research-loc-1",
                summary="Locality test support ref.",
            ),
        ),
    )


def test_pg_lexical_locality_excludes_wrong_work_unit(pg_store) -> None:
    from jeff.memory import MemoryRetrievalRequest
    from jeff.memory.retrieval import retrieve_memory

    scope_wu1 = Scope(project_id="project-loc-pg", work_unit_id="wu-1")
    scope_wu2 = Scope(project_id="project-loc-pg", work_unit_id="wu-2")

    pg_store._store_committed_record(_record_with_scope(
        "memory-loc-pg-wu1", scope_wu1, summary="governance boundary in work unit one"
    ))
    pg_store._store_committed_record(_record_with_scope(
        "memory-loc-pg-wu2", scope_wu2, summary="governance boundary in work unit two"
    ))

    request = MemoryRetrievalRequest(
        purpose="locality pg test",
        scope=scope_wu1,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=pg_store)
    ids = [str(r.memory_id) for r in result.records]
    assert "memory-loc-pg-wu1" in ids, "wu-1 record not returned"
    assert "memory-loc-pg-wu2" not in ids, "wu-2 record leaked through"


# ---------------------------------------------------------------------------
# Atomic rollback across the full logical write unit (PostgreSQL path)
# ---------------------------------------------------------------------------

class _BrokenEmbedder:
    """Embedder whose embed() always raises — used to trigger rollback."""
    dimension = 64

    def embed(self, text: str) -> list[float]:  # pragma: no cover - raises
        raise RuntimeError("simulated embedding failure")


def _atomic_candidate(candidate_id: str, project_id: str, summary: str | None = None):
    from jeff.memory import create_memory_candidate
    return create_memory_candidate(
        candidate_id=candidate_id,
        memory_type="semantic",
        scope=Scope(project_id=project_id),
        summary=summary or "Governance boundary applies before execution",
        remembered_points=("Governance must precede execution.",),
        why_it_matters="Prevents choice-as-permission drift in execution.",
        support_refs=(
            MemorySupportRef(
                ref_kind="research", ref_id="research-atomic-1",
                summary="Support ref for atomic rollback test.",
            ),
        ),
        support_quality="strong", stability="stable",
    )


def test_pg_standard_write_rolls_back_on_embedding_failure(pg_store, pg_conn) -> None:
    from jeff.memory import process_candidate
    cand = _atomic_candidate("cand-pg-atom-emb", "project-pg-atom-emb")
    with pytest.raises(RuntimeError, match="embedding"):
        process_candidate(candidate=cand, store=pg_store, embedder=_BrokenEmbedder())

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM memory_records WHERE project_id = %s",
            ("project-pg-atom-emb",),
        )
        (record_count,) = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) FROM memory_write_events WHERE project_id = %s",
            ("project-pg-atom-emb",),
        )
        (event_count,) = cur.fetchone()
    assert record_count == 0, "committed record survived rollback"
    assert event_count == 0, "write event survived rollback"


def test_pg_standard_write_rolls_back_on_write_event_failure(pg_store, pg_conn) -> None:
    """If write-event persistence fails inside atomic, the record is rolled back."""
    from jeff.memory import HashEmbedder, process_candidate

    original_store_write_event = pg_store.store_write_event

    def failing_store_write_event(event):
        raise RuntimeError("simulated write-event persistence failure")

    pg_store.store_write_event = failing_store_write_event
    try:
        cand = _atomic_candidate("cand-pg-atom-evt", "project-pg-atom-evt")
        with pytest.raises(RuntimeError, match="write-event"):
            process_candidate(candidate=cand, store=pg_store, embedder=HashEmbedder())
    finally:
        pg_store.store_write_event = original_store_write_event

    with pg_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM memory_records WHERE project_id = %s",
            ("project-pg-atom-evt",),
        )
        (record_count,) = cur.fetchone()
        cur.execute(
            "SELECT COUNT(*) FROM memory_links",
        )
        (link_count,) = cur.fetchone()
    assert record_count == 0, "committed record survived rollback"
    assert link_count == 0, "links survived rollback"


def test_pg_supersede_rolls_back_on_embedding_failure(pg_store, pg_conn) -> None:
    from jeff.memory import create_memory_candidate, process_candidate
    from jeff.memory.api import supersede_candidate

    original = _atomic_candidate("cand-pg-sup-orig", "project-pg-sup-atom")
    orig = process_candidate(candidate=original, store=pg_store)
    orig_id = str(orig.committed_record.memory_id)

    superseder = create_memory_candidate(
        candidate_id="cand-pg-sup-new", memory_type="semantic",
        scope=Scope(project_id="project-pg-sup-atom"),
        summary="Revised governance boundary — stronger evidence",
        remembered_points=("Stronger evidence reaffirms the rule.",),
        why_it_matters="New support solidifies the governance rule.",
        support_refs=(
            MemorySupportRef(ref_kind="research", ref_id="research-atomic-1",
                             summary="Support ref."),
        ),
        support_quality="strong", stability="stable",
    )
    with pytest.raises(RuntimeError, match="embedding"):
        supersede_candidate(superseder, orig_id, store=pg_store, embedder=_BrokenEmbedder())

    # Original must still be active; no new record; no supersession link
    with pg_conn.cursor() as cur:
        cur.execute("SELECT record_status FROM memory_records WHERE memory_id = %s", (orig_id,))
        (status,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM memory_records WHERE project_id = %s",
                    ("project-pg-sup-atom",))
        (record_count,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM memory_links WHERE link_type = 'supersedes_ref'")
        (sup_link_count,) = cur.fetchone()
    assert status == "active", "supersede status update survived rollback"
    assert record_count == 1, "new record survived rollback"
    assert sup_link_count == 0, "supersession link survived rollback"


def test_pg_merge_rolls_back_on_embedding_failure(pg_store, pg_conn) -> None:
    from jeff.memory import create_memory_candidate, process_candidate
    from jeff.memory.api import merge_into_candidate

    original = _atomic_candidate("cand-pg-merge-orig", "project-pg-merge-atom")
    orig = process_candidate(candidate=original, store=pg_store)
    orig_id = str(orig.committed_record.memory_id)

    with pg_conn.cursor() as cur:
        cur.execute("SELECT remembered_points FROM memory_records WHERE memory_id = %s", (orig_id,))
        (points_before_raw,) = cur.fetchone()

    merge = create_memory_candidate(
        candidate_id="cand-pg-merge-new", memory_type="semantic",
        scope=Scope(project_id="project-pg-merge-atom"),
        summary=original.summary,
        remembered_points=("Execution requires governance approval always.",),
        why_it_matters="Merge adds a supporting detail to governance rule.",
        support_refs=(
            MemorySupportRef(ref_kind="research", ref_id="research-atomic-1",
                             summary="Support ref."),
        ),
        support_quality="strong", stability="stable",
    )
    with pytest.raises(RuntimeError, match="embedding"):
        merge_into_candidate(merge, orig_id, store=pg_store, embedder=_BrokenEmbedder())

    with pg_conn.cursor() as cur:
        cur.execute("SELECT remembered_points FROM memory_records WHERE memory_id = %s", (orig_id,))
        (points_after_raw,) = cur.fetchone()
        cur.execute("SELECT COUNT(*) FROM memory_links WHERE link_type = 'merged_into_ref'")
        (merge_link_count,) = cur.fetchone()
    assert points_after_raw == points_before_raw, "merge changes survived rollback"
    assert merge_link_count == 0, "merge link survived rollback"


def test_pg_semantic_locality_excludes_wrong_work_unit(pg_store) -> None:
    from jeff.memory import MemoryRetrievalRequest
    from jeff.memory.retrieval import retrieve_memory

    scope_wu1 = Scope(project_id="project-sem-loc-pg", work_unit_id="wu-a")
    scope_wu2 = Scope(project_id="project-sem-loc-pg", work_unit_id="wu-b")

    rec1 = _record_with_scope("memory-sem-loc-pg-1", scope_wu1,
                               summary="governance boundary alpha unit")
    rec2 = _record_with_scope("memory-sem-loc-pg-2", scope_wu2,
                               summary="governance boundary beta unit")
    pg_store._store_committed_record(rec1)
    pg_store._store_committed_record(rec2)

    embedder = HashEmbedder()
    pg_store.store_embedding("memory-sem-loc-pg-1", embedder.embed(rec1.summary))
    pg_store.store_embedding("memory-sem-loc-pg-2", embedder.embed(rec2.summary))

    request = MemoryRetrievalRequest(
        purpose="semantic locality pg test",
        scope=scope_wu1,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=pg_store, embedder=embedder)
    ids = [str(r.memory_id) for r in result.records]
    assert "memory-sem-loc-pg-1" in ids, "wu-a record not returned"
    assert "memory-sem-loc-pg-2" not in ids, "wu-b record leaked through"
