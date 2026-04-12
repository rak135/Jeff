import json
from pathlib import Path

import pytest

from jeff.cognitive import ResearchArtifactStore, ResearchRequest, collect_document_sources
from jeff.cognitive.research import web as web_module
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.interface import InterfaceContext, JeffCLI
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_cli_web_research_source_rendering_shows_title_locator_and_date_when_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "What does the bounded rollout support?"
    query = "bounded rollout"
    cli = _build_web_cli(tmp_path, question=question, query=query, monkeypatch=monkeypatch, published_at="2026-04-12")

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research web "{question}" "{query}"')

    assert "source: Bounded article | https://example.com/a" in result.text
    assert "published: 2026-04-12" in result.text


def test_cli_research_source_rendering_omits_date_cleanly_when_unavailable(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    assert "source: plan.md | " in result.text
    assert "published:" not in result.text


def test_json_projection_exposes_published_at_and_clean_snippet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "What does the bounded rollout support?"
    query = "bounded rollout"
    cli = _build_web_cli(
        tmp_path,
        question=question,
        query=query,
        monkeypatch=monkeypatch,
        published_at="2026-04-12",
        fetched_excerpt="Useful support text. <b>tags gone</b> Extra context.",
    )

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research web "{question}" "{query}"', json_output=True))

    assert payload["support"]["sources"][0]["published_at"] == "2026-04-12"
    assert payload["support"]["sources"][0]["snippet"].startswith("Useful support text.")
    assert payload["support"]["findings"][0]["resolved_sources"][0]["published_at"] == "2026-04-12"


def _build_docs_cli(tmp_path: Path, *, question: str) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    source_id = collect_document_sources(
        ResearchRequest(
            question=question,
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
    return JeffCLI(
        context=_build_research_context(
            tmp_path,
            fake_json_response={
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": ["A narrow implementation remains better supported."],
                "uncertainties": ["No external validation was performed."],
                "recommendation": "Proceed with the bounded path.",
            },
        )
    ), document


def _build_web_cli(
    tmp_path: Path,
    *,
    question: str,
    query: str,
    monkeypatch: pytest.MonkeyPatch,
    published_at: str | None,
    fetched_excerpt: str = "The bounded rollout remains stable and avoids widening scope.",
) -> JeffCLI:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda incoming_query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded article",
                url="https://example.com/a",
                snippet=f"<div>The bounded rollout remains stable for {incoming_query}.</div>",
            ),
        ),
    )

    def fake_fetch(url: str, *, max_chars: int) -> str:
        web_module._PUBLISHED_AT_CACHE[(url, max_chars)] = published_at
        return fetched_excerpt

    monkeypatch.setattr(web_module, "_fetch_web_page_excerpt", fake_fetch)
    source_id = web_module.collect_web_sources(
        ResearchRequest(
            question=question,
            web_queries=(query,),
            source_mode="web",
        )
    )[0].source_id
    return JeffCLI(
        context=_build_research_context(
            tmp_path,
            fake_json_response={
                "summary": "The fetched web source supports a bounded rollout.",
                "findings": [{"text": "The article supports the bounded rollout.", "source_refs": ["S1"]}],
                "inferences": ["A narrow path remains better supported."],
                "uncertainties": ["Only one fetched source was considered."],
                "recommendation": "Keep the rollout bounded.",
            },
        )
    )


def _build_research_context(tmp_path: Path, *, fake_json_response: dict[str, object]) -> InterfaceContext:
    state, _ = build_state_with_runs(run_specs=())
    return InterfaceContext(
        state=state,
        infrastructure_services=build_infrastructure_services(
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
        ),
        research_artifact_store=ResearchArtifactStore(tmp_path),
        memory_store=InMemoryMemoryStore(),
    )
