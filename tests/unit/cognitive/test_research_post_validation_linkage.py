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
from jeff.interface.json_views import research_result_json
from jeff.interface.session import CliSession, SessionScope


def test_valid_post_remap_artifact_stays_valid_through_build_save_load_and_projection(tmp_path: Path) -> None:
    request = _request()
    evidence_pack = _evidence_pack()
    artifact = _artifact()
    store = ResearchArtifactStore(tmp_path)

    record = build_research_artifact_record(request, evidence_pack, artifact)
    store.save(record)
    loaded = store.load(record.artifact_id)
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="docs",
        handoff_memory_requested=False,
        record=loaded,
        memory_handoff_result=None,
        session=_session(),
    )

    assert record.findings[0].source_refs == ("document-a",)
    assert loaded.findings[0].source_refs == ("document-a",)
    assert loaded.source_ids == ("document-a", "document-b")
    assert len(loaded.source_items) == 2
    assert payload["support"]["findings"][0]["source_refs"] == ["document-a"]
    assert payload["support"]["findings"][0]["resolved_sources"][0]["source_id"] == "document-a"


def test_source_item_counts_and_refs_stay_aligned_across_downstream_reconstruction(tmp_path: Path) -> None:
    request = _request()
    evidence_pack = _evidence_pack()
    artifact = _artifact()
    store = ResearchArtifactStore(tmp_path)
    events: list[dict[str, object]] = []

    record = build_research_artifact_record(request, evidence_pack, artifact, debug_emitter=events.append)
    store.save(record, debug_emitter=events.append)
    loaded = store.load(record.artifact_id, debug_emitter=events.append)

    assert len(record.source_items) == len(loaded.source_items) == 2
    assert record.source_ids == loaded.source_ids
    assert record.findings[0].source_refs == loaded.findings[0].source_refs
    checkpoints = [event["checkpoint"] for event in events]
    assert "artifact_record_build_succeeded" in checkpoints
    assert "artifact_store_save_succeeded" in checkpoints
    assert "artifact_store_load_succeeded" in checkpoints


def test_dropped_source_regression_is_caught_explicitly_on_load(tmp_path: Path) -> None:
    request = _request()
    evidence_pack = _evidence_pack()
    artifact = _artifact()
    store = ResearchArtifactStore(tmp_path)

    record = build_research_artifact_record(request, evidence_pack, artifact)
    path = store.save(record)
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["source_items"] = payload["source_items"][:1]
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    with pytest.raises(ValueError, match="malformed persisted research artifact record"):
        store.load(record.artifact_id)


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
                source_id="document-a",
                source_type="document",
                title="Plan A",
                locator="doc://a",
                snippet="The bounded plan stays narrow.",
            ),
            SourceItem(
                source_id="document-b",
                source_type="document",
                title="Plan B",
                locator="doc://b",
                snippet="The bounded plan remains stable.",
            ),
        ),
        evidence_items=(
            EvidenceItem(text="The bounded plan stays narrow.", source_refs=("document-a",)),
            EvidenceItem(text="The bounded plan remains stable.", source_refs=("document-b",)),
        ),
    )


def _artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded plan support?",
        summary="The bounded plan supports a narrow rollout.",
        findings=(ResearchFinding(text="The plan stays narrow.", source_refs=("document-a",)),),
        inferences=("A narrow rollout remains supported.",),
        uncertainties=("No live validation was performed.",),
        recommendation="Proceed with the bounded path.",
        source_ids=("document-a", "document-b"),
    )


def _session() -> CliSession:
    return CliSession(scope=SessionScope(project_id="project-1", work_unit_id="wu-1", run_id="run-1"))
