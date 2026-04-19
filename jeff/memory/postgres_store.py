"""PostgreSQL-backed memory store implementing MemoryStoreProtocol.

Uses psycopg2 for synchronous PostgreSQL access.
FTS is provided by PostgreSQL's native tsvector/plainto_tsquery with a GIN index.
Semantic retrieval uses pgvector's <=> (cosine distance) operator with an HNSW index —
no Python-side similarity computation is performed for the PostgreSQL path.

Requires:
  - psycopg2-binary >= 2.9
  - PostgreSQL with the pgvector extension (CREATE EXTENSION vector)
    https://github.com/pgvector/pgvector  (>= 0.5.0 for HNSW index)

Transaction ownership:
  Every mutating method executes its SQL but only commits when _auto_commit is True
  (the default).  Call store.atomic() as a context manager to group multiple operations
  into one transaction.  On normal exit the context manager commits; on exception it
  rolls back, so no partial writes can survive a failure.

Usage:
    import psycopg2
    from jeff.memory.postgres_store import PostgresMemoryStore

    conn = psycopg2.connect("postgresql://user:pass@host/dbname")
    store = PostgresMemoryStore(conn)
    store.initialize_schema()   # idempotent — creates extension, tables, indexes

    # Atomic logical write:
    with store.atomic():
        store._store_committed_record(record)
        store.store_link(link1)
        store.store_link(link2)
    # Single commit on exit; full rollback if anything raised.
"""

from __future__ import annotations

import contextlib
import json
import uuid

from jeff.core.schemas import MemoryId, Scope, coerce_memory_id

from .models import CommittedMemoryRecord, MemorySupportRef

try:
    import psycopg2  # type: ignore[import]
    import psycopg2.extras  # type: ignore[import]
    _PSYCOPG2_AVAILABLE = True
except ImportError:
    _PSYCOPG2_AVAILABLE = False


def _make_schema_sql(embedding_dim: int) -> str:
    """Return the DDL for all memory tables, parameterised by embedding dimension.

    The embedding column is typed vector(N) for native pgvector storage and indexing.
    Re-running this on an existing database is safe (all statements use IF NOT EXISTS).
    """
    return f"""\
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS memory_records (
    memory_id               TEXT PRIMARY KEY,
    memory_type             TEXT NOT NULL,
    project_id              TEXT NOT NULL,
    work_unit_id            TEXT,
    run_id                  TEXT,
    summary                 TEXT NOT NULL,
    remembered_points       JSONB NOT NULL,
    why_it_matters          TEXT NOT NULL,
    support_quality         TEXT NOT NULL,
    stability               TEXT NOT NULL,
    record_status           TEXT NOT NULL DEFAULT 'active',
    conflict_posture        TEXT NOT NULL DEFAULT 'none',
    freshness_sensitivity   TEXT NOT NULL DEFAULT 'low',
    created_at              TEXT NOT NULL,
    updated_at              TEXT NOT NULL,
    created_from_run_id     TEXT,
    schema_version          TEXT NOT NULL DEFAULT '1.0',
    supersedes_memory_id    TEXT,
    superseded_by_memory_id TEXT,
    merged_into_memory_id   TEXT,
    support_refs            JSONB NOT NULL DEFAULT '[]',
    fts_vector              TSVECTOR,
    embedding               vector({embedding_dim})
);

CREATE INDEX IF NOT EXISTS memory_records_project_id_idx
    ON memory_records (project_id);

CREATE INDEX IF NOT EXISTS memory_records_fts_idx
    ON memory_records USING GIN (fts_vector);

-- HNSW index for approximate nearest-neighbour semantic search (pgvector >= 0.5.0).
-- cosine distance: ORDER BY embedding <=> query_vec (lower = more similar)
CREATE INDEX IF NOT EXISTS memory_records_embedding_idx
    ON memory_records USING hnsw (embedding vector_cosine_ops);

CREATE TABLE IF NOT EXISTS memory_links (
    link_id       TEXT PRIMARY KEY,
    memory_id     TEXT NOT NULL REFERENCES memory_records (memory_id),
    link_type     TEXT NOT NULL,
    target_id     TEXT NOT NULL,
    target_family TEXT NOT NULL,
    metadata      JSONB NOT NULL DEFAULT '{{}}'
);

CREATE INDEX IF NOT EXISTS memory_links_target_id_idx
    ON memory_links (target_id);
CREATE INDEX IF NOT EXISTS memory_links_memory_id_idx
    ON memory_links (memory_id);

CREATE TABLE IF NOT EXISTS memory_write_events (
    write_event_id    TEXT PRIMARY KEY,
    candidate_id      TEXT NOT NULL,
    project_id        TEXT NOT NULL,
    write_outcome     TEXT NOT NULL,
    decision_summary  TEXT NOT NULL,
    created_at        TEXT NOT NULL,
    defer_reason_code TEXT,
    related_memory_id TEXT
);

CREATE TABLE IF NOT EXISTS memory_retrieval_events (
    retrieval_event_id  TEXT PRIMARY KEY,
    project_id          TEXT NOT NULL,
    purpose             TEXT NOT NULL,
    returned_count      INTEGER NOT NULL,
    explicit_hit_count  INTEGER NOT NULL,
    lexical_hit_count   INTEGER NOT NULL,
    semantic_hit_count  INTEGER NOT NULL,
    contradiction_count INTEGER NOT NULL,
    created_at          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS maintenance_jobs (
    job_id     TEXT PRIMARY KEY,
    job_type   TEXT NOT NULL,
    project_id TEXT NOT NULL,
    job_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    details    JSONB NOT NULL DEFAULT '{{}}'
);
"""


class PostgresMemoryStore:
    """PostgreSQL-backed memory store.

    Transaction ownership
    ---------------------
    When _auto_commit is True (the default), each mutating method commits after
    its SQL executes.  Use atomic() to group a logical write into one transaction:

        with store.atomic():
            store._store_committed_record(record)
            store.store_link(link)
        # single commit here; rollback if anything raised

    Semantic retrieval
    ------------------
    Embeddings are stored in a pgvector vector(N) column.  search_semantic()
    delegates distance computation entirely to PostgreSQL via the <=> cosine
    distance operator and an HNSW index.  No Python-side row fetching or
    cosine computation is performed.

    Locality filtering
    ------------------
    Both search_lexical() and search_semantic() filter by project_id only.
    Callers (retrieve_memory in retrieval.py) apply _scope_matches() to enforce
    work_unit_id / run_id locality before results enter the candidate pool.
    """

    def __init__(self, conn, *, embedding_dim: int = 64) -> None:
        if not _PSYCOPG2_AVAILABLE:
            raise ImportError(
                "psycopg2 is required for PostgresMemoryStore; "
                "install it with: pip install psycopg2-binary"
            )
        self._conn = conn
        self._embedding_dim = embedding_dim
        self._auto_commit = True  # flipped to False inside atomic()

    def initialize_schema(self) -> None:
        """Create extension, tables, and indexes (idempotent).

        Raises RuntimeError if the pgvector extension is not installed on the server.
        """
        with self._conn.cursor() as cur:
            cur.execute(_make_schema_sql(self._embedding_dim))
        self._conn.commit()

    # ------------------------------------------------------------------ #
    # Transaction management                                               #
    # ------------------------------------------------------------------ #

    @contextlib.contextmanager
    def atomic(self):
        """Context manager for atomic logical write operations.

        Suspends per-method auto-commit.  On normal exit, commits the whole
        transaction.  On exception, rolls back cleanly so no partial writes
        survive a failure.

        Nested calls are supported: only the outermost atomic() commits/rolls back.
        """
        if not self._auto_commit:
            # Already inside an atomic block — inner block is a no-op
            yield
            return
        self._auto_commit = False
        try:
            yield
            self._conn.commit()
        except Exception:
            self._conn.rollback()
            raise
        finally:
            self._auto_commit = True

    def _commit_if_auto(self) -> None:
        if self._auto_commit:
            self._conn.commit()

    # ------------------------------------------------------------------ #
    # Record operations                                                    #
    # ------------------------------------------------------------------ #

    def allocate_memory_id(self) -> MemoryId:
        return coerce_memory_id(f"memory-{uuid.uuid4().hex[:12]}")

    def get_committed(self, memory_id: str) -> CommittedMemoryRecord | None:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM memory_records WHERE memory_id = %s",
                (memory_id,),
            )
            row = cur.fetchone()
            desc = cur.description
        if row is None:
            return None
        return _row_to_record(row, desc)

    def list_project_records(self, project_id: str) -> tuple[CommittedMemoryRecord, ...]:
        with self._conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM memory_records WHERE project_id = %s ORDER BY memory_id",
                (project_id,),
            )
            rows = cur.fetchall()
            desc = cur.description
        return tuple(_row_to_record(row, desc) for row in rows)

    def _store_committed_record(self, record: CommittedMemoryRecord) -> None:
        points_json = json.dumps(list(record.remembered_points))
        refs_json = json.dumps([
            {"ref_kind": r.ref_kind, "ref_id": r.ref_id, "summary": r.summary}
            for r in record.support_refs
        ])
        fts_text = " ".join([record.summary, record.why_it_matters, *record.remembered_points])
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_records (
                    memory_id, memory_type, project_id, work_unit_id, run_id,
                    summary, remembered_points, why_it_matters,
                    support_quality, stability, record_status, conflict_posture,
                    freshness_sensitivity, created_at, updated_at,
                    created_from_run_id, schema_version,
                    supersedes_memory_id, superseded_by_memory_id, merged_into_memory_id,
                    support_refs, fts_vector
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s::jsonb, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s::jsonb, to_tsvector('english', %s)
                )
                ON CONFLICT (memory_id) DO UPDATE SET
                    summary                 = EXCLUDED.summary,
                    remembered_points       = EXCLUDED.remembered_points,
                    why_it_matters          = EXCLUDED.why_it_matters,
                    support_quality         = EXCLUDED.support_quality,
                    stability               = EXCLUDED.stability,
                    record_status           = EXCLUDED.record_status,
                    conflict_posture        = EXCLUDED.conflict_posture,
                    freshness_sensitivity   = EXCLUDED.freshness_sensitivity,
                    updated_at              = EXCLUDED.updated_at,
                    created_from_run_id     = EXCLUDED.created_from_run_id,
                    supersedes_memory_id    = EXCLUDED.supersedes_memory_id,
                    superseded_by_memory_id = EXCLUDED.superseded_by_memory_id,
                    merged_into_memory_id   = EXCLUDED.merged_into_memory_id,
                    support_refs            = EXCLUDED.support_refs,
                    fts_vector              = EXCLUDED.fts_vector
                """,
                (
                    str(record.memory_id), record.memory_type,
                    str(record.scope.project_id),
                    str(record.scope.work_unit_id) if record.scope.work_unit_id else None,
                    str(record.scope.run_id) if record.scope.run_id else None,
                    record.summary, points_json, record.why_it_matters,
                    record.support_quality, record.stability, record.record_status,
                    record.conflict_posture,
                    record.freshness_sensitivity, record.created_at, record.updated_at,
                    record.created_from_run_id, record.schema_version,
                    record.supersedes_memory_id, record.superseded_by_memory_id,
                    record.merged_into_memory_id,
                    refs_json, fts_text,
                ),
            )
        self._commit_if_auto()

    def _mark_superseded(self, *, superseded_memory_id: MemoryId, new_memory_id: MemoryId) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                UPDATE memory_records
                SET record_status = 'superseded', superseded_by_memory_id = %s
                WHERE memory_id = %s
                """,
                (str(new_memory_id), str(superseded_memory_id)),
            )
        self._commit_if_auto()

    # ------------------------------------------------------------------ #
    # Link operations                                                      #
    # ------------------------------------------------------------------ #

    def store_link(self, link) -> None:
        meta_json = json.dumps(dict(link.metadata) if link.metadata else {})
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_links
                    (link_id, memory_id, link_type, target_id, target_family, metadata)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (link_id) DO NOTHING
                """,
                (
                    str(link.memory_link_id), str(link.memory_id),
                    link.link_type, link.target_id, link.target_family, meta_json,
                ),
            )
        self._commit_if_auto()

    def get_links_for_target(self, target_id: str, project_id: str) -> tuple:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT ml.link_id, ml.memory_id, ml.link_type,
                       ml.target_id, ml.target_family, ml.metadata
                FROM memory_links ml
                JOIN memory_records mr ON ml.memory_id = mr.memory_id
                WHERE ml.target_id = %s AND mr.project_id = %s
                """,
                (target_id, project_id),
            )
            rows = cur.fetchall()
        return tuple(_row_to_link(row) for row in rows)

    def get_links_for_memory(self, memory_id: str) -> tuple:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                SELECT link_id, memory_id, link_type, target_id, target_family, metadata
                FROM memory_links WHERE memory_id = %s
                """,
                (memory_id,),
            )
            rows = cur.fetchall()
        return tuple(_row_to_link(row) for row in rows)

    # ------------------------------------------------------------------ #
    # Retrieval search                                                     #
    # ------------------------------------------------------------------ #

    def search_lexical(
        self,
        project_id: str,
        query: str,
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Full-text search using PostgreSQL plainto_tsquery (English dictionary).

        Filters by project_id and active status only.  Callers are responsible for
        applying work_unit_id / run_id locality filtering on the returned records.
        """
        if not query.strip():
            return ()

        type_clause = "AND memory_type = %s" if memory_type_filter else ""
        # Parameter order must match %s positions in the SQL string:
        # 1: query (for ts_rank)  2: project_id  3: query (for @@ match)
        # [optional 4: memory_type_filter]  final: limit
        if memory_type_filter:
            exec_params = [query, project_id, query, memory_type_filter, limit]
        else:
            exec_params = [query, project_id, query, limit]

        sql = f"""
            SELECT *,
                   ts_rank(fts_vector, plainto_tsquery('english', %s)) AS _rank
            FROM memory_records
            WHERE project_id = %s
              AND record_status = 'active'
              AND fts_vector @@ plainto_tsquery('english', %s)
              {type_clause}
            ORDER BY _rank DESC
            LIMIT %s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, exec_params)
            rows = cur.fetchall()
            desc = cur.description

        # Strip the synthetic _rank column so _row_to_record receives clean columns
        rank_idx = [d[0] for d in desc].index("_rank")
        clean_rows = [row[:rank_idx] + row[rank_idx + 1:] for row in rows]
        clean_desc = [d for d in desc if d[0] != "_rank"]
        return tuple(_row_to_record(row, clean_desc) for row in clean_rows)

    def search_semantic(
        self,
        project_id: str,
        query_embedding: list[float],
        *,
        memory_type_filter: str | None,
        limit: int,
    ) -> tuple[CommittedMemoryRecord, ...]:
        """Cosine similarity search using pgvector's <=> operator.

        Distance computation and ordering happen entirely inside PostgreSQL via the
        HNSW index on the embedding column.  No Python-side similarity computation
        is performed.

        Filters by project_id and active status only.  Callers are responsible for
        applying work_unit_id / run_id locality filtering on the returned records.
        """
        if not query_embedding:
            return ()

        # Format the query vector as a pgvector literal: [f1,f2,...,fN]
        vec_str = "[" + ",".join(str(float(x)) for x in query_embedding) + "]"

        type_clause = "AND memory_type = %s" if memory_type_filter else ""
        # Parameter order: project_id, [memory_type,] vec_str (for ORDER BY), limit
        if memory_type_filter:
            exec_params = [project_id, memory_type_filter, vec_str, limit]
        else:
            exec_params = [project_id, vec_str, limit]

        sql = f"""
            SELECT *
            FROM memory_records
            WHERE project_id = %s
              AND record_status = 'active'
              AND embedding IS NOT NULL
              {type_clause}
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with self._conn.cursor() as cur:
            cur.execute(sql, exec_params)
            rows = cur.fetchall()
            desc = cur.description

        return tuple(_row_to_record(row, desc) for row in rows)

    def store_embedding(self, memory_id: str, embedding: list[float]) -> None:
        """Store a vector embedding for a committed record.

        The embedding is stored as a pgvector vector(N) value, enabling native
        distance computation in search_semantic().
        """
        vec_str = "[" + ",".join(str(float(x)) for x in embedding) + "]"
        with self._conn.cursor() as cur:
            cur.execute(
                "UPDATE memory_records SET embedding = %s::vector WHERE memory_id = %s",
                (vec_str, memory_id),
            )
        self._commit_if_auto()

    # ------------------------------------------------------------------ #
    # Audit / event operations                                             #
    # ------------------------------------------------------------------ #

    def store_write_event(self, event) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_write_events
                    (write_event_id, candidate_id, project_id, write_outcome,
                     decision_summary, created_at, defer_reason_code, related_memory_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (write_event_id) DO NOTHING
                """,
                (
                    str(event.write_event_id), str(event.candidate_id),
                    event.project_id, event.write_outcome,
                    event.decision_summary, event.created_at,
                    event.defer_reason_code, event.related_memory_id,
                ),
            )
        self._commit_if_auto()

    def store_retrieval_event(self, event) -> None:
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO memory_retrieval_events
                    (retrieval_event_id, project_id, purpose, returned_count,
                     explicit_hit_count, lexical_hit_count, semantic_hit_count,
                     contradiction_count, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (retrieval_event_id) DO NOTHING
                """,
                (
                    str(event.retrieval_event_id), event.project_id,
                    event.purpose, event.returned_count,
                    event.explicit_hit_count, event.lexical_hit_count,
                    event.semantic_hit_count, event.contradiction_count,
                    event.created_at,
                ),
            )
        self._commit_if_auto()

    def store_maintenance_job(self, job) -> None:
        details_json = json.dumps(dict(job.details) if job.details else {})
        with self._conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO maintenance_jobs
                    (job_id, job_type, project_id, job_status, created_at, updated_at, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                ON CONFLICT (job_id) DO UPDATE SET
                    job_status = EXCLUDED.job_status,
                    updated_at = EXCLUDED.updated_at,
                    details    = EXCLUDED.details
                """,
                (
                    str(job.job_id), job.job_type, job.project_id,
                    job.job_status, job.created_at, job.updated_at, details_json,
                ),
            )
        self._commit_if_auto()


# ------------------------------------------------------------------ #
# Private helpers                                                      #
# ------------------------------------------------------------------ #

def _row_to_record(row: tuple, description) -> CommittedMemoryRecord:
    cols = [d[0] for d in description]
    data: dict = dict(zip(cols, row))

    points_raw = data["remembered_points"]
    points: tuple[str, ...] = tuple(
        points_raw if isinstance(points_raw, list) else json.loads(points_raw)
    )

    refs_raw = data.get("support_refs") or "[]"
    refs_list: list = refs_raw if isinstance(refs_raw, list) else json.loads(refs_raw)
    refs = tuple(
        MemorySupportRef(ref_kind=r["ref_kind"], ref_id=r["ref_id"], summary=r["summary"])
        for r in refs_list
    )

    scope = Scope(
        project_id=data["project_id"],
        work_unit_id=data.get("work_unit_id"),
        run_id=data.get("run_id"),
    )

    return CommittedMemoryRecord(
        memory_id=data["memory_id"],
        memory_type=data["memory_type"],
        scope=scope,
        summary=data["summary"],
        remembered_points=points,
        why_it_matters=data["why_it_matters"],
        support_quality=data["support_quality"],
        stability=data["stability"],
        record_status=data.get("record_status", "active"),
        conflict_posture=data.get("conflict_posture", "none"),
        freshness_sensitivity=data.get("freshness_sensitivity", "low"),
        created_at=data["created_at"],
        updated_at=data["updated_at"],
        support_refs=refs,
        created_from_run_id=data.get("created_from_run_id"),
        schema_version=data.get("schema_version", "1.0"),
        supersedes_memory_id=data.get("supersedes_memory_id"),
        superseded_by_memory_id=data.get("superseded_by_memory_id"),
        merged_into_memory_id=data.get("merged_into_memory_id"),
    )


def _row_to_link(row: tuple):
    from jeff.core.schemas import coerce_memory_id as _cmi
    from .ids import coerce_link_id
    from .schemas import MemoryLink
    link_id, memory_id, link_type, target_id, target_family, metadata = row
    meta: dict = metadata if isinstance(metadata, dict) else json.loads(metadata or "{}")
    return MemoryLink(
        memory_link_id=coerce_link_id(link_id),
        memory_id=_cmi(memory_id),
        link_type=link_type,
        target_id=target_id,
        target_family=target_family,
        metadata=meta,
    )
