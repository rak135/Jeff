import pytest

from jeff.core.schemas import Scope
from jeff.memory import (
    InMemoryMemoryStore,
    MemoryRetrievalRequest,
    MemorySupportRef,
    build_truth_first_memory_view,
    canonical_memory_link_for_state,
    create_memory_candidate,
    retrieve_memory,
    write_memory_candidate,
)


def _support_ref() -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="evaluation",
        ref_id="evaluation-1",
        summary="Evaluation evidence supported the continuity judgment",
    )


def test_truth_first_helper_keeps_state_authoritative_over_memory() -> None:
    store = InMemoryMemoryStore()
    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Earlier evidence suggested the work unit was still open",
            remembered_points=("This was true earlier but may no longer match current truth.",),
            why_it_matters="It explains prior decisions without becoming present truth.",
            support_refs=(_support_ref(),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )
    retrieval = retrieve_memory(
        request=MemoryRetrievalRequest(
            purpose="current truth comparison",
            scope=Scope(project_id="project-1"),
        ),
        store=store,
    )

    view = build_truth_first_memory_view(
        current_truth_summary="Current truth says the work unit is now closed.",
        retrieval_result=retrieval,
    )

    assert view.truth_wins is True
    assert view.current_truth_summary == "Current truth says the work unit is now closed."
    assert "state wins for current-truth questions" in view.notes[-1]


def test_canonical_memory_link_helper_accepts_committed_memory_id_only() -> None:
    store = InMemoryMemoryStore()
    write = write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="operational",
            scope=Scope(project_id="project-1"),
            summary="Only committed memory IDs belong in canonical linkage",
            remembered_points=("Candidate IDs and memory bodies must stay out of state.",),
            why_it_matters="This keeps canonical truth linked only to committed support references.",
            support_refs=(_support_ref(),),
            support_quality="strong",
            stability="stable",
        ),
        store=store,
    )

    committed_id = canonical_memory_link_for_state(memory_id="memory-1", store=store)

    assert str(committed_id) == "memory-1"

    with pytest.raises(ValueError, match="already committed memory_id"):
        canonical_memory_link_for_state(memory_id="candidate-1", store=store)

    with pytest.raises(TypeError, match="memory_id string"):
        canonical_memory_link_for_state(memory_id=write.committed_record, store=store)


def test_pending_or_failed_candidates_never_become_canonical_references() -> None:
    store = InMemoryMemoryStore()
    candidate = create_memory_candidate(
        candidate_id="candidate-2",
        memory_type="episodic",
        scope=Scope(project_id="project-1"),
        summary="Weak support stayed pending instead of becoming memory truth",
        remembered_points=("The candidate was intentionally deferred.",),
        why_it_matters="It should never appear as a canonical memory link until committed.",
        support_refs=(_support_ref(),),
        support_quality="weak",
        stability="volatile",
    )
    decision = write_memory_candidate(candidate=candidate, store=store)

    assert decision.write_outcome == "defer"
    with pytest.raises(ValueError, match="already committed memory_id"):
        canonical_memory_link_for_state(memory_id="candidate-2", store=store)
