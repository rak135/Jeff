import pytest

from jeff.cognitive import EvidenceItem, EvidencePack, ResearchRequest, SourceItem, build_research_model_request
from jeff.cognitive.research.deterministic_transformer import (
    parse_step1_bounded_text,
    transform_step1_bounded_text_to_candidate_payload,
)
from jeff.cognitive.research.errors import ResearchSynthesisValidationError
from jeff.cognitive.research.validators import validate_candidate_research_payload


def test_transform_step1_bounded_text_to_candidate_payload_succeeds_for_valid_input() -> None:
    payload = transform_step1_bounded_text_to_candidate_payload(_valid_step1_text())

    assert payload == {
        "summary": "The prepared evidence supports a bounded rollout.",
        "findings": [
            {
                "text": "The prepared evidence supports a stable current state.",
                "source_refs": ["S1", "S2"],
            },
            {
                "text": "The local planning note keeps the scope narrow.",
                "source_refs": ["S2"],
            },
        ],
        "inferences": ["A narrow next step is better supported than immediate expansion."],
        "uncertainties": ["External verification was not performed."],
        "recommendation": None,
    }


def test_parse_step1_bounded_text_keeps_only_present_content() -> None:
    artifact = parse_step1_bounded_text(_valid_step1_text())

    assert artifact.summary == "The prepared evidence supports a bounded rollout."
    assert len(artifact.findings) == 2
    assert artifact.findings[0].citation_keys == ("S1", "S2")
    assert artifact.inferences == ("A narrow next step is better supported than immediate expansion.",)
    assert artifact.uncertainties == ("External verification was not performed.",)
    assert artifact.recommendation is None


def test_transformer_fails_closed_on_missing_required_section() -> None:
    invalid_text = _valid_step1_text().replace(
        "\nUNCERTAINTIES:\n- External verification was not performed.\n",
        "\n",
    )

    with pytest.raises(ResearchSynthesisValidationError, match="UNCERTAINTIES"):
        transform_step1_bounded_text_to_candidate_payload(invalid_text)


def test_transformer_fails_closed_on_malformed_finding_structure() -> None:
    invalid_text = _valid_step1_text().replace(
        "  cites: S1,S2",
        "  source_refs: S1,S2",
        1,
    )

    with pytest.raises(ResearchSynthesisValidationError, match="following '  cites: ' line"):
        transform_step1_bounded_text_to_candidate_payload(invalid_text)


def test_transformer_fails_closed_on_malformed_citation_keys() -> None:
    invalid_text = _valid_step1_text().replace("  cites: S1,S2", "  cites: source-a", 1)

    with pytest.raises(ResearchSynthesisValidationError, match="S<number>"):
        transform_step1_bounded_text_to_candidate_payload(invalid_text)


def test_transformer_fails_closed_on_duplicate_citation_keys() -> None:
    invalid_text = _valid_step1_text().replace("  cites: S1,S2", "  cites: S1,S1", 1)

    with pytest.raises(ResearchSynthesisValidationError, match="must not repeat citation keys"):
        transform_step1_bounded_text_to_candidate_payload(invalid_text)


def test_transformer_fails_closed_on_ambiguous_structure() -> None:
    invalid_text = _valid_step1_text().replace(
        "\nINFERENCES:\n- A narrow next step is better supported than immediate expansion.\n",
        "\nFINDINGS:\n- text: Another claim\n  cites: S1\n",
    )

    with pytest.raises(ResearchSynthesisValidationError, match="canonical order"):
        transform_step1_bounded_text_to_candidate_payload(invalid_text)


def test_candidate_payload_validator_rejects_internal_or_step1_only_fields() -> None:
    with pytest.raises(ResearchSynthesisValidationError, match="must not include internal or Step1-only fields"):
        validate_candidate_research_payload(
            {
                "summary": "Bounded summary",
                "findings": [
                    {
                        "text": "Observed fact",
                        "source_refs": ["S1"],
                        "source_id": "source-a",
                    }
                ],
                "inferences": ["Interpretation"],
                "uncertainties": ["Open question"],
                "recommendation": None,
            }
        )


def test_live_research_synthesis_request_now_uses_bounded_text_first() -> None:
    request = build_research_model_request(_research_request(), _evidence_pack(), adapter_id="fake-json")

    assert request.response_mode.value == "TEXT"
    assert request.purpose == "research_synthesis"
    assert "Output bounded plain text using the exact section syntax below." in request.prompt
    assert "SUMMARY:" in request.prompt
    assert "FINDINGS:" in request.prompt


def test_transformer_accepts_sentinel_uncertainty_bullet() -> None:
    """Test that the canonical sentinel uncertainty bullet is properly parsed."""
    text_with_sentinel = _valid_step1_text().replace(
        "- External verification was not performed.",
        "- No explicit uncertainties identified from the provided evidence.",
    )
    
    payload = transform_step1_bounded_text_to_candidate_payload(text_with_sentinel)
    
    assert payload["uncertainties"] == ["No explicit uncertainties identified from the provided evidence."]


def test_parser_extracts_sentinel_uncertainty_to_artifact() -> None:
    """Test that sentinel uncertainty is correctly extracted to Step1BoundedArtifact."""
    text_with_sentinel = _valid_step1_text().replace(
        "- External verification was not performed.",
        "- No explicit uncertainties identified from the provided evidence.",
    )
    
    artifact = parse_step1_bounded_text(text_with_sentinel)
    
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
            "NONE",
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
