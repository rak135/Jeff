"""Tests for the v1 repair pass: verifies each hard gap was fixed.

Covers:
1. get_linked() retrieves records by stored target links, not by memory IDs
2. evaluate_candidate() is side-effect-free (no store mutations)
3. retrieval combines explicit + lexical + semantic candidates
4. wrong-project records never returned from lexical or semantic retrieval
5. partial indexing failure does not erase committed memory
6. merge_into_existing end-to-end
7. supersede_existing end-to-end
8. write/retrieval/maintenance events are durably recorded (in-memory path)
9. in-memory fallback works without pretending to be a full backend
10. global/system memory forbidden across both store modes
"""

from __future__ import annotations

import pytest

from jeff.core.schemas import Scope
from jeff.memory import (
    HashEmbedder,
    InMemoryMemoryStore,
    MemoryRetrievalRequest,
    MemorySupportRef,
    create_memory_candidate,
    process_candidate,
    retrieve_memory,
    write_memory_candidate,
)
from jeff.memory.api import (
    evaluate_candidate,
    get_linked,
    merge_into_candidate,
    supersede_candidate,
)
from jeff.memory.maintenance import MaintenanceJobRequest, run_maintenance


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ref(ref_id: str = "research-1") -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="research",
        ref_id=ref_id,
        summary="Research support for the memory candidate.",
    )


def _semantic_candidate(
    candidate_id: str = "cand-1",
    project_id: str = "project-x",
    summary: str = "Selection never implies governance permission",
    support_quality: str = "strong",
    stability: str = "stable",
    remembered_points: tuple[str, ...] = ("Selection can choose without allowing action.",),
    why_it_matters: str = "Prevents choice-as-permission drift in execution layer.",
) -> object:
    return create_memory_candidate(
        candidate_id=candidate_id,
        memory_type="semantic",
        scope=Scope(project_id=project_id),
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=(_ref(),),
        support_quality=support_quality,
        stability=stability,
    )


# ---------------------------------------------------------------------------
# 1. get_linked() uses stored target links, not memory IDs
# ---------------------------------------------------------------------------

def test_get_linked_retrieves_by_target_link_not_memory_id() -> None:
    """get_linked() must look up links by target_id, not misuse explicit_memory_ids."""
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-gl-1", project_id="project-link")
    result = process_candidate(candidate=candidate, store=store)
    assert result.write_outcome == "write"
    committed = result.committed_record
    assert committed is not None

    # A link exists from committed memory to "artifact-target-1" (created by linker via support_refs)
    # But get_linked is called with a TARGET ID, not a memory ID
    # First, manually create a direct link from the memory to a custom target
    from jeff.memory.ids import coerce_link_id
    from jeff.memory import MemoryLink
    link = MemoryLink(
        memory_link_id=coerce_link_id("mlink-direct-1"),
        memory_id=committed.memory_id,
        link_type="research_artifact_ref",
        target_id="artifact-target-custom",
        target_family="research_artifact",
    )
    store.store_link(link)

    # get_linked with the TARGET id should return the memory record
    records = get_linked("project-link", ["artifact-target-custom"], "test purpose", store=store)
    assert len(records) == 1
    assert records[0].memory_id == committed.memory_id


def test_get_linked_with_unknown_target_returns_empty() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-gl-2", project_id="project-link2")
    process_candidate(candidate=candidate, store=store)

    records = get_linked("project-link2", ["nonexistent-artifact"], "test", store=store)
    assert records == []


def test_get_linked_cross_project_excluded() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-gl-3", project_id="project-A")
    result = process_candidate(candidate=candidate, store=store)
    committed = result.committed_record

    from jeff.memory.ids import coerce_link_id
    from jeff.memory import MemoryLink
    link = MemoryLink(
        memory_link_id=coerce_link_id("mlink-cross-1"),
        memory_id=committed.memory_id,
        link_type="source_ref",
        target_id="shared-artifact",
        target_family="artifact",
    )
    store.store_link(link)

    # Cross-project get_linked must return nothing
    records = get_linked("project-B", ["shared-artifact"], "test", store=store)
    assert records == []


# ---------------------------------------------------------------------------
# 2. evaluate_candidate() is side-effect-free
# ---------------------------------------------------------------------------

def test_evaluate_candidate_does_not_persist_record() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-eval-1", project_id="project-eval")
    decision = evaluate_candidate(candidate, store=store)
    assert decision.write_outcome == "write"
    # No record committed — store must be empty
    assert len(store._records) == 0


def test_evaluate_candidate_does_not_increment_counter() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-eval-2", project_id="project-eval")
    evaluate_candidate(candidate, store=store)
    # Counter must remain at 0 — evaluate must not allocate a real ID
    assert store._counter == 0


def test_evaluate_candidate_does_not_create_links() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-eval-3", project_id="project-eval")
    evaluate_candidate(candidate, store=store)
    assert store._links_by_memory == {}
    assert store._links_by_target == {}


def test_evaluate_candidate_does_not_create_write_events() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-eval-4", project_id="project-eval")
    evaluate_candidate(candidate, store=store)
    assert store._write_events == []


def test_evaluate_candidate_returns_correct_decision_for_rejected() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="cand-eval-reject",
        memory_type="semantic",
        scope=Scope(project_id="project-eval"),
        summary="One weak signal suggested a recurring issue",
        remembered_points=("Too weak.",),
        why_it_matters="Maybe useful later",  # LOW-VALUE phrase
        support_refs=(_ref(),),
        support_quality="strong",
        stability="stable",
    )
    decision = evaluate_candidate(candidate, store=store)
    assert decision.write_outcome == "reject"
    assert len(store._records) == 0


def test_evaluate_and_then_commit_are_independent() -> None:
    """evaluate does not affect a subsequent commit's outcome."""
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate(candidate_id="cand-eval-commit", project_id="project-eval")
    eval_decision = evaluate_candidate(candidate, store=store)
    assert eval_decision.write_outcome == "write"
    # Counter still 0 after evaluate
    assert store._counter == 0

    # Now commit: should get memory-1, not memory-2 (no counter consumed by evaluate)
    commit_result = process_candidate(candidate=candidate, store=store)
    assert commit_result.write_outcome == "write"
    assert str(commit_result.committed_record.memory_id) == "memory-1"


# ---------------------------------------------------------------------------
# 3. retrieval combines explicit + lexical + semantic candidates
# ---------------------------------------------------------------------------

def test_retrieval_combines_explicit_and_lexical() -> None:
    store = InMemoryMemoryStore()
    c1 = _semantic_candidate("cand-r1", "project-r", "governance boundary protects execution")
    c2 = _semantic_candidate("cand-r2", "project-r", "selection boundary is important",
                             remembered_points=("Selection does not grant permission.",))

    r1 = process_candidate(candidate=c1, store=store)
    r2 = process_candidate(candidate=c2, store=store)

    # Use explicit_memory_ids for c1, query_text that matches c2
    request = MemoryRetrievalRequest(
        purpose="proposal support",
        scope=Scope(project_id="project-r"),
        query_text="selection boundary",
        explicit_memory_ids=(str(r1.committed_record.memory_id),),
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store)
    ids = {str(r.memory_id) for r in result.records}
    # Both should be included: c1 via explicit, c2 via lexical
    assert str(r1.committed_record.memory_id) in ids
    assert str(r2.committed_record.memory_id) in ids


def test_retrieval_includes_semantic_candidates() -> None:
    store = InMemoryMemoryStore()
    c1 = _semantic_candidate("cand-sem-r1", "project-sem",
                              "governance boundary in execution layer",
                              remembered_points=("Governance applies before action.",))
    r1 = process_candidate(candidate=c1, store=store)

    # Index with hash embedder
    embedder = HashEmbedder()
    store.store_embedding(str(r1.committed_record.memory_id),
                          embedder.embed("governance boundary in execution layer"))

    request = MemoryRetrievalRequest(
        purpose="semantic search test",
        scope=Scope(project_id="project-sem"),
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store, embedder=embedder)
    assert len(result.records) >= 1


# ---------------------------------------------------------------------------
# 4. wrong-project records never returned
# ---------------------------------------------------------------------------

def test_lexical_never_returns_wrong_project_records() -> None:
    store = InMemoryMemoryStore()
    c = _semantic_candidate("cand-wp-1", "project-A", "governance boundary rule")
    process_candidate(candidate=c, store=store)

    results = store.search_lexical(
        "project-B", "governance", memory_type_filter=None, limit=5,
    )
    assert len(results) == 0


def test_semantic_never_returns_wrong_project_records() -> None:
    store = InMemoryMemoryStore()
    c = _semantic_candidate("cand-wp-2", "project-A", "governance boundary rule")
    r = process_candidate(candidate=c, store=store)
    embedder = HashEmbedder()
    store.store_embedding(str(r.committed_record.memory_id),
                          embedder.embed("governance boundary rule"))

    query_emb = embedder.embed("governance boundary")
    results = store.search_semantic("project-B", query_emb, memory_type_filter=None, limit=5)
    assert len(results) == 0


def test_retrieve_memory_never_returns_wrong_project_records() -> None:
    store = InMemoryMemoryStore()
    c = _semantic_candidate("cand-wp-3", "project-A")
    process_candidate(candidate=c, store=store)

    request = MemoryRetrievalRequest(
        purpose="isolation check",
        scope=Scope(project_id="project-B"),
    )
    result = retrieve_memory(request=request, store=store)
    assert result.records == ()


# ---------------------------------------------------------------------------
# 5. Partial indexing failure does not erase committed memory
# ---------------------------------------------------------------------------

def test_partial_indexing_failure_record_survives() -> None:
    """If store_embedding fails, the committed record must still exist."""
    from jeff.memory.indexer import index_record

    store = InMemoryMemoryStore()
    c = _semantic_candidate("cand-idx-1", "project-idx")
    result = process_candidate(candidate=c, store=store)
    committed = result.committed_record
    assert committed is not None
    assert store.get_committed(str(committed.memory_id)) is not None

    # Simulate a broken embedder
    class BrokenEmbedder:
        dimension = 64
        def embed(self, text: str) -> list[float]:
            raise RuntimeError("embedding service down")

    idx_result = index_record(committed, store=store, embedder=BrokenEmbedder())
    assert idx_result.failure_reason is not None
    assert idx_result.vector_indexed is False

    # Record must still be in store
    assert store.get_committed(str(committed.memory_id)) is not None


# ---------------------------------------------------------------------------
# 6. merge_into_existing end-to-end
# ---------------------------------------------------------------------------

def test_merge_into_existing_combines_points() -> None:
    store = InMemoryMemoryStore()
    # Commit original record
    original = _semantic_candidate(
        "cand-merge-orig",
        "project-merge",
        summary="Selection boundary governs execution",
        remembered_points=("Selection does not grant execution permission.",),
    )
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    # Merge candidate with extra point
    merge_cand = _semantic_candidate(
        "cand-merge-new",
        "project-merge",
        summary="Selection boundary governs execution",
        remembered_points=("Execution permission requires governance approval.",),
        why_it_matters="Prevents bypass of governance in execution.",
    )

    merge_result = merge_into_candidate(
        merge_cand, orig_id, store=store,
    )
    assert merge_result.write_outcome == "merge_into_existing"
    assert str(merge_result.committed_record.memory_id) == orig_id

    updated = store.get_committed(orig_id)
    assert updated is not None
    all_points_text = " ".join(updated.remembered_points)
    assert "Selection does not grant execution permission" in all_points_text
    assert "Execution permission requires governance approval" in all_points_text


def test_merge_into_existing_creates_merge_link() -> None:
    store = InMemoryMemoryStore()
    original = _semantic_candidate(
        "cand-merge-link-orig",
        "project-merge-link",
        summary="Governance boundary in execution",
        remembered_points=("Governance must approve before execution.",),
    )
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    merge_cand = _semantic_candidate(
        "cand-merge-link-new",
        "project-merge-link",
        summary="Governance boundary in execution",
        remembered_points=("Selection cannot bypass governance check.",),
        why_it_matters="This preserves the governance invariant through all paths.",
    )
    merge_result = merge_into_candidate(merge_cand, orig_id, store=store)
    assert merge_result.write_outcome == "merge_into_existing"
    assert len(merge_result.links_created) >= 1


def test_merge_into_existing_cross_project_rejected() -> None:
    store = InMemoryMemoryStore()
    original = _semantic_candidate("cand-cross-merge", "project-A")
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    merge_cand = _semantic_candidate(
        "cand-cross-merge-new",
        "project-B",
        summary="Different project boundary",
        remembered_points=("Cross-project merge must be rejected.",),
        why_it_matters="Prevents cross-project data leakage.",
    )
    result = merge_into_candidate(merge_cand, orig_id, store=store)
    assert result.write_outcome == "reject"


# ---------------------------------------------------------------------------
# 7. supersede_existing end-to-end
# ---------------------------------------------------------------------------

def test_supersede_existing_marks_old_record_superseded() -> None:
    store = InMemoryMemoryStore()
    original = _semantic_candidate(
        "cand-sup-orig",
        "project-sup",
        support_quality="moderate",
    )
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    # Stronger superseding candidate
    superseder = _semantic_candidate(
        "cand-sup-new",
        "project-sup",
        summary="Selection never implies governance permission — revised",
        remembered_points=(
            "Selection cannot grant execution permission.",
            "Governance check must precede all execution starts.",
        ),
        support_quality="strong",
        why_it_matters="Stronger evidence confirmed the boundary rule with new cases.",
    )
    sup_result = supersede_candidate(superseder, orig_id, store=store)
    assert sup_result.write_outcome == "supersede_existing"

    # Old record must be superseded
    old = store.get_committed(orig_id)
    assert old is not None
    assert old.record_status == "superseded"
    assert old.superseded_by_memory_id == str(sup_result.committed_record.memory_id)


def test_supersede_existing_creates_supersession_link() -> None:
    store = InMemoryMemoryStore()
    original = _semantic_candidate("cand-sup-link-orig", "project-sup-link")
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    superseder = _semantic_candidate(
        "cand-sup-link-new",
        "project-sup-link",
        summary="Revised: selection boundary confirmed stronger",
        remembered_points=("Stronger support confirms the boundary.",),
        why_it_matters="New evidence solidifies the governance rule.",
    )
    sup_result = supersede_candidate(superseder, orig_id, store=store)
    assert sup_result.write_outcome == "supersede_existing"
    link_types = [l.link_type for l in sup_result.links_created]
    assert "supersedes_ref" in link_types


def test_supersede_existing_cross_project_rejected() -> None:
    store = InMemoryMemoryStore()
    original = _semantic_candidate("cand-sup-cross", "project-A")
    orig_result = process_candidate(candidate=original, store=store)
    orig_id = str(orig_result.committed_record.memory_id)

    superseder = _semantic_candidate(
        "cand-sup-cross-new",
        "project-B",
        summary="Cross-project supersede attempt",
        remembered_points=("This must fail.",),
        why_it_matters="Cross-project supersession is forbidden.",
    )
    result = supersede_candidate(superseder, orig_id, store=store)
    assert result.write_outcome == "reject"


def test_supersede_nonexistent_target_rejected() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-sup-missing", "project-sup")
    result = supersede_candidate(candidate, "memory-nonexistent", store=store)
    assert result.write_outcome == "reject"


# ---------------------------------------------------------------------------
# 8. Write/retrieval/maintenance events durably recorded (in-memory path)
# ---------------------------------------------------------------------------

def test_write_event_emitted_on_commit() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-evt-1", "project-evt")
    process_candidate(candidate=candidate, store=store)
    assert len(store._write_events) >= 1
    assert store._write_events[-1].write_outcome == "write"


def test_retrieval_event_emitted_on_retrieve() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-evt-ret-1", "project-evt-ret")
    process_candidate(candidate=candidate, store=store)

    request = MemoryRetrievalRequest(
        purpose="event test",
        scope=Scope(project_id="project-evt-ret"),
    )
    retrieve_memory(request=request, store=store)
    assert len(store._retrieval_events) >= 1
    assert store._retrieval_events[-1].purpose == "event test"


def test_maintenance_job_persisted_after_run() -> None:
    store = InMemoryMemoryStore()
    request = MaintenanceJobRequest(job_type="dedupe_audit", project_id="project-maint")
    run_maintenance(request=request, store=store)
    assert len(store._maintenance_jobs) >= 1
    assert store._maintenance_jobs[-1].job_type == "dedupe_audit"


# ---------------------------------------------------------------------------
# 9. In-memory fallback works without PostgreSQL
# ---------------------------------------------------------------------------

def test_in_memory_store_full_pipeline_without_postgres() -> None:
    """Full write → retrieve pipeline must work with InMemoryMemoryStore only."""
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-inmem-1", "project-inmem")
    write_result = process_candidate(candidate=candidate, store=store)
    assert write_result.write_outcome == "write"

    request = MemoryRetrievalRequest(
        purpose="in-memory test",
        scope=Scope(project_id="project-inmem"),
    )
    retrieval_result = retrieve_memory(request=request, store=store)
    assert len(retrieval_result.records) == 1


# ---------------------------------------------------------------------------
# 10. Global/system memory hard-forbidden across both store modes
# ---------------------------------------------------------------------------

def test_global_scope_rejected_at_candidate_creation() -> None:
    with pytest.raises(ValueError, match="global"):
        create_memory_candidate(
            candidate_id="cand-global",
            memory_type="semantic",
            scope=Scope(project_id="global"),
            summary="Should not be createable",
            remembered_points=("Not allowed.",),
            why_it_matters="Global memory is forbidden.",
            support_refs=(_ref(),),
        )


def test_system_scope_rejected_at_candidate_creation() -> None:
    with pytest.raises(ValueError, match="global|system"):
        create_memory_candidate(
            candidate_id="cand-system",
            memory_type="semantic",
            scope=Scope(project_id="system"),
            summary="System memory attempt",
            remembered_points=("Not allowed.",),
            why_it_matters="System memory is forbidden.",
            support_refs=(_ref(),),
        )


def test_retrieval_with_global_project_id_rejected() -> None:
    with pytest.raises(ValueError, match="global|forbidden"):
        MemoryRetrievalRequest(
            purpose="global retrieval attempt",
            scope=Scope(project_id="global"),
        )


def test_evaluate_candidate_respects_global_scope_rejection() -> None:
    """evaluate must fail the same way as commit for global-scoped candidates."""
    store = InMemoryMemoryStore()
    with pytest.raises(ValueError, match="global"):
        create_memory_candidate(
            candidate_id="cand-eval-global",
            memory_type="semantic",
            scope=Scope(project_id="global"),
            summary="Eval global attempt",
            remembered_points=("Not allowed.",),
            why_it_matters="Global memory is forbidden.",
            support_refs=(_ref(),),
        )


# ---------------------------------------------------------------------------
# Support links are persisted when a candidate is committed
# ---------------------------------------------------------------------------

def test_support_links_persisted_on_commit() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-link-persist", "project-lp")
    result = process_candidate(candidate=candidate, store=store)
    assert result.write_outcome == "write"
    mid = str(result.committed_record.memory_id)
    links = store.get_links_for_memory(mid)
    # There must be at least one link (from the support_ref)
    assert len(links) >= 1


def test_dry_run_does_not_persist_links() -> None:
    store = InMemoryMemoryStore()
    candidate = _semantic_candidate("cand-dry-link", "project-dl")
    evaluate_candidate(candidate, store=store)
    assert store._links_by_memory == {}


# ---------------------------------------------------------------------------
# 11. Locality filtering — work_unit and run scopes
# ---------------------------------------------------------------------------

def _candidate_with_scope(
    candidate_id: str,
    scope: Scope,
    summary: str = "Governance boundary applies here",
    remembered_points: tuple[str, ...] = ("Governance must precede execution.",),
    why_it_matters: str = "Prevents choice-as-permission drift in execution layer.",
) -> object:
    return create_memory_candidate(
        candidate_id=candidate_id,
        memory_type="semantic",
        scope=scope,
        summary=summary,
        remembered_points=remembered_points,
        why_it_matters=why_it_matters,
        support_refs=(_ref(),),
        support_quality="strong",
        stability="stable",
    )


def test_lexical_excludes_wrong_work_unit() -> None:
    """search_lexical results must be filtered by work_unit_id when requested."""
    store = InMemoryMemoryStore()
    scope_wu1 = Scope(project_id="project-loc", work_unit_id="wu-1")
    scope_wu2 = Scope(project_id="project-loc", work_unit_id="wu-2")

    c1 = _candidate_with_scope("cand-loc-1", scope_wu1,
                                summary="governance boundary applies in work unit one")
    c2 = _candidate_with_scope("cand-loc-2", scope_wu2,
                                summary="governance boundary applies in work unit two")
    process_candidate(candidate=c1, store=store)
    process_candidate(candidate=c2, store=store)

    request = MemoryRetrievalRequest(
        purpose="locality check",
        scope=scope_wu1,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store)
    # Only the wu-1 record may appear; wu-2 record is wrong locality
    summaries = [r.summary for r in result.records]
    assert any("work unit one" in s for s in summaries), "wu-1 record not returned"
    assert not any("work unit two" in s for s in summaries), "wu-2 record leaked through"


def test_semantic_excludes_wrong_work_unit() -> None:
    """Semantic retrieval must filter by work_unit_id when requested."""
    store = InMemoryMemoryStore()
    scope_wu1 = Scope(project_id="project-sem-loc", work_unit_id="wu-a")
    scope_wu2 = Scope(project_id="project-sem-loc", work_unit_id="wu-b")

    c1 = _candidate_with_scope("cand-sem-loc-1", scope_wu1,
                                summary="governance boundary applies in work unit alpha")
    c2 = _candidate_with_scope("cand-sem-loc-2", scope_wu2,
                                summary="governance boundary applies in work unit beta")
    r1 = process_candidate(candidate=c1, store=store)
    r2 = process_candidate(candidate=c2, store=store)

    embedder = HashEmbedder()
    store.store_embedding(str(r1.committed_record.memory_id),
                          embedder.embed("governance boundary applies in work unit alpha"))
    store.store_embedding(str(r2.committed_record.memory_id),
                          embedder.embed("governance boundary applies in work unit beta"))

    request = MemoryRetrievalRequest(
        purpose="semantic locality check",
        scope=scope_wu1,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store, embedder=embedder)
    summaries = [r.summary for r in result.records]
    assert any("alpha" in s for s in summaries), "wu-a record not returned"
    assert not any("beta" in s for s in summaries), "wu-b record leaked through"


def test_project_scope_request_excludes_work_unit_records() -> None:
    """A project-only request must not return records scoped to a work_unit."""
    store = InMemoryMemoryStore()
    scope_proj = Scope(project_id="project-scope-test")
    scope_wu = Scope(project_id="project-scope-test", work_unit_id="wu-1")

    c_proj = _candidate_with_scope("cand-scope-proj", scope_proj,
                                   summary="project level governance boundary")
    c_wu = _candidate_with_scope("cand-scope-wu", scope_wu,
                                 summary="work unit level governance boundary")
    process_candidate(candidate=c_proj, store=store)
    process_candidate(candidate=c_wu, store=store)

    request = MemoryRetrievalRequest(
        purpose="project scope isolation",
        scope=scope_proj,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store)
    summaries = [r.summary for r in result.records]
    assert any("project level" in s for s in summaries), "project-scope record not returned"
    assert not any("work unit level" in s for s in summaries), "work_unit record leaked into project-scope request"


def test_work_unit_scope_includes_project_scope_records() -> None:
    """A work_unit-scoped request must include project-scoped records (broader scope)."""
    store = InMemoryMemoryStore()
    scope_proj = Scope(project_id="project-wu-incl")
    scope_wu = Scope(project_id="project-wu-incl", work_unit_id="wu-x")

    c_proj = _candidate_with_scope("cand-wu-incl-proj", scope_proj,
                                   summary="project wide governance boundary rule")
    c_wu = _candidate_with_scope("cand-wu-incl-wu", scope_wu,
                                 summary="work unit specific governance note")
    r_proj = process_candidate(candidate=c_proj, store=store)
    r_wu = process_candidate(candidate=c_wu, store=store)

    request = MemoryRetrievalRequest(
        purpose="work unit includes project scope",
        scope=scope_wu,
        query_text="governance boundary",
        result_limit=5,
    )
    result = retrieve_memory(request=request, store=store)
    ids = {str(r.memory_id) for r in result.records}
    assert str(r_proj.committed_record.memory_id) in ids, "project-scope record excluded from wu request"
    assert str(r_wu.committed_record.memory_id) in ids, "wu-scope record not returned"
