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


def test_docs_command_parses_correctly(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    records = result.context.research_artifact_store.list_records(project_id="project-1", work_unit_id="wu-1")

    assert "RESEARCH docs project_id=project-1 work_unit_id=wu-1 run_id=run-1" in result.text
    assert records[0].question == question
    assert records[0].source_mode == "local_documents"


def test_web_command_parses_correctly(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = "What does the bounded rollout support?"
    query = "bounded rollout"
    cli = _build_web_cli(tmp_path, question=question, query=query, monkeypatch=monkeypatch)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research web "{question}" "{query}"')

    records = result.context.research_artifact_store.list_records(project_id="project-1", work_unit_id="wu-1")

    assert "RESEARCH web project_id=project-1 work_unit_id=wu-1 run_id=run-1" in result.text
    assert records[0].question == question
    assert records[0].source_mode == "web"


@pytest.mark.parametrize(
    ("command", "message"),
    (
        ('/research docs What does this support? path.txt', "quoted question/objective"),
        ('/research docs "What does this support?"', "at least one explicit path"),
        ('/research web "What does this support?"', "at least one explicit query"),
        ('/research api "What does this support?" anything', "research mode must be"),
    ),
)
def test_malformed_research_command_forms_fail_clearly(command: str, message: str) -> None:
    state, _ = build_state_with_runs(run_specs=())
    cli = JeffCLI(context=InterfaceContext(state=state))

    with pytest.raises(ValueError, match=message):
        cli.run_one_shot(command)


def test_research_without_project_scope_anchors_into_general_research_lawfully(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    result = cli.execute(f'/research docs "{question}" "{document}"')

    assert "anchored ad-hoc research into project_id=general_research" in result.text
    assert cli.session.scope.project_id == "general_research"
    assert cli.session.scope.work_unit_id is not None
    assert cli.session.scope.work_unit_id.startswith("research-docs-what-does-the-bounded-plan-support-")
    assert cli.session.scope.run_id == "run-1"
    assert "general_research" in result.context.state.projects


def test_research_with_current_project_and_work_unit_uses_current_scope(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    result = cli.execute(f'/research docs "{question}" "{document}"')

    assert cli.session.scope.project_id == "project-1"
    assert cli.session.scope.work_unit_id == "wu-1"
    assert cli.session.scope.run_id == "run-1"
    assert "general_research" not in result.context.state.projects


def test_handoff_memory_flag_toggles_memory_handoff_explicitly(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli_without_handoff, document = _build_docs_cli(tmp_path / "without", question=question)

    cli_without_handoff.run_one_shot("/project use project-1")
    cli_without_handoff.run_one_shot("/work use wu-1")
    without_result = cli_without_handoff.execute(f'/research docs "{question}" "{document}"')

    assert "memory_handoff=not requested" in without_result.text
    assert without_result.context.memory_store.list_project_records("project-1") == ()

    cli_with_handoff, document_with_handoff = _build_docs_cli(tmp_path / "with", question=question)
    cli_with_handoff.run_one_shot("/project use project-1")
    cli_with_handoff.run_one_shot("/work use wu-1")
    with_result = cli_with_handoff.execute(
        f'/research docs "{question}" "{document_with_handoff}" --handoff-memory'
    )

    assert "memory_handoff=write memory_id=memory-1" in with_result.text
    assert len(with_result.context.memory_store.list_project_records("project-1")) == 1


def test_research_json_mode_returns_research_result_payload(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    cli.run_one_shot("/json on")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"'))

    assert payload["view"] == "research_result"
    assert payload["truth"]["project_id"] == "project-1"
    assert payload["derived"]["research_mode"] == "docs"


def test_research_json_payload_keeps_support_distinct_from_truth(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(tmp_path, question=question)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    assert set(payload["truth"]) == {"project_id", "work_unit_id", "run_id"}
    assert "artifact_id" not in payload["truth"]
    assert payload["support"]["artifact_id"].startswith("research-")
    assert payload["support"]["summary"] == "The documents support a bounded rollout."
    assert payload["derived"]["memory_handoff_result"] is None


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
) -> JeffCLI:
    monkeypatch.setattr(
        web_module,
        "_search_web_query",
        lambda incoming_query, *, max_results: (
            web_module._WebSearchResult(
                title="Bounded article",
                url="https://example.com/a",
                snippet=f"The bounded rollout remains stable for {incoming_query}.",
            ),
        ),
    )
    monkeypatch.setattr(
        web_module,
        "_fetch_web_page_excerpt",
        lambda url, *, max_chars: "The bounded rollout remains stable and avoids widening scope.",
    )
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
