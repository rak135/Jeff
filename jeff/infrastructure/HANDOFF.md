# Module Name

- `jeff.infrastructure`

# Module Purpose

- Hold Jeff-owned replaceable infrastructure plumbing that supports the semantic layers without owning their meaning.

# Current Role in Jeff

- Owns infrastructure-layer plumbing: model adapter contracts, registry, factory, telemetry normalization, runtime assembly, and local runtime config loading.
- Provides the neutral adapter/runtime layer consumed by CLI bootstrap for downstream research and the current bounded `/run` objective path.
- Keeps provider-specific behavior inside Infrastructure rather than leaking it into Interface, Governance, or Orchestrator.

# Boundaries / Non-Ownership

- Does not own proposal, selection, governance, evaluation, orchestration, truth mutation, or interface behavior.
- Does not define semantic proposal/planning/evaluation behavior, operator wording, telemetry persistence, or orchestrator routing policy.
- Raw provider outputs remain support data, not canonical Jeff truth.

# Owned Files / Areas

- `jeff/infrastructure/__init__.py`
- `jeff/infrastructure/purposes.py`
- `jeff/infrastructure/output_strategies.py`
- `jeff/infrastructure/capability_profiles.py`
- `jeff/infrastructure/contract_runtime.py`
- `jeff/infrastructure/config.py`
- `jeff/infrastructure/runtime.py`
- `jeff/infrastructure/model_adapters/`

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `handoffs/system/REPO_HANDOFF.md`
- This module handoff

# Current Implementation Reality

- Runtime config loads from local `jeff.runtime.toml` through typed config models and fail-closed validation.
- InfrastructureServices assembles adapters and purpose overrides explicitly.
- Purpose-based adapter lookup exists with fallback logic for `formatter_bridge`.
- ContractRuntime remains the neutral strategy-aware LLM invocation surface.
- CLI bootstrap consumes this config to enable downstream research and the current bounded `/run` objective path without moving operator semantics into Infrastructure.
- No environment-driven runtime auto-discovery or CLI-owned provider config exists.

# Important Invariants

- Infrastructure adapters stay provider-neutral at the public contract boundary.
- Provider-specific imports must stay inside this module.
- Adapter outputs are normalized support artifacts, not semantic decisions or truth writes.
- Registry behavior is explicit, deterministic, and fail-closed.
- Runtime assembly may hold adapter services, but it does not assign semantic meaning or task-specific provider choice.
- Ollama-specific request shaping such as configured context length remains inside the Ollama provider adapter.

# Active Risks / Unresolved Issues

- Only two real providers exist (Fake for testing, Ollama for HTTP), so cross-provider normalization edges are still lightly exercised.
- Ollama JSON mode currently parses returned text as JSON rather than using a provider-native structured response mode when `json_schema` is provided.
- ContractCallRequest still does not carry `reasoning_effort` and `json_schema` at the top level, so some clean `invoke()` paths still require full ModelRequest construction.
- Retry, async, streaming, tool-calling, telemetry persistence, runtime auto-discovery, and provider auto-detection remain intentionally out of scope.

# Next Continuation Steps

- Expand ContractCallRequest only when a downstream bounded slice actually needs cleaner `invoke()` coverage.
- Add future providers by keeping provider-specific details inside this module and preserving semantic-layer ownership boundaries.
- Keep infrastructure vocabulary domain-neutral and thin; grow it only as verified routing needs demand it.

# Submodule Map

- `purposes.py`: Purpose enum with stable routing labels.
- `output_strategies.py`: OutputStrategy enum with technical output handling strategies.
- `capability_profiles.py`: CapabilityProfile immutable model for adapter capability metadata.
- `contract_runtime.py`: ContractCallRequest and ContractRuntime.
- `config.py`: local runtime config loading and validation from TOML.
- `runtime.py`: InfrastructureServices assembly and runtime service management.
- `model_adapters/types.py`: normalized adapter request, response, usage, and status models.
- `model_adapters/base.py`: narrow provider-neutral adapter contract.
- `model_adapters/errors.py`: adapter-layer exceptions.
- `model_adapters/registry.py`: deterministic adapter registration and lookup.
- `model_adapters/telemetry.py`: normalized invocation telemetry events.
- `model_adapters/factory.py`: explicit adapter construction boundary.
- `model_adapters/providers/fake.py`: deterministic fake adapter for tests.
- `model_adapters/providers/ollama.py`: minimal Ollama HTTP adapter with configurable context length.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `jeff/cognitive/HANDOFF.md`
- `jeff/action/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
- `jeff/interface/HANDOFF.md`
