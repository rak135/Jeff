from pathlib import Path

import pytest

from jeff.cognitive.research import ResearchArtifactRecord, ResearchFinding
from jeff.cognitive.research.archive import (
    ArchiveEvidenceItem,
    ClaimEvidenceLink,
    create_evidence_bundle,
    create_research_brief,
)
from jeff.cognitive.research.contracts import EvidenceItem, SourceItem
from jeff.knowledge import (
    KnowledgeRetrievalRequest,
    KnowledgeStore,
    build_memory_handoff_signal,
    create_source_digest_from_archive_artifact,
    create_source_digest_from_research_record,
    create_topic_note,
    get_knowledge_artifact_by_id,
    refresh_knowledge_artifact,
    relabel_artifact,
    retrieve_project_knowledge,
    save_knowledge_artifact,
    supersede_artifact,
)


def _research_record(*, project_id: str = "project-1", work_unit_id: str | None = "wu-1", run_id: str | None = "run-1") -> ResearchArtifactRecord:
    return ResearchArtifactRecord(
        artifact_id="research-artifact-1",
        project_id=project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        question="What should Jeff keep as bounded support?",
        source_mode="prepared_evidence",
        summary="Jeff should preserve support in a bounded, inspectable form.",
        findings=(ResearchFinding(text="Bounded support remains inspectable.", source_refs=("source-1",)),),
        inferences=("A digest can sit between raw research and memory.",),
        uncertainties=("Long-term maintenance cadence is still unsettled.",),
        recommendation=None,
        source_ids=("source-1", "source-2"),
        source_items=(
            SourceItem(source_id="source-1", source_type="doc", title="Doc 1"),
            SourceItem(source_id="source-2", source_type="web", title="Doc 2"),
        ),
        evidence_items=(
            EvidenceItem(text="Evidence A", source_refs=("source-1",)),
            EvidenceItem(text="Evidence B", source_refs=("source-2",)),
        ),
        created_at="2026-04-19T10:00:00+00:00",
    )


def _archive_artifact(*, project_id: str = "project-1", work_unit_id: str | None = "wu-1", run_id: str | None = "run-1"):
    return create_evidence_bundle(
        project_id=project_id,
        work_unit_id=work_unit_id,
        run_id=run_id,
        title="Evidence bundle",
        summary="Evidence remains inspectable for later compilation.",
        question_or_objective="What evidence supports the bounded answer?",
        source_refs=("source-1", "source-2"),
        evidence_items=(
            ArchiveEvidenceItem(
                evidence_id="evidence-1",
                claim="Claim A",
                evidence_text="Evidence text A",
                source_refs=("source-1",),
            ),
            ArchiveEvidenceItem(
                evidence_id="evidence-2",
                claim="Claim B",
                evidence_text="Evidence text B",
                source_refs=("source-2",),
            ),
        ),
        claim_evidence_links=(
            ClaimEvidenceLink(claim_text="Claim A", evidence_ids=("evidence-1",)),
            ClaimEvidenceLink(claim_text="Claim B", evidence_ids=("evidence-2",)),
        ),
    )


def test_source_digest_from_research_record_preserves_support_only_provenance() -> None:
    digest = create_source_digest_from_research_record(_research_record())

    assert digest.artifact_family == "source_digest"
    assert digest.support_only is True
    assert digest.truth_posture == "support_only"
    assert digest.source_refs == ("source-1", "source-2")
    assert digest.provenance[0].upstream_kind == "research_artifact_record"


def test_source_digest_from_archive_artifact_preserves_evidence_and_caveats() -> None:
    digest = create_source_digest_from_archive_artifact(_archive_artifact())

    assert digest.evidence_points == ("Evidence text A", "Evidence text B")
    assert digest.provenance[0].upstream_kind == "research_archive_artifact"
    assert digest.source_refs == ("source-1", "source-2")


def test_topic_note_preserves_supported_contested_and_unresolved_points() -> None:
    digest_a = create_source_digest_from_research_record(_research_record())
    digest_b = create_source_digest_from_archive_artifact(_archive_artifact())

    note = create_topic_note(
        topic="bounded knowledge",
        supports=(digest_a, digest_b),
        major_supported_points=("Compiled knowledge can stay inspectable and support-only.",),
        contested_points=("Whether every digest should trigger a memory review remains open.",),
        unresolved_items=("Staleness refresh policy needs operator tuning.",),
        topic_framing="Compiled knowledge summarizes a bounded topic without collapsing provenance.",
    )

    assert note.artifact_family == "topic_note"
    assert note.supporting_artifact_ids == tuple(sorted((str(digest_a.artifact_id), str(digest_b.artifact_id))))
    assert note.contested_points == ("Whether every digest should trigger a memory review remains open.",)
    assert note.unresolved_items == ("Staleness refresh policy needs operator tuning.",)


def test_topic_note_rejects_cross_project_support_inputs() -> None:
    digest_a = create_source_digest_from_research_record(_research_record(project_id="project-1"))
    digest_b = create_source_digest_from_research_record(_research_record(project_id="project-2"))

    with pytest.raises(ValueError, match="project boundaries"):
        create_topic_note(
            topic="bounded knowledge",
            supports=(digest_a, digest_b),
            major_supported_points=("Point",),
        )


def test_knowledge_persists_under_project_scoped_registry_and_family_dirs(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest = create_source_digest_from_research_record(_research_record())

    path = Path(save_knowledge_artifact(digest, store=store))

    assert path == tmp_path / "projects" / "project-1" / "research" / "knowledge" / "source_digests" / f"{digest.artifact_id}.json"
    assert (tmp_path / "projects" / "project-1" / "research" / "knowledge" / "registry.json").exists()


def test_exact_lookup_returns_saved_artifact() -> None:
    store = KnowledgeStore(Path(".") / ".pytest_knowledge_exact")
    try:
        digest = create_source_digest_from_research_record(_research_record())
        save_knowledge_artifact(digest, store=store)

        loaded = get_knowledge_artifact_by_id(project_id="project-1", artifact_id=str(digest.artifact_id), store=store)

        assert loaded is not None
        assert loaded.artifact_id == digest.artifact_id
    finally:
        import shutil

        shutil.rmtree(store.root_dir, ignore_errors=True)


def test_duplicate_topic_notes_are_rejected(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest_a = create_source_digest_from_research_record(_research_record())
    digest_b = create_source_digest_from_archive_artifact(_archive_artifact())
    save_knowledge_artifact(digest_a, store=store)
    save_knowledge_artifact(digest_b, store=store)
    note = create_topic_note(
        topic="bounded knowledge",
        supports=(digest_a, digest_b),
        major_supported_points=("Point",),
    )
    save_knowledge_artifact(note, store=store)

    with pytest.raises(ValueError, match="duplicate active topic_note"):
        save_knowledge_artifact(
            create_topic_note(
                topic="bounded knowledge",
                supports=(digest_a, digest_b),
                major_supported_points=("Point",),
            ),
            store=store,
        )


def test_supersession_preserves_old_artifact_for_inspection(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    original = create_source_digest_from_research_record(_research_record())
    save_knowledge_artifact(original, store=store)
    replacement = refresh_knowledge_artifact(original, source_summary="Refreshed source summary.")

    superseded = supersede_artifact(
        project_id="project-1",
        superseded_artifact_id=str(original.artifact_id),
        replacement=replacement,
        store=store,
    )

    preserved_original = get_knowledge_artifact_by_id(project_id="project-1", artifact_id=str(original.artifact_id), store=store)
    assert superseded.supersedes_artifact_id == str(original.artifact_id)
    assert preserved_original is not None
    assert preserved_original.status == "superseded"
    assert preserved_original.superseded_by_artifact_id == str(superseded.artifact_id)


def test_retrieval_is_bounded_and_labels_stale_artifacts_explicitly(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest_a = create_source_digest_from_research_record(_research_record())
    digest_b = create_source_digest_from_archive_artifact(_archive_artifact())
    extra = create_source_digest_from_research_record(_research_record(run_id=None, work_unit_id=None))
    note_one = create_topic_note(
        topic="bounded knowledge",
        supports=(digest_a, digest_b),
        major_supported_points=("Point A",),
    )
    note_two = create_topic_note(
        topic="bounded knowledge",
        supports=(digest_a, extra),
        major_supported_points=("Point B",),
    )
    for artifact in (digest_a, digest_b, extra, note_one, note_two):
        save_knowledge_artifact(artifact, store=store)
    relabel_artifact(project_id="project-1", artifact_id=str(note_one.artifact_id), status="stale_review_needed", store=store)

    result = retrieve_project_knowledge(
        KnowledgeRetrievalRequest(
            project_id="project-1",
            purpose="context support",
            artifact_family="topic_note",
            topic_query="bounded knowledge",
            work_unit_id="wu-1",
            run_id="run-1",
            limit=5,
        ),
        store=store,
    )

    assert len(result.artifacts) == 1
    assert str(note_one.artifact_id) in result.stale_artifact_ids or str(note_two.artifact_id) in {str(item.artifact_id) for item in result.artifacts}
    assert any("below truth and committed memory" in note for note in result.notes)


def test_scope_aware_retrieval_excludes_narrower_run_local_items_from_project_wide_fetch(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    project_digest = create_source_digest_from_research_record(_research_record(work_unit_id=None, run_id=None))
    run_digest = create_source_digest_from_research_record(_research_record(work_unit_id="wu-1", run_id="run-1"))
    save_knowledge_artifact(project_digest, store=store)
    save_knowledge_artifact(run_digest, store=store)

    result = retrieve_project_knowledge(
        KnowledgeRetrievalRequest(project_id="project-1", purpose="project context", limit=10),
        store=store,
    )

    assert {str(artifact.artifact_id) for artifact in result.artifacts} == {str(project_digest.artifact_id)}


def test_exact_lookup_does_not_cross_projects(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest = create_source_digest_from_research_record(_research_record(project_id="project-2"))
    save_knowledge_artifact(digest, store=store)

    loaded = get_knowledge_artifact_by_id(project_id="project-1", artifact_id=str(digest.artifact_id), store=store)

    assert loaded is None


def test_memory_handoff_signal_is_only_a_signal_and_does_not_create_memory(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest = create_source_digest_from_research_record(_research_record())
    signal = build_memory_handoff_signal(digest)
    digest_with_signal = refresh_knowledge_artifact(digest, memory_handoff_signal=signal)

    save_knowledge_artifact(digest_with_signal, store=store)

    assert digest_with_signal.memory_handoff_signal is not None
    assert not (tmp_path / "projects" / "project-1" / "memory").exists()


def test_knowledge_save_does_not_auto_create_research_history(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest = create_source_digest_from_research_record(_research_record())

    save_knowledge_artifact(digest, store=store)

    assert not (tmp_path / "projects" / "project-1" / "research" / "history").exists()


def test_retrieval_declares_truth_first_ordering_for_context_usage(tmp_path: Path) -> None:
    store = KnowledgeStore(tmp_path)
    digest = create_source_digest_from_research_record(_research_record(work_unit_id=None, run_id=None))
    save_knowledge_artifact(digest, store=store)

    result = retrieve_project_knowledge(
        KnowledgeRetrievalRequest(project_id="project-1", purpose="context support"),
        store=store,
    )

    assert result.context_priority == "after_committed_memory"
    assert result.intended_context_order == (
        "canonical_truth",
        "governance_truth",
        "committed_memory",
        "compiled_knowledge",
        "raw_sources",
    )


def test_topic_note_can_link_real_archive_and_research_outputs_together() -> None:
    digest_a = create_source_digest_from_research_record(_research_record())
    digest_b = create_source_digest_from_archive_artifact(
        create_research_brief(
            project_id="project-1",
            work_unit_id="wu-1",
            run_id="run-1",
            title="Brief",
            summary="A research brief remains a lawful upstream input.",
            question_or_objective="What is the lawful upstream input?",
            findings=("A persisted research brief is valid support.",),
            inference=("Compiled knowledge can reuse archive outputs directly.",),
            uncertainty=("Operator policy still decides what to preserve.",),
            source_refs=("source-1",),
        )
    )

    note = create_topic_note(
        topic="integration path",
        supports=(digest_a, digest_b),
        major_supported_points=("Knowledge compilation reuses real research/archive outputs only.",),
    )

    assert note.supporting_artifact_ids == tuple(sorted((str(digest_a.artifact_id), str(digest_b.artifact_id))))