import os
from pathlib import Path

from jeff.bootstrap import build_startup_interface_context, run_startup_preflight
from jeff.memory import InMemoryMemoryStore, LocalFileMemoryStore


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
    assert context.research_artifact_store.root_dir == tmp_path / ".jeff_runtime" / "artifacts" / "research"
    assert context.memory_store is not None


def test_startup_preflight_reports_local_file_memory_backend_status(tmp_path: Path) -> None:
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
""".strip(),
    )

    checks = run_startup_preflight(base_dir=tmp_path)

    assert any("bounded /run objective path enabled: repo-local validation" in check for check in checks)
    assert any("research memory backend configured: local_file" in check for check in checks)


def test_bootstrap_uses_local_file_memory_backend_by_default_for_local_runtime(tmp_path: Path) -> None:
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
""".strip(),
    )

    context = build_startup_interface_context(base_dir=tmp_path)

    assert isinstance(context.memory_store, LocalFileMemoryStore)


def test_bootstrap_can_select_postgres_memory_backend_from_runtime_config(
    tmp_path: Path,
    monkeypatch,
) -> None:
    import jeff.bootstrap as bootstrap_module

    _write_runtime_config(
        tmp_path,
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"
enable_memory_handoff = true

[research.memory]
backend = "postgres"
postgres_dsn = "postgresql://user:pass@localhost:5432/jeff_test"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
    )

    calls: list[tuple[str, int]] = []

    def _fake_build_postgres_memory_store(memory_config):
        calls.append((memory_config.backend, memory_config.postgres_embedding_dim))
        return InMemoryMemoryStore()

    monkeypatch.setattr(bootstrap_module, "_build_postgres_memory_store", _fake_build_postgres_memory_store)

    context = build_startup_interface_context(base_dir=tmp_path)
    checks = run_startup_preflight(base_dir=tmp_path)

    assert context.memory_store is not None
    assert calls[0] == ("postgres", 64)
    assert any("research memory backend configured: postgres" in check for check in checks)


def test_bootstrap_can_select_in_memory_backend_from_runtime_config(tmp_path: Path) -> None:
    _write_runtime_config(
        tmp_path,
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"
enable_memory_handoff = true

[research.memory]
backend = "in_memory"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
    )

    context = build_startup_interface_context(base_dir=tmp_path)
    checks = run_startup_preflight(base_dir=tmp_path)

    assert isinstance(context.memory_store, InMemoryMemoryStore)
    assert any("research memory backend configured: in_memory" in check for check in checks)


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
formatter_bridge = "fake-repair"
""".strip(),
    )

    context = build_startup_interface_context(base_dir=tmp_path)
    research_adapter = context.infrastructure_services.get_adapter_for_purpose("research")
    formatter_adapter = context.infrastructure_services.get_adapter_for_purpose("formatter_bridge")
    default_adapter = context.infrastructure_services.get_default_model_adapter()

    assert research_adapter.adapter_id == "fake-research"
    assert formatter_adapter.adapter_id == "fake-repair"
    assert default_adapter.adapter_id == "fake-default"


def test_missing_config_keeps_non_research_startup_usable(tmp_path: Path) -> None:
    context = build_startup_interface_context(base_dir=tmp_path)
    checks = run_startup_preflight(base_dir=tmp_path)

    assert tuple(context.state.projects.keys()) == ("project-1",)
    assert context.infrastructure_services is None
    assert any("bounded /run objective path unavailable because no local runtime config is loaded" in check for check in checks)
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
