from pathlib import Path

import pytest

from jeff.cognitive import ResearchRequest, SourceItem
from jeff.cognitive.research import documents as documents_module
from jeff.cognitive.research import persistence as persistence_module
from jeff.interface import JeffCLI, InterfaceContext
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    build_infrastructure_services,
)
from jeff.main import _run_interactive
from jeff.cognitive import ResearchArtifactStore
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_debug_stream_shows_downstream_post_validation_checkpoints_and_success(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, document, call_counter = _build_docs_cli_with_single_use_source_collection(tmp_path, monkeypatch)
    _install_inputs(
        monkeypatch,
        [
            "/project use project-1",
            "/work use wu-1",
            "/mode debug",
            f'/research docs "What does the bounded plan support?" "{document}"',
            "quit",
        ],
    )

    exit_code = _run_interactive(cli)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert call_counter["count"] == 1
    assert "[debug][research] provenance_validation_succeeded" in captured.out
    assert "[debug][research] artifact_record_build_started" in captured.out
    assert "[debug][research] artifact_record_build_succeeded" in captured.out
    assert "[debug][research] artifact_store_save_started" in captured.out
    assert "[debug][research] artifact_store_save_succeeded" in captured.out
    assert "[debug][research] projection_started" in captured.out
    assert "[debug][research] projection_succeeded" in captured.out
    assert "[debug][research] render_started" in captured.out
    assert "[debug][research] render_succeeded" in captured.out
    assert captured.out.index("[debug][research] artifact_record_build_succeeded") < captured.out.index("RESEARCH docs")
    assert "finding references unknown source ids" not in captured.out
    assert "finding references unknown source ids" not in captured.err


def _build_docs_cli_with_single_use_source_collection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[JeffCLI, Path, dict[str, int]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    call_counter = {"count": 0}

    def alternating_collect(request: ResearchRequest):  # type: ignore[no-untyped-def]
        call_counter["count"] += 1
        suffix = "a" if call_counter["count"] == 1 else "b"
        return (
            SourceItem(
                source_id=f"document-{suffix}",
                source_type="document",
                title=f"Plan {suffix.upper()}",
                locator=str(document.resolve()),
                snippet="The bounded plan keeps the rollout stable.",
            ),
        )

    monkeypatch.setattr(persistence_module, "collect_document_sources", alternating_collect)
    monkeypatch.setattr(documents_module, "collect_document_sources", alternating_collect)

    state, _ = build_state_with_runs(run_specs=())
    cli = JeffCLI(
        context=InterfaceContext(
            state=state,
            infrastructure_services=build_infrastructure_services(
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
                                "inferences": [],
                                "uncertainties": [],
                                "recommendation": None,
                            },
                        ),
                    ),
                )
            ),
            research_artifact_store=ResearchArtifactStore(tmp_path),
            memory_store=InMemoryMemoryStore(),
        )
    )
    return cli, document, call_counter


def _install_inputs(monkeypatch: pytest.MonkeyPatch, commands: list[str]) -> None:
    iterator = iter(commands)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(iterator))
