import json
from pathlib import Path

import pytest

from jeff.cognitive import (
    ResearchArtifactStore,
    ResearchRequest,
    build_document_evidence_pack,
    collect_document_sources,
    run_document_research,
    validate_research_provenance,
)
from jeff.cognitive.research import ResearchSynthesisValidationError
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.interface import InterfaceContext, JeffCLI
from jeff.interface.json_views import research_result_json
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_cli_document_research_accepts_citation_key_model_output_and_keeps_real_source_ids(
    tmp_path: Path,
) -> None:
    question = "What does the bounded plan support?"
    cli, document, source_id = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    records = result.context.research_artifact_store.list_records(project_id="project-1", work_unit_id="wu-1")
    payload = research_result_json(
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        research_mode="local_documents",
        handoff_memory_requested=False,
        record=records[0],
        memory_handoff_result=None,
        session=cli.session,
    )

    assert 'RESEARCH docs project_id=project-1 work_unit_id=wu-1 run_id=run-1' in result.text
    assert records[0].findings[0].source_refs == (source_id,)
    assert records[0].source_ids == (source_id,)
    assert payload["support"]["findings"][0]["source_refs"] == [source_id]
    assert payload["support"]["findings"][0]["resolved_sources"][0]["source_id"] == source_id


def test_qwen_like_invented_citation_key_fails_closed_cleanly(tmp_path: Path) -> None:
    request = _document_request(tmp_path / "drift")

    services = _build_services(
        {
            "summary": "This should fail closed.",
            "findings": [{"text": "Unsupported claim", "source_refs": ["S9"]}],
            "inferences": [],
            "uncertainties": [],
            "recommendation": None,
        }
    )

    with pytest.raises(ResearchSynthesisValidationError, match="unknown citation refs"):
        run_document_research(request, services)


def test_provenance_validator_still_accepts_remapped_real_source_ids_after_synthesis(
    tmp_path: Path,
) -> None:
    doc_a = tmp_path / "a.md"
    doc_b = tmp_path / "b.md"
    doc_a.write_text("The first note supports the bounded path.\n", encoding="utf-8")
    doc_b.write_text("The second note confirms the safer bounded path.\n", encoding="utf-8")
    request = ResearchRequest(
        question="What does the bounded path support?",
        document_paths=(str(doc_a), str(doc_b)),
        source_mode="local_documents",
    )
    sources = collect_document_sources(request)
    evidence_pack = build_document_evidence_pack(request, sources)
    services = _build_services(
        {
            "summary": "The second note is the strongest support.",
            "findings": [{"text": "The second note confirms the safer path.", "source_refs": ["S2"]}],
            "inferences": ["The narrower rollout is better supported."],
            "uncertainties": ["No external validation was performed."],
            "recommendation": None,
        }
    )

    artifact = run_document_research(request, services)

    validate_research_provenance(
        findings=artifact.findings,
        source_ids=artifact.source_ids,
        source_items=sources,
        evidence_items=evidence_pack.evidence_items,
    )

    assert artifact.findings[0].source_refs == (sources[1].source_id,)
    assert artifact.source_ids == (sources[1].source_id,)


def _build_docs_cli(tmp_path: Path, *, question: str) -> tuple[JeffCLI, Path, str]:
    request = _document_request(tmp_path, question=question)
    document = Path(request.document_paths[0])
    source_id = collect_document_sources(request)[0].source_id
    return JeffCLI(
        context=_build_context(
            tmp_path,
            {
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": ["A narrow implementation remains better supported."],
                "uncertainties": ["No external validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        )
    ), document, source_id


def _document_request(root: Path, *, question: str = "What does the bounded plan support?") -> ResearchRequest:
    root.mkdir(parents=True, exist_ok=True)
    document = root / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    return ResearchRequest(
        question=question,
        document_paths=(str(document),),
        source_mode="local_documents",
    )


def _build_context(tmp_path: Path, fake_json_response: dict[str, object]) -> InterfaceContext:
    state, _ = build_state_with_runs(run_specs=())
    return InterfaceContext(
        state=state,
        infrastructure_services=_build_services(fake_json_response),
        research_artifact_store=ResearchArtifactStore(tmp_path),
        memory_store=InMemoryMemoryStore(),
    )


def _build_services(fake_json_response: dict[str, object]):
    return build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_json_response=fake_json_response,
                ),
            ),
        )
    )
