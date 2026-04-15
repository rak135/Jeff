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
                    fake_text_response=_bounded_text(
                        summary="The documents support a bounded rollout.",
                        findings=(("The plan emphasizes bounded rollout.", "S1"),),
                        inference="A narrow implementation remains better supported.",
                        uncertainty="No external validation was performed.",
                        recommendation="Proceed with the bounded path.",
                    ),
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
                    fake_text_response=_bounded_text(
                        summary="The fetched web source supports a bounded rollout.",
                        findings=(("The article supports the bounded rollout.", "S1"),),
                        inference="A narrow path remains better supported.",
                        uncertainty="Only one fetched source was considered.",
                        recommendation="Keep the rollout bounded.",
                    ),
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


def _bounded_text(
    *,
    summary: str,
    findings: tuple[tuple[str, str], ...],
    inference: str,
    uncertainty: str,
    recommendation: str,
) -> str:
    finding_lines: list[str] = []
    for text, citation_key in findings:
        finding_lines.extend([f"- text: {text}", f"  cites: {citation_key}"])

    return "\n".join(
        [
            "SUMMARY:",
            summary,
            "",
            "FINDINGS:",
            *finding_lines,
            "",
            "INFERENCES:",
            f"- {inference}",
            "",
            "UNCERTAINTIES:",
            f"- {uncertainty}",
            "",
            "RECOMMENDATION:",
            recommendation,
        ]
    )
