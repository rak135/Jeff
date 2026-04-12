import json

import pytest

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchRequest,
    ResearchSynthesisValidationError,
    SourceItem,
    build_research_model_request,
    synthesize_research,
)
from jeff.cognitive.research.synthesis import build_citation_key_map, build_model_facing_sources
from jeff.infrastructure import FakeModelAdapter


def test_build_citation_key_map_is_deterministic_for_stable_source_order() -> None:
    evidence_pack = _evidence_pack()

    assert build_citation_key_map(evidence_pack) == {
        "S1": "web-359eb9e7c0c0",
        "S2": "document-a81f1c0a",
    }
    assert build_citation_key_map(evidence_pack) == build_citation_key_map(evidence_pack)


def test_model_facing_sources_use_request_local_citation_keys() -> None:
    model_facing_sources = build_model_facing_sources(_evidence_pack())

    assert [source.citation_key for source in model_facing_sources] == ["S1", "S2"]
    assert model_facing_sources[0].locator == "https://example.com/a"
    assert model_facing_sources[1].locator == "doc://plan"


def test_model_request_uses_citation_keys_without_leaking_raw_source_ids() -> None:
    request = build_research_model_request(_research_request(), _evidence_pack(), adapter_id="fake-json")

    assert "Allowed citation keys: S1, S2" in request.prompt
    assert "refs=S1" in request.prompt
    assert "refs=S2" in request.prompt
    assert "web-359eb9e7c0c0" not in request.prompt
    assert "document-a81f1c0a" not in request.prompt
    assert "web-359eb9e7c0c0" not in json.dumps(request.json_schema)
    assert "document-a81f1c0a" not in json.dumps(request.json_schema)
    assert "web-359eb9e7c0c0" not in json.dumps(request.metadata)
    assert "document-a81f1c0a" not in json.dumps(request.metadata)


def test_dynamic_allowed_key_contract_is_generated_correctly() -> None:
    request = build_research_model_request(_research_request(), _evidence_pack(), adapter_id="fake-json")

    source_refs_schema = request.json_schema["properties"]["findings"]["items"]["properties"]["source_refs"]

    assert source_refs_schema["minItems"] == 1
    assert source_refs_schema["items"]["enum"] == ["S1", "S2"]


def test_valid_returned_citation_keys_remap_back_to_real_source_ids() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-json",
            default_json_response={
                "summary": "The prepared evidence supports the bounded option.",
                "findings": [
                    {"text": "The web article supports the bounded option.", "source_refs": ["S1"]},
                    {"text": "The document note supports the same path.", "source_refs": ["S2"]},
                ],
                "inferences": ["Both sources point toward the narrow rollout."],
                "uncertainties": ["No live validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        ),
    )

    assert artifact.findings[0].source_refs == ("web-359eb9e7c0c0",)
    assert artifact.findings[1].source_refs == ("document-a81f1c0a",)
    assert artifact.source_ids == ("web-359eb9e7c0c0", "document-a81f1c0a")


def test_unknown_returned_citation_keys_fail_closed() -> None:
    with pytest.raises(ResearchSynthesisValidationError, match="unknown citation refs"):
        synthesize_research(
            research_request=_research_request(),
            evidence_pack=_evidence_pack(),
            adapter=FakeModelAdapter(
                adapter_id="fake-json",
                default_json_response={
                    "summary": "This should fail closed.",
                    "findings": [{"text": "Unsupported claim", "source_refs": ["S9"]}],
                    "inferences": [],
                    "uncertainties": [],
                    "recommendation": None,
                },
            ),
        )


def test_final_artifact_keeps_real_internal_source_ids_after_remap() -> None:
    artifact = synthesize_research(
        research_request=_research_request(),
        evidence_pack=_evidence_pack(),
        adapter=FakeModelAdapter(
            adapter_id="fake-json",
            default_json_response={
                "summary": "The prepared evidence supports the bounded option.",
                "findings": [{"text": "The web article supports the bounded option.", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        ),
    )

    assert artifact.findings[0].source_refs == ("web-359eb9e7c0c0",)
    assert artifact.source_ids == ("web-359eb9e7c0c0",)
    assert artifact.source_ids != ("S1",)


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
                source_id="web-359eb9e7c0c0",
                source_type="web",
                title="Bounded Article",
                locator="https://example.com/a",
                snippet="The bounded rollout remains stable.",
                published_at="2026-04-12",
            ),
            SourceItem(
                source_id="document-a81f1c0a",
                source_type="document",
                title="Local Plan",
                locator="doc://plan",
                snippet="The local plan keeps scope narrow.",
            ),
        ),
        evidence_items=(
            EvidenceItem(text="The bounded rollout remains stable.", source_refs=("web-359eb9e7c0c0",)),
            EvidenceItem(text="The local plan keeps scope narrow.", source_refs=("document-a81f1c0a",)),
        ),
        contradictions=("web-359eb9e7c0c0: no direct contradiction was found.",),
        uncertainties=("External verification was not performed.",),
        constraints=("Stay bounded.",),
    )
