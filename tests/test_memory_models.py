import pytest

from jeff.core.schemas import Scope
from jeff.memory import CommittedMemoryRecord, MemoryCandidate, MemorySupportRef, create_memory_candidate


def _support_ref() -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind="evaluation",
        ref_id="evaluation-1",
        summary="Evaluation rationale pointed to a repeatable lesson",
    )


def test_memory_candidate_has_one_primary_type_and_pending_review_status() -> None:
    candidate = create_memory_candidate(
        candidate_id="candidate-1",
        memory_type="operational",
        scope=Scope(project_id="project-1", work_unit_id="wu-1"),
        summary="Keep scope checks at the memory boundary",
        remembered_points=("Canonical linkage must use committed memory IDs only.",),
        why_it_matters="This prevents candidate IDs from leaking into truth surfaces later.",
        support_refs=(_support_ref(),),
        support_quality="strong",
        stability="stable",
    )

    assert candidate.memory_type == "operational"
    assert candidate.candidate_status == "pending_review"


def test_memory_candidate_cannot_be_created_outside_memory_pipeline() -> None:
    with pytest.raises(ValueError, match="created by jeff.memory.write_pipeline"):
        MemoryCandidate(
            candidate_id="candidate-1",
            memory_type="episodic",
            scope=Scope(project_id="project-1"),
            summary="Direct construction attempt",
            remembered_points=("This should fail.",),
            why_it_matters="The public boundary keeps candidate authorship inside Memory.",
            support_refs=(_support_ref(),),
            support_quality="moderate",
            stability="tentative",
        )


def test_committed_memory_record_requires_committed_shape() -> None:
    record = CommittedMemoryRecord(
        memory_id="memory-1",
        memory_type="semantic",
        scope=Scope(project_id="project-1"),
        summary="Project isolation must stay harder than retrieval convenience",
        remembered_points=("Wrong-project retrieval must stay empty or be rejected.",),
        why_it_matters="Cross-project bleed would turn memory into a shadow truth layer.",
        support_quality="strong",
        stability="stable",
        created_at="2026-04-10T20:05:00+00:00",
        updated_at="2026-04-10T20:05:00+00:00",
        support_refs=(_support_ref(),),
    )

    assert str(record.memory_id) == "memory-1"
    assert record.record_status == "active"


def test_dump_like_candidate_text_rejects_cleanly() -> None:
    oversized = "x" * 260

    with pytest.raises(ValueError, match="stay concise"):
        create_memory_candidate(
            candidate_id="candidate-2",
            memory_type="episodic",
            scope=Scope(project_id="project-1"),
            summary=oversized,
            remembered_points=("Bounded memories cannot be raw dumps.",),
            why_it_matters="Oversized summaries would turn memory into sludge.",
            support_refs=(_support_ref(),),
        )
