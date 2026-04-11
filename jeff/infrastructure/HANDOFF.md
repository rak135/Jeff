# Module Name

- `jeff.infrastructure`

# Module Purpose

- Hold Jeff-owned replaceable infrastructure plumbing that supports the semantic layers without owning their meaning.

# Current Role in Jeff

- Currently contains Slice A and Slice B model-adapter infrastructure plus Slice C1 runtime assembly: provider-neutral contracts, registry, telemetry normalization, a small adapter factory, a deterministic fake provider, one real Ollama HTTP adapter, and explicit runtime service assembly.

# Boundaries / Non-Ownership

- Does not own proposal, selection, governance, evaluation, orchestration, truth mutation, or interface behavior.
- Does not define semantic provider selection policy, runtime wiring, global config loading, telemetry persistence, or stage integration yet.
- Raw provider outputs remain support data, not canonical Jeff truth.

# Owned Files / Areas

- `jeff/infrastructure/__init__.py`
- `jeff/infrastructure/model_adapters/`

# Canonical Docs to Read First

- `v1_doc/ARCHITECTURE.md`
- `handoffs/system/REPO_HANDOFF.md`
- This module handoff

# Current Implementation Reality

- Slice A foundations exist as a standalone package with a narrow synchronous adapter contract.
- Slice B now adds normalized invocation telemetry, a minimal explicit factory, and one real Ollama HTTP adapter implemented with the standard library.
- Slice C1 now adds explicit runtime assembly that builds and holds adapter services through the factory and registry, with an optional bootstrap helper that accepts an explicit runtime config object.
- No stage integration, CLI integration, orchestration integration, provider routing policy, or environment-driven runtime wiring exists yet.

# Important Invariants

- Infrastructure adapters stay provider-neutral at the public contract boundary.
- Provider-specific imports must stay inside this module.
- Adapter outputs are normalized support artifacts, not semantic decisions or truth writes.
- Registry behavior is explicit, deterministic, and fail-closed.
- Factory construction stays explicit and does not auto-load environment or global runtime settings.
- Telemetry remains normalized observability data and does not invent Jeff semantics.
- Runtime assembly may hold adapter services, but it does not assign semantic meaning or task-specific provider choice.

# Active Risks / Unresolved Issues

- Only one real provider exists so far, so cross-provider normalization edges are still lightly exercised.
- Ollama JSON mode currently parses returned text as JSON rather than using a provider-native structured response mode.
- Retry, async, streaming, tool-calling, telemetry persistence, runtime auto-discovery, and stage integration remain intentionally out of scope.

# Next Continuation Steps

- Add future providers or downstream integration only by keeping provider-specific details inside `jeff.infrastructure` and preserving semantic-layer ownership boundaries.

# Submodule Map

- `model_adapters/types.py`: normalized adapter request, response, usage, and status models.
- `model_adapters/base.py`: narrow provider-neutral adapter contract.
- `model_adapters/errors.py`: adapter-layer exceptions.
- `model_adapters/registry.py`: deterministic adapter registration and lookup.
- `model_adapters/telemetry.py`: normalized invocation telemetry events.
- `model_adapters/factory.py`: explicit adapter construction boundary.
- `model_adapters/providers/fake.py`: deterministic fake adapter for tests.
- `model_adapters/providers/ollama.py`: minimal Ollama HTTP adapter.
- `runtime.py`: explicit infrastructure service assembly and default adapter holding.

# Related Handoffs

- `handoffs/system/REPO_HANDOFF.md`
- `jeff/core/HANDOFF.md`
- `jeff/governance/HANDOFF.md`
- `jeff/cognitive/HANDOFF.md`
- `jeff/action/HANDOFF.md`
- `jeff/memory/HANDOFF.md`
- `jeff/orchestrator/HANDOFF.md`
- `jeff/interface/HANDOFF.md`
