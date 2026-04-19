from pathlib import Path

import pytest

from jeff.infrastructure import load_runtime_config


def test_valid_toml_loads_into_typed_runtime_config(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "ollama_default"

[research]
artifact_store_root = ".jeff_runtime"
enable_memory_handoff = true

[[adapters]]
adapter_id = "ollama_default"
provider_kind = "ollama"
provider_name = "ollama"
model_name = "qwen2.5:7b"
base_url = "http://127.0.0.1:11434"
timeout_seconds = 60

[adapters.provider_options]
context_length = 8192

[purpose_overrides]
research = "ollama_default"
formatter_bridge = "ollama_default"
proposal = "ollama_default"
planning = "ollama_default"
evaluation = "ollama_default"
""".strip(),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.defaults.default_adapter_id == "ollama_default"
    assert config.research.artifact_store_root == ".jeff_runtime"
    assert config.research.enable_memory_handoff is True
    assert config.research.memory.backend == "in_memory"
    assert config.adapters[0].provider_kind == "ollama"
    assert config.adapters[0].provider_options.context_length == 8192
    assert config.purpose_overrides.formatter_bridge == "ollama_default"


def test_research_memory_backend_parses_postgres_configuration(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"
enable_memory_handoff = true

[research.memory]
backend = "postgres"
postgres_dsn = "postgresql://user:pass@localhost:5432/jeff_test"
postgres_embedding_dim = 96

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.research.memory.backend == "postgres"
    assert config.research.memory.postgres_dsn == "postgresql://user:pass@localhost:5432/jeff_test"
    assert config.research.memory.postgres_embedding_dim == 96


def test_postgres_memory_backend_requires_dsn(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "fake-default"

[research]
artifact_store_root = ".jeff_runtime"

[research.memory]
backend = "postgres"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="research.memory.postgres_dsn is required"):
        load_runtime_config(config_path)


def test_malformed_toml_fails_closed(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text("[runtime\n", encoding="utf-8")

    with pytest.raises(ValueError, match="malformed runtime config TOML"):
        load_runtime_config(config_path)


def test_missing_required_fields_fail_closed(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "fake-default"

[[adapters]]
adapter_id = "fake-default"
provider_kind = "fake"
model_name = "fake-model"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="research table is required"):
        load_runtime_config(config_path)


def test_purpose_override_mapping_is_parsed_correctly(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
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

[purpose_overrides]
research = "fake-research"
formatter_bridge = "fake-default"
planning = "fake-default"
""".strip(),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.purpose_overrides.research == "fake-research"
    assert config.purpose_overrides.formatter_bridge == "fake-default"
    assert config.purpose_overrides.planning == "fake-default"
    assert config.purpose_overrides.proposal is None


def test_provider_options_context_length_is_parsed_correctly(tmp_path: Path) -> None:
    config_path = tmp_path / "jeff.runtime.toml"
    config_path.write_text(
        """
[runtime]
default_adapter_id = "ollama-default"

[research]
artifact_store_root = ".jeff_runtime"

[[adapters]]
adapter_id = "ollama-default"
provider_kind = "ollama"
model_name = "qwen2.5:7b"

[adapters.provider_options]
context_length = 16384
""".strip(),
        encoding="utf-8",
    )

    config = load_runtime_config(config_path)

    assert config.adapters[0].provider_options.context_length == 16384
