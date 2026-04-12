import os
from pathlib import Path

from jeff.bootstrap import build_startup_interface_context, run_startup_preflight


def test_bootstrap_loads_jeff_runtime_toml_when_present(tmp_path: Path) -> None:
    _write_runtime_config(
        tmp_path,
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
adapter_id = "fake-research"
provider_kind = "fake"
model_name = "fake-research-model"

[purpose_overrides]
research = "fake-research"
""".strip(),
    )

    context = build_startup_interface_context(base_dir=tmp_path)

    assert context.infrastructure_services is not None
    assert context.research_artifact_store is not None
    assert context.research_artifact_store.root_dir == tmp_path / ".jeff_runtime"
    assert context.memory_store is not None


def test_bootstrap_assembles_infrastructure_runtime_and_supports_research_purpose_lookup(tmp_path: Path) -> None:
    _write_runtime_config(
        tmp_path,
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"

[[adapters]]
adapter_id = "fake-research"
provider_kind = "fake"
model_name = "fake-research-model"

[[adapters]]
adapter_id = "fake-repair"
provider_kind = "fake"
model_name = "fake-repair-model"

[purpose_overrides]
research = "fake-research"
research_repair = "fake-repair"
""".strip(),
    )

    context = build_startup_interface_context(base_dir=tmp_path)
    research_adapter = context.infrastructure_services.get_adapter_for_purpose("research")
    repair_adapter = context.infrastructure_services.get_adapter_for_purpose("research_repair")
    default_adapter = context.infrastructure_services.get_default_model_adapter()

    assert research_adapter.adapter_id == "fake-research"
    assert repair_adapter.adapter_id == "fake-repair"
    assert default_adapter.adapter_id == "fake-default"


def test_missing_config_keeps_non_research_startup_usable(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    checks = run_startup_preflight(base_dir=tmp_path)

    assert tuple(context.state.projects.keys()) == ("project-1",)
    assert context.infrastructure_services is None
    assert any("research CLI remains unavailable" in check for check in checks)


def test_bootstrap_does_not_depend_on_environment_variables(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("JEFF_RUNTIME_TOML", str(tmp_path / "ignored.toml"))

    context = build_startup_interface_context(base_dir=tmp_path)

    assert context.infrastructure_services is None
    assert "JEFF_RUNTIME_TOML" in os.environ


def _write_runtime_config(tmp_path: Path, text: str) -> Path:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(text, encoding="utf-8")
    return config_path
