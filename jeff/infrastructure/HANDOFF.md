# Module Name

- `jeff.infrastructure`

# Module Purpose

- Hold Jeff-owned replaceable infrastructure plumbing that supports the semantic layers without owning their meaning.

# Current Role in Jeff

- Owns infrastructure-layer plumbing: model adapter contracts, registry, factory, telemetry normalization, and runtime assembly.
- Implements Slices A, B, and C from the v1 architecture (model adapters, runtime substrate, adapter routing).
- Provides infrastructure-owned vocabulary modules for routing and capability metadata: Purpose (research, formatter_bridge, proposal, planning, evaluation), OutputStrategy (plain_text, bounded_text_then_parse, bounded_text_then_formatter), CapabilityProfile (adapter capability metadata), and ContractRuntime (thin strategy-aware LLM invocation surface).
- Introduces ContractCallRequest and ContractRuntime as neutral entry points for domain layers to invoke adapters without building ModelRequest manually.
- Supports explicit local runtime config loading from `jeff.runtime.toml` with validation and fail-closed config checks.

# Boundaries / Non-Ownership

- Does not own proposal, selection, governance, evaluation, orchestration, truth mutation, or interface behavior.
- Does not define semantic proposal/planning/evaluation behavior, interface semantics, telemetry persistence, or orchestrator stage integration.
- Raw provider outputs remain support data, not canonical Jeff truth.

# Owned Files / Areas

- `jeff/infrastructure/__init__.py`
- `jeff/infrastructure/purposes.py` — Purpose enum (research, formatter_bridge, proposal, planning, evaluation)
- `jeff/infrastructure/output_strategies.py` — OutputStrategy enum (plain_text, bounded_text_then_parse, bounded_text_then_formatter)
- `jeff/infrastructure/capability_profiles.py` — CapabilityProfile immutable metadata model
- `jeff/infrastructure/contract_runtime.py` — ContractCallRequest and ContractRuntime entry points
- `jeff/infrastructure/config.py` — local runtime config loading and validation
- `jeff/infrastructure/runtime.py` — InfrastructureServices assembly
- `jeff/infrastructure/model_adapters/`

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `handoffs/system/REPO_HANDOFF.md`
- This module handoff

# Current Implementation Reality

- Slice A foundations exist as a standalone package with a narrow synchronous adapter contract (ModelRequest → ModelResponse).
- Slice B adds normalized invocation telemetry, a minimal explicit factory, and two implementations (Fake adapter for tests, Ollama HTTP adapter with standard library).
- Slice C (runtime assembly) now adds explicit runtime service assembly through InfrastructureServices that holds and routes adapters by purpose using PurposeOverrides.
- Four vocabulary modules exist and are exported:
  - `Purpose`: routing labels (research, formatter_bridge, proposal, planning, evaluation). The `formatter_bridge` purpose is used by research Step 3 (formatter fallback) as a neutral descriptor for the formatter adapter routing.
  - `OutputStrategy`: technical strategy labels for model output handling (plain_text, bounded_text_then_parse, bounded_text_then_formatter).
  - `CapabilityProfile`: immutable adapter capability metadata (supports_structured_output, max_context_tokens, provider_kind).
  - `ContractRuntime`: thin strategy-aware LLM invocation entry point that accepts ContractCallRequest and routes to adapters via InfrastructureServices.
- Local `jeff.runtime.toml` can now be loaded through config models and converted into runtime services plus purpose overrides.
- Purpose-based adapter lookup exists in InfrastructureServices, with fallback logic for formatter_bridge (falls back to research adapter when not configured).
- PurposeOverrides are validated at config load time to reject unknown keys with a clear error.
- No environment-driven runtime wiring, CLI-owned provider config, or orchestrator routing policy exists.

# Important Invariants

- Infrastructure adapters stay provider-neutral at the public contract boundary.
- Provider-specific imports must stay inside this module.
- Adapter outputs are normalized support artifacts, not semantic decisions or truth writes.
- Registry behavior is explicit, deterministic, and fail-closed.
- Factory construction stays explicit and does not auto-load environment or global runtime settings.
- Telemetry remains normalized observability data and does not invent Jeff semantics.
- Runtime assembly may hold adapter services, but it does not assign semantic meaning or task-specific provider choice.
- Ollama-specific request shaping such as configured context length remains inside the Ollama provider adapter.

# Active Risks / Unresolved Issues

- Only two real providers exist (Fake for testing, Ollama for HTTP), so cross-provider normalization edges are still lightly exercised.
- Ollama JSON mode currently parses returned text as JSON rather than using a provider-native structured response mode when json_schema is provided.
- ContractCallRequest still does not carry reasoning_effort and json_schema at the top level (those live in the full ModelRequest today); clean `invoke()` path requires ModelRequest construction in some cases.
- Research persistence double-nests the artifact store path (.jeff_runtime/research_artifacts/research_artifacts) — this is a known issue in the research layer, not infrastructure owned.
- Retry, async, streaming, tool-calling, telemetry persistence, runtime auto-discovery, and provider auto-detection remain intentionally out of scope for this slice.

# Next Continuation Steps

- Expand ContractCallRequest to carry response_mode, json_schema, and reasoning_effort at the top level so domain layers can use the clean `invoke()` path without manually building ModelRequest.
- Add future providers by keeping provider-specific details inside this module and preserving semantic-layer ownership boundaries.
- Keep infrastructure vocabulary (Purpose, OutputStrategy, CapabilityProfile) domain-neutral and thin; grow it only as routing decisions actually need new metadata.

# Submodule Map

- `purposes.py`: Purpose enum with stable routing labels (research, formatter_bridge, proposal, planning, evaluation).
- `output_strategies.py`: OutputStrategy enum with technical output handling strategies (plain_text, bounded_text_then_parse, bounded_text_then_formatter).
- `capability_profiles.py`: CapabilityProfile immutable model for adapter capability metadata.
- `contract_runtime.py`: ContractCallRequest and ContractRuntime; thin strategy-aware LLM invocation surface.
- `config.py`: local runtime config loading and validation from TOML.
- `runtime.py`: InfrastructureServices assembly and runtime service management.
- `model_adapters/types.py`: normalized adapter request, response, usage, and status models.
- `model_adapters/base.py`: narrow provider-neutral adapter contract (ModelAdapter interface).
- `model_adapters/errors.py`: adapter-layer exceptions (ModelAdapterError, ModelAdapterNotFoundError, ModelInvocationError, etc.).
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
