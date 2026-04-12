import json
from dataclasses import dataclass, field
from pathlib import Path

from jeff.interface import JeffCLI, InterfaceContext
from jeff.infrastructure import (
    AdapterRegistry,
    InfrastructureServices,
    ModelInvocationStatus,
    ModelMalformedOutputError,
    ModelRequest,
    ModelResponse,
    ModelUsage,
)
from jeff.cognitive import ResearchArtifactStore
from jeff.memory import InMemoryMemoryStore

from tests.fixtures.cli import build_state_with_runs


def test_mode_debug_emits_research_checkpoints_progressively_in_cli_output(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(
        tmp_path,
        script=(
            {
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        ),
    )

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            "/mode debug",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    rendered = outputs[-1]

    assert rendered.index("[debug][research] source_key_map_built") < rendered.index(
        "[debug][research] primary_synthesis_started"
    )
    assert rendered.index("[debug][research] primary_synthesis_succeeded") < rendered.index(
        "[debug][research] citation_remap_started"
    )
    assert rendered.index("[debug][research] provenance_validation_succeeded") < rendered.index("RESEARCH docs")


def test_non_debug_mode_does_not_emit_research_debug_stream(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(
        tmp_path,
        script=(
            {
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        ),
    )

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    assert "[debug][research]" not in outputs[-1]


def test_debug_payloads_are_bounded_and_include_adapter_model_without_stack_trace_noise(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(
        tmp_path,
        script=(
            ModelMalformedOutputError("adapter returned malformed output", raw_output=("X" * 400)),
            ModelMalformedOutputError("repair malformed", raw_output=("Y" * 400)),
        ),
    )

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            "/mode debug",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    rendered = outputs[-1]

    assert "adapter_id=debug-research" in rendered
    assert "model_name=research-model" in rendered
    assert "primary_synthesis_failed" in rendered
    assert "repair_pass_started" in rendered
    assert "Traceback" not in rendered
    assert ("X" * 250) not in rendered
    assert "..." in rendered


def test_json_mode_in_debug_keeps_structured_result_and_exposes_debug_events(tmp_path: Path) -> None:
    cli, document = _build_docs_cli(
        tmp_path,
        script=(
            {
                "summary": "The documents support a bounded rollout.",
                "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
                "inferences": [],
                "uncertainties": [],
                "recommendation": None,
            },
        ),
    )

    outputs = cli.run_interactive(
        [
            "/project use project-1",
            "/work use wu-1",
            "/mode debug",
            "/json on",
            f'/research docs "What does the bounded plan support?" "{document}"',
        ]
    )

    payload = json.loads(outputs[-1])

    assert payload["view"] == "research_result"
    assert payload["support"]["summary"] == "The documents support a bounded rollout."
    assert payload["debug"]["events"][0]["checkpoint"] == "source_key_map_built"
    assert payload["debug"]["events"][1]["checkpoint"] == "primary_synthesis_started"


def _build_docs_cli(tmp_path: Path, *, script: tuple[object, ...]) -> tuple[JeffCLI, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    document = tmp_path / "plan.md"
    document.write_text(
        "The bounded plan keeps the rollout stable.\n"
        "The bounded plan avoids widening the surface.\n",
        encoding="utf-8",
    )
    state, _ = build_state_with_runs(run_specs=())
    adapter = _ScriptedAdapter(script=script)
    registry = AdapterRegistry()
    registry.register(adapter)
    cli = JeffCLI(
        context=InterfaceContext(
            state=state,
            infrastructure_services=InfrastructureServices(
                model_adapter_registry=registry,
                default_model_adapter_id=adapter.adapter_id,
            ),
            research_artifact_store=ResearchArtifactStore(tmp_path),
            memory_store=InMemoryMemoryStore(),
        )
    )
    return cli, document


@dataclass(slots=True)
class _ScriptedAdapter:
    script: tuple[object, ...]
    adapter_id: str = "debug-research"
    provider_name: str = "fake"
    model_name: str = "research-model"
    requests: list[ModelRequest] = field(default_factory=list)

    def invoke(self, request_model: ModelRequest) -> ModelResponse:
        self.requests.append(request_model)
        step = self.script[len(self.requests) - 1]
        if isinstance(step, Exception):
            raise step
        assert isinstance(step, dict)
        return ModelResponse(
            request_id=request_model.request_id,
            adapter_id=self.adapter_id,
            provider_name=self.provider_name,
            model_name=self.model_name,
            status=ModelInvocationStatus.COMPLETED,
            output_text=None,
            output_json=step,
            usage=ModelUsage(input_tokens=1, output_tokens=1, total_tokens=2, estimated_cost=0.0, latency_ms=1),
            warnings=(),
            raw_response_ref=f"fake://{self.adapter_id}/{request_model.request_id}",
        )
