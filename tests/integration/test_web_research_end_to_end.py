from jeff.cognitive import ResearchRequest, run_web_research
from jeff.cognitive.research import web as web_module
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)


def test_web_queries_and_fake_default_adapter_drive_end_to_end_research(monkeypatch) -> None:
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
                        "findings": [{"text": "The article supports the bounded rollout.", "source_refs": ["S1"]}],
                        "inferences": ["A narrow path remains better supported."],
                        "uncertainties": ["Only one fetched source was considered."],
                        "recommendation": "Keep the rollout bounded.",
                    },
                ),
            ),
        )
    )

    artifact = run_web_research(request, services)

    assert artifact.summary == "The fetched web source supports a bounded rollout."
    assert artifact.source_ids == (source_id,)


def test_explicit_adapter_selection_works_with_multiple_registered_fake_adapters(monkeypatch) -> None:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda query, *, max_results: (
            web_module._WebSearchResult(
                title="Secondary article",
                url="https://example.com/b",
                snippet="The secondary source says the bounded path is safer.",
            ),
        ),
    )
    monkeypatch.setattr(
        web_module,
        "_fetch_web_page_excerpt",
        lambda url, *, max_chars: "The secondary source says the bounded path is safer.",
    )

    request = ResearchRequest(
        question="What does the bounded path support?",
        web_queries=("bounded path",),
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
                        "summary": "Default summary.",
                        "findings": [{"text": "Default finding", "source_refs": ["S1"]}],
                        "inferences": [],
                        "uncertainties": [],
                        "recommendation": None,
                    },
                ),
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-secondary",
                    model_name="fake-model-2",
                    fake_json_response={
                        "summary": "Secondary summary.",
                        "findings": [{"text": "Secondary finding", "source_refs": ["S1"]}],
                        "inferences": ["Secondary inference"],
                        "uncertainties": ["Secondary uncertainty"],
                        "recommendation": "Use the secondary adapter.",
                    },
                ),
            ),
        )
    )

    artifact = run_web_research(request, services, adapter_id="fake-secondary")

    assert artifact.summary == "Secondary summary."
    assert artifact.findings[0].text == "Secondary finding"
