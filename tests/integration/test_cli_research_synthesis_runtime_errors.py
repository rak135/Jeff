import json
from pathlib import Path

import pytest

from jeff.bootstrap import build_startup_interface_context
from jeff.cognitive import ResearchArtifactStore, ResearchRequest, ResearchSynthesisRuntimeError, collect_document_sources
from jeff.cognitive.research import web as web_module
from jeff.infrastructure import (
    AdapterFactoryConfig,
    AdapterProviderKind,
    ModelAdapterRuntimeConfig,
    PurposeOverrides,
    build_infrastructure_services,
)
from jeff.infrastructure.model_adapters.providers import ollama as ollama_module
from jeff.interface import InterfaceContext, JeffCLI
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_cli_docs_failure_shows_bounded_useful_reason_instead_of_generic_invocation_failure(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(
        tmp_path,
        question=question,
        failing_adapter=AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.FAKE,
            adapter_id="research-timeout",
            model_name="research-model",
            provider_name="fake",
        ),
    )
    cli = _with_forced_exception(cli, exc_message="timed out while waiting for provider", timeout=True)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ResearchSynthesisRuntimeError, match="research synthesis failed: timeout"):
        cli.run_one_shot(f'/research docs "{question}" "{document}"')


def test_cli_web_failure_shows_bounded_useful_reason_instead_of_generic_invocation_failure(
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
        failing_adapter=AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.FAKE,
            adapter_id="research-malformed",
            model_name="research-model",
            provider_name="fake",
        ),
    )
    cli = _with_forced_exception(cli, exc_message="adapter returned malformed output", malformed=True)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")

    with pytest.raises(ResearchSynthesisRuntimeError, match="research synthesis failed: malformed_output"):
        cli.run_one_shot(f'/research web "{question}" "{query}"')


def test_json_failure_output_exposes_bounded_structured_fields(tmp_path: Path) -> None:
    question = "What does the bounded plan support?"
    cli, document = _build_docs_cli(
        tmp_path,
        question=question,
        failing_adapter=AdapterFactoryConfig(
            provider_kind=AdapterProviderKind.FAKE,
            adapter_id="research-timeout",
            model_name="research-model",
            provider_name="fake",
        ),
    )
    cli = _with_forced_exception(cli, exc_message="timed out while waiting for provider", timeout=True)

    cli.run_one_shot("/project use project-1")
    cli.run_one_shot("/work use wu-1")
    payload = json.loads(cli.run_one_shot(f'/research docs "{question}" "{document}"', json_output=True))

    assert payload["view"] == "research_error"
    assert payload["support"]["error_code"] == "timeout"
    assert payload["support"]["provider_name"] == "fake"
    assert payload["support"]["adapter_id"] == "research-timeout"
    assert payload["support"]["model_name"] == "research-model"
    assert "Traceback" not in payload["support"]["message"]


def test_runtime_configured_research_adapter_timeout_is_respected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    question = "What does the bounded plan support?"
    document = _write_document(tmp_path / "docs" / "plan.md")
    source_id = collect_document_sources(
        ResearchRequest(
            question=question,
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
    captured_timeouts: list[int | None] = []
    _install_ollama_stub(
        monkeypatch,
        captured_timeouts=captured_timeouts,
        output_json={
            "summary": "The documents support a bounded rollout.",
            "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
            "inferences": [],
            "uncertainties": [],
            "recommendation": None,
        },
    )
    _write_runtime_config(tmp_path)

    cli = JeffCLI(context=build_startup_interface_context(base_dir=tmp_path))

    cli.run_one_shot(f'/research docs "{question}" "{document}"')

    assert captured_timeouts == [60]


def _build_docs_cli(
    tmp_path: Path,
    *,
    question: str,
    failing_adapter: AdapterFactoryConfig,
) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = _write_document(tmp_path / "plan.md")
    return JeffCLI(
        context=_build_research_context(
            tmp_path,
            failing_adapter=failing_adapter,
        )
    ), document


def _build_web_cli(
    tmp_path: Path,
    *,
    question: str,
    query: str,
    monkeypatch: pytest.MonkeyPatch,
    failing_adapter: AdapterFactoryConfig,
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
    return JeffCLI(context=_build_research_context(tmp_path, failing_adapter=failing_adapter))


def _build_research_context(
    tmp_path: Path,
    *,
    failing_adapter: AdapterFactoryConfig,
) -> InterfaceContext:
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
                    failing_adapter,
                ),
                purpose_overrides=PurposeOverrides(research=failing_adapter.adapter_id),
            )
        ),
        research_artifact_store=ResearchArtifactStore(tmp_path),
        memory_store=InMemoryMemoryStore(),
    )


def _with_forced_exception(cli: JeffCLI, *, exc_message: str, timeout: bool = False, malformed: bool = False) -> JeffCLI:
    from jeff.infrastructure import ModelMalformedOutputError, ModelTimeoutError

    adapter = cli._context.infrastructure_services.get_adapter_for_purpose("research")  # type: ignore[attr-defined]
    object.__setattr__(
        adapter,
        "forced_exception",
        ModelTimeoutError(exc_message)
        if timeout
        else ModelMalformedOutputError(exc_message)
        if malformed
        else Exception(exc_message),
    )
    return cli


class _FakeHttpResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = json.dumps(payload).encode("utf-8")
        self.headers = {"Content-Type": "application/json"}

    def read(self, _size: int | None = None) -> bytes:
        return self._payload

    def __enter__(self) -> "_FakeHttpResponse":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


def _install_ollama_stub(
    monkeypatch: pytest.MonkeyPatch,
    *,
    captured_timeouts: list[int | None],
    output_json: dict[str, object],
) -> None:
    def _fake_urlopen(http_request, timeout=None):  # type: ignore[no-untyped-def]
        captured_timeouts.append(timeout)
        return _FakeHttpResponse(
            {
                "response": json.dumps(output_json),
                "prompt_eval_count": 11,
                "eval_count": 17,
            }
        )

    monotonic_values = iter((100.0, 100.05, 101.0, 101.04))
    monkeypatch.setattr(ollama_module.request, "urlopen", _fake_urlopen)
    monkeypatch.setattr(ollama_module.time, "monotonic", lambda: next(monotonic_values))


def _write_document(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    return path


def _write_runtime_config(tmp_path: Path) -> Path:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"
enable_memory_handoff = true

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"

[[adapters]]
adapter_id = "ollama-research"
provider_kind = "ollama"
provider_name = "ollama"
model_name = "qwen2.5:14b"
base_url = "http://127.0.0.1:11434"
timeout_seconds = 60

[adapters.provider_options]
context_length = 16384

[purpose_overrides]
research = "ollama-research"
proposal = "fake-default"
planning = "fake-default"
evaluation = "fake-default"
""".strip(),
        encoding="utf-8",
    )
    return config_path
