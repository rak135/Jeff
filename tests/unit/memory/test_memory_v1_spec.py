"""Comprehensive Memory v1 spec tests.

Covers all required test behaviors from MEMORY_V1.md §25 and the task spec:
- only Memory creates candidates
- project_id required on all write paths
- global/system memory hard-forbidden
- cross-project write forbidden
- cross-project retrieval forbidden
- archive-dump rejection
- current-truth masquerade rejection
- type assignment enforces exactly one primary type
- dedupe exact duplicate rejection
- merge and supersede behavior (defer path)
- defer(review_required) for directional and broad operational
- retrieval remains bounded
- retrieval returns conflict/stale labels against truth anchor
- memory does not silently call knowledge retrieval
- memory only thin-links; does not own research/knowledge persistence
- commit issues memory_id only at commit
- partial indexing failure does not erase committed authority
- maintenance jobs stay project-scoped and non-semantic
- api.py public surface requires project_id on all paths
"""

from __future__ import annotations

import pytest

from jeff.core.schemas import Scope
from jeff.memory import (
    CommittedMemoryRecord,
    InMemoryMemoryStore,
    MemoryCandidate,
    MemoryRetrievalRequest,
    MemorySupportRef,
    MemoryWriteDecision,
    build_truth_first_memory_view,
    create_memory_candidate,
    retrieve_memory,
    write_memory_candidate,
)
from jeff.memory.candidate_builder import build_candidate
from jeff.memory.conflict_labeler import apply_conflict_labels, has_conflict
from jeff.memory.dedupe import check_dedupe
from jeff.memory.indexer import index_record
from jeff.memory.maintenance import MaintenanceJobRequest, run_maintenance
from jeff.memory.reranker import rerank
from jeff.memory.schemas import MemoryLink, MemoryWriteResult
from jeff.memory.scope_assigner import validate_scope
from jeff.memory.telemetry import MemoryCounters, record_write_outcome
from jeff.memory.type_assigner import assert_single_primary_type, requires_review_by_type
from jeff.memory.validator import validate_candidate, validate_project_id_present
from jeff.memory.write_pipeline import process_candidate


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _ref(ref_id: str = "research-1", kind: str = "research") -> MemorySupportRef:
    return MemorySupportRef(
        ref_kind=kind,
        ref_id=ref_id,
        summary="Research finding supports this continuity unit.",
    )


def _semantic_candidate(
    candidate_id: str = "c-1",
    project_id: str = "project-alpha",
    summary: str = "Strong semantic lesson",
    points: tuple[str, ...] = ("Lesson A applies in future similar contexts.",),
    why: str = "Prevents repeated costly mistakes in the same pattern.",
    support_quality: str = "strong",
    stability: str = "stable",
    work_unit_id: str | None = None,
) -> MemoryCandidate:
    scope = Scope(project_id=project_id, work_unit_id=work_unit_id)
    return build_candidate(
        candidate_id=candidate_id,
        memory_type="semantic",
        scope=scope,
        summary=summary,
        remembered_points=points,
        why_it_matters=why,
        support_refs=(_ref(),),
        support_quality=support_quality,
        stability=stability,
    )


# ---------------------------------------------------------------------------
# 1. Only Memory creates candidates
# ---------------------------------------------------------------------------

class TestOnlyMemoryCreatesCandidates:
    def test_direct_construction_raises_without_token(self) -> None:
        with pytest.raises(ValueError, match="jeff.memory"):
            MemoryCandidate(
                candidate_id="c-1",
                memory_type="semantic",
                scope=Scope(project_id="project-1"),
                summary="Unauthorized construction",
                remembered_points=("Point.",),
                why_it_matters="Why.",
                support_refs=(_ref(),),
                support_quality="strong",
                stability="stable",
            )

    def test_build_candidate_succeeds_through_builder(self) -> None:
        c = build_candidate(
            candidate_id="c-1",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Authorized candidate via builder",
            remembered_points=("Point.",),
            why_it_matters="Prevents repeat mistakes.",
            support_refs=(_ref(),),
        )
        assert c.candidate_status == "pending_review"

    def test_create_memory_candidate_alias_works(self) -> None:
        c = create_memory_candidate(
            candidate_id="c-2",
            memory_type="operational",
            scope=Scope(project_id="project-1"),
            summary="Backward-compat alias",
            remembered_points=("Alias works as expected.",),
            why_it_matters="Preserves backward compatibility for callers.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        assert isinstance(c, MemoryCandidate)


# ---------------------------------------------------------------------------
# 2. project_id required on all write paths
# ---------------------------------------------------------------------------

class TestProjectIdRequired:
    def test_candidate_with_empty_project_id_raises(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            build_candidate(
                candidate_id="c-1",
                memory_type="semantic",
                scope=Scope(project_id="  "),  # type: ignore[arg-type]
                summary="Missing project",
                remembered_points=("Point.",),
                why_it_matters="Will fail.",
                support_refs=(_ref(),),
            )

    def test_validate_project_id_present_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="project_id"):
            validate_project_id_present("")

    def test_validate_project_id_present_accepts_valid(self) -> None:
        validate_project_id_present("project-x")  # must not raise

    def test_retrieval_request_requires_project_scope(self) -> None:
        with pytest.raises((ValueError, TypeError)):
            MemoryRetrievalRequest(
                purpose="test",
                scope=Scope(project_id="  "),  # type: ignore[arg-type]
            )


# ---------------------------------------------------------------------------
# 3. Global/system memory hard-forbidden
# ---------------------------------------------------------------------------

class TestGlobalMemoryForbidden:
    @pytest.mark.parametrize("sentinel", ["global", "system", "*", "_global", "_system", "__global__"])
    def test_global_scope_rejected_at_candidate_creation(self, sentinel: str) -> None:
        with pytest.raises(ValueError, match="hard-forbidden|project_id"):
            build_candidate(
                candidate_id="c-1",
                memory_type="semantic",
                scope=Scope(project_id=sentinel),
                summary="Global candidate",
                remembered_points=("Should fail.",),
                why_it_matters="Global memory is forbidden in v1.",
                support_refs=(_ref(),),
            )

    def test_global_scope_rejected_at_retrieval(self) -> None:
        store = InMemoryMemoryStore()
        with pytest.raises(ValueError, match="hard-forbidden|project_id"):
            retrieve_memory(
                request=MemoryRetrievalRequest(
                    purpose="test",
                    scope=Scope(project_id="global"),
                ),
                store=store,
            )

    def test_validate_project_id_present_rejects_global(self) -> None:
        with pytest.raises(ValueError, match="hard-forbidden"):
            validate_project_id_present("global")

    def test_validate_scope_rejects_system_sentinel(self) -> None:
        with pytest.raises(ValueError, match="hard-forbidden"):
            validate_scope(Scope(project_id="system"))


# ---------------------------------------------------------------------------
# 4. Cross-project write forbidden
# ---------------------------------------------------------------------------

class TestCrossProjectWriteForbidden:
    def test_write_creates_record_only_in_owning_project(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate(project_id="project-a")
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "write"
        # Record must not appear in another project
        records_b = store.list_project_records("project-b")
        assert records_b == ()

    def test_candidate_scope_binds_to_one_project(self) -> None:
        c = _semantic_candidate(project_id="project-a")
        assert str(c.scope.project_id) == "project-a"


# ---------------------------------------------------------------------------
# 5. Cross-project retrieval forbidden
# ---------------------------------------------------------------------------

class TestCrossProjectRetrievalForbidden:
    def test_retrieval_in_different_project_returns_empty(self) -> None:
        store = InMemoryMemoryStore()
        write_memory_candidate(candidate=_semantic_candidate(project_id="project-a"), store=store)
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="test",
                scope=Scope(project_id="project-b"),
            ),
            store=store,
        )
        assert result.records == ()

    def test_get_by_id_cross_project_returns_none(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        write_memory_candidate(candidate=_semantic_candidate(project_id="project-a"), store=store)
        result = api.get_by_id("project-b", "memory-1", store=store)
        assert result is None


# ---------------------------------------------------------------------------
# 6. Archive-dump rejection
# ---------------------------------------------------------------------------

class TestArchiveDumpRejection:
    @pytest.mark.parametrize("signal", [
        "summary of everything",
        "all findings",
        "full brief",
        "complete research",
        "raw output",
    ])
    def test_archive_dump_summary_is_rejected(self, signal: str) -> None:
        # Validator should catch these signals
        c = build_candidate(
            candidate_id="c-dump",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary=signal,
            remembered_points=("Point.",),
            why_it_matters="Archive dump detected.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = validate_candidate(c)
        assert decision is not None
        assert decision.write_outcome == "reject"
        assert "archive" in decision.reasons[0].lower() or "dump" in decision.reasons[0].lower()

    def test_oversized_summary_is_rejected_at_model_level(self) -> None:
        with pytest.raises(ValueError, match="stay concise"):
            build_candidate(
                candidate_id="c-oversized",
                memory_type="episodic",
                scope=Scope(project_id="project-1"),
                summary="x" * 260,
                remembered_points=("Point.",),
                why_it_matters="Oversized.",
                support_refs=(_ref(),),
            )


# ---------------------------------------------------------------------------
# 7. Current-truth masquerade rejection
# ---------------------------------------------------------------------------

class TestCurrentTruthMasqueradeRejection:
    @pytest.mark.parametrize("signal", [
        "current state is ready",
        "current status is approved",
    ])
    def test_current_truth_framing_is_rejected(self, signal: str) -> None:
        c = build_candidate(
            candidate_id="c-truth",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary=signal,
            remembered_points=("Point.",),
            why_it_matters="Avoids truth-as-memory confusion.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = validate_candidate(c)
        assert decision is not None
        assert decision.write_outcome == "reject"
        assert "truth" in decision.reasons[0].lower() or "current" in decision.reasons[0].lower()


# ---------------------------------------------------------------------------
# 8. Type assignment enforces exactly one primary type
# ---------------------------------------------------------------------------

class TestTypeAssignment:
    @pytest.mark.parametrize("mem_type", ["episodic", "semantic", "directional", "operational"])
    def test_valid_types_pass_type_assigner(self, mem_type: str) -> None:
        c = build_candidate(
            candidate_id="c-type",
            memory_type=mem_type,
            scope=Scope(project_id="project-1"),
            summary="Type test candidate",
            remembered_points=("Point.",),
            why_it_matters="Testing type assignment.",
            support_refs=(_ref(),),
        )
        result = assert_single_primary_type(c)
        assert result == mem_type

    def test_invalid_type_raises_in_model(self) -> None:
        with pytest.raises(ValueError, match="unsupported memory_type"):
            build_candidate(
                candidate_id="c-bad-type",
                memory_type="fuzzy_important",  # type: ignore[arg-type]
                scope=Scope(project_id="project-1"),
                summary="Invalid type",
                remembered_points=("Point.",),
                why_it_matters="Testing invalid type.",
                support_refs=(_ref(),),
            )


# ---------------------------------------------------------------------------
# 9. Dedupe: exact duplicate rejection
# ---------------------------------------------------------------------------

class TestDedupeExactDuplicate:
    def test_exact_duplicate_is_rejected(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        write_memory_candidate(candidate=c, store=store)
        c2 = build_candidate(
            candidate_id="c-dup",
            memory_type="semantic",
            scope=Scope(project_id="project-alpha"),
            summary="Strong semantic lesson",
            remembered_points=("Lesson A applies in future similar contexts.",),
            why_it_matters="Prevents repeated costly mistakes in the same pattern.",
            support_refs=(_ref("research-2"),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c2, store=store)
        assert decision.write_outcome == "reject"
        assert "duplicate" in decision.reasons[0].lower()

    def test_different_scope_is_not_duplicate(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        write_memory_candidate(candidate=c, store=store)
        c2 = build_candidate(
            candidate_id="c-2",
            memory_type="semantic",
            scope=Scope(project_id="project-alpha", work_unit_id="wu-1"),
            summary="Strong semantic lesson",
            remembered_points=("Lesson A applies in future similar contexts.",),
            why_it_matters="Prevents repeated costly mistakes in the same pattern.",
            support_refs=(_ref("research-2"),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c2, store=store)
        # Different scope → not a duplicate → should write or defer
        assert decision.write_outcome in {"write", "defer"}

    def test_dedupe_check_returns_reject_for_near_duplicate(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        write_memory_candidate(candidate=c, store=store)
        near_dup = build_candidate(
            candidate_id="c-near",
            memory_type="semantic",
            scope=Scope(project_id="project-alpha"),
            summary="Strong semantic lesson",
            remembered_points=("Lesson A applies in future similar contexts.",),
            why_it_matters="Prevents repeated costly mistakes in the same pattern.",
            support_refs=(_ref("research-3"),),
            support_quality="weak",  # weaker, same content
            stability="stable",
        )
        check_result = check_dedupe(candidate=near_dup, store=store)
        assert check_result is not None
        assert check_result.write_outcome == "reject"


# ---------------------------------------------------------------------------
# 10. Merge and supersede behavior (defer path in v1)
# ---------------------------------------------------------------------------

class TestMergeAndSupersede:
    def test_stronger_near_duplicate_defers_for_review(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-orig",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Original weak semantic lesson",
            remembered_points=("Original point from weak evidence.",),
            why_it_matters="Recorded from early weak evidence.",
            support_refs=(_ref(),),
            support_quality="moderate",
            stability="stable",
        )
        write_memory_candidate(candidate=c, store=store)

        stronger = build_candidate(
            candidate_id="c-stronger",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Original weak semantic lesson",
            remembered_points=("Original point from weak evidence.",),
            why_it_matters="Recorded from early weak evidence.",
            support_refs=(_ref("research-2"),),
            support_quality="strong",  # stronger than existing
            stability="stable",
        )
        decision = write_memory_candidate(candidate=stronger, store=store)
        assert decision.write_outcome == "defer"
        assert decision.defer_reason_code == "dedupe_ambiguity"


# ---------------------------------------------------------------------------
# 11. defer(review_required) for directional and broad operational
# ---------------------------------------------------------------------------

class TestDeferReviewRequired:
    def test_directional_memory_defers_with_review_required(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-directional",
            memory_type="directional",
            scope=Scope(project_id="project-1"),
            summary="Avoid scope creep in all project phases",
            remembered_points=("Scope creep caused significant rework in similar projects.",),
            why_it_matters="This shapes future project direction choices.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "defer"
        assert decision.defer_reason_code == "review_required"

    def test_project_wide_operational_with_moderate_support_defers(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-op-wide",
            memory_type="operational",
            scope=Scope(project_id="project-1"),  # no work_unit_id = project-wide
            summary="Always validate action binding before execution",
            remembered_points=("Missing validation caused three failures across runs.",),
            why_it_matters="Applies broadly to all execution paths in the project.",
            support_refs=(_ref(),),
            support_quality="moderate",  # non-strong + project-wide = defer
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "defer"
        assert decision.defer_reason_code == "review_required"

    def test_narrow_operational_with_strong_support_commits(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-op-narrow",
            memory_type="operational",
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            summary="Revalidate action binding in this work unit",
            remembered_points=("Local validation prevented a governance bypass in wu-1.",),
            why_it_matters="Specific to this work unit; prevents local execution failures.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "write"
        assert decision.memory_id is not None

    def test_strong_narrow_semantic_auto_commits(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-semantic-strong",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Evidence-backed pattern for governance bypass avoidance",
            remembered_points=("Governance checks must bind to the exact action shape.",),
            why_it_matters="Protects downstream execution from stale action reuse.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "write"

    def test_defer_carries_machine_readable_reason_code(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-dir",
            memory_type="directional",
            scope=Scope(project_id="project-1"),
            summary="Strategic non-goal: avoid overbuilding memory infrastructure",
            remembered_points=("Over-engineering memory caused delays in v0.",),
            why_it_matters="This anti-drift lesson shapes future architecture choices.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.defer_reason_code is not None
        assert decision.defer_reason_code in {
            "review_required",
            "dedupe_ambiguity",
            "insufficient_support",
            "scope_ambiguity",
            "candidate_needs_rewrite",
            "linkage_incomplete",
        }


# ---------------------------------------------------------------------------
# 12. Retrieval remains bounded
# ---------------------------------------------------------------------------

class TestRetrievalBounded:
    def test_result_limit_is_enforced(self) -> None:
        store = InMemoryMemoryStore()
        for i in range(8):
            write_memory_candidate(
                candidate=build_candidate(
                    candidate_id=f"c-{i}",
                    memory_type="semantic",
                    scope=Scope(project_id="project-1"),
                    summary=f"Unique lesson {i} about a distinct pattern",
                    remembered_points=(f"Point {i} is specific and distinct.",),
                    why_it_matters=f"Lesson {i} prevents repeat errors in different contexts.",
                    support_refs=(_ref(f"r-{i}"),),
                    support_quality="strong",
                    stability="stable",
                ),
                store=store,
            )
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="context assembly",
                scope=Scope(project_id="project-1"),
                result_limit=3,
            ),
            store=store,
        )
        assert len(result.records) <= 3

    def test_result_limit_maximum_is_ten(self) -> None:
        with pytest.raises(ValueError, match="result_limit"):
            MemoryRetrievalRequest(
                purpose="test",
                scope=Scope(project_id="project-1"),
                result_limit=11,
            )

    def test_retrieval_support_only_flag_is_always_true(self) -> None:
        store = InMemoryMemoryStore()
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="test",
                scope=Scope(project_id="project-1"),
            ),
            store=store,
        )
        assert result.support_only is True


# ---------------------------------------------------------------------------
# 13. Retrieval returns conflict/stale labels against truth anchor
# ---------------------------------------------------------------------------

class TestConflictLabelingAgainstTruth:
    def test_stale_record_returns_with_stale_posture_label(self) -> None:
        store = InMemoryMemoryStore()
        store._store_committed_record(
            CommittedMemoryRecord(
                memory_id="memory-stale",
                memory_type="semantic",
                scope=Scope(project_id="project-1"),
                summary="Earlier assumption about status",
                remembered_points=("Work unit was open last time.",),
                why_it_matters="Provides continuity context.",
                support_quality="strong",
                stability="stable",
                conflict_posture="stale_support",
                created_at="2026-04-01T10:00:00+00:00",
                updated_at="2026-04-01T10:00:00+00:00",
                support_refs=(_ref(),),
            )
        )
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="compare contradiction",
                scope=Scope(project_id="project-1"),
            ),
            store=store,
        )
        assert result.records[0].conflict_posture == "stale_support"
        assert any("stale or conflicting" in note for note in result.notes)

    def test_conflict_label_does_not_override_truth(self) -> None:
        store = InMemoryMemoryStore()
        write_memory_candidate(
            candidate=_semantic_candidate(
                summary="Earlier evidence showed open state",
                why="Provides context for prior decisions.",
            ),
            store=store,
        )
        retrieval = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="truth comparison",
                scope=Scope(project_id="project-alpha"),
                truth_anchor="Current state is now closed.",
            ),
            store=store,
        )
        view = build_truth_first_memory_view(
            current_truth_summary="Current state is now closed.",
            retrieval_result=retrieval,
        )
        assert view.truth_wins is True
        assert view.current_truth_summary == "Current state is now closed."

    def test_apply_conflict_labels_detects_stale_via_truth_anchor(self) -> None:
        record = CommittedMemoryRecord(
            memory_id="m-1",
            memory_type="semantic",
            scope=Scope(project_id="p-1"),
            summary="Status was active",
            remembered_points=("Status was active before.",),
            why_it_matters="Provides context.",
            support_quality="strong",
            stability="stable",
            conflict_posture="none",
            created_at="2026-01-01T00:00:00+00:00",
            updated_at="2026-01-01T00:00:00+00:00",
            support_refs=(_ref(),),
            record_status="superseded",
        )
        labeled = apply_conflict_labels(
            records=(record,),
            truth_anchor="The state has changed to inactive.",
        )
        assert labeled[0].conflict_posture == "stale_support"


# ---------------------------------------------------------------------------
# 14. Memory does not silently call knowledge retrieval
# ---------------------------------------------------------------------------

class TestMemoryDoesNotCallKnowledgeRetrieval:
    def test_retrieval_result_contains_only_committed_memory(self) -> None:
        store = InMemoryMemoryStore()
        write_memory_candidate(candidate=_semantic_candidate(), store=store)
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="support",
                scope=Scope(project_id="project-alpha"),
            ),
            store=store,
        )
        # All returned records must be CommittedMemoryRecord instances
        for record in result.records:
            assert isinstance(record, CommittedMemoryRecord)
        # Notes must declare support-only status
        assert any("support only" in note for note in result.notes)

    def test_knowledge_artifact_not_in_memory_retrieval_result(self) -> None:
        """Memory retrieval never merges knowledge layer artifacts into results."""
        store = InMemoryMemoryStore()
        result = retrieve_memory(
            request=MemoryRetrievalRequest(
                purpose="topic overview",
                scope=Scope(project_id="project-alpha"),
                query_text="topic note",
            ),
            store=store,
        )
        # No knowledge artifacts — result is empty or pure memory
        for record in result.records:
            assert isinstance(record, CommittedMemoryRecord)


# ---------------------------------------------------------------------------
# 15. Memory thin-links to research/knowledge artifacts; does not own persistence
# ---------------------------------------------------------------------------

class TestMemoryThinLinks:
    def test_support_refs_in_committed_record_are_thin_links(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        result = process_candidate(candidate=c, store=store)
        assert result.write_outcome == "write"
        record = result.committed_record
        assert record is not None
        # Support refs must be MemorySupportRef objects — thin references, not full artifacts
        for ref in record.support_refs:
            assert isinstance(ref, MemorySupportRef)
            assert ref.ref_id  # must have an ID pointing externally
            # The actual artifact content is NOT embedded in memory
            assert len(ref.summary) <= 160

    def test_process_candidate_creates_thin_memory_links(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        result = process_candidate(candidate=c, store=store)
        assert result.write_outcome == "write"
        # Links are created as thin MemoryLink objects
        for link in result.links_created:
            assert isinstance(link, MemoryLink)
            assert link.link_type in {
                "research_artifact_ref",
                "history_record_ref",
                "knowledge_artifact_ref",
                "source_ref",
                "evidence_ref",
                "related_memory_ref",
                "supersedes_ref",
                "merged_into_ref",
                "derived_from_ref",
            }


# ---------------------------------------------------------------------------
# 16. Commit issues memory_id only at commit
# ---------------------------------------------------------------------------

class TestCommitIssuesMemoryIdOnlyAtCommit:
    def test_deferred_candidate_has_no_memory_id(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-dir",
            memory_type="directional",
            scope=Scope(project_id="project-1"),
            summary="Strategic direction: minimize external dependencies",
            remembered_points=("External dependencies caused two outages.",),
            why_it_matters="Shapes future architectural choices.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "defer"
        assert decision.memory_id is None
        assert decision.committed_record is None

    def test_rejected_candidate_has_no_memory_id(self) -> None:
        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-reject",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Low value note",
            remembered_points=("Not useful.",),
            why_it_matters="maybe useful later",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "reject"
        assert decision.memory_id is None

    def test_committed_candidate_has_memory_id(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        decision = write_memory_candidate(candidate=c, store=store)
        assert decision.write_outcome == "write"
        assert decision.memory_id is not None
        assert str(decision.memory_id).startswith("memory-")

    def test_candidate_id_is_not_a_memory_id(self) -> None:
        store = InMemoryMemoryStore()
        from jeff.memory import canonical_memory_link_for_state

        c = build_candidate(
            candidate_id="c-weak",
            memory_type="semantic",
            scope=Scope(project_id="project-1"),
            summary="Weak candidate not committed",
            remembered_points=("Not committed.",),
            why_it_matters="Support too weak.",
            support_refs=(_ref(),),
            support_quality="weak",
            stability="volatile",
        )
        write_memory_candidate(candidate=c, store=store)
        with pytest.raises(ValueError, match="committed memory_id"):
            canonical_memory_link_for_state(memory_id="c-weak", store=store)


# ---------------------------------------------------------------------------
# 17. Partial indexing failure does not erase committed authority
# ---------------------------------------------------------------------------

class TestIndexingFailureDoesNotEraseCommit:
    def test_index_result_backlog_does_not_lose_committed_record(self) -> None:
        store = InMemoryMemoryStore()
        c = _semantic_candidate()
        result = process_candidate(candidate=c, store=store)
        assert result.write_outcome == "write"
        assert result.committed_record is not None

        # Simulate indexing stub returning backlog=True
        idx_result = index_record(result.committed_record)
        assert idx_result.backlog is True

        # The committed record must still be retrievable
        committed = store.get_committed(str(result.memory_id))
        assert committed is not None
        assert str(committed.memory_id) == str(result.memory_id)


# ---------------------------------------------------------------------------
# 18. Maintenance jobs stay project-scoped and non-semantic
# ---------------------------------------------------------------------------

class TestMaintenanceJobsProjectScoped:
    @pytest.mark.parametrize("job_type", [
        "embedding_refresh",
        "dedupe_audit",
        "supersession_audit",
        "stale_memory_review",
        "broken_link_audit",
        "retrieval_quality_evaluation",
        "index_consistency_audit",
        "compression_refresh",
        "quarantine_review",
    ])
    def test_all_required_maintenance_job_types_are_valid(self, job_type: str) -> None:
        req = MaintenanceJobRequest(job_type=job_type, project_id="project-1")
        assert req.job_type == job_type

    def test_maintenance_job_requires_project_id(self) -> None:
        with pytest.raises(ValueError, match="project_id"):
            MaintenanceJobRequest(job_type="dedupe_audit", project_id="")

    def test_maintenance_job_runs_project_scoped(self) -> None:
        store = InMemoryMemoryStore()
        write_memory_candidate(candidate=_semantic_candidate(project_id="project-1"), store=store)
        write_memory_candidate(candidate=_semantic_candidate(candidate_id="c-2", project_id="project-2",
                                                              summary="Different project lesson",
                                                              why="Why project 2."), store=store)

        result = run_maintenance(
            request=MaintenanceJobRequest(job_type="dedupe_audit", project_id="project-1"),
            store=store,
        )
        # Job must be scoped to project-1 only
        assert result.job.project_id == "project-1"
        assert result.records_inspected == 1  # only project-1 record

    def test_invalid_maintenance_job_type_raises(self) -> None:
        with pytest.raises(ValueError, match="job_type"):
            MaintenanceJobRequest(job_type="rewrite_everything_semantically", project_id="project-1")


# ---------------------------------------------------------------------------
# 19. api.py public surface
# ---------------------------------------------------------------------------

class TestApiPublicSurface:
    def test_api_process_candidate_requires_project_id(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        with pytest.raises(ValueError, match="project_id|hard-forbidden"):
            api.process_candidate(
                build_candidate(
                    candidate_id="c-1",
                    memory_type="semantic",
                    scope=Scope(project_id="global"),
                    summary="Should fail",
                    remembered_points=("Point.",),
                    why_it_matters="Global forbidden.",
                    support_refs=(_ref(),),
                ),
                store=store,
            )

    def test_api_retrieve_requires_project_id(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        with pytest.raises(ValueError):
            api.retrieve(
                MemoryRetrievalRequest(
                    purpose="test",
                    scope=Scope(project_id="system"),
                ),
                store=store,
            )

    def test_api_run_maintenance_requires_project_id(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        with pytest.raises(ValueError, match="project_id"):
            api.run_maintenance(
                MaintenanceJobRequest(job_type="dedupe_audit", project_id=""),
                store=store,
            )

    def test_api_get_by_id_returns_none_for_cross_project(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        write_memory_candidate(candidate=_semantic_candidate(project_id="project-a"), store=store)
        record = api.get_by_id("project-b", "memory-1", store=store)
        assert record is None

    def test_api_commit_candidate_raises_on_defer(self) -> None:
        from jeff.memory import api

        store = InMemoryMemoryStore()
        c = build_candidate(
            candidate_id="c-dir",
            memory_type="directional",
            scope=Scope(project_id="project-1"),
            summary="Strategic direction to defer",
            remembered_points=("Directional memory requires review.",),
            why_it_matters="Shapes broad project direction.",
            support_refs=(_ref(),),
            support_quality="strong",
            stability="stable",
        )
        with pytest.raises(ValueError, match="not committed"):
            api.commit_candidate(c, store=store)


# ---------------------------------------------------------------------------
# 20. Telemetry scaffolding
# ---------------------------------------------------------------------------

class TestTelemetryScaffolding:
    def test_write_outcome_increments_counters(self) -> None:
        counters = MemoryCounters()
        record_write_outcome("write", counters=counters)
        record_write_outcome("reject", counters=counters)
        record_write_outcome("defer", counters=counters)
        snapshot = counters.snapshot()
        assert snapshot["candidate_created"] == 3
        assert snapshot["candidate_committed"] == 1
        assert snapshot["candidate_rejected"] == 1
        assert snapshot["candidate_deferred"] == 1

    def test_supersede_increments_supersession_count(self) -> None:
        counters = MemoryCounters()
        record_write_outcome("supersede_existing", counters=counters)
        snapshot = counters.snapshot()
        assert snapshot["supersession_count"] == 1
        assert snapshot["candidate_committed"] == 1


# ---------------------------------------------------------------------------
# 21. Reranker: scope fit, support quality, status ordering
# ---------------------------------------------------------------------------

class TestReranker:
    def test_run_level_record_ranks_before_project_level(self) -> None:
        scope_run = Scope(project_id="p-1", work_unit_id="wu-1", run_id="run-1")
        scope_project = Scope(project_id="p-1")

        def _make(mid: str, scope: Scope, quality: str) -> CommittedMemoryRecord:
            return CommittedMemoryRecord(
                memory_id=mid,
                memory_type="semantic",
                scope=scope,
                summary=f"Record {mid}",
                remembered_points=(f"Point in {mid}.",),
                why_it_matters=f"Matters for {mid}.",
                support_quality=quality,
                stability="stable",
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:00+00:00",
                support_refs=(_ref(),),
            )

        run_record = _make("m-run", scope_run, "moderate")
        project_record = _make("m-project", scope_project, "strong")

        ranked = rerank(
            [project_record, run_record],
            request_scope=scope_run,
            query_text=None,
        )
        assert ranked[0].memory_id == "m-run"

    def test_active_before_superseded(self) -> None:
        scope = Scope(project_id="p-1")

        def _make(mid: str, status: str) -> CommittedMemoryRecord:
            return CommittedMemoryRecord(
                memory_id=mid,
                memory_type="semantic",
                scope=scope,
                summary=f"Record {mid}",
                remembered_points=(f"Point {mid}.",),
                why_it_matters=f"Matters {mid}.",
                support_quality="strong",
                stability="stable",
                record_status=status,
                created_at="2026-01-01T00:00:00+00:00",
                updated_at="2026-01-01T00:00:00+00:00",
                support_refs=(_ref(),),
            )

        superseded = _make("m-old", "superseded")
        active = _make("m-new", "active")
        ranked = rerank([superseded, active], request_scope=scope, query_text=None)
        assert ranked[0].memory_id == "m-new"
