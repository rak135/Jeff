import json
from pathlib import Path

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
from tests.fixtures.research import bounded_research_text_from_payload


def test_cli_docs_research_runs_end_to_end_with_persistence_and_rendered_result(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    records = result.context.research_artifact_store.list_records(project_id="project-1", work_unit_id="wu-1")

    assert "created and selected new run: run-1" in result.text
    assert "artifact_id=research-" in result.text
    assert "summary=The documents support a bounded rollout." in result.text
    assert "plan.md | " in result.text
    assert str(document) in result.text
    assert "persistence=research artifact persisted as support at " in result.text
    assert len(records) == 1
    assert records[0].run_id == "run-1"


def test_cli_web_research_runs_end_to_end_with_persistence_and_rendered_result(
    tmp_path: Path,
    monkeypatch,
) -> None:
    question = "What does the bounded rollout support?"
    query = "bounded rollout"
    cli = _build_web_cli(tmp_path, question=question, query=query, monkeypatch=monkeypatch)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research web "{question}" "{query}"')

    records = result.context.research_artifact_store.list_records(project_id="project-1", work_unit_id="wu-1")

    assert "RESEARCH web project_id=project-1 work_unit_id=wu-1 run_id=run-1" in result.text
    assert "summary=The fetched web source supports a bounded rollout." in result.text
    assert records[0].source_mode == "web"
    assert records[0].source_items[0].locator == "https://example.com/a"


def test_ad_hoc_research_creates_and_reuses_general_research_lawfully(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    first = cli.execute(f'/research docs "{question}" "{document}"')
    cli.run_one_shot("/scope clear")
    second = cli.execute(f'/research docs "{question}" "{document}"')

    general_project = second.context.state.projects["general_research"]

    assert "general_research" in first.context.state.projects
    assert len(general_project.work_units) == 1
    assert "created built-in project: general_research" in first.text
    assert "created built-in project: general_research" not in second.text
    assert "auto-selected current run: run-1" in second.text


def test_research_inside_selected_project_does_not_jump_to_general_research(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    assert cli.session.scope.project_id == "project-1"
    assert "general_research" not in result.context.state.projects


def test_explicit_memory_handoff_surfaces_write_reject_and_defer_outcomes_without_reinterpretation(
    tmp_path: Path,
    monkeypatch,
) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path / "write-reject", question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    first = cli.execute(f'/research docs "{question}" "{document}" --handoff-memory')
    second = cli.execute(f'/research docs "{question}" "{document}" --handoff-memory')

    defer_cli = _build_web_cli(
        tmp_path / "defer",
        question="What risk does the bounded rollout carry?",
        query="bounded rollout risk",
        monkeypatch=monkeypatch,
        step1_text=bounded_research_text_from_payload(
            {
            "summary": "The fetched web source warns about bounded rollout risk.",
            "findings": [{"text": "The article flags unresolved risk.", "source_refs": ["S1"]}],
            "inferences": [],
            "uncertainties": ["Risk remains unresolved."],
            "recommendation": None,
            }
        ),
        snippet="The bounded rollout remains risky.",
        excerpt="The bounded rollout remains risky and uncertain.",
    )
    defer_cli.run_one_shot("/project use project-1")
    defer_cli.run_one_shot("/work use wu-1")
    defer = defer_cli.execute(
        '/research web "What risk does the bounded rollout carry?" "bounded rollout risk" --handoff-memory'
    )

    assert "memory_handoff=write memory_id=memory-1" in first.text
    assert "memory_handoff=reject" in second.text
    assert "duplicate committed memory already exists" in second.text
    assert "memory_handoff=defer" in defer.text
    assert "support is not yet stable or strong enough for committed memory" in defer.text


def test_research_json_payload_exposes_truth_and_support_without_provider_specific_interface_imports(
    tmp_path: Path,
) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    assert payload["view"] == "research_result"
    assert payload["truth"]["project_id"] == "project-1"
    assert "artifact_id" not in payload["truth"]
    assert payload["support"]["artifact_id"].startswith("research-")

    interface_sources = [
        Path("jeff/interface/commands.py"),
        Path("jeff/interface/json_views.py"),
        Path("jeff/interface/render.py"),
        Path("jeff/interface/cli.py"),
    ]
    for source_path in interface_sources:
        source_text = source_path.read_text(encoding="utf-8").lower()
        assert "ollama" not in source_text
        assert "adapterproviderkind" not in source_text


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
            step1_text=bounded_research_text_from_payload(
                {
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": ["A narrow implementation remains better supported."],
                "uncertainties": ["No external validation was performed."],
                "recommendation": "Proceed with the bounded path.",
                }
            ),
        )
    ), document


def _build_web_cli(
    tmp_path: Path,
    *,
    question: str,
    query: str,
    monkeypatch,
    step1_text: str | None = None,
    snippet: str = "The bounded rollout remains stable.",
    excerpt: str = "The bounded rollout remains stable and avoids widening scope.",
) -> JeffCLI:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda incoming_query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded article",
                url="https://example.com/a",
                snippet=f"{snippet} Query={incoming_query}.",
            ),
        ),
    )
    monkeypatch.setattr(
        web_module,
        "_fetch_web_page_excerpt",
        lambda url, *, max_chars: excerpt,
    )
    source_id = web_module.collect_web_sources(
        ResearchRequest(
            question=question,
            web_queries=(query,),
            source_mode="web",
        )
    )[0].source_id
    if step1_text is None:
        step1_text = bounded_research_text_from_payload(
            {
            "summary": "The fetched web source supports a bounded rollout.",
            "findings": [{"text": "The article supports the bounded rollout.", "source_refs": ["S1"]}],
            "inferences": ["A narrow path remains better supported."],
            "uncertainties": ["Only one fetched source was considered."],
            "recommendation": "Keep the rollout bounded.",
            }
        )
    return JeffCLI(
        context=_build_research_context(
            tmp_path,
            step1_text=step1_text,
        )
    )


def _build_research_context(tmp_path: Path, *, step1_text: str) -> InterfaceContext:
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
                        fake_text_response=step1_text,
                    ),
                ),
            )
        ),
        research_artifact_store=ResearchArtifactStore(tmp_path),
        memory_store=InMemoryMemoryStore(),
    )
