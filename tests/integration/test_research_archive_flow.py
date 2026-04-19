from pathlib import Path

from jeff.cognitive.research.archive import (
    ResearchArchiveStore,
    create_brief_history_record,
    create_event_history_record,
    create_research_brief,
    create_research_comparison,
    get_archive_artifact_by_id,
    retrieve_project_archive,
    save_archive_artifact,
)


def test_archive_exact_retrieval_family_retrieval_and_wrong_project_rejection(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    brief = create_research_brief(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Brief",
        summary="A stored brief stays project-scoped.",
        question_or_objective="What changed?",
        findings=("Finding A",),
        inference=("Inference A",),
        uncertainty=("Uncertainty A",),
        source_refs=("source-1",),
    )
    comparison = create_research_comparison(
        project_id="project-1",
        work_unit_id="wu-1",
        title="Comparison",
        summary="A stored comparison stays queryable by family.",
        question_or_objective="Which option fits?",
        comparison_targets=("option-a", "option-b"),
        comparison_criteria=("fit",),
        findings=("Option A fits.",),
        inference=(),
        uncertainty=("Implementation cost is still unclear.",),
        source_refs=("source-2",),
    )
    save_archive_artifact(brief, store=store)
    save_archive_artifact(comparison, store=store)

    loaded = get_archive_artifact_by_id("project-1", str(brief.artifact_id), store=store)
    wrong_project = get_archive_artifact_by_id("project-2", str(brief.artifact_id), store=store)
    family_result = retrieve_project_archive(
        purpose="comparison reuse",
        project_id="project-1",
        work_unit_id="wu-1",
        artifact_family_filter="research_comparison",
        store=store,
    )
    project_result = retrieve_project_archive(
        purpose="project archive overview",
        project_id="project-1",
        store=store,
        result_limit=10,
    )

    assert loaded == brief
    assert wrong_project is None
    assert family_result.records == (comparison,)
    assert {record.artifact_id for record in project_result.records} == {
        brief.artifact_id,
        comparison.artifact_id,
    }


def test_history_retrieval_stays_explicitly_historical_and_bounded(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    first = create_brief_history_record(
        project_id="project-1",
        title="Daily brief 1",
        summary="First historical brief.",
        source_refs=("source-1",),
        freshness_posture="dated",
        effective_date="2026-04-18",
    )
    second = create_brief_history_record(
        project_id="project-1",
        title="Daily brief 2",
        summary="Second historical brief.",
        source_refs=("source-2",),
        freshness_posture="dated",
        effective_date="2026-04-19",
    )
    weekly = create_brief_history_record(
        project_id="project-1",
        title="Weekly brief",
        summary="Weekly historical brief.",
        source_refs=("source-3",),
        freshness_posture="historical",
        effective_period="2026-W16",
    )
    save_archive_artifact(first, store=store)
    save_archive_artifact(second, store=store)
    save_archive_artifact(weekly, store=store)

    dated_result = retrieve_project_archive(
        purpose="daily history lookup",
        project_id="project-1",
        store=store,
        history_only=True,
        effective_date="2026-04-19",
        result_limit=2,
    )
    period_result = retrieve_project_archive(
        purpose="weekly history lookup",
        project_id="project-1",
        store=store,
        history_only=True,
        effective_period="2026-W16",
        result_limit=1,
    )
    bounded = retrieve_project_archive(
        purpose="bounded history overview",
        project_id="project-1",
        store=store,
        history_only=True,
        result_limit=2,
    )

    assert dated_result.explicitly_historical is True
    assert dated_result.records == (second,)
    assert any("explicitly historical" in note for note in dated_result.notes)
    assert period_result.records == (weekly,)
    assert len(bounded.records) == 2
    assert all(record.artifact_family == "brief_history_record" for record in bounded.records)


def test_event_history_retrieval_stays_explicitly_historical_and_support_only(tmp_path: Path) -> None:
    store = ResearchArchiveStore(tmp_path)
    dated = create_event_history_record(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        title="Release event",
        summary="A release record remained historical support.",
        event_framing="Release event captured as dated support.",
        source_refs=("source-1",),
        event_date="2026-04-19",
        uncertainty=("Rollout depth was still uncertain.",),
    )
    observed = create_event_history_record(
        project_id="project-1",
        work_unit_id="wu-1",
        title="Observed development",
        summary="An observed development remained historical support.",
        event_framing="Observed service change captured as historical support.",
        source_refs=("source-2",),
        observed_date="2026-04-20",
        uncertainty=("Cause was not yet confirmed.",),
    )
    save_archive_artifact(dated, store=store)
    save_archive_artifact(observed, store=store)

    by_family = retrieve_project_archive(
        purpose="event history lookup",
        project_id="project-1",
        work_unit_id="wu-1",
        artifact_family_filter="event_history_record",
        store=store,
    )
    by_date = retrieve_project_archive(
        purpose="dated event history lookup",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        artifact_family_filter="event_history_record",
        effective_date="2026-04-19",
        store=store,
    )
    by_observed_date = retrieve_project_archive(
        purpose="observed event history lookup",
        project_id="project-1",
        work_unit_id="wu-1",
        artifact_family_filter="event_history_record",
        observed_date="2026-04-20",
        store=store,
    )

    assert by_family.explicitly_historical is True
    assert all(record.artifact_family == "event_history_record" for record in by_family.records)
    assert any("explicitly historical" in note for note in by_family.notes)
    assert by_family.support_only is True
    assert by_date.records == (dated,)
    assert by_observed_date.records == (observed,)
    assert get_archive_artifact_by_id("project-2", str(dated.artifact_id), store=store) is None