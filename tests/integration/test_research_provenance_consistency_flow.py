from pathlib import Path

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchArtifactRecord,
    ResearchArtifactStore,
    ResearchFinding,
    ResearchProvenanceValidationError,
    ResearchRequest,
    SourceItem,
    persist_research_artifact,
    run_and_persist_document_research,
)
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.interface.json_views import research_result_json
from jeff.interface.session import CliSession, SessionScope


def test_persistence_rejects_inconsistent_source_linkage(tmp_path: Path) -> None:
    request = ResearchRequest(
        question="What does the bounded source set support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        source_mode="prepared_evidence",
    )
    evidence_pack = EvidencePack(
        question=request.question,
        sources=(
            SourceItem(
                source_id="source-1",
                source_type="document",
                title="Plan",
                locator="doc://plan",
                snippet="The bounded plan remains narrow.",
            ),
        ),
        evidence_items=(EvidenceItem(text="The bounded plan remains narrow.", source_refs=("source-1",)),),
    )
    artifact = ResearchArtifact(
        question=request.question,
        summary="This artifact is internally inconsistent.",
        findings=(ResearchFinding(text="Broken linkage", source_refs=("missing-source",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
    )

    with pytest.raises(ResearchProvenanceValidationError, match="finding references unknown source ids"):
        persist_research_artifact(request, evidence_pack, artifact, ResearchArtifactStore(tmp_path))


def test_valid_document_research_flow_still_persists_successfully(tmp_path: Path) -> None:
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    request = ResearchRequest(
        question="What does the bounded plan support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        document_paths=(str(document),),
        source_mode="local_documents",
    )
    source_id = __import__("jeff.cognitive", fromlist=["collect_document_sources"]).collect_document_sources(request)[0].source_id
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_json_response={
                        "summary": "The documents support a bounded rollout.",
                        "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                        "inferences": ["A narrow implementation remains better supported."],
                        "uncertainties": ["No external validation was performed."],
                        "recommendation": "Proceed with the bounded path.",
                    },
                ),
            ),
        )
    )
    store = ResearchArtifactStore(tmp_path)

    record = run_and_persist_document_research(request, services, store)

    assert store.load(record.artifact_id) == record
    assert record.source_items[0].source_id == source_id
    assert record.findings[0].source_refs == (source_id,)


def test_operator_facing_result_construction_does_not_mask_invalid_persisted_linkage() -> None:
    record = ResearchArtifactRecord(
        artifact_id="research-bad",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        question="What does the bounded source set support?",
        source_mode="prepared_evidence",
        summary="This record should not render as coherent support.",
        findings=(ResearchFinding(text="Broken linkage", source_refs=("missing-source",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
        source_items=(
            SourceItem(
                source_id="source-1",
                source_type="document",
                title="Plan",
                locator="doc://plan",
                snippet="The bounded plan remains narrow.",
            ),
        ),
        evidence_items=(EvidenceItem(text="The bounded plan remains narrow.", source_refs=("source-1",)),),
        created_at="2026-04-12T09:00:00+00:00",
    )

    with pytest.raises(ResearchProvenanceValidationError, match="finding references unknown source ids"):
        research_result_json(
            project_id="project-1",
            work_unit_id="wu-1",
            run_id="run-1",
            research_mode="docs",
            handoff_memory_requested=False,
            record=record,
            memory_handoff_result=None,
            session=CliSession(scope=SessionScope(project_id="project-1", work_unit_id="wu-1", run_id="run-1")),
        )
