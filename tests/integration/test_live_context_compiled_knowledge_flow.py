from pathlib import Path

from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.research.archive import ResearchArchiveStore, create_research_brief, save_archive_artifact
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.interface import InterfaceContext, assemble_live_context_package
from jeff.knowledge import (
    KnowledgeStore,
    create_source_digest_from_archive_artifact,
    create_source_digest_from_research_record,
    create_topic_note,
    save_knowledge_artifact,
)
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate


def _state() -> object:
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-project",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id="project-1"),
            payload={"name": "Alpha"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-work-unit",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id="project-1"),
            payload={"work_unit_id": "wu-1", "objective": "Live context support"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id="transition-run",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id="project-1", work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    ).state
    return state


def _research_record() -> ResearchArtifactRecord:
    return ResearchArtifactRecord(
        artifact_id="research-record-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        question="What topic support should the live context helper surface?",
        source_mode="prepared_evidence",
        summary="The live helper should reuse the same truth-first context assembler.",
        findings=(ResearchFinding(text="A bounded topic summary remains useful.", source_refs=("source-1",)),),
        inferences=("Compiled knowledge remains support-only.",),
        uncertainties=("Freshness should stay visible.",),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )


def test_assemble_live_context_package_uses_existing_runtime_stores(tmp_path: Path) -> None:
    scope = Scope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path / "knowledge")
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    write_memory_candidate(
        candidate=create_memory_candidate(
            candidate_id="candidate-1",
            memory_type="semantic",
            scope=scope,
            summary="The prior operator explanation used the thematic background.",
            remembered_points=("Memory support stays ahead of compiled knowledge in context.",),
            why_it_matters="This continuity signal is still relevant for live explanation.",
            support_refs=(
                MemorySupportRef(ref_kind="research", ref_id="research-record-1", summary="Grounded in research."),
            ),
            support_quality="strong",
            stability="stable",
        ),
        store=memory_store,
    )

    archive_artifact = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Live evidence brief",
        summary="Direct evidence remains available for operator inspection.",
        question_or_objective="What direct evidence still matters?",
        findings=("One direct brief remains inspectable.",),
        inference=("Live context should keep direct evidence separate from thematic notes.",),
        uncertainty=("Evidence may still need refresh.",),
        source_refs=("source-1",),
    )
    save_archive_artifact(archive_artifact, store=archive_store)

    digest_a = create_source_digest_from_research_record(_research_record())
    digest_b = create_source_digest_from_archive_artifact(archive_artifact)
    save_knowledge_artifact(digest_a, store=knowledge_store)
    save_knowledge_artifact(digest_b, store=knowledge_store)
    save_knowledge_artifact(
        create_topic_note(
            topic="live context support",
            supports=(digest_a, digest_b),
            major_supported_points=("Live context can surface thematic support without weakening truth-first ordering.",),
            topic_framing="The live runtime helper reuses the same bounded compiled-knowledge path.",
        ),
        store=knowledge_store,
    )

    context = assemble_live_context_package(
        context=InterfaceContext(
            state=_state(),
            memory_store=memory_store,
            knowledge_store=knowledge_store,
            research_archive_store=archive_store,
        ),
        trigger_summary="Explain the thematic background with direct evidence.",
        purpose="operator explanation direct evidence",
        scope=scope,
    )

    assert context.memory_support_inputs
    assert context.compiled_knowledge_support_inputs
    assert context.archive_support_inputs
    assert context.ordered_support_inputs[: len(context.memory_support_inputs)] == context.memory_support_inputs