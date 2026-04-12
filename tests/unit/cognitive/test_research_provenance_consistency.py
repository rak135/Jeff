import pytest

from jeff.cognitive import (
    EvidenceItem,
    ResearchArtifact,
    ResearchFinding,
    ResearchProvenanceValidationError,
    SourceItem,
    validate_research_provenance,
)


def test_valid_artifact_evidence_and_source_linkage_passes() -> None:
    validate_research_provenance(
        findings=_artifact().findings,
        source_ids=_artifact().source_ids,
        source_items=_source_items(),
        evidence_items=_evidence_items(),
    )


def test_finding_with_missing_source_ref_fails_closed() -> None:
    artifact = ResearchArtifact(
        question="What does the bounded source set support?",
        summary="A broken finding should fail.",
        findings=(ResearchFinding(text="Missing linkage", source_refs=("missing-source",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
    )

    with pytest.raises(ResearchProvenanceValidationError, match="finding references unknown source ids"):
        validate_research_provenance(
            findings=artifact.findings,
            source_ids=artifact.source_ids,
            source_items=_source_items(),
            evidence_items=_evidence_items(),
        )


def test_evidence_item_with_missing_source_ref_fails_closed() -> None:
    with pytest.raises(ResearchProvenanceValidationError, match="evidence item references unknown source ids"):
        validate_research_provenance(
            findings=_artifact().findings,
            source_ids=_artifact().source_ids,
            source_items=_source_items(),
            evidence_items=(EvidenceItem(text="Broken evidence", source_refs=("missing-source",)),),
        )


def test_duplicate_source_id_in_source_items_fails_closed() -> None:
    duplicate_sources = _source_items() + (
        SourceItem(
            source_id="source-1",
            source_type="web",
            title="Duplicate",
            locator="https://example.com/duplicate",
            snippet="Duplicate snippet",
        ),
    )

    with pytest.raises(ResearchProvenanceValidationError, match="duplicate source ids"):
        validate_research_provenance(
            findings=_artifact().findings,
            source_ids=_artifact().source_ids,
            source_items=duplicate_sources,
            evidence_items=_evidence_items(),
        )


def test_listed_source_ids_not_present_in_source_items_fails_closed() -> None:
    artifact = ResearchArtifact(
        question="What does the bounded source set support?",
        summary="Artifact lists an unknown source id.",
        findings=(ResearchFinding(text="Known finding", source_refs=("source-1",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1", "missing-source"),
    )

    with pytest.raises(ResearchProvenanceValidationError, match="lists unknown source id"):
        validate_research_provenance(
            findings=artifact.findings,
            source_ids=artifact.source_ids,
            source_items=_source_items(),
            evidence_items=_evidence_items(),
        )


def test_malformed_or_empty_source_refs_fail_explicitly() -> None:
    with pytest.raises(ValueError, match="source_refs"):
        ResearchFinding(text="Bad finding", source_refs=("",))

    with pytest.raises(ValueError, match="source_refs"):
        EvidenceItem(text="Bad evidence", source_refs=("",))


def test_no_silent_repair_behavior_occurs() -> None:
    artifact = ResearchArtifact(
        question="What does the bounded source set support?",
        summary="Broken linkage should not be auto-healed.",
        findings=(ResearchFinding(text="Missing linkage", source_refs=("missing-source",)),),
        inferences=(),
        uncertainties=(),
        recommendation=None,
        source_ids=("source-1",),
    )
    source_items = _source_items()

    with pytest.raises(ResearchProvenanceValidationError):
        validate_research_provenance(
            findings=artifact.findings,
            source_ids=artifact.source_ids,
            source_items=source_items,
            evidence_items=_evidence_items(),
        )

    assert source_items == _source_items()
    assert artifact.findings[0].source_refs == ("missing-source",)


def _artifact() -> ResearchArtifact:
    return ResearchArtifact(
        question="What does the bounded source set support?",
        summary="The bounded source set supports a narrow conclusion.",
        findings=(ResearchFinding(text="Source 1 supports the bounded path.", source_refs=("source-1",)),),
        inferences=("A narrow next step is better supported.",),
        uncertainties=("No external validation was performed.",),
        recommendation="Proceed with the bounded path.",
        source_ids=("source-1",),
    )


def _source_items() -> tuple[SourceItem, ...]:
    return (
        SourceItem(
            source_id="source-1",
            source_type="document",
            title="Plan",
            locator="doc://plan",
            snippet="The bounded plan remains narrow.",
        ),
        SourceItem(
            source_id="source-2",
            source_type="web",
            title="Article",
            locator="https://example.com/article",
            snippet="The article describes the same bounded constraint.",
        ),
    )


def _evidence_items() -> tuple[EvidenceItem, ...]:
    return (
        EvidenceItem(text="The bounded plan remains narrow.", source_refs=("source-1",)),
        EvidenceItem(text="The same bounded constraint still holds.", source_refs=("source-2",)),
    )
