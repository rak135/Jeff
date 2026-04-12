import pytest

from jeff.cognitive import EvidenceItem, ResearchArtifactRecord, ResearchFinding, SourceItem
from jeff.cognitive.research import ResearchProvenanceValidationError
from jeff.interface.json_views import research_result_json
from jeff.interface.render import render_research_result
from jeff.interface.session import CliSession, SessionScope


def test_human_facing_research_rendering_resolves_source_refs_into_title_and_locator() -> None:
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="web",
        handoff_memory_requested=False,
        record=_record(),
        memory_handoff_result=None,
        session=_session(),
    )

    rendered = render_research_result(payload)

    assert "Bounded article | https://example.com/a" in rendered
    assert "artifact_id=research-1" in rendered
    assert "[support] findings" in rendered


def test_source_ids_are_not_primary_human_facing_display_for_findings() -> None:
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="web",
        handoff_memory_requested=False,
        record=_record(),
        memory_handoff_result=None,
        session=_session(),
    )

    rendered = render_research_result(payload)

    assert "[sources:" not in rendered
    assert "source-web-a" not in rendered


def test_multiple_sources_on_one_finding_render_cleanly() -> None:
    record = _record(
        findings=(
            ResearchFinding(
                text="Two sources support the bounded rollout.",
                source_refs=("source-web-a", "source-doc-b"),
            ),
        )
    )
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="mixed",
        handoff_memory_requested=False,
        record=record,
        memory_handoff_result=None,
        session=_session(),
    )

    rendered = render_research_result(payload)

    assert "source: Bounded article | https://example.com/a" in rendered
    assert "source: Local plan | C:/docs/plan.md" in rendered


def test_missing_invalid_linkage_is_not_silently_patched_here() -> None:
    record = _record(
        findings=(ResearchFinding(text="Broken linkage", source_refs=("missing-source",)),),
    )

    with pytest.raises(ResearchProvenanceValidationError):
        research_result_json(
            project_id="project-1",
            work_unit_id="wu-1",
            run_id="run-1",
            research_mode="web",
            handoff_memory_requested=False,
            record=record,
            memory_handoff_result=None,
            session=_session(),
        )


def test_support_vs_truth_distinction_remains_visible_and_date_is_not_fabricated() -> None:
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="web",
        handoff_memory_requested=False,
        record=_record(),
        memory_handoff_result=None,
        session=_session(),
    )

    assert set(payload["truth"]) == {"project_id", "work_unit_id", "run_id"}
    assert payload["support"]["sources"][0]["title"] == "Bounded article"
    assert payload["support"]["sources"][0]["locator"] == "https://example.com/a"
    assert payload["support"]["sources"][0]["published_at"] is None
    assert payload["support"]["findings"][0]["resolved_sources"][0]["source_id"] == "source-web-a"


def _record(
    *,
    findings: tuple[ResearchFinding, ...] | None = None,
) -> ResearchArtifactRecord:
    actual_findings = findings or (
        ResearchFinding(
            text="The article supports the bounded rollout.",
            source_refs=("source-web-a",),
        ),
    )
    return ResearchArtifactRecord(
        artifact_id="research-1",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        question="What does the bounded rollout support?",
        source_mode="web",
        summary="The fetched source supports a bounded rollout.",
        findings=actual_findings,
        inferences=("A narrow path remains better supported.",),
        uncertainties=("Only bounded support was considered.",),
        recommendation="Keep the rollout bounded.",
        source_ids=("source-web-a", "source-doc-b"),
        source_items=(
            SourceItem(
                source_id="source-web-a",
                source_type="web",
                title="Bounded article",
                locator="https://example.com/a",
                snippet="The bounded rollout remains stable.",
            ),
            SourceItem(
                source_id="source-doc-b",
                source_type="document",
                title="Local plan",
                locator="C:/docs/plan.md",
                snippet="The bounded plan avoids widening scope.",
            ),
        ),
        evidence_items=(
            EvidenceItem(text="The bounded rollout remains stable.", source_refs=("source-web-a",)),
            EvidenceItem(text="The bounded plan avoids widening scope.", source_refs=("source-doc-b",)),
        ),
        created_at="2026-04-12T11:00:00+00:00",
    )


def _session() -> CliSession:
    return CliSession(scope=SessionScope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"))
