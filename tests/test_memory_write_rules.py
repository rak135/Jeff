from jeff.core.schemas import Scope
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate


def _support_ref(ref_id: str = "evaluation-1") -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="evaluation",
        ref_id=ref_id,
        summary="Evaluation result carried durable support for memory review",
    )


def test_write_pipeline_commits_valid_candidate_and_issues_memory_id() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="semantic",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        summary="Use exact action binding when checking governed execution entry",
        remembered_points=("Governance decisions should bind to the exact action shape, not just action_id.",),
        why_it_matters="This protects later execution from stale or reshaped action reuse.",
        support_refs=(_support_ref(),),
        support_quality="strong",
        stability="stable",
    )

    decision = write_memory_candidate(candidate=candidate, store=store)

    assert decision.write_outcome == "write"
    assert str(decision.memory_id) == "memory-1"
    assert decision.committed_record is not None
    assert store.get_committed("memory-1") == decision.committed_record


def test_duplicate_memory_candidate_rejects() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="operational",
        scope=Scope(project_id="project-1"),
        summary="Run memory retrieval only after reading current truth",
        remembered_points=("Current truth answers current-state questions before memory is consulted.",),
        why_it_matters="This stops stale continuity support from reframing active reality.",
        support_refs=(_support_ref(),),
        support_quality="strong",
        stability="stable",
    )
    write_memory_candidate(candidate=candidate, store=store)

    duplicate = create_memory_candidate(
        candidate_id="candidate-2",
        memory_type="operational",
        scope=Scope(project_id="project-1"),
        summary="Run memory retrieval only after reading current truth",
        remembered_points=("Current truth answers current-state questions before memory is consulted.",),
        why_it_matters="This stops stale continuity support from reframing active reality.",
        support_refs=(_support_ref("evaluation-2"),),
        support_quality="strong",
        stability="stable",
    )

    decision = write_memory_candidate(candidate=duplicate, store=store)

    assert decision.write_outcome == "reject"
    assert decision.reasons == ("duplicate committed memory already exists for this bounded memory",)


def test_weak_or_volatile_candidate_defers() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-3",
        memory_type="episodic",
        scope=Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"),
        summary="One run hinted that a blocker might recur",
        remembered_points=("The blocker pattern showed up once but is not yet confirmed.",),
        why_it_matters="It may matter later, but the support is not settled yet.",
        support_refs=(_support_ref(),),
        support_quality="weak",
        stability="volatile",
    )

    decision = write_memory_candidate(candidate=candidate, store=store)

    assert decision.write_outcome == "defer"
    assert decision.memory_id is None
    assert store.list_project_records("project-1") == ()


def test_low_value_candidate_rejects() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-4",
        memory_type="directional",
        scope=Scope(project_id="project-1"),
        summary="Keep this around",
        remembered_points=("A vague note should not become committed memory.",),
        why_it_matters="maybe useful later",
        support_refs=(_support_ref(),),
        support_quality="moderate",
        stability="tentative",
    )

    decision = write_memory_candidate(candidate=candidate, store=store)

    assert decision.write_outcome == "reject"
    assert decision.reasons == ("candidate lacks strong durable continuity value",)
