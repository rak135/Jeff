import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchRequest,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
    SourceItem,
    build_research_model_request,
    synthesize_research,
)
from jeff.infrastructure import FakeModelAdapter, ModelMalformedOutputError


def test_build_research_model_request_includes_bounded_evidence_and_step1_syntax() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack, adapter_id="fake-text")

    assert model_request.response_mode.value == "TEXT"
    assert model_request.json_schema is None
    assert model_request.purpose == "research_synthesis"
    assert "TASK: bounded research synthesis" in model_request.prompt
    assert "Output bounded plain text using the exact section syntax below." in model_request.prompt
    assert "REQUIRED_BOUNDED_SYNTAX:" in model_request.prompt
    assert "SUMMARY:" in model_request.prompt
    assert "FINDINGS:" in model_request.prompt
    assert "RECOMMENDATION:" in model_request.prompt
    assert "source-a" not in model_request.prompt
    assert "source-b" not in model_request.prompt
    assert "E1|refs=S1|text=The current state is stable." in model_request.prompt
    assert "Return bounded plain text in the declared section syntax." in model_request.system_instructions
    assert "Do not return JSON." in model_request.system_instructions
    assert model_request.metadata["expected_output_shape"] == "step1_bounded_text_v1"


def test_successful_synthesis_uses_bounded_text_then_deterministic_transform() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-text",
            default_text_response=_valid_step1_text(),
        ),
    )

    assert isinstance(artifact, ResearchArtifact)
    assert artifact.summary == "The prepared evidence supports a bounded conclusion."
    assert artifact.findings[0].text == "Source A describes the current state."
    assert artifact.findings[0].source_refs == ("source-a",)
    assert artifact.inferences == ("A minimal next step is better supported than expansion.",)
    assert artifact.uncertainties == ("External conditions were not observed directly.",)


def test_malformed_output_fails_closed() -> None:
    with pytest.raises(ResearchSynthesisRuntimeError, match="malformed_output"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-text",
                forced_exception=ModelMalformedOutputError("adapter returned malformed output"),
            ),
        )


def test_invalid_bounded_text_fails_closed_at_syntax_precheck() -> None:
    events: list[dict[str, object]] = []

    with pytest.raises(ResearchSynthesisValidationError, match="UNCERTAINTIES"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-text",
                default_text_response=_invalid_step1_text_missing_uncertainties(),
            ),
            debug_emitter=events.append,
        )

    checkpoints = [event["checkpoint"] for event in events]
    assert "content_generation_started" in checkpoints
    assert "content_generation_succeeded" in checkpoints
    assert "syntax_precheck_failed" in checkpoints
    assert "deterministic_transform_started" not in checkpoints
    assert "repair_pass_started" not in checkpoints


def test_deterministic_transform_succeeds_before_citation_remap() -> None:
    events: list[dict[str, object]] = []

    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-text",
            default_text_response=_valid_step1_text(),
        ),
        debug_emitter=events.append,
    )

    assert artifact.summary == "The prepared evidence supports a bounded conclusion."
    checkpoints = [event["checkpoint"] for event in events]
    assert "content_generation_succeeded" in checkpoints
    assert "deterministic_transform_started" in checkpoints
    assert "deterministic_transform_succeeded" in checkpoints
    assert checkpoints.index("content_generation_succeeded") < checkpoints.index("deterministic_transform_started")
    assert checkpoints.index("deterministic_transform_succeeded") < checkpoints.index("citation_remap_started")


def test_findings_inferences_and_uncertainties_remain_distinct() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-text",
            default_text_response=_valid_step1_text(),
        ),
    )

    assert artifact.findings[0].text == "Source A describes the current state."
    assert artifact.inferences == ("A minimal next step is better supported than expansion.",)
    assert artifact.uncertainties == ("External conditions were not observed directly.",)


def test_synthesize_research_returns_research_artifact_not_model_response() -> None:
    result = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-text",
            default_text_response=_valid_step1_text(),
        ),
    )

    assert isinstance(result, ResearchArtifact)
    assert not hasattr(result, "output_json")


def test_synthesis_accepts_sentinel_uncertainty_bullet() -> None:
    """Test that synthesis properly handles the sentinel uncertainty bullet."""
    text_with_sentinel = _valid_step1_text().replace(
        "- External conditions were not observed directly.",
        "- No explicit uncertainties identified from the provided evidence.",
    )
    
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-text",
            default_text_response=text_with_sentinel,
        ),
    )

    assert artifact.uncertainties == ("No explicit uncertainties identified from the provided evidence.",)
    assert artifact.summary == "The prepared evidence supports a bounded conclusion."
    assert len(artifact.findings) > 0


def _valid_step1_text() -> str:
    return "\n".join(
        [
            "SUMMARY:",
            "The prepared evidence supports a bounded conclusion.",
            "",
            "FINDINGS:",
            "- text: Source A describes the current state.",
            "  cites: S1",
            "- text: Source B confirms the same constraint.",
            "  cites: S2",
            "",
            "INFERENCES:",
            "- A minimal next step is better supported than expansion.",
            "",
            "UNCERTAINTIES:",
            "- External conditions were not observed directly.",
            "",
            "RECOMMENDATION:",
            "Proceed with the bounded option first.",
        ]
    )


def _invalid_step1_text_missing_uncertainties() -> str:
    return "\n".join(
        [
            "SUMMARY:",
            "The prepared evidence supports a bounded conclusion.",
            "",
            "FINDINGS:",
            "- text: Source A describes the current state.",
            "  cites: S1",
            "",
            "INFERENCES:",
            "- A minimal next step is better supported than expansion.",
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
        constraints=("Constraint A",),
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
                snippet="Source A says the current state is stable.",
            ),
            SourceItem(
                source_id="source-b",
                source_type="document",
                title="Bounded Note B",
                locator="doc://b",
                snippet="Source B says the same constraint still holds.",
            ),
        ),
        evidence_items=(
            EvidenceItem(
                text="The current state is stable.",
                source_refs=("source-a",),
            ),
            EvidenceItem(
                text="The key constraint still holds.",
                source_refs=("source-b",),
            ),
        ),
        contradictions=("No direct contradiction found.",),
        uncertainties=("External verification was not performed.",),
        constraints=("Constraint A",),
    )
