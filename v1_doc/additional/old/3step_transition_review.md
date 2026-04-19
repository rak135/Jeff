# 1. Executive Verdict
The target 3-step design is a highly compatible and necessary evolution of the current repository state. The repo already implements the "spirit" of the 3-step process (synthesis -> repair -> remap -> validate), but it does so using a "JSON-first" approach that is brittle. Moving to a "Bounded Text First" approach (Step 1) with a deterministic transformer (Step 2) and a formatter fallback (Step 3) aligns perfectly with the existing modular boundaries and the current "repair" logic already present in `synthesis.py`.

# 2. Real Repo State Summary
The current repository has a mature, bounded research implementation:
- **Research Package**: `jeff/cognitive/research/` is a dedicated submodule. It handles acquisition (`documents.py`, `web.py`), synthesis (`synthesis.py`), persistence (`persistence.py`), and memory handoff (`memory_handoff.py`).
- **Synthesis Pipeline**: Currently uses a one-shot JSON request. It includes a "repair pass" that triggers on `ModelMalformedOutputError` or `schema_incomplete` JSON, which is a primitive precursor to the Step 3 formatter.
- **Citation Discipline**: Implements a robust `S1..Sn` citation-key remap system to decouple model-facing keys from internal `source_id`s.
- **Infrastructure**: `jeff/infrastructure/` provides a provider-neutral adapter layer. It supports purpose-based routing (e.g., `research`, `research_repair`) and runtime configuration via `jeff.runtime.toml`.
- **Observability**: `/mode debug` provides live checkpoints of the synthesis, repair, and provenance stages.

# 3. Canon and Reality Fit Check
- **Where it fits**:
    - The separation of acquisition from synthesis is already real.
    - The "repair" logic in `synthesis.py` is the direct ancestor of the Step 3 Formatter.
    - The citation-key remap and provenance validation are already implemented and fail-closed.
    - Infrastructure already supports purpose-based adapter overrides.
- **Where it does not fit yet**:
    - Step 1 is currently "JSON-first" rather than "Bounded Text first".
    - Step 2 (Deterministic Transformer) is currently a set of `_required_string` helpers and JSON validation, not a dedicated transformer module.
    - Step 3 is a "repair" call that often asks the model to "fix the JSON" rather than "format this bounded text into JSON".
- **Tensions to preserve**:
    - The hard boundary between Infrastructure (routing/adapters) and Cognitive (research semantics).
    - The fail-closed nature of provenance validation.

# 4. Keep / Change / Delete Matrix

| File or Module | Current Role | Action | Reason | Replacement / Migration Note |
| :--- | :--- | :--- | :--- | :--- |
| `research/contracts.py` | Research schemas | **Modify** | Needs to add Step 1 Bounded Text artifact types. | Extend with `BoundedTextArtifact`. |
| `research/synthesis.py` | Pipeline orchestrator | **Modify** | Shift from JSON-first to 3-step orchestration. | Move logic to `synthesis.py` (orchestrator) and `deterministic_transformer.py`. |
| `research/documents.py` | Local acquisition | **Keep** | Working as intended. | No change. |
| `research/web.py` | Web acquisition | **Keep** | Working as intended. | No change. |
| `research/persistence.py` | Artifact storage | **Keep** | Working as intended. | No change. |
| `research/memory_handoff.py` | Memory distillation | **Keep** | Working as intended. | No change. |
| `research/legacy.py` | Compatibility shim | **Retire Later** | Only needed for old tests/callers. | Delete once all tests migrate to new contracts. |
| `research/errors.py` | Exception classes | **Keep** | Essential for fail-closed behavior. | No change. |
| `infrastructure/runtime.py` | Service assembly | **Modify** | Expand to support `purpose_router` and `output_strategies`. | Implement `contract_runtime.py` logic here. |
| `infrastructure/config.py` | TOML loading | **Modify** | Add support for strategy and capability profiles. | Extend `JeffRuntimeConfig`. |
| `model_adapters/*` | Provider wrappers | **Keep** | Stable and provider-neutral. | No change. |

# 5. Final Target Folder Structure — Research
`jeff/cognitive/research/`
- `__init__.py`: Package exports.
- `contracts.py`: (Modify) EvidencePack, ResearchArtifact, and new BoundedText types.
- `bounded_syntax.py`: (New) Step 1 syntax contract and prompt builder.
- `synthesis.py`: (Modify) Orchestrates Step 1 $\rightarrow$ Step 2 $\rightarrow$ Step 3.
- `deterministic_transformer.py`: (New) Step 2 mechanical parse/normalization.
- `formatter.py`: (New) Step 3 formatter request builder and Instructor wrapper.
- `validators.py`: (New) Shared syntax and schema checks.
- `fallback_policy.py`: (New) Logic for when Step 3 is eligible.
- `debug.py`: (Keep) Truthful debug checkpoints.
- `documents.py`: (Keep) Local acquisition.
- `web.py`: (Keep) Web acquisition.
- `persistence.py`: (Keep) Artifact storage.
- `memory_handoff.py`: (Keep) Memory distillation.
- `errors.py`: (Keep) Research exceptions.
- `legacy.py`: (Retire) Compatibility shim.

# 6. Final Target Folder Structure — Infrastructure
`jeff/infrastructure/`
- `__init__.py`: Package exports.
- `runtime.py`: (Modify) Assembles `InfrastructureServices` including the new `contract_runtime`.
- `config.py`: (Modify) Loads purpose, strategy, and capability profiles.
- `purposes.py`: (New) Stable purpose names (e.g., `research_step1`).
- `capability_profiles.py`: (New) Model capability metadata.
- `fallback_policies.py`: (New) Technical provider fallback logic.
- `output_strategies.py`: (New) Strategy definitions (`bounded_text_then_parse`, etc.).
- `contract_runtime.py`: (New) Reusable LLM contract runtime.
- `typed_calls/`: (New)
    - `__init__.py`
    - `instructor_runtime.py`: (New) Instructor-backed typed calls.
    - `guardrails_runtime.py`: (Optional) Validation composition.
    - `baml_runtime.py`: (Optional) Future contract layer.
- `model_adapters/`: (Keep) Base, Registry, Factory, and Providers.
- `telemetry/`: (New) `llm_events.py` for low-level runtime events.

# 7. Responsibility Placement
- **Step 1 Syntax Contract**: `research/bounded_syntax.py`
- **Step 1 Request Builder**: `research/bounded_syntax.py`
- **Step 1 Model Call**: `research/synthesis.py` $\rightarrow$ `infrastructure/contract_runtime.py`
- **Step 2 Deterministic Transformer**: `research/deterministic_transformer.py`
- **Step 2 Validation Helpers**: `research/validators.py`
- **Step 3 Formatter Request Builder**: `research/formatter.py`
- **Step 3 Formatter Call**: `research/formatter.py` $\rightarrow$ `infrastructure/typed_calls/instructor_runtime.py`
- **Formatter Fallback Policy**: `research/fallback_policy.py`
- **Debug Checkpoint Emission**: `research/debug.py`
- **Shared Research Validation**: `research/validators.py`
- **Runtime Purpose Routing**: `infrastructure/runtime.py` $\rightarrow$ `infrastructure/purposes.py`
- **Capability Profiles**: `infrastructure/capability_profiles.py`
- **Fallback Policies**: `infrastructure/fallback_policies.py`
- **Output Strategies**: `infrastructure/output_strategies.py`

# 8. Open-Source Component Decisions

| Component | Decision | Where it fits | Why | Why not elsewhere |
| :--- | :--- | :--- | :--- | :--- |
| **Instructor** | **USE NOW** | `infrastructure/typed_calls/instructor_runtime.py` | Practical, provider-swappable typed output for Step 3. | Not for Step 2 (must be deterministic). |
| **Guardrails** | **OPTIONAL** | `infrastructure/typed_calls/guardrails_runtime.py` | Useful for complex validator composition. | Not for core semantic repair. |
| **Outlines** | **OPTIONAL LATER** | `infrastructure/model_adapters/` | Constrained generation for local backends. | Not required for initial 3-step. |
| **BAML** | **OPTIONAL LATER** | `infrastructure/typed_calls/baml_runtime.py` | Strong contract testing for complex flows. | Too heavy for initial implementation. |

# 9. Step-by-Step Migration Plan

### Slice 1: Infrastructure Strategy Vocabulary
- **Goal**: Introduce the reusable Infrastructure concepts without changing Research behavior.
- **Files**: `infrastructure/purposes.py`, `infrastructure/output_strategies.py`, `infrastructure/capability_profiles.py`, `infrastructure/contract_runtime.py`.
- **Unchanged**: Current research behavior, persistence, provenance.
- **Acceptance**: Infrastructure can describe `research_step1` and `research_formatter` without active routing.
- **Rollback Risk**: Low (additive).

### Slice 2: Step 1 & Step 2 Implementation
- **Goal**: Build the cheap primary path (Bounded Text $\rightarrow$ Deterministic Parse).
- **Files**: `research/bounded_syntax.py`, `research/deterministic_transformer.py`, `research/validators.py`, `research/synthesis.py`.
- **Unchanged**: Step 3 formatter fallback (not yet live), downstream remap/provenance.
- **Acceptance**: Research can produce bounded text; transformer can parse it; invalid artifacts fail closed.
- **Rollback Risk**: Medium (changes primary synthesis path).

### Slice 3: Step 3 Formatter Fallback
- **Goal**: Add the rescue path using Instructor.
- **Files**: `research/formatter.py`, `research/fallback_policy.py`, `infrastructure/typed_calls/instructor_runtime.py`.
- **Unchanged**: Downstream remap/provenance/persistence.
- **Acceptance**: Step 3 runs only after Step 2 structural failure; uses Step 1 artifact.
- **Rollback Risk**: Low (fallback path only).

### Slice 4: Debug and Telemetry Alignment
- **Goal**: Make stage visibility truthful.
- **Files**: `research/debug.py`, `infrastructure/telemetry/llm_events.py`.
- **Acceptance**: Debug labels correspond to real 3-step stages.
- **Rollback Risk**: Low.

# 10. First Recommended Implementation Slice
**Introduce the reusable Infrastructure strategy vocabulary.**
This is the smallest correct first slice. It strengthens the Infrastructure layer for Research, Proposal, and Evaluation without risking the currently working Research pipeline. It prevents the 3-step refactor from becoming a one-off hardcoded hack in the Cognitive layer.

# 11. Red Flags
- **Semantic Transformer**: Allowing Step 2 to "guess" or "infer" missing content. It must be mechanical.
- **Reasoning Formatter**: Allowing Step 3 to analyze the evidence pack. It must only format the Step 1 artifact.
- **Infrastructure Semantics**: Letting `infrastructure/` decide what a "finding" is.
- **Interface Truth**: Letting the CLI "smooth over" a Step 2 failure by showing a "repaired" result without a debug trace.

# 12. Final Recommendation
The target shape is a **Bounded Text $\rightarrow$ Deterministic Parse $\rightarrow$ Formatter Fallback** pipeline. The most practical path is to first build the Infrastructure "vocabulary" (purposes, strategies, profiles), then implement the primary Step 1/2 path, and finally add the Step 3 rescue layer. This preserves the existing working research slices while evolving the runtime into a reusable asset for the rest of the Cognitive layer.
