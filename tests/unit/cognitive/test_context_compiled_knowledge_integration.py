from pathlib import Path

from jeff.cognitive.context import assemble_context_package
from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.research.archive import create_research_brief, save_archive_artifact
from jeff.cognitive.types import SupportInput, TriggerInput
from jeff.core.schemas import Scope
from jeff.core.state import bootstrap_global_state
from jeff.core.transition import TransitionRequest, apply_transition
from jeff.knowledge import (
    KnowledgeStore,
    create_source_digest_from_archive_artifact,
    create_source_digest_from_research_record,
    create_topic_note,
    relabel_artifact,
    save_knowledge_artifact,
)
from jeff.memory import InMemoryMemoryStore, MemorySupportRef, create_memory_candidate, write_memory_candidate


def _state_with_run(*, project_id: str = "project-1"):
    state = bootstrap_global_state()
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-1",
            transition_type="create_project",
            basis_state_version=0,
            scope=Scope(project_id=project_id),
            payload={"name": f"Project {project_id}"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-2",
            transition_type="create_work_unit",
            basis_state_version=1,
            scope=Scope(project_id=project_id),
            payload={"work_unit_id": "wu-1", "objective": "Lawful context assembly"},
        ),
    ).state
    state = apply_transition(
        state,
        TransitionRequest(
            transition_id=f"{project_id}-transition-3",
            transition_type="create_run",
            basis_state_version=2,
            scope=Scope(project_id=project_id, work_unit_id="wu-1"),
            payload={"run_id": "run-1"},
        ),
    ).state
    return state


def _scope(*, project_id: str = "project-1") -> Scope:
    return Scope(project_id=project_id, work_unit_id="wu-1", run_id="run-1")


def _research_record(*, project_id: str = "project-1") -> ResearchArtifactRecord:
    return ResearchArtifactRecord(
        artifact_id=f"research-{project_id}",
        project_id=project_id,
        work_unit_id="wu-1",
        run_id="run-1",
        question="What thematic support should stay visible?",
        source_mode="prepared_evidence",
        summary="Thematic support helps later follow-up without becoming truth.",
        findings=(ResearchFinding(text="Prior research narrowed the topic.", source_refs=("source-1",)),),
        inferences=("Compiled knowledge can summarize repeat themes.",),
        uncertainties=("Freshness still matters.",),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(),
        evidence_items=(),
        created_at="2026-04-19T10:00:00+00:00",
    )


def _persist_memory(store: InMemoryMemoryStore, *, scope: Scope, summary: str) -> None:
    candidate = create_memory_candidate(
        candidate_id=f"candidate-{summary[:8]}",
        memory_type="semantic",
        scope=scope,
        summary=summary,
        remembered_points=("Memory support should remain ahead of compiled knowledge.",),
        why_it_matters="This continuity signal accelerates bounded context reuse.",
        support_refs=(
            MemorySupportRef(ref_kind="research", ref_id="research-1", summary="Research grounded this memory."),
        ),
        support_quality="strong",
        stability="stable",
    )
    write_memory_candidate(candidate=candidate, store=store)


def _persist_topic_note(store: KnowledgeStore, *, project_id: str = "project-1", topic: str = "thematic support"):
    archive_artifact = create_research_brief(
        project_id=project_id,
        work_unit_id="wu-1",
        run_id="run-1",
        title="Direct evidence brief",
        summary="Direct evidence remains available for bounded verification.",
        question_or_objective="What evidence is still directly inspectable?",
        findings=("A direct brief remains available.",),
        inference=("Compiled knowledge should not suppress direct evidence.",),
        uncertainty=("Evidence posture can still change.",),
        source_refs=("source-1",),
    )
    digest_a = create_source_digest_from_research_record(_research_record(project_id=project_id))
    digest_b = create_source_digest_from_archive_artifact(archive_artifact)
    save_knowledge_artifact(digest_a, store=store)
    save_knowledge_artifact(digest_b, store=store)
    note = create_topic_note(
        topic=topic,
        supports=(digest_a, digest_b),
        major_supported_points=("The theme stays useful as support-only background.",),
        contested_points=("Freshness posture still matters.",),
        unresolved_items=("Operator confirmation may still be needed.",),
        topic_framing="A bounded topic note supports later follow-up without becoming truth.",
    )
    save_knowledge_artifact(note, store=store)
    return archive_artifact, note


def test_context_keeps_truth_first_and_memory_ahead_of_compiled_knowledge(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path)

    _persist_memory(memory_store, scope=scope, summary="Remember the last thematic framing.")
    _persist_topic_note(knowledge_store)

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue the thematic proposal follow-up."),
        purpose="proposal support",
        scope=scope,
        state=state,
        memory_store=memory_store,
        knowledge_store=knowledge_store,
    )

    assert [record.truth_family for record in context.truth_records] == ["project", "work_unit", "run"]
    assert context.memory_support_inputs
    assert context.compiled_knowledge_support_inputs
    assert context.ordered_support_inputs[: len(context.memory_support_inputs)] == context.memory_support_inputs
    assert all(item.source_family == "compiled_knowledge" for item in context.compiled_knowledge_support_inputs)


def test_context_includes_compiled_knowledge_only_when_purpose_gating_allows_it(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    knowledge_store = KnowledgeStore(tmp_path)
    _persist_topic_note(knowledge_store)

    allowed = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue the research topic."),
        purpose="research continuation",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
    )
    blocked = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Answer the current state question directly."),
        purpose="current truth status check",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
    )

    assert allowed.compiled_knowledge_support_inputs
    assert blocked.compiled_knowledge_support_inputs == ()


def test_context_rejects_cross_project_compiled_knowledge_retrieval_by_scope(tmp_path: Path) -> None:
    state = _state_with_run(project_id="project-1")
    scope = _scope(project_id="project-1")
    knowledge_store = KnowledgeStore(tmp_path)
    _persist_topic_note(knowledge_store, project_id="project-2")

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue proposal support."),
        purpose="proposal support",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
    )

    assert context.compiled_knowledge_support_inputs == ()


def test_stale_compiled_knowledge_stays_labeled_as_support(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    knowledge_store = KnowledgeStore(tmp_path)
    _, note = _persist_topic_note(knowledge_store)
    relabel_artifact(
        project_id="project-1",
        artifact_id=str(note.artifact_id),
        status="stale_review_needed",
        store=knowledge_store,
    )

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Explain the thematic background."),
        purpose="operator explanation",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
    )

    assert context.compiled_knowledge_support_inputs
    assert "[stale_review_needed]" in context.compiled_knowledge_support_inputs[0].summary
    assert all("stale_review_needed" not in record.summary for record in context.truth_records)


def test_compiled_knowledge_does_not_create_memory_objects(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    memory_store = InMemoryMemoryStore()
    knowledge_store = KnowledgeStore(tmp_path)
    _persist_topic_note(knowledge_store)

    before = memory_store.list_project_records("project-1")
    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue the research topic."),
        purpose="research continuation",
        scope=scope,
        state=state,
        memory_store=memory_store,
        knowledge_store=knowledge_store,
    )
    after = memory_store.list_project_records("project-1")

    assert context.compiled_knowledge_support_inputs
    assert before == after == ()


def test_direct_evidence_purpose_keeps_archive_support_alongside_compiled_knowledge(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    knowledge_store = KnowledgeStore(tmp_path)
    archive_dir = tmp_path / "archive"
    archive_dir.mkdir()
    from jeff.cognitive.research.archive import ResearchArchiveStore

    archive_store = ResearchArchiveStore(archive_dir)
    archive_artifact, _ = _persist_topic_note(knowledge_store)
    save_archive_artifact(archive_artifact, store=archive_store)

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Support the proposal with direct evidence."),
        purpose="proposal support direct evidence",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
        archive_store=archive_store,
    )

    assert context.compiled_knowledge_support_inputs
    assert context.archive_support_inputs
    assert context.ordered_support_inputs.index(context.compiled_knowledge_support_inputs[0]) < context.ordered_support_inputs.index(context.archive_support_inputs[0])


def test_context_stays_bounded_and_dedupes_overlapping_topic_notes(tmp_path: Path) -> None:
    state = _state_with_run()
    scope = _scope()
    knowledge_store = KnowledgeStore(tmp_path)
    _, first = _persist_topic_note(knowledge_store, topic="overlap topic")
    relabel_artifact(
        project_id="project-1",
        artifact_id=str(first.artifact_id),
        status="stale_review_needed",
        store=knowledge_store,
    )
    _persist_topic_note(knowledge_store, topic="overlap topic")

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Continue the overlap topic."),
        purpose="research continuation",
        scope=scope,
        state=state,
        knowledge_store=knowledge_store,
    )

    assert len(context.compiled_knowledge_support_inputs) == 1


def test_existing_direct_support_behavior_remains_available_without_runtime_stores() -> None:
    state = _state_with_run()
    scope = _scope()
    direct_support = SupportInput(
        source_family="research",
        scope=scope,
        summary="A bounded direct research note remains available.",
    )

    context = assemble_context_package(
        trigger=TriggerInput(trigger_summary="Prepare bounded proposal support."),
        purpose="proposal support",
        scope=scope,
        state=state,
        support_inputs=(direct_support,),
    )

    assert context.support_inputs == (direct_support,)
    assert context.memory_support_inputs == ()
    assert context.compiled_knowledge_support_inputs == ()
    assert context.archive_support_inputs == ()