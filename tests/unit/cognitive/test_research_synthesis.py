import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifact,
    ResearchRequest,
    ResearchSynthesisError,
    ResearchSynthesisRuntimeError,
    ResearchSynthesisValidationError,
    SourceItem,
    build_research_model_request,
    synthesize_research,
)
from jeff.infrastructure import FakeModelAdapter


def test_build_research_model_request_includes_bounded_evidence_and_instructions() -> None:
    request = _research_request()
    evidence_pack = _evidence_pack()

    model_request = build_research_model_request(request, evidence_pack, adapter_id="fake-json")

    assert model_request.response_mode.value == "JSON"
    assert model_request.purpose == "research_synthesis"
    assert "Stay within the provided evidence." in model_request.prompt
    assert "Do not invent sources" in model_request.prompt
    assert "Question: What does the prepared evidence support?" in model_request.prompt
    assert "Allowed citation keys: S1, S2" in model_request.prompt
    assert "source-a" not in model_request.prompt
    assert "source-b" not in model_request.prompt
    assert "refs=S1" in model_request.prompt
    assert "Constraint A" in model_request.prompt
    assert model_request.json_schema["properties"]["findings"]["items"]["properties"]["source_refs"]["items"]["enum"] == [
        "S1",
        "S2",
    ]
    assert model_request.metadata["citation_keys"] == ["S1", "S2"]
    assert model_request.metadata["adapter_id"] == "fake-json"


def test_successful_synthesis_using_fake_model_adapter_json_mode() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-json",
            default_json_response={
                "summary": "The prepared evidence supports a bounded conclusion.",
                "findings": [
                    {"text": "Source A describes the current state.", "source_refs": ["S1"]},
                    {"text": "Source B confirms the same constraint.", "source_refs": ["S2"]},
                ],
                "inferences": ["A minimal next step is better supported than expansion."],
                "uncertainties": ["External conditions were not observed directly."],
                "recommendation": "Proceed with the bounded option first.",
            },
        ),
    )

    assert isinstance(artifact, ResearchArtifact)
    assert artifact.summary == "The prepared evidence supports a bounded conclusion."
    assert artifact.findings[0].text == "Source A describes the current state."
    assert artifact.findings[0].source_refs == ("source-a",)
    assert artifact.inferences == ("A minimal next step is better supported than expansion.",)
    assert artifact.uncertainties == ("External conditions were not observed directly.",)


def test_malformed_json_output_fails_closed() -> None:
    with pytest.raises(ResearchSynthesisRuntimeError, match="malformed_output"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(adapter_id="fake-json", default_json_response=None),
        )


def test_missing_required_fields_fail_closed() -> None:
    with pytest.raises(ResearchSynthesisValidationError, match="findings must be a list"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-json",
                default_json_response={
                    "summary": "Missing findings should fail.",
                    "inferences": [],
                    "uncertainties": [],
                    "recommendation": None,
                },
            ),
        )


def test_unknown_citation_refs_in_returned_findings_fail_closed() -> None:
    with pytest.raises(ResearchSynthesisValidationError, match="unknown citation refs"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-json",
                default_json_response={
                    "summary": "This should fail source validation.",
                    "findings": [{"text": "Unsupported claim", "source_refs": ["S9"]}],
                    "inferences": [],
                    "uncertainties": [],
                    "recommendation": None,
                },
            ),
        )


def test_findings_inferences_and_uncertainties_remain_distinct() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-json",
                default_json_response={
                    "summary": "Distinct fields stay distinct.",
                    "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
                    "inferences": ["Interpretation"],
                    "uncertainties": ["Open question"],
                    "recommendation": None,
                },
            ),
    )

    assert artifact.findings[0].text == "Observed fact"
    assert artifact.inferences == ("Interpretation",)
    assert artifact.uncertainties == ("Open question",)


def test_synthesize_research_returns_research_artifact_not_model_response() -> None:
    result = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-json",
                default_json_response={
                    "summary": "Artifact only.",
                    "findings": [{"text": "Observed fact", "source_refs": ["S1"]}],
                    "inferences": [],
                    "uncertainties": [],
                    "recommendation": None,
                },
            ),
    )

    assert isinstance(result, ResearchArtifact)
    assert not hasattr(result, "output_json")


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
