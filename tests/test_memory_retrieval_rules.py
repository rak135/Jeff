from jeff.core.schemas import Scope
from jeff.memory import (
    CommittedMemoryRecord,
    InMemoryMemoryStore,
    MemoryRetrievalRequest,
    MemorySupportRef,
    create_memory_candidate,
    retrieve_memory,
    write_memory_candidate,
)


def _support_ref(ref_id: str) -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="research",
        ref_id=ref_id,
        summary="Research support stayed source-aware and bounded",
    )


def test_retrieval_returns_committed_memory_only() -> None:
    store = InMemoryMemoryStore()
    committed = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="semantic",
        scope=Scope(project_id="project-1"),
        summary="Selection never implies governance permission",
        remembered_points=("Selection can choose a path without allowing action start.",),
        why_it_matters="This boundary protects execution from choice-as-permission drift.",
        support_refs=(_support_ref("research-1"),),
        support_quality="strong",
        stability="stable",
    )
    deferred = create_memory_candidate(
        candidate_id="candidate-2",
        memory_type="episodic",
        scope=Scope(project_id="project-1"),
        summary="One weak signal suggested a recurring issue",
        remembered_points=("The signal is too weak to commit yet.",),
        why_it_matters="It may matter later, but not enough to commit now.",
        support_refs=(_support_ref("research-2"),),
        support_quality="weak",
        stability="volatile",
    )
    write_memory_candidate(candidate=committed, store=store)
    write_memory_candidate(candidate=deferred, store=store)

    result = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="proposal support",
            scope=Scope(project_id="project-1"),
        ),
        store=store,
    )

    assert [str(record.memory_id) for record in result.records] == ["memory-1"]


def test_wrong_project_retrieval_returns_nothing() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="operational",
        scope=Scope(project_id="project-1"),
        summary="Keep project memory scoped to its owning project",
        remembered_points=("Cross-project recall is conservative by default in v1.",),
        why_it_matters="This preserves project isolation across retrieval surfaces.",
        support_refs=(_support_ref("research-1"),),
        support_quality="strong",
        stability="stable",
    )
    write_memory_candidate(candidate=candidate, store=store)

    result = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="context support",
            scope=Scope(project_id="project-2"),
        ),
        store=store,
    )

    assert result.records == ()


def test_retrieval_stays_local_first_inside_project_scope() -> None:
    store = InMemoryMemoryStore()
    project_level = write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="directional",
            scope=Scope(project_id="project-1"),
            summary="Truth-first discipline is a project-wide anchor",
            remembered_points=("All later support stays subordinate to current truth.",),
            why_it_matters="This anchor matters across the whole project.",
            support_refs=(_support_ref("research-1"),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )
    work_unit_level = write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-2",
            memory_type="operational",
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            summary="This work unit needed explicit revalidation before action entry",
            remembered_points=("Local blocker checks mattered more than the broader project default.",),
            why_it_matters="This lesson is most useful inside the same work unit.",
            support_refs=(_support_ref("research-2"),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )
    run_level = write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-3",
            memory_type="episodic",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
            summary="This run hit a mismatch before governed execution",
            remembered_points=("The mismatch mattered at the exact run scope.",),
            why_it_matters="Future reasoning in the same run should see it first.",
            support_refs=(_support_ref("research-3"),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )

    result = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="run-local support",
            scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
        ),
        store=store,
    )

    assert [str(record.memory_id) for record in result.records] == [
        str(run_level.memory_id),
        str(work_unit_level.memory_id),
        str(project_level.memory_id),
    ]


def test_retrieval_preserves_stale_or_conflicting_labels_as_support_only() -> None:
    store = InMemoryMemoryStore()
    store._store_committed_record(
        CommittedMemoryRecord(
            memory_id="memory-9",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="An older assumption may now be stale",
            remembered_points=("This summary conflicts with newer state and must stay support-only.",),
            why_it_matters="It can explain why a contradiction emerged without becoming truth.",
            support_quality="strong",
            stability="stable",
            conflict_posture="stale",
            created_at="2026-04-10T20:05:00+00:00",
            updated_at="2026-04-10T20:05:00+00:00",
            support_refs=(_support_ref("research-9"),),
        )
    )

    result = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="compare contradiction",
            scope=Scope(project_id="project-1"),
        ),
        store=store,
    )

    assert result.records[0].conflict_posture == "stale"
    assert "support only" in result.notes[0]
    assert "stale or conflicting support" in result.notes[1]
