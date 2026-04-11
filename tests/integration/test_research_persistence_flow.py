from pathlib import Path

from jeff.cognitive import (
    ResearchArtifactStore,
    ResearchRequest,
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


def test_document_research_can_produce_and_persist_artifact(tmp_path: Path) -> None:
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
                        "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": []}],
                        "inferences": ["A narrow implementation remains better supported."],
                        "uncertainties": ["No external validation was performed."],
                        "recommendation": "Proceed with the bounded path.",
                    },
                ),
            ),
        )
    )
    source_id = "document"
    collected = __import__("jeff.cognitive", fromlist=["collect_document_sources"]).collect_document_sources(request)
    source_id = collected[0].source_id
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
                        "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": [source_id]}],
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

    assert record.summary == "The documents support a bounded rollout."
    assert record.source_items[0].source_id == source_id
    assert record.evidence_items[0].source_refs == (source_id,)
    assert store.load(record.artifact_id) == record


def test_web_research_can_produce_and_persist_artifact(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded article",
                url="https://example.com/a",
                snippet="The bounded rollout remains stable.",
            ),
        ),
    )
    monkeypatch.setattr(
        web_module,
        "_fetch_web_page_excerpt",
        lambda url, *, max_chars: "The bounded rollout remains stable and avoids widening scope.",
    )
    request = ResearchRequest(
        question="What does the bounded rollout support?",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        web_queries=("bounded rollout",),
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
                        "summary": "The fetched web source supports a bounded rollout.",
                        "findings": [{"text": "The article supports the bounded rollout.", "source_refs": [source_id]}],
                        "inferences": ["A narrow path remains better supported."],
                        "uncertainties": ["Only one fetched source was considered."],
                        "recommendation": "Keep the rollout bounded.",
                    },
                ),
            ),
        )
    )
    store = ResearchArtifactStore(tmp_path)

    record = run_and_persist_web_research(request, services, store)

    assert record.source_mode == "web"
    assert record.source_items[0].locator == "https://example.com/a"
    assert record.evidence_items[0].source_refs == (source_id,)
    assert store.load(record.artifact_id) == record
