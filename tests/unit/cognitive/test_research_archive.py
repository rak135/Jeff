from pathlib import Path

from jeff.cognitive.research.archive import (
    ArchiveEvidenceItem,
    ClaimEvidenceLink,
    ResearchArchiveStore,
    SourceGrouping,
    create_brief_history_record,
    create_event_history_record,
    create_evidence_bundle,
    create_research_brief,
    create_research_comparison,
    create_source_set,
    refresh_archive_artifact,
    save_archive_artifact,
)


def test_research_brief_preserves_source_refs() -> None:
    artifact = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Brief",
        summary="A bounded answer remains available for later inspection.",
        question_or_objective="What is the bounded answer?",
        findings=("Finding A",),
        inference=("Inference A",),
        uncertainty=("Uncertainty A",),
        source_refs=("source-1", "source-2"),
    )

    assert artifact.artifact_family == "research_brief"
    assert artifact.source_refs == ("source-1", "source-2")


def test_research_comparison_preserves_compared_alternatives_clearly() -> None:
    artifact = create_research_comparison(
        project_id="project-1",
        title="Comparison",
        summary="Two bounded alternatives were compared.",
        question_or_objective="Which bounded path fits best?",
        comparison_targets=("option-a", "option-b"),
        comparison_criteria=("fit", "risk"),
        findings=("Option A fits the current constraints better.",),
        inference=("Option A is the narrower next move.",),
        uncertainty=("Long-term cost is still uncertain.",),
        source_refs=("source-1",),
    )

    assert artifact.comparison_targets == ("option-a", "option-b")
    assert artifact.comparison_criteria == ("fit", "risk")


def test_evidence_bundle_preserves_source_evidence_linkage() -> None:
    evidence_items = (
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
    )
    artifact = create_evidence_bundle(
        project_id="project-1",
        title="Evidence bundle",
        summary="Evidence remains inspectable.",
        question_or_objective="What evidence supports the bounded answer?",
        source_refs=("source-1", "source-2"),
        evidence_items=evidence_items,
        claim_evidence_links=(
            ClaimEvidenceLink(claim_text="Claim A", evidence_ids=("evidence-1",)),
            ClaimEvidenceLink(claim_text="Claim B", evidence_ids=("evidence-2",)),
        ),
    )

    assert artifact.evidence_refs == ("evidence-1", "evidence-2")
    assert artifact.claim_evidence_links[0].evidence_ids == ("evidence-1",)
    assert artifact.evidence_items[1].source_refs == ("source-2",)


def test_source_set_preserves_bounded_source_selection() -> None:
    artifact = create_source_set(
        project_id="project-1",
        title="Source set",
        summary="The bounded source set remains reproducible.",
        source_refs=("source-1", "source-2", "source-3"),
        source_selection_scope="Top three sources selected for the daily brief.",
        source_ordering=("source-2", "source-1", "source-3"),
        source_groupings=(
            SourceGrouping(group_name="authoritative", source_refs=("source-2", "source-1")),
            SourceGrouping(group_name="supplemental", source_refs=("source-3",)),
        ),
    )

    assert artifact.source_selection_scope == "Top three sources selected for the daily brief."
    assert artifact.source_ordering == ("source-2", "source-1", "source-3")
    assert artifact.source_groupings[0].group_name == "authoritative"


def test_brief_history_record_preserves_date_or_period_correctly() -> None:
    dated = create_brief_history_record(
        project_id="project-1",
        title="Daily brief",
        summary="Daily brief remained explicitly historical.",
        source_refs=("source-1",),
        freshness_posture="dated",
        effective_date="2026-04-19",
    )
    period = create_brief_history_record(
        project_id="project-1",
        title="Weekly brief",
        summary="Weekly brief remained explicitly historical.",
        source_refs=("source-2",),
        freshness_posture="historical",
        effective_period="2026-W16",
    )

    assert dated.effective_date == "2026-04-19"
    assert dated.effective_period is None
    assert period.effective_period == "2026-W16"
    assert period.effective_date is None


def test_event_history_record_preserves_event_and_observed_date_semantics() -> None:
    dated = create_event_history_record(
        project_id="project-1",
        title="Release event",
        summary="A release event remained explicitly historical.",
        event_framing="Release announcement captured as dated support.",
        source_refs=("source-1",),
        event_date="2026-04-19",
        uncertainty=("Exact rollout breadth remains uncertain.",),
    )
    observed = create_event_history_record(
        project_id="project-1",
        title="Observed incident",
        summary="An observed incident remained explicitly historical.",
        event_framing="Observed outage report captured as historical support.",
        source_refs=("source-2",),
        observed_date="2026-04-20",
        uncertainty=("Root cause was not yet confirmed.",),
    )

    assert dated.artifact_family == "event_history_record"
    assert dated.event_date == "2026-04-19"
    assert dated.effective_date == "2026-04-19"
    assert dated.observed_date is None
    assert dated.event_framing == "Release announcement captured as dated support."
    assert observed.event_date is None
    assert observed.observed_date == "2026-04-20"
    assert observed.effective_date is None
    assert observed.freshness_posture == "historical"


def test_lineage_survives_refresh_rebuild() -> None:
    original = create_research_brief(
        project_id="project-1",
        title="Brief",
        summary="Original brief summary.",
        question_or_objective="What is the bounded answer?",
        findings=("Finding A",),
        inference=("Inference A",),
        uncertainty=("Uncertainty A",),
        source_refs=("source-1",),
        derived_from_artifact_ids=("artifact-seed",),
    )

    refreshed = refresh_archive_artifact(
        original,
        summary="Refreshed brief summary.",
        generated_at="2026-04-19T12:00:00+00:00",
    )

    assert refreshed.summary == "Refreshed brief summary."
    assert refreshed.artifact_id != original.artifact_id
    assert refreshed.derived_from_artifact_ids == ("artifact-seed", str(original.artifact_id))


def test_archive_objects_do_not_become_memory_automatically(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    artifact = create_research_brief(
        project_id="project-1",
        title="Brief",
        summary="Archive persistence stays in research-owned storage.",
        question_or_objective="What persists?",
        findings=("The archive writes only research support objects.",),
        inference=(),
        uncertainty=(),
        source_refs=("source-1",),
    )

    save_archive_artifact(artifact, store=store)

    assert not (tmp_path / "projects" / "project-1" / "memory").exists()


def test_archive_objects_do_not_become_compiled_knowledge_automatically(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    artifact = create_research_brief(
        project_id="project-1",
        title="Brief",
        summary="Archive persistence does not widen into compiled knowledge.",
        question_or_objective="What does not happen automatically?",
        findings=("No knowledge artifact is created during archive persistence.",),
        inference=(),
        uncertainty=(),
        source_refs=("source-1",),
    )

    path = save_archive_artifact(artifact, store=store)

    assert path.parent == tmp_path / "projects" / "project-1" / "research" / "artifacts"
    assert not (tmp_path / "projects" / "project-1" / "research" / "knowledge").exists()


def test_event_history_objects_stay_in_research_history_without_memory_or_knowledge(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    artifact = create_event_history_record(
        project_id="project-1",
        title="Incident",
        summary="The event record stays in project-scoped research history.",
        event_framing="Observed incident remains historical support only.",
        source_refs=("source-1",),
        observed_date="2026-04-19",
        uncertainty=("Impact assessment remained incomplete.",),
    )

    path = save_archive_artifact(artifact, store=store)

    assert path.parent == tmp_path / "projects" / "project-1" / "research" / "history"
    assert not (tmp_path / "projects" / "project-1" / "memory").exists()
    assert not (tmp_path / "projects" / "project-1" / "research" / "knowledge").exists()