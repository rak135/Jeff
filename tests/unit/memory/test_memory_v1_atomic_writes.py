"""Atomic-write unit tests for the memory v1 logical write boundary.

These tests exercise the PostgreSQL-class atomic contract without requiring a
running database.  A TransactionalFakeStore mimics PostgresMemoryStore's
atomic() semantics: mutations are buffered while inside atomic(), committed on
clean exit, and discarded on exception.  The fake satisfies the parts of
MemoryStoreProtocol exercised by the write pipeline.

Rollback is verified by asserting that after an injected failure:
 - no committed record survives
 - no links survive
 - no superseded status update survives
 - no embedding survives
 - no write-event survives

For behaviour against a real PostgreSQL instance, see
tests/integration/memory/test_postgres_memory.py (gated on JEFF_TEST_POSTGRES_DSN).
"""

from __future__ import annotations

import contextlib

import pytest

from jeff.core.schemas import Scope, coerce_memory_id
from jeff.memory import (
    HashEmbedder,
    MemorySupportRef,
    create_memory_candidate,
    process_candidate,
)
from jeff.memory.api import merge_into_candidate, supersede_candidate


# --------------------------------------------------------------------------- #
# Transactional fake store                                                     #
# --------------------------------------------------------------------------- #

class TransactionalFakeStore:
    """A minimal transactional store whose atomic() mirrors PostgresMemoryStore.

    While inside atomic() mutations write only to a pending buffer; on clean
    exit the buffer is merged into the committed state; on exception the buffer
    is discarded and no committed state changes.  Outside atomic(), mutations
    commit immediately (matching postgres_store._commit_if_auto()).
    """

    def __init__(self) -> None:
        self._records: dict[str, object] = {}
        self._links: list = []
        self._embeddings: dict[str, list[float]] = {}
        self._write_events: list = []
        self._counter = 0

        self._in_atomic = False
        self._pending_records: dict[str, object] | None = None
        self._pending_links: list | None = None
        self._pending_embeddings: dict[str, list[float]] | None = None
        self._pending_events: list | None = None

    # --- transaction control ---

    @contextlib.contextmanager
    def atomic(self):
        if self._in_atomic:
            # Nested — outer owns commit/rollback
            yield
            return
        self._in_atomic = True
        self._pending_records = dict(self._records)
        self._pending_links = list(self._links)
        self._pending_embeddings = dict(self._embeddings)
        self._pending_events = list(self._write_events)
        try:
            yield
        except Exception:
            self._pending_records = None
            self._pending_links = None
            self._pending_embeddings = None
            self._pending_events = None
            self._in_atomic = False
            raise
        # Commit buffered state
        self._records = self._pending_records
        self._links = self._pending_links
        self._embeddings = self._pending_embeddings
        self._write_events = self._pending_events
        self._pending_records = None
        self._pending_links = None
        self._pending_embeddings = None
        self._pending_events = None
        self._in_atomic = False

    # --- record operations ---

    def allocate_memory_id(self):
        self._counter += 1
        return coerce_memory_id(f"memory-atomic-{self._counter}")

    def get_committed(self, memory_id: str):
        return self._records.get(str(memory_id))

    def list_project_records(self, project_id: str):
        target = self._pending_records if self._in_atomic else self._records
        recs = [r for r in target.values() if str(r.scope.project_id) == project_id]
        recs.sort(key=lambda r: str(r.memory_id))
        return tuple(recs)

    def _store_committed_record(self, record):
        target = self._pending_records if self._in_atomic else self._records
        target[str(record.memory_id)] = record

    def _mark_superseded(self, *, superseded_memory_id, new_memory_id):
        from jeff.memory.models import CommittedMemoryRecord
        target = self._pending_records if self._in_atomic else self._records
        old = target.get(str(superseded_memory_id))
        if old is None:
            return
        target[str(superseded_memory_id)] = CommittedMemoryRecord(
            memory_id=old.memory_id, memory_type=old.memory_type, scope=old.scope,
            summary=old.summary, remembered_points=old.remembered_points,
            why_it_matters=old.why_it_matters, support_quality=old.support_quality,
            stability=old.stability, record_status="superseded",
            conflict_posture=old.conflict_posture, created_at=old.created_at,
            updated_at=old.updated_at, support_refs=old.support_refs,
            freshness_sensitivity=old.freshness_sensitivity,
            created_from_run_id=old.created_from_run_id,
            schema_version=old.schema_version,
            supersedes_memory_id=old.supersedes_memory_id,
            superseded_by_memory_id=str(new_memory_id),
            merged_into_memory_id=old.merged_into_memory_id,
        )

    # --- link operations ---

    def store_link(self, link):
        target = self._pending_links if self._in_atomic else self._links
        target.append(link)

    def get_links_for_target(self, target_id, project_id):
        return tuple(
            l for l in self._links
            if l.target_id == target_id
            and str(self._records.get(str(l.memory_id)).scope.project_id) == project_id
        ) if self._records else ()

    def get_links_for_memory(self, memory_id):
        return tuple(l for l in self._links if str(l.memory_id) == str(memory_id))

    # --- retrieval (unused here, stubs) ---

    def search_lexical(self, *a, **k): return ()
    def search_semantic(self, *a, **k): return ()

    # --- embedding + audit ---

    def store_embedding(self, memory_id, embedding):
        target = self._pending_embeddings if self._in_atomic else self._embeddings
        target[str(memory_id)] = embedding

    def store_write_event(self, event):
        target = self._pending_events if self._in_atomic else self._write_events
        target.append(event)

    def store_retrieval_event(self, event): pass
    def store_maintenance_job(self, job): pass


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #

def _ref():
    return MemorySupportRef(
        ref_kind="research", ref_id="research-atomic-1",
        summary="support ref for atomic tests",
    )


def _candidate(candidate_id: str = "cand-atom", project_id: str = "project-atom",
               summary: str = "Governance boundary applies before execution"):
    return create_memory_candidate(
        candidate_id=candidate_id, memory_type="semantic",
        scope=Scope(project_id=project_id),
        summary=summary,
        remembered_points=("Governance must precede execution.",),
        why_it_matters="Prevents choice-as-permission drift in execution.",
        support_refs=(_ref(),),
        support_quality="strong", stability="stable",
    )


class _BrokenEmbedder:
    dimension = 64

    def embed(self, text: str):
        raise RuntimeError("simulated embedding failure")


class _FailingEventStore(TransactionalFakeStore):
    """Store that raises when persisting a write-event, to exercise rollback."""

    def store_write_event(self, event):
        raise RuntimeError("simulated write-event persistence failure")


# --------------------------------------------------------------------------- #
# Tests                                                                        #
# --------------------------------------------------------------------------- #

def test_standard_write_rolls_back_on_embedding_failure() -> None:
    store = TransactionalFakeStore()
    cand = _candidate("cand-atom-emb")
    with pytest.raises(RuntimeError, match="embedding"):
        process_candidate(candidate=cand, store=store, embedder=_BrokenEmbedder())
    assert store._records == {}, "committed record survived rollback"
    assert store._links == [], "links survived rollback"
    assert store._embeddings == {}, "embedding survived rollback"
    assert store._write_events == [], "write event survived rollback"


def test_standard_write_rolls_back_on_write_event_failure() -> None:
    store = _FailingEventStore()
    cand = _candidate("cand-atom-evt")
    with pytest.raises(RuntimeError, match="write-event"):
        process_candidate(candidate=cand, store=store, embedder=HashEmbedder())
    assert store._records == {}, "committed record survived rollback"
    assert store._links == [], "links survived rollback"
    assert store._embeddings == {}, "embedding survived rollback"


def test_supersede_rolls_back_on_embedding_failure() -> None:
    store = TransactionalFakeStore()
    original = _candidate("cand-atom-sup-orig", "project-atom-sup")
    orig = process_candidate(candidate=original, store=store)
    orig_id = str(orig.committed_record.memory_id)
    orig_status_before = store._records[orig_id].record_status
    assert orig_status_before == "active"

    superseder = create_memory_candidate(
        candidate_id="cand-atom-sup-new", memory_type="semantic",
        scope=Scope(project_id="project-atom-sup"),
        summary="Revised governance boundary — stronger evidence",
        remembered_points=("Stronger evidence reaffirms the rule.",),
        why_it_matters="New support solidifies the governance rule.",
        support_refs=(_ref(),),
        support_quality="strong", stability="stable",
    )

    records_before = dict(store._records)
    links_before = list(store._links)
    events_before = list(store._write_events)

    with pytest.raises(RuntimeError, match="embedding"):
        supersede_candidate(superseder, orig_id, store=store, embedder=_BrokenEmbedder())

    # Original record + its original status preserved; no new record; no new links/events
    assert store._records[orig_id].record_status == "active", "superseded status survived rollback"
    assert set(store._records.keys()) == set(records_before.keys()), "new record survived rollback"
    assert store._links == links_before, "supersession link survived rollback"
    assert store._write_events == events_before, "supersede event survived rollback"


def test_supersede_rolls_back_on_write_event_failure() -> None:
    # Seed the original on a normal store, then swap to a failing-event store
    # with the same committed state so the write-event failure is the only thing
    # that fails inside supersede's atomic block.
    base = TransactionalFakeStore()
    original = _candidate("cand-atom-sup-evt-orig", "project-atom-sup-evt")
    orig = process_candidate(candidate=original, store=base)
    orig_id = str(orig.committed_record.memory_id)

    failing = _FailingEventStore()
    failing._records = dict(base._records)
    failing._links = list(base._links)
    failing._embeddings = dict(base._embeddings)
    failing._counter = base._counter

    superseder = create_memory_candidate(
        candidate_id="cand-atom-sup-evt-new", memory_type="semantic",
        scope=Scope(project_id="project-atom-sup-evt"),
        summary="Revised governance boundary — stronger evidence",
        remembered_points=("Stronger evidence reaffirms the rule.",),
        why_it_matters="New support solidifies the governance rule.",
        support_refs=(_ref(),),
        support_quality="strong", stability="stable",
    )

    records_before = dict(failing._records)
    links_before = list(failing._links)

    with pytest.raises(RuntimeError, match="write-event"):
        supersede_candidate(superseder, orig_id, store=failing, embedder=HashEmbedder())

    assert failing._records[orig_id].record_status == "active"
    assert set(failing._records.keys()) == set(records_before.keys())
    assert failing._links == links_before


def test_merge_rolls_back_on_embedding_failure() -> None:
    store = TransactionalFakeStore()
    original = _candidate("cand-atom-merge-orig", "project-atom-merge")
    orig = process_candidate(candidate=original, store=store)
    orig_id = str(orig.committed_record.memory_id)
    orig_points_before = tuple(store._records[orig_id].remembered_points)
    records_before = {k: v for k, v in store._records.items()}
    links_before = list(store._links)
    events_before = list(store._write_events)

    merge = create_memory_candidate(
        candidate_id="cand-atom-merge-new", memory_type="semantic",
        scope=Scope(project_id="project-atom-merge"),
        summary=original.summary,
        remembered_points=("Execution requires governance approval always.",),
        why_it_matters="Merge path adds support detail.",
        support_refs=(_ref(),),
        support_quality="strong", stability="stable",
    )

    with pytest.raises(RuntimeError, match="embedding"):
        merge_into_candidate(merge, orig_id, store=store, embedder=_BrokenEmbedder())

    # Target record's points unchanged; no merge link; no merge event
    assert store._records[orig_id].remembered_points == orig_points_before
    assert set(store._records.keys()) == set(records_before.keys())
    assert store._links == links_before
    assert store._write_events == events_before


def test_merge_rolls_back_on_write_event_failure() -> None:
    base = TransactionalFakeStore()
    original = _candidate("cand-atom-merge-evt-orig", "project-atom-merge-evt")
    orig = process_candidate(candidate=original, store=base)
    orig_id = str(orig.committed_record.memory_id)
    orig_points_before = tuple(base._records[orig_id].remembered_points)

    failing = _FailingEventStore()
    failing._records = dict(base._records)
    failing._links = list(base._links)
    failing._embeddings = dict(base._embeddings)
    failing._counter = base._counter

    merge = create_memory_candidate(
        candidate_id="cand-atom-merge-evt-new", memory_type="semantic",
        scope=Scope(project_id="project-atom-merge-evt"),
        summary=original.summary,
        remembered_points=("Execution requires governance approval always.",),
        why_it_matters="Merge path adds support detail.",
        support_refs=(_ref(),),
        support_quality="strong", stability="stable",
    )
    links_before = list(failing._links)

    with pytest.raises(RuntimeError, match="write-event"):
        merge_into_candidate(merge, orig_id, store=failing, embedder=HashEmbedder())

    assert failing._records[orig_id].remembered_points == orig_points_before
    assert failing._links == links_before


def test_dry_run_produces_no_side_effects_even_with_broken_embedder() -> None:
    """evaluate_candidate() must persist nothing — even broken embedders don't run."""
    from jeff.memory.api import evaluate_candidate

    store = TransactionalFakeStore()
    cand = _candidate("cand-atom-dry", "project-atom-dry")
    decision = evaluate_candidate(cand, store=store, embedder=_BrokenEmbedder())
    assert decision.write_outcome == "write"
    assert store._records == {}
    assert store._links == []
    assert store._embeddings == {}
    assert store._write_events == []
    assert store._counter == 0
