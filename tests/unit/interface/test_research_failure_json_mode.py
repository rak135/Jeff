import json
from pathlib import Path

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
from jeff.cognitive import ResearchArtifactStore
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_json_on_failure_path_returns_structured_research_error_payload(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(tmp_path, adapter_id="research-timeout")
    _force_research_exception(cli, ModelTimeoutError("timed out while waiting for provider"))

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            "/json on",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    payload = json.loads(outputs[-1])

    assert payload["view"] == "research_error"
    assert payload["support"]["error_code"] == "timeout"
    assert payload["support"]["adapter_id"] == "research-timeout"
    assert payload["support"]["model_name"] == "research-model"


def test_non_json_failure_path_returns_bounded_human_readable_detail(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(tmp_path, adapter_id="research-malformed")
    _force_research_exception(cli, ModelMalformedOutputError("adapter returned malformed output"))

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    assert outputs[-1].startswith("research synthesis failed: malformed_output")
    assert "adapter=research-malformed" in outputs[-1]
    assert "model=research-model" in outputs[-1]


def test_generic_flattening_does_not_reappear_when_structured_detail_exists(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(tmp_path, adapter_id="research-timeout")
    _force_research_exception(cli, ModelTimeoutError("timed out while waiting for provider"))

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    assert "research synthesis invocation failed" not in outputs[-1]


def _build_docs_cli(tmp_path: Path, *, adapter_id: str) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
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
    return cli, document


def _force_research_exception(cli: JeffCLI, exc: Exception) -> None:
    adapter = cli._context.infrastructure_services.get_adapter_for_purpose("research")  # type: ignore[attr-defined]
    object.__setattr__(adapter, "forced_exception", exc)
