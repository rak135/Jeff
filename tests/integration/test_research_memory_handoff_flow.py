from pathlib import Path

from jeff.cognitive import (
    ResearchArtifactStore,
    ResearchRequest,
    handoff_persisted_research_record_to_memory,
    run_and_persist_document_research,
    run_and_persist_web_research,
)
from jeff.cognitive.research import web as web_module
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.memory import InMemoryMemoryStore


def test_document_research_persisted_artifact_can_handoff_to_current_memory_pipeline(tmp_path: Path) -> None:
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
    record = run_and_persist_document_research(request, services, ResearchArtifactStore(tmp_path))
    store = InMemoryMemoryStore()

    first = handoff_persisted_research_record_to_memory(record, store)
    second = handoff_persisted_research_record_to_memory(record, store)

    assert first is not None and first.write_outcome == "write"
    assert second is not None and second.write_outcome == "reject"


def test_web_research_persisted_artifact_can_handoff_to_current_memory_pipeline_with_defer(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded article",
                url="https://example.com/a",
                snippet="The bounded rollout remains risky.",
            ),
        ),
    )
    monkeypatch.setattr(
        web_module,
        "_fetch_web_page_excerpt",
        lambda url, *, max_chars: "The bounded rollout remains risky and uncertain.",
    )
    request = ResearchRequest(
        question="What risk does the bounded rollout carry?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        web_queries=("bounded rollout risk",),
        source_mode="web",
    )
    source_id = web_module.collect_web_sources(request)[0].source_id
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_json_response={
                        "summary": "The fetched web source warns about bounded rollout risk.",
                        "findings": [{"text": "The article flags unresolved risk.", "source_refs": ["S1"]}],
                        "inferences": [],
                        "uncertainties": ["Risk remains unresolved."],
                        "recommendation": None,
                    },
                ),
            ),
        )
    )
    record = run_and_persist_web_research(request, services, ResearchArtifactStore(tmp_path))
    store = InMemoryMemoryStore()

    decision = handoff_persisted_research_record_to_memory(record, store)

    assert decision is not None
    assert decision.write_outcome == "defer"
