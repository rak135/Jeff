from jeff.cognitive import (
    ResearchArtifact,
    ResearchFinding,
    ResearchRequest,
    ResearchArtifactRecord,
    ResearchMemoryHandoffInput,
    build_research_memory_handoff_input,
    build_research_artifact_record,
    handoff_research_to_memory,
    should_handoff_research_to_memory,
)
from jeff.cognitive.research.contracts import EvidenceItem, EvidencePack, SourceItem
from jeff.memory import InMemoryMemoryStore


def test_build_research_memory_handoff_input_preserves_scope_and_bounded_content() -> None:
    request = _request()
    artifact = _meaningful_artifact()
    record = build_research_artifact_record(request, _evidence_pack(), artifact)

    handoff = build_research_memory_handoff_input(request, artifact, record)

    assert isinstance(handoff, ResearchMemoryHandoffInput)
    assert handoff.project_id == "project-1"
    assert handoff.work_unit_id == "wu-1"
    assert handoff.run_id == "run-1"
    assert handoff.artifact_id == record.artifact_id
    assert handoff.source_ids == ("source-1", "source-2")
    assert handoff.findings[0] == "Finding one"


def test_should_handoff_research_to_memory_returns_false_for_thin_trivial_artifact() -> None:
    artifact = ResearchArtifact(
        question="Q",
        summary="No strong evidence found in the fetched web sources for the research question.",
        findings=(ResearchFinding(text="Single thin fact", source_refs=("source-1",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
    )

    assert should_handoff_research_to_memory(artifact) is False


def test_should_handoff_research_to_memory_returns_true_for_meaningful_artifact() -> None:
    assert should_handoff_research_to_memory(_meaningful_artifact()) is True


def test_handoff_uses_current_memory_write_pipeline_without_bypass() -> None:
    store = InMemoryMemoryStore()
    decision = handoff_research_to_memory(
        research_request=_request(),
        artifact=_meaningful_artifact(),
        memory_store=store,
        artifact_record=build_research_artifact_record(_request(), _evidence_pack(), _meaningful_artifact()),
    )

    assert decision is not None
    assert decision.write_outcome == "write"
    assert decision.committed_record is not None
    assert store.get_committed(str(decision.memory_id)) == decision.committed_record


def test_no_raw_source_bodies_are_copied_into_handoff_input() -> None:
    request = _request()
    artifact = _meaningful_artifact()
    handoff = build_research_memory_handoff_input(
        request,
        artifact,
        build_research_artifact_record(request, _evidence_pack(), artifact),
    )

    assert "Raw body" not in handoff.summary
    assert all("Raw body" not in item for item in handoff.findings)
    assert handoff.source_ids == ("source-1", "source-2")


def test_handoff_can_surface_defer_from_current_memory_layer() -> None:
    store = InMemoryMemoryStore()
    artifact = ResearchArtifact(
        question="Q",
        summary="Meaningful caution",
        findings=(ResearchFinding(text="Finding one", source_refs=("source-1",)),),
        inferences=(),
        uncertainties=("Risk remains unresolved.",),
        recommendation=None,
        source_ids=("source-1",),
    )

    decision = handoff_research_to_memory(
        research_request=_request(),
        artifact=artifact,
        memory_store=store,
        artifact_record=build_research_artifact_record(_request(), _evidence_pack(single_source=True), artifact),
    )

    assert decision is not None
    assert decision.write_outcome == "defer"


def _request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the bounded plan support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        source_mode="local_documents",
    )


def _meaningful_artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded plan support?",
        summary="Research found durable bounded guidance.",
        findings=(
            ResearchFinding(text="Finding one", source_refs=("source-1",)),
            ResearchFinding(text="Finding two", source_refs=("source-2",)),
        ),
        inferences=("A bounded path remains safer.",),
        uncertainties=("External validation is still limited.",),
        recommendation="Keep the implementation bounded.",
        source_ids=("source-1", "source-2"),
    )


def _evidence_pack(*, single_source: bool = False) -> EvidencePack:
    sources = (
        SourceItem(source_id="source-1", source_type="document", title="A", locator="doc://a", snippet="Snippet A"),
    )
    if not single_source:
        sources = sources + (
            SourceItem(source_id="source-2", source_type="document", title="B", locator="doc://b", snippet="Snippet B"),
        )
    return EvidencePack(
        question="What does the bounded plan support?",
        sources=sources,
        evidence_items=(EvidenceItem(text="Evidence A", source_refs=("source-1",)),),
    )
