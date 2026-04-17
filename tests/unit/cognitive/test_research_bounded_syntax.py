import pytest

from jeff.cognitive import EvidenceItem, EvidencePack, ResearchRequest, SourceItem, build_research_model_request
from jeff.cognitive.research.bounded_syntax import STEP1_BOUNDED_SYNTAX_DESCRIPTION, validate_step1_bounded_text
from jeff.cognitive.research.contracts import Step1BoundedArtifact, Step1BoundedFinding
from jeff.cognitive.research.errors import ResearchSynthesisValidationError


def test_step1_bounded_artifact_contract_is_citation_key_only() -> None:
    artifact = Step1BoundedArtifact(
        summary="The evidence supports a bounded first step.",
        findings=(
            Step1BoundedFinding(
                text="The current state is stable across the prepared evidence.",
                citation_keys=("S1", "S2"),
            ),
        ),
        inferences=("A small next step is better supported than expansion.",),
        uncertainties=("External validation was not performed.",),
        recommendation="NONE",
    )

    assert artifact.findings[0].citation_keys == ("S1", "S2")
    assert artifact.recommendation is None


def test_step1_bounded_finding_explicitly_excludes_internal_source_id_fields() -> None:
    assert "source_id" not in Step1BoundedFinding.__dataclass_fields__
    assert "source_refs" not in Step1BoundedFinding.__dataclass_fields__

    with pytest.raises(TypeError, match="source_id"):
        Step1BoundedFinding(  # type: ignore[call-arg]
            text="Observed fact",
            citation_keys=("S1",),
            source_id="source-a",
        )


def test_validate_step1_bounded_text_accepts_canonical_structure() -> None:
    validate_step1_bounded_text(_valid_step1_text())

    assert "SUMMARY:" in STEP1_BOUNDED_SYNTAX_DESCRIPTION
    assert "FINDINGS:" in STEP1_BOUNDED_SYNTAX_DESCRIPTION
    assert "RECOMMENDATION:" in STEP1_BOUNDED_SYNTAX_DESCRIPTION


def test_validate_step1_bounded_text_rejects_missing_required_section() -> None:
    invalid_text = _valid_step1_text().replace(
        "\nUNCERTAINTIES:\n- External verification was not performed.\n",
        "\n",
    )

    with pytest.raises(ResearchSynthesisValidationError, match="UNCERTAINTIES"):
        validate_step1_bounded_text(invalid_text)


def test_validate_step1_bounded_text_rejects_malformed_finding_section() -> None:
    invalid_text = _valid_step1_text().replace(
        "- text: The prepared evidence supports a stable current state.\n  cites: S1,S2",
        "- note: The prepared evidence supports a stable current state.\n  cites: S1,S2",
    )

    with pytest.raises(ResearchSynthesisValidationError, match="findings entries must start"):
        validate_step1_bounded_text(invalid_text)


def test_validate_step1_bounded_text_rejects_invalid_citation_key_shape() -> None:
    invalid_text = _valid_step1_text().replace("  cites: S1,S2", "  cites: source-a")

    with pytest.raises(ResearchSynthesisValidationError, match="S<number>"):
        validate_step1_bounded_text(invalid_text)


def test_validate_step1_bounded_text_rejects_duplicate_citation_keys() -> None:
    invalid_text = _valid_step1_text().replace("  cites: S1,S2", "  cites: S1,S1")

    with pytest.raises(ResearchSynthesisValidationError, match="must not repeat citation keys"):
        validate_step1_bounded_text(invalid_text)


def test_step1_bounded_artifact_rejects_empty_required_content() -> None:
    with pytest.raises(ValueError, match="summary must be a non-empty string"):
        Step1BoundedArtifact(
            summary="   ",
            findings=(Step1BoundedFinding(text="Observed fact", citation_keys=("S1",)),),
            inferences=("Interpretation",),
            uncertainties=("Open question",),
            recommendation="Proceed carefully.",
        )

    with pytest.raises(ValueError, match="inferences must contain at least one item"):
        Step1BoundedArtifact(
            summary="Bounded summary",
            findings=(Step1BoundedFinding(text="Observed fact", citation_keys=("S1",)),),
            inferences=(),
            uncertainties=("Open question",),
            recommendation="Proceed carefully.",
        )


def test_live_research_synthesis_request_now_uses_bounded_text_first() -> None:
    request = build_research_model_request(_research_request(), _evidence_pack(), adapter_id="fake-json")

    assert request.response_mode.value == "TEXT"
    assert request.purpose == "research_synthesis"
    assert "Output bounded plain text using the exact section syntax below." in request.prompt
    assert "SUMMARY:" in request.prompt
    assert "FINDINGS:" in request.prompt


def test_step1_bounded_text_accepts_sentinel_uncertainty_bullet() -> None:
    """Test that the canonical sentinel uncertainty bullet is accepted."""
    text_with_sentinel = _valid_step1_text().replace(
        "- External verification was not performed.",
        "- No explicit uncertainties identified from the provided evidence.",
    )
    
    validate_step1_bounded_text(text_with_sentinel)
    
    # Should not raise


def test_step1_bounded_artifact_with_sentinel_uncertainty() -> None:
    """Test that Step1BoundedArtifact accepts the sentinel uncertainty."""
    artifact = Step1BoundedArtifact(
        summary="The evidence is consistent.",
        findings=(
            Step1BoundedFinding(
                text="Source A supports the analysis.",
                citation_keys=("S1",),
            ),
        ),
        inferences=("The conclusion follows directly from the evidence.",),
        uncertainties=("No explicit uncertainties identified from the provided evidence.",),
        recommendation="Accept the conclusion.",
    )

    assert artifact.uncertainties == ("No explicit uncertainties identified from the provided evidence.",)


def _valid_step1_text() -> str:
    return "\n".join(
        [
            "SUMMARY:",
            "The prepared evidence supports a bounded rollout.",
            "",
            "FINDINGS:",
            "- text: The prepared evidence supports a stable current state.",
            "  cites: S1,S2",
            "- text: The local planning note keeps the scope narrow.",
            "  cites: S2",
            "",
            "INFERENCES:",
            "- A narrow next step is better supported than immediate expansion.",
            "",
            "UNCERTAINTIES:",
            "- External verification was not performed.",
            "",
            "RECOMMENDATION:",
            "Proceed with the bounded option first.",
        ]
    )


def _research_request() -> ResearchRequest:
    return ResearchRequest(
        question="What does the prepared evidence support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        constraints=("Stay bounded.",),
    )


def _evidence_pack() -> EvidencePack:
    return EvidencePack(
        question="What does the prepared evidence support?",
        sources=(
            SourceItem(
                source_id="source-a",
                source_type="document",
                title="Bounded Note A",
                locator="doc://a",
                snippet="The prepared evidence supports a stable current state.",
            ),
            SourceItem(
                source_id="source-b",
                source_type="document",
                title="Bounded Note B",
                locator="doc://b",
                snippet="The local planning note keeps the scope narrow.",
            ),
        ),
        evidence_items=(
            EvidenceItem(
                text="The prepared evidence supports a stable current state.",
                source_refs=("source-a",),
            ),
            EvidenceItem(
                text="The local planning note keeps the scope narrow.",
                source_refs=("source-b",),
            ),
        ),
        constraints=("Stay bounded.",),
    )
