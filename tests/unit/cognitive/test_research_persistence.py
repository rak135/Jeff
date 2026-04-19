import json
from dataclasses import replace
from pathlib import Path

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchArtifactStore,
    ResearchFinding,
    ResearchRequest,
    SourceItem,
    build_research_artifact_record,
    validate_research_artifact_record,
)
from jeff.cognitive.research.archive import (
    ResearchArchiveStore,
    archive_research_record,
    retrieve_project_archive,
)


def test_build_research_artifact_record_preserves_scope_sources_evidence_and_output() -> None:
    request = _request()
    evidence_pack = _evidence_pack()
    artifact = _artifact()

    record = build_research_artifact_record(request, evidence_pack, artifact)

    assert record.project_id == "project-1"
    assert record.work_unit_id == "wu-1"
    assert record.run_id == "run-1"
    assert record.source_mode == "local_documents"
    assert record.source_items == evidence_pack.sources
    assert record.evidence_items == evidence_pack.evidence_items
    assert record.findings == artifact.findings


def test_save_writes_json_file(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())

    path = store.save(record)

    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["artifact_id"] == record.artifact_id


def test_save_uses_configured_root_dir_without_extra_artifact_suffix(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())

    path = store.save(record)

    assert path.parent == tmp_path
    assert path == tmp_path / f"{record.artifact_id}.json"
    assert not (tmp_path / "research_artifacts").exists()


def test_load_round_trips_record(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store.save(record)

    loaded = store.load(record.artifact_id)

    assert loaded == record


def test_list_records_filters_by_scope(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record_a = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    record_b = build_research_artifact_record(
        ResearchRequest(
            question="Q2",
            project_id="project-2",
            work_unit_id="wu-2",
            run_id="run-2",
            source_mode="web",
        ),
        EvidencePack(
            question="Q2",
            sources=(SourceItem(source_id="source-2", source_type="web", title="B", locator="https://b", snippet="B"),),
            evidence_items=(EvidenceItem(text="Evidence B", source_refs=("source-2",)),),
        ),
        ResearchArtifact(
            question="Q2",
            summary="Summary B",
            findings=(ResearchFinding(text="Finding B", source_refs=("source-2",)),),
            inferences=(),
            uncertainties=(),
            recommendation=None,
            source_ids=("source-2",),
        ),
    )
    store.save(record_a)
    store.save(record_b)

    assert store.list_records(project_id="project-1") == (record_a,)
    assert store.list_records(work_unit_id="wu-2") == (record_b,)
    assert store.list_records(run_id="run-1") == (record_a,)


def test_persisted_ordering_is_newest_first(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    older = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    newer = build_research_artifact_record(
        _request(),
        _evidence_pack(),
        ResearchArtifact(
            question="What does the bounded plan support?",
            summary="The bounded plan supports a newer rollout.",
            findings=(ResearchFinding(text="The newer plan still stays narrow.", source_refs=("source-1",)),),
            inferences=("A newer bounded rollout is better supported.",),
            uncertainties=("No external validation.",),
            recommendation="Proceed carefully.",
            source_ids=("source-1",),
        ),
    )
    older_path = store.save(older)
    newer_path = store.save(newer)

    old_payload = json.loads(older_path.read_text(encoding="utf-8"))
    new_payload = json.loads(newer_path.read_text(encoding="utf-8"))
    old_payload["created_at"] = "2026-04-11T20:00:00+00:00"
    new_payload["created_at"] = "2026-04-11T21:00:00+00:00"
    older_path.write_text(json.dumps(old_payload, indent=2, sort_keys=True), encoding="utf-8")
    newer_path.write_text(json.dumps(new_payload, indent=2, sort_keys=True), encoding="utf-8")

    records = store.list_records()

    assert tuple(record.created_at for record in records) == (
        "2026-04-11T21:00:00+00:00",
        "2026-04-11T20:00:00+00:00",
    )


def test_malformed_persisted_json_fails_closed(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    bad_path = tmp_path / "bad.json"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed persisted research artifact file"):
        store.load("bad")


def test_persistence_requires_only_research_contracts_and_filesystem(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())

    path = store.save(record)

    assert path.suffix == ".json"


def test_research_artifact_validation_accepts_summary_longer_than_200_chars() -> None:
    long_summary = (
        "The bounded plan supports a narrow rollout because the prepared evidence consistently points "
        "to keeping scope tight, sequencing work in smaller steps, and avoiding premature expansion while "
        "the current operator-facing path is still being validated against realistic runtime behavior."
    )
    record = build_research_artifact_record(
        _request(),
        _evidence_pack(),
        replace(_artifact(), summary=long_summary),
    )

    validate_research_artifact_record(record)

    assert len(record.summary) > 200
    assert record.summary == long_summary


def test_research_artifact_validation_rejects_whitespace_only_summary() -> None:
    record = replace(build_research_artifact_record(_request(), _evidence_pack(), _artifact()), summary="   ")

    with pytest.raises(ValueError, match="summary must be a non-empty string"):
        validate_research_artifact_record(record)


def test_research_artifact_validation_rejects_obvious_report_dump_summary() -> None:
    dump_summary = "\n".join(
        [
            "FINDINGS:",
            "- text: The plan stays narrow.",
            "  cites: S1",
        ]
    )
    record = replace(build_research_artifact_record(_request(), _evidence_pack(), _artifact()), summary=dump_summary)

    with pytest.raises(ValueError, match="summary must be concise prose"):
        validate_research_artifact_record(record)


def test_archive_research_record_persists_project_scoped_artifacts_without_memory_or_knowledge(tmp_path: Path) -> None:
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store = ResearchArchiveStore(tmp_path / "archive")

    archived = archive_research_record(record, store=store, target_project_id="project-1")
    families = {artifact.artifact_family for artifact in archived}

    assert families == {"research_brief", "evidence_bundle", "source_set"}
    assert store.path_for(archived[0]).parent == store.artifacts_dir_for("project-1")
    assert not (store.root_dir / "projects" / "project-1" / "memory").exists()
    assert not (store.root_dir / "projects" / "project-1" / "research" / "knowledge").exists()


def test_archive_research_record_rejects_wrong_project_write(tmp_path: Path) -> None:
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store = ResearchArchiveStore(tmp_path / "archive")

    with pytest.raises(ValueError, match="cannot write across projects"):
        archive_research_record(record, store=store, target_project_id="project-2")

    assert not store.artifacts_dir_for("project-2").exists()


def test_archive_research_record_can_emit_explicit_history_only_when_dated(tmp_path: Path) -> None:
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store = ResearchArchiveStore(tmp_path / "archive")

    archived = archive_research_record(
        record,
        store=store,
        target_project_id="project-1",
        effective_date="2026-04-19",
        freshness_posture="dated",
    )
    history = [artifact for artifact in archived if artifact.artifact_family == "brief_history_record"]
    result = retrieve_project_archive(
        purpose="dated archive inspection",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        history_only=True,
        effective_date="2026-04-19",
        store=store,
    )

    assert len(history) == 1
    assert history[0].effective_date == "2026-04-19"
    assert result.explicitly_historical is True
    assert result.records == tuple(history)


def test_archive_research_record_persists_event_history_when_event_shaped_and_dated(tmp_path: Path) -> None:
    request = ResearchRequest(
        question="What changed in the rollout on 2026-04-19?",
        project_id="project-1",
        work_unit_id="wu-event",
        run_id="run-event",
        source_mode="web",
    )
    evidence_pack = EvidencePack(
        question=request.question,
        sources=(
            SourceItem(
                source_id="source-1",
                source_type="web",
                title="Release note",
                locator="https://example.com/release",
                snippet="The vendor announced the rollout change.",
                published_at="2026-04-19T09:00:00Z",
            ),
        ),
        evidence_items=(EvidenceItem(text="The vendor announced the rollout change.", source_refs=("source-1",)),),
    )
    artifact = ResearchArtifact(
        question=request.question,
        summary="The vendor announced a rollout change on 2026-04-19.",
        findings=(ResearchFinding(text="The rollout change was announced on 2026-04-19.", source_refs=("source-1",)),),
        inferences=("The change is a dated event, not a timeless fact.",),
        uncertainties=("Customer impact is still being assessed.",),
        recommendation=None,
        source_ids=("source-1",),
    )
    record = build_research_artifact_record(request, evidence_pack, artifact)
    store = ResearchArchiveStore(tmp_path / "archive")

    archived = archive_research_record(record, store=store, target_project_id="project-1")
    event_records = [item for item in archived if item.artifact_family == "event_history_record"]

    assert len(event_records) == 1
    assert event_records[0].event_date == "2026-04-19"
    assert event_records[0].source_refs == ("source-1",)
    assert event_records[0].uncertainty == ("Customer impact is still being assessed.",)
    assert store.path_for(event_records[0]).parent == store.history_dir_for("project-1")
    assert not (store.root_dir / "projects" / "project-1" / "memory").exists()
    assert not (store.root_dir / "projects" / "project-1" / "research" / "knowledge").exists()


def test_archive_research_record_does_not_misclassify_non_event_brief_as_event_history(tmp_path: Path) -> None:
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())
    store = ResearchArchiveStore(tmp_path / "archive")

    archived = archive_research_record(record, store=store, target_project_id="project-1")

    assert all(item.artifact_family != "event_history_record" for item in archived)


def _request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the bounded plan support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        source_mode="local_documents",
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the bounded plan support?",
        sources=(
            SourceItem(
                source_id="source-1",
                source_type="document",
                title="Plan",
                locator="doc://plan",
                snippet="Bounded plan snippet",
            ),
        ),
        evidence_items=(EvidenceItem(text="Bounded plan evidence", source_refs=("source-1",)),),
    )


def _artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded plan support?",
        summary="The bounded plan supports a narrow rollout.",
        findings=(ResearchFinding(text="The plan stays narrow.", source_refs=("source-1",)),),
        inferences=("A bounded rollout is better supported.",),
        uncertainties=("No external validation.",),
        recommendation="Proceed carefully.",
        source_ids=("source-1",),
    )
