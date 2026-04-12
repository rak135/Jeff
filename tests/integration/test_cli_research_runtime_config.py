import json
from pathlib import Path

import pytest

from jeff.bootstrap import build_startup_interface_context
from jeff.cognitive import ResearchRequest, collect_document_sources
from jeff.infrastructure.model_adapters.providers import ollama as ollama_module
from jeff.interface import JeffCLI


def test_cli_research_works_with_runtime_config_and_anchors_general_research(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "What does the bounded plan support?"
    document = _write_document(tmp_path / "docs" / "plan.md")
    source_id = collect_document_sources(
        ResearchRequest(
            question=question,
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
    captured_payloads: list[dict[str, object]] = []
    _install_ollama_stub(
        monkeypatch,
        captured_payloads=captured_payloads,
        output_json={
            "summary": "The documents support a bounded rollout.",
            "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
            "inferences": ["A narrow implementation remains better supported."],
            "uncertainties": ["No external validation was performed."],
            "recommendation": "Proceed with the bounded path.",
        },
    )
    _write_runtime_config(tmp_path)

    cli = JeffCLI(context=build_startup_interface_context(base_dir=tmp_path))

    text = cli.run_one_shot(f'/research docs "{question}" "{document}"')

    artifact_files = tuple((tmp_path / ".jeff_runtime" / "research_artifacts").glob("*.json"))

    assert "anchored ad-hoc research into project_id=general_research" in text
    assert "summary=The documents support a bounded rollout." in text
    assert cli.session.scope.project_id == "general_research"
    assert captured_payloads[0]["model"] == "qwen2.5:14b"
    assert captured_payloads[0]["options"] == {"num_ctx": 16384}
    assert artifact_files


def test_runtime_configured_research_adapter_is_used_instead_of_default_adapter(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "What does the bounded plan support?"
    document = _write_document(tmp_path / "docs" / "plan.md")
    source_id = collect_document_sources(
        ResearchRequest(
            question=question,
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
    captured_payloads: list[dict[str, object]] = []
    _install_ollama_stub(
        monkeypatch,
        captured_payloads=captured_payloads,
        output_json={
            "summary": "Research used the research-specific adapter.",
            "findings": [{"text": "The research adapter path executed.", "source_refs": ["S1"]}],
            "inferences": [],
            "uncertainties": [],
            "recommendation": "Keep the purpose override.",
        },
    )
    _write_runtime_config(tmp_path)

    cli = JeffCLI(context=build_startup_interface_context(base_dir=tmp_path))
    text = cli.run_one_shot(f'/research docs "{question}" "{document}"')

    assert "Research used the research-specific adapter." in text
    assert captured_payloads[0]["model"] == "qwen2.5:14b"


def test_runtime_configured_handoff_memory_still_delegates_to_current_memory_layer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    question = "What does the bounded plan support?"
    document = _write_document(tmp_path / "docs" / "plan.md")
    source_id = collect_document_sources(
        ResearchRequest(
            question=question,
            document_paths=(str(document),),
            source_mode="local_documents",
        )
    )[0].source_id
    _install_ollama_stub(
        monkeypatch,
        captured_payloads=[],
        output_json={
            "summary": "The documents support a bounded rollout.",
            "findings": [{"text": "The plan emphasizes bounded rollout.", "source_refs": ["S1"]}],
            "inferences": ["A narrow implementation remains better supported."],
            "uncertainties": ["No external validation was performed."],
            "recommendation": "Proceed with the bounded path.",
        },
    )
    _write_runtime_config(tmp_path)

    cli = JeffCLI(context=build_startup_interface_context(base_dir=tmp_path))

    first = cli.run_one_shot(f'/research docs "{question}" "{document}" --handoff-memory')
    second = cli.run_one_shot(f'/research docs "{question}" "{document}" --handoff-memory')

    assert "memory_handoff=write memory_id=memory-1" in first
    assert "memory_handoff=reject" in second
    assert "duplicate committed memory already exists" in second

    interface_sources = [
        Path("jeff/interface/commands.py"),
        Path("jeff/interface/json_views.py"),
        Path("jeff/interface/render.py"),
        Path("jeff/interface/cli.py"),
    ]
    for source_path in interface_sources:
        source_text = source_path.read_text(encoding="utf-8").lower()
        assert "ollama" not in source_text


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
    captured_payloads: list[dict[str, object]],
    output_json: dict[str, object],
) -> None:
    def _fake_urlopen(http_request, timeout=None):  # type: ignore[no-untyped-def]
        del timeout
        captured_payloads.append(json.loads(http_request.data.decode("utf-8")))
        return _FakeHttpResponse(
            {
                "response": json.dumps(output_json),
                "prompt_eval_count": 11,
                "eval_count": 17,
            }
        )

    monotonic_values = iter((100.0, 100.05, 101.0, 101.04, 102.0, 102.03, 103.0, 103.02))
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
