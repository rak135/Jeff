import json
from pathlib import Path

import pytest

from jeff.main import _run_interactive
from jeff.interface import JeffCLI, InterfaceContext
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    ModelMalformedOutputError,
    ModelTimeoutError,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.cognitive import ResearchArtifactStore, ResearchRequest, collect_document_sources
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_live_cli_timeout_with_json_on_surfaces_structured_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, document = _build_docs_cli(tmp_path, mode="timeout")
    _install_inputs(
        monkeypatch,
        [
            "/project use project-1",
            "/work use wu-1",
            "/json on",
            f'/research docs "What does the bounded plan support?" "{document}"',
            "quit",
        ],
    )

    exit_code = _run_interactive(cli)
    captured = capsys.readouterr()
    payload = _last_json_line(captured.out)

    assert exit_code == 0
    assert payload["view"] == "research_error"
    assert payload["support"]["error_code"] == "timeout"
    assert payload["support"]["adapter_id"] == "research-timeout"
    assert "research synthesis invocation failed" not in captured.out


def test_live_cli_malformed_output_without_json_surfaces_useful_bounded_detail(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, document = _build_docs_cli(tmp_path, mode="malformed")
    _install_inputs(
        monkeypatch,
        [
            "/project use project-1",
            "/work use wu-1",
            f'/research docs "What does the bounded plan support?" "{document}"',
            "quit",
        ],
    )

    exit_code = _run_interactive(cli)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "research synthesis failed: malformed_output" in captured.err
    assert "adapter=research-malformed" in captured.err
    assert "research synthesis invocation failed" not in captured.err


def test_live_cli_success_path_remains_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    cli, document = _build_success_docs_cli(tmp_path)
    _install_inputs(
        monkeypatch,
        [
            "/project use project-1",
            "/work use wu-1",
            f'/research docs "What does the bounded plan support?" "{document}"',
            "quit",
        ],
    )

    exit_code = _run_interactive(cli)
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "summary=The documents support a bounded rollout." in captured.out
    assert "research_error" not in captured.out


def _build_docs_cli(tmp_path: Path, *, mode: str) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    adapter_id = "research-timeout" if mode == "timeout" else "research-malformed"
    exc = ModelTimeoutError("timed out while waiting for provider") if mode == "timeout" else ModelMalformedOutputError(
        "adapter returned malformed output"
    )
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
                            model_name="fallback-model",
                            provider_name="fake",
                            fake_json_response={
                                "summary": "Fallback should not be used.",
                                "findings": [],
                                "inferences": [],
                                "uncertainties": [],
                                "recommendation": None,
                            },
                        ),
                        AdapterFactoryConfig(
                            provider_kind=AdapterProviderKind.FAKE,
                            adapter_id=adapter_id,
                            model_name="research-model",
                            provider_name="fake",
                        ),
                    ),
                    purpose_overrides=PurposeOverrides(research=adapter_id),
                )
            ),
            research_artifact_store=ResearchArtifactStore(tmp_path),
            memory_store=InMemoryMemoryStore(),
        )
    )
    adapter = cli._context.infrastructure_services.get_adapter_for_purpose("research")  # type: ignore[attr-defined]
    object.__setattr__(adapter, "forced_exception", exc)
    return cli, document


def _build_success_docs_cli(tmp_path: Path) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    source_id = collect_document_sources(
        ResearchRequest(
            question="What does the bounded plan support?",
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
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
                            model_name="research-model",
                            provider_name="fake",
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
            ),
            research_artifact_store=ResearchArtifactStore(tmp_path),
            memory_store=InMemoryMemoryStore(),
        )
    )
    return cli, document


def _install_inputs(monkeypatch: pytest.MonkeyPatch, commands: list[str]) -> None:
    iterator = iter(commands)
    monkeypatch.setattr("builtins.input", lambda prompt="": next(iterator))


def _last_json_line(text: str) -> dict[str, object]:
    lines = [line for line in text.splitlines() if line.strip()]
    for line in reversed(lines):
        if line.lstrip().startswith("{"):
            return json.loads(line)
    raise AssertionError("no JSON payload line found in captured output")
