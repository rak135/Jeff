from pathlib import Path

from jeff.cognitive import (
    EvidenceItem,
    EvidencePack,
    ResearchArtifactStore,
    ResearchRequest,
    SourceItem,
    run_and_persist_document_research,
    run_and_persist_web_research,
)
from jeff.cognitive.research.archive import (
    ResearchArchiveStore,
    get_archive_artifact_by_id,
    retrieve_project_archive,
)
from jeff.cognitive.research import persistence as research_persistence
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


def test_document_research_real_output_persists_research_brief_to_archive_lawfully(tmp_path: Path) -> None:
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
    store = ResearchArtifactStore(tmp_path / "records")
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    record = run_and_persist_document_research(request, services, store, archive_store=archive_store)
    brief_result = retrieve_project_archive(
        purpose="inspect brief archive",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        artifact_family_filter="research_brief",
        store=archive_store,
    )

    assert store.load(record.artifact_id) == record
    assert len(brief_result.records) == 1
    brief = brief_result.records[0]
    assert brief.question_or_objective == request.question
    assert brief.summary == record.summary
    assert get_archive_artifact_by_id("project-1", str(brief.artifact_id), store=archive_store) == brief
    assert archive_store.artifacts_dir_for("project-1") == tmp_path / "archive" / "projects" / "project-1" / "research" / "artifacts"
    assert not archive_store.history_dir_for("project-1").exists()
    assert not (tmp_path / "archive" / "projects" / "project-1" / "memory").exists()
    assert not (tmp_path / "archive" / "projects" / "project-1" / "research" / "knowledge").exists()


def test_comparison_shaped_research_output_persists_research_comparison_lawfully(tmp_path: Path) -> None:
    document = tmp_path / "compare.md"
    document.write_text(
        "Option A is narrower.\n"
        "Option B is broader but riskier.\n",
        encoding="utf-8",
    )
    request = ResearchRequest(
        question="Compare option-a vs option-b on fit and risk.",
        project_id="project-1",
        work_unit_id="wu-compare",
        run_id="run-compare",
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
                    fake_text_response=_bounded_text(
                        summary="Option A fits the bounded rollout better.",
                        findings=(("Option A stays narrower than option B.", "S1"),),
                        inference="Option A is the cleaner immediate fit.",
                        uncertainty="Long-term operating cost is still uncertain.",
                        recommendation="Prefer option A for the current bounded move.",
                    ),
                ),
            ),
        )
    )
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    run_and_persist_document_research(
        request,
        services,
        ResearchArtifactStore(tmp_path / "records"),
        archive_store=archive_store,
    )
    comparison_result = retrieve_project_archive(
        purpose="inspect comparison archive",
        project_id="project-1",
        work_unit_id="wu-compare",
        run_id="run-compare",
        artifact_family_filter="research_comparison",
        store=archive_store,
    )

    assert len(comparison_result.records) == 1
    comparison = comparison_result.records[0]
    assert comparison.comparison_targets == ("option-a", "option-b")
    assert comparison.comparison_criteria == ("fit", "risk")


def test_real_research_output_persists_evidence_bundle_and_source_set_with_provenance_linkage(tmp_path: Path) -> None:
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
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    run_and_persist_document_research(
        request,
        services,
        ResearchArtifactStore(tmp_path / "records"),
        archive_store=archive_store,
    )
    evidence_result = retrieve_project_archive(
        purpose="inspect evidence archive",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        artifact_family_filter="evidence_bundle",
        store=archive_store,
    )
    source_set_result = retrieve_project_archive(
        purpose="inspect source-set archive",
        project_id="project-1",
        work_unit_id="wu-1",
        run_id="run-1",
        artifact_family_filter="source_set",
        store=archive_store,
    )

    assert len(evidence_result.records) == 1
    assert evidence_result.records[0].claim_evidence_links[0].evidence_ids
    assert all(
        evidence_id.startswith(f"{evidence_result.records[0].derived_from_artifact_ids[0]}:evidence:")
        for evidence_id in evidence_result.records[0].claim_evidence_links[0].evidence_ids
    )
    assert evidence_result.records[0].evidence_items[0].source_refs
    assert len(source_set_result.records) == 1
    assert source_set_result.records[0].source_ordering == tuple(source_set_result.records[0].source_refs)


def test_event_shaped_web_research_output_persists_event_history_record_lawfully(tmp_path: Path, monkeypatch) -> None:
    request = ResearchRequest(
        question="What changed in the service rollout?",
        project_id="project-1",
        work_unit_id="wu-event",
        run_id="run-event",
        web_queries=("service rollout change",),
        source_mode="web",
    )
    source = SourceItem(
        source_id="source-1",
        source_type="web",
        title="Service update",
        locator="https://example.com/update",
        snippet="The provider announced a service rollout change.",
        published_at="2026-04-19T09:00:00Z",
    )
    monkeypatch.setattr(research_persistence, "collect_web_sources", lambda _request: (source,))
    monkeypatch.setattr(
        research_persistence,
        "build_web_evidence_pack",
        lambda _request, sources: EvidencePack(
            question=_request.question,
            sources=sources,
            evidence_items=(EvidenceItem(text="The provider announced a service rollout change.", source_refs=("source-1",)),),
        ),
    )
    services = build_infrastructure_services(
        ModelAdapterRuntimeConfig(
            default_adapter_id="fake-default",
            adapters=(
                AdapterFactoryConfig(
                    provider_kind=AdapterProviderKind.FAKE,
                    adapter_id="fake-default",
                    model_name="fake-model",
                    fake_text_response=_bounded_text(
                        summary="The provider announced a service rollout change.",
                        findings=(("The service rollout change was announced on 2026-04-19.", "S1"),),
                        inference="This is a dated event that should remain historical support.",
                        uncertainty="User impact is still being assessed.",
                        recommendation="Track the rollout before treating it as stable.",
                    ),
                ),
            ),
        )
    )
    archive_store = ResearchArchiveStore(tmp_path / "archive")

    run_and_persist_web_research(
        request,
        services,
        ResearchArtifactStore(tmp_path / "records"),
        archive_store=archive_store,
    )
    event_result = retrieve_project_archive(
        purpose="inspect event history archive",
        project_id="project-1",
        work_unit_id="wu-event",
        run_id="run-event",
        artifact_family_filter="event_history_record",
        effective_date="2026-04-19",
        store=archive_store,
    )

    assert len(event_result.records) == 1
    event_record = event_result.records[0]
    assert event_record.event_date == "2026-04-19"
    assert event_record.event_framing == request.question
    assert event_record.source_refs == ("source-1",)
    assert event_record.uncertainty == ("User impact is still being assessed.",)
    assert event_result.explicitly_historical is True
    assert not (tmp_path / "archive" / "projects" / "project-1" / "memory").exists()
    assert not (tmp_path / "archive" / "projects" / "project-1" / "research" / "knowledge").exists()


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
