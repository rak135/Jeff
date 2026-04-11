import json
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
    bad_path = tmp_path / "research_artifacts" / "bad.json"
    bad_path.parent.mkdir(parents=True, exist_ok=True)
    bad_path.write_text("{not valid json", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed persisted research artifact file"):
        store.load("bad")


def test_persistence_requires_only_research_contracts_and_filesystem(tmp_path: Path) -> None:
    store = ResearchArtifactStore(tmp_path)
    record = build_research_artifact_record(_request(), _evidence_pack(), _artifact())

    path = store.save(record)

    assert path.suffix == ".json"


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
