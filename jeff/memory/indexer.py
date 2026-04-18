"""FTS and vector indexing for committed memory records.

For PostgreSQL-backed stores, index_record() writes the FTS vector and embedding
to the database so that search_lexical() and search_semantic() can find the record.
The FTS vector is maintained by _store_committed_record(); this module handles the
embedding side which requires a VectorEmbedder.

Partial indexing failure must not erase committed authority: the record stays
authoritative regardless of indexing outcome.  Only retrieval quality degrades.
"""

from __future__ import annotations

from dataclasses import dataclass

from .models import CommittedMemoryRecord


@dataclass(frozen=True, slots=True)
class IndexResult:
    memory_id: str
    fts_indexed: bool
    vector_indexed: bool
    backlog: bool
    failure_reason: str | None = None


def index_record(
    record: CommittedMemoryRecord,
    *,
    store,
    embedder=None,
) -> IndexResult:
    """Index a committed record for FTS and vector retrieval.

    FTS: The PostgreSQL store writes fts_vector during _store_committed_record(),
    so fts_indexed reflects whether the store supports FTS natively.

    Vector: If an embedder is provided, embeds the record text and calls
    store.store_embedding().  Failure is isolated so the committed record survives.

    In-memory stores produce fts_indexed=False (token search is used instead).
    """
    from .postgres_store import PostgresMemoryStore  # local import avoids circular

    is_postgres = isinstance(store, PostgresMemoryStore)
    fts_indexed = is_postgres  # FTS written during _store_committed_record for Postgres

    vector_indexed = False
    failure_reason: str | None = None

    if embedder is not None:
        try:
            text = " ".join([record.summary, record.why_it_matters, *record.remembered_points])
            embedding = embedder.embed(text)
            store.store_embedding(str(record.memory_id), embedding)
            vector_indexed = True
        except Exception as exc:
            # Partial indexing failure must not erase committed record
            failure_reason = f"embedding failed: {exc}"

    if not fts_indexed and not vector_indexed and embedder is None:
        failure_reason = "no indexing backend configured"

    return IndexResult(
        memory_id=str(record.memory_id),
        fts_indexed=fts_indexed,
        vector_indexed=vector_indexed,
        backlog=not (fts_indexed and vector_indexed),
        failure_reason=failure_reason,
    )


def rebuild_project_index(
    project_id: str,
    *,
    store,
    embedder=None,
) -> dict[str, int]:
    """Re-index all active project records.

    Returns counts: records_inspected, records_fts_indexed, records_vector_indexed, failures.
    """
    records = store.list_project_records(project_id)
    active = [r for r in records if r.record_status == "active"]
    fts_count = 0
    vec_count = 0
    fail_count = 0
    for record in active:
        result = index_record(record, store=store, embedder=embedder)
        if result.fts_indexed:
            fts_count += 1
        if result.vector_indexed:
            vec_count += 1
        if result.failure_reason:
            fail_count += 1
    return {
        "records_inspected": len(active),
        "records_fts_indexed": fts_count,
        "records_vector_indexed": vec_count,
        "failures": fail_count,
    }
