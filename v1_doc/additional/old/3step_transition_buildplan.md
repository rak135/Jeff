# 3step_transition_buildplan.md

Status: working build plan for the Jeff 3-step transition  
Authority: subordinate to `3step_transition.md`, Jeff canon in `v1_doc/`, and current repo reality  
Purpose: define the concrete, step-by-step implementation plan for moving Jeff Research from the current JSON-first synthesis/repair flow to the new 3-step transition without broad rewrite

---

## 1. Build-plan purpose

This document is not a fresh architecture spec.
It is the practical implementation plan for migrating the real current repo.

The migration target is:

1. **Step 1 — bounded text generation**
2. **Step 2 — deterministic transformer**
3. **Step 3 — formatter fallback**
4. existing downstream unchanged:
   - citation remap
   - provenance validation
   - persistence
   - projection/render
   - optional memory handoff

This build plan is designed to:
- preserve what already works
- avoid broad rewrite
- keep research semantics in `jeff/cognitive/research/`
- keep runtime/config and execution posture in `jeff/infrastructure/`
- make the new infrastructure reusable later for proposal and evaluation

---

## 2. Non-negotiable constraints

The following remain hard constraints throughout all slices:

- research remains support, not truth
- evidence-first research remains
- fail-closed provenance remains
- citation-key remap remains
- remap from `S1..Sn` back to internal `source_id` remains downstream
- persistence, projection/render, and memory handoff remain downstream
- Interface remains downstream
- Orchestrator does not own research business logic
- Infrastructure owns runtime/config and technical routing, not research semantics
- no broad rewrite
- no parallel competing pipeline left alive for long-term drift

---

## 3. Current repo reality we are building from

The current repo already has:

- a dedicated `jeff/cognitive/research/` package
- acquisition split across `documents.py` and `web.py`
- current `synthesis.py` with JSON-first synthesis and bounded repair behavior
- fail-closed citation-key remap and provenance validation
- downstream `persistence.py` and `memory_handoff.py`
- `errors.py`
- `legacy.py` compatibility surface
- debug checkpoint support through `debug.py`
- `jeff/infrastructure/` with provider-neutral adapters and runtime config
- purpose-based routing already supporting at least `research` and `research_repair`

This means we are not inventing a new research module.
We are evolving the existing one.

---

## 4. Final target shape

### 4.1 Research flow

Final intended flow:

`evidence pack -> Step 1 bounded text -> Step 2 deterministic transformer -> Step 3 formatter fallback if needed -> remap -> provenance -> persistence/render -> optional memory handoff`

### 4.2 Responsibility boundaries

#### Research owns
- Step 1 syntax contract
- Step 1 prompt/request builder
- Step 1 bounded-text artifact definitions
- Step 2 deterministic parsing/normalization
- Step 2 research-local validation rules
- Step 3 formatter request builder
- Step 3 fallback eligibility policy
- research debug checkpoints
- research-local exceptions

#### Infrastructure owns
- runtime config
- stable purpose vocabulary
- output strategy vocabulary
- capability profile vocabulary
- technical fallback execution policy
- model/provider selection and adapter calls
- optional typed-call helpers used by research/proposal/evaluation later

#### Downstream remains unchanged
- citation remap
- provenance validation
- persistence
- projection/render
- memory handoff semantics

---

## 5. Final target folder structure

## 5.1 Research target structure

```text
jeff/cognitive/research/
├── __init__.py
├── contracts.py
├── bounded_syntax.py
├── synthesis.py
├── deterministic_transformer.py
├── formatter.py
├── validators.py
├── fallback_policy.py
├── debug.py
├── documents.py
├── web.py
├── persistence.py
├── memory_handoff.py
├── errors.py
└── legacy.py   # temporary only, retired later
```

### File roles

- `contracts.py`
  - keep and extend
  - continues to own research request/evidence/final artifact contracts
  - add Step 1 bounded-text artifact contract types

- `bounded_syntax.py`
  - new
  - owns Step 1 hard syntax specification and request-builder helpers
  - no provider/runtime ownership

- `synthesis.py`
  - keep and modify
  - remains research pipeline orchestrator
  - should stop being the dumping ground for every helper
  - should orchestrate Step 1 -> Step 2 -> Step 3 -> downstream handoff

- `deterministic_transformer.py`
  - new
  - owns pure mechanical parse and normalization from Step 1 text to candidate final shape
  - must fail closed on unsafe or ambiguous cases

- `formatter.py`
  - new
  - owns Step 3 formatter request builder and formatter-stage call wrapper
  - may initially use existing runtime/adapters directly
  - later may use Instructor-backed typed calls through Infrastructure

- `validators.py`
  - new
  - shared research-local validation helpers
  - syntax checks
  - section completeness checks
  - citation-key shape checks
  - final artifact structural checks that are still research-local

- `fallback_policy.py`
  - new
  - owns the decision rules for when formatter fallback is allowed
  - not provider routing
  - not technical retry policy

- `debug.py`
  - keep
  - update checkpoint vocabulary to truthful 3-step stage labels

- `documents.py`, `web.py`, `persistence.py`, `memory_handoff.py`, `errors.py`
  - keep

- `legacy.py`
  - keep temporarily
  - retire later after all callers/tests migrate

## 5.2 Infrastructure target structure

```text
jeff/infrastructure/
├── __init__.py
├── config.py
├── runtime.py
├── purposes.py
├── output_strategies.py
├── capability_profiles.py
├── contract_runtime.py
├── typed_calls/
│   ├── __init__.py
│   └── instructor_runtime.py   # later or optional in first wave
└── model_adapters/
    ├── __init__.py
    ├── base.py
    ├── registry.py
    ├── factory.py
    └── providers/
```

### File roles

- `config.py`
  - keep and extend
  - add optional strategy/profile vocabulary without breaking current config

- `runtime.py`
  - keep and extend
  - assemble infrastructure services
  - may expose a small contract runtime entrypoint

- `purposes.py`
  - new
  - stable purpose names for reusable LLM stages

- `output_strategies.py`
  - new
  - stable strategy names such as:
    - `plain_text`
    - `bounded_text_then_parse`
    - `bounded_text_then_formatter`
    - `native_json_schema`
    - `baml_contract` (future)

- `capability_profiles.py`
  - new
  - model/provider capability hints
  - no research semantics

- `contract_runtime.py`
  - new
  - reusable technical runtime surface for typed or strategy-aware calls
  - should stay thin in first wave

- `typed_calls/instructor_runtime.py`
  - optional first wave, likely second wave
  - helper for typed formatter/proposal/evaluation calls later

- `model_adapters/*`
  - keep

### Explicitly deferred for now

Do **not** add in the first wave unless a real need appears:

- `guardrails_runtime.py`
- `baml_runtime.py`
- dedicated `telemetry/` package
- large strategy registry framework
- complex fallback chain engine

---

## 6. Open-source component decisions

## 6.1 Use now

### Instructor
Use **later in the Step 3 slice if needed**, not as the first thing to add.

Role:
- typed formatter fallback helper
- later reusable typed-call helper for proposal/evaluation

Why:
- practical multi-provider structured output helper
- good fit for formatter fallback over a small bounded artifact

Why not earlier:
- Step 1 and Step 2 must be proven first
- do not make fallback tooling the primary path

## 6.2 Optional later

### Guardrails
Optional later only.

Role:
- validator composition helper if research/proposal/evaluation later need it

Why not now:
- first wave can stay deterministic and Jeff-owned
- avoid introducing a second validation abstraction before the basic path exists

### Outlines
Optional later only.

Role:
- constrained generation experiments for local backends

Why not now:
- not required for the initial 3-step transition
- not necessary to prove bounded syntax generation

### BAML
Optional later only.

Role:
- contract testing and typed LLM contract layer for future complex flows
- potentially useful later for formatter/proposal/evaluation contracts

Why not now:
- too heavy for the first migration wave
- must not become the owner of Jeff infrastructure or research semantics

---

## 7. Output-strategy vocabulary

Infrastructure should support reusable strategy names, but only a minimal subset must be wired first.

### 7.1 Required now

- `plain_text`
- `bounded_text_then_parse`
- `bounded_text_then_formatter`

### 7.2 Defer until real need

- `native_json_schema`
- `baml_contract`

### 7.3 Initial default posture

For research:
- default = `bounded_text_then_parse`
- fallback path = `bounded_text_then_formatter`

For proposal later:
- likely start with `plain_text` or `bounded_text_then_parse`
- only later evaluate `native_json_schema` or `baml_contract`

For evaluation later:
- likely smaller structured outputs
- may later benefit from `native_json_schema` or Instructor-backed typed calls

---

## 8. Slice strategy

This migration should happen in **two waves**:

- **Wave 1** = minimal working transition to the new 3-step research path
- **Wave 2** = infrastructure hardening and cleanup for broader reuse

This prevents the transition from turning into a giant infrastructure rewrite.

---

## 9. Wave 1 — minimal working transition

## Slice 1 — Step 1 syntax contract and bounded artifact types

### Goal
Introduce the new Step 1 bounded syntax contract without changing the runtime behavior yet.

### Files touched
- `jeff/cognitive/research/contracts.py`
- `jeff/cognitive/research/bounded_syntax.py` (new)
- `tests/unit/cognitive/...` add new tests

### Work
- add bounded Step 1 artifact types to `contracts.py`
- define the hard syntax contract in `bounded_syntax.py`
- add validators for syntax sections and citation-key discipline
- do not switch the main synthesis flow yet

### Must remain unchanged
- `synthesis.py` behavior
- downstream remap/provenance/persistence/memory handoff
- infrastructure runtime behavior

### Acceptance criteria
- Step 1 syntax contract exists
- bounded artifact types exist
- tests cover valid/invalid bounded syntax cases
- no behavior change in normal research flow yet

### Rollback risk
Low.
Purely additive.

---

## Slice 2 — Deterministic transformer implementation

### Goal
Build the cheap primary path from bounded text to candidate final artifact shape.

### Files touched
- `jeff/cognitive/research/deterministic_transformer.py` (new)
- `jeff/cognitive/research/validators.py` (new)
- tests

### Work
- implement mechanical parse rules
- implement fail-closed behavior
- implement citation-key and section checks needed for transformer safety
- keep transformer free of semantic repair

### Must remain unchanged
- current live synthesis path
- infrastructure routing
- persistence/provenance

### Acceptance criteria
- deterministic transformer can convert valid bounded text to a candidate final artifact
- malformed or ambiguous bounded text fails closed
- no semantic filling, guessing, or inference occurs in transformer code

### Rollback risk
Low to medium.
Still additive if not wired into main path yet.

---

## Slice 3 — Wire Step 1 and Step 2 into research synthesis as primary path

### Goal
Switch research from JSON-first primary synthesis to bounded-text-first primary synthesis with deterministic parse.

### Files touched
- `jeff/cognitive/research/synthesis.py`
- `jeff/cognitive/research/bounded_syntax.py`
- `jeff/cognitive/research/deterministic_transformer.py`
- `jeff/cognitive/research/debug.py`
- tests

### Work
- change Step 1 prompt/request builder to bounded hard syntax
- use deterministic transformer after Step 1 output
- keep existing downstream remap/provenance/persistence path unchanged
- emit truthful new debug checkpoints for Step 1 and Step 2
- do not introduce Step 3 formatter yet unless needed for compatibility bridge

### Must remain unchanged
- remap/provenance
- persistence
- memory handoff
- infrastructure purpose config

### Acceptance criteria
- normal research flow runs through bounded text then deterministic transformer
- downstream remains unchanged
- debug labels truthfully show Step 1 and Step 2
- failure cases stop honestly

### Rollback risk
Medium.
This is the first slice that changes the primary path.

---

## Slice 4 — Formatter fallback using existing runtime first

### Goal
Introduce Step 3 formatter fallback without adding unnecessary tooling first.

### Files touched
- `jeff/cognitive/research/formatter.py` (new)
- `jeff/cognitive/research/fallback_policy.py` (new)
- `jeff/cognitive/research/synthesis.py`
- `jeff/cognitive/research/debug.py`
- tests

### Work
- build Step 3 formatter request builder
- define fallback eligibility policy
- use already produced Step 1 bounded text as formatter input
- do not resend the original evidence pack to formatter
- initially route formatter through the existing runtime/adapters, reusing current `research_repair` capability if practical
- validate formatter output hard before downstream handoff

### Must remain unchanged
- acquisition
- downstream remap/provenance/persistence/memory handoff
- infrastructure adapter base/factory/registry

### Acceptance criteria
- Step 3 is invoked only when Step 2 cannot safely complete
- Step 3 receives bounded text, not the full evidence pack
- Step 3 output is validated hard
- formatter does not become a second reasoner
- debug labels show actual fallback execution truthfully

### Rollback risk
Low to medium.
Fallback path only.

---

## Slice 5 — Cleanup current repair terminology and bridge code

### Goal
Align names and helpers with the real 3-step design after the flow is live.

### Files touched
- `jeff/cognitive/research/synthesis.py`
- `jeff/cognitive/research/formatter.py`
- `jeff/infrastructure/config.py`
- `jeff/infrastructure/runtime.py`
- tests
- docs/handoffs/status notes

### Work
- decide what happens to the old `research_repair` purpose naming
- either:
  - keep it as a technical provider override name temporarily, or
  - rename it to `research_formatter` once the migration is stable
- remove stale repair-only wording from debug/docs where it no longer reflects reality

### Must remain unchanged
- actual behavior
- downstream semantics

### Acceptance criteria
- naming matches the real 3-step flow
- no misleading repair-first terminology remains in active paths
- runtime behavior is stable

### Rollback risk
Low.
Mostly naming and cleanup.

---

## 10. Wave 2 — infrastructure hardening for broader reuse

## Slice 6 — Minimal infrastructure vocabulary

### Goal
Introduce reusable infrastructure vocabulary without overbuilding.

### Files touched
- `jeff/infrastructure/purposes.py` (new)
- `jeff/infrastructure/output_strategies.py` (new)
- `jeff/infrastructure/capability_profiles.py` (new)
- `jeff/infrastructure/config.py`
- `jeff/infrastructure/runtime.py`
- tests

### Work
- add minimal purpose vocabulary
- add minimal strategy vocabulary
- add minimal capability profile model
- keep integration thin
- do not build large dispatch framework yet

### Must remain unchanged
- current model adapters
- current research flow behavior

### Acceptance criteria
- infrastructure can describe strategy and capability choices for research
- no semantic ownership leaks into infrastructure
- current behavior remains stable

### Rollback risk
Low.
Additive.

---

## Slice 7 — Thin contract runtime

### Goal
Create a reusable technical surface for strategy-aware LLM calls that future proposal/evaluation can reuse.

### Files touched
- `jeff/infrastructure/contract_runtime.py` (new)
- `jeff/infrastructure/runtime.py`
- tests

### Work
- expose thin strategy-aware call entrypoints
- keep research semantics out of it
- keep implementation minimal

### Must remain unchanged
- research-local parsing/validation/semantics
- model adapter internals unless a small bridge is needed

### Acceptance criteria
- research can call through a reusable infrastructure runtime surface if desired
- proposal/evaluation have a clean place to plug in later
- no framework bloat introduced

### Rollback risk
Low.

---

## Slice 8 — Optional Instructor integration for formatter and future typed calls

### Goal
Add typed-call support only after the primary path is stable.

### Files touched
- `jeff/infrastructure/typed_calls/instructor_runtime.py` (new)
- `jeff/infrastructure/runtime.py`
- `jeff/cognitive/research/formatter.py`
- tests

### Work
- wrap Step 3 formatter call with Instructor if it improves reliability enough to justify the dependency
- keep direct adapter fallback available during migration if useful

### Must remain unchanged
- Step 1 bounded syntax
- Step 2 deterministic transformer
- downstream remap/provenance

### Acceptance criteria
- typed formatter calls work through infrastructure helper
- no change to research semantics
- dependency cost is justified by real stability gains

### Rollback risk
Low.
Optional slice.

---

## Slice 9 — Compatibility cleanup and retirement

### Goal
Remove temporary compatibility surfaces once migration is complete.

### Files touched
- `jeff/cognitive/research/legacy.py`
- callers/tests relying on old compatibility APIs
- docs/handoffs/status notes

### Work
- identify remaining `legacy.py` dependencies
- remove them deliberately
- retire `legacy.py`

### Must remain unchanged
- stable public behavior of the new 3-step path

### Acceptance criteria
- no active caller depends on `legacy.py`
- compatibility shim removed cleanly
- tests all green

### Rollback risk
Medium if attempted too early.
Do not do this before migration is fully complete.

---

## 11. First recommended implementation slice

The **smallest correct first slice** is:

### Slice 1 — Step 1 syntax contract and bounded artifact types

Why this is first:
- smallest additive slice
- no infrastructure replatforming required
- no behavior switch yet
- creates the contract foundation for the rest of the migration
- keeps the repo grounded in the actual research transition instead of starting with abstract infrastructure

If you prefer a more architecture-first posture, the acceptable alternative first slice is:

### Alternate first slice — minimal infrastructure vocabulary

But that is **not** the smallest working research slice.
It is the cleaner future-facing slice.

Recommended order between the two:
- if your priority is quickest research progress: start with Step 1 contract
- if your priority is infrastructure-first reuse discipline: start with minimal infrastructure vocabulary

My recommendation for this repo right now:
**start with Step 1 contract first, then do minimal infrastructure vocabulary second**.

---

## 12. Files that should stay untouched in early slices

During Slices 1 and 2, do not touch unless absolutely necessary:

- `jeff/cognitive/research/documents.py`
- `jeff/cognitive/research/web.py`
- `jeff/cognitive/research/persistence.py`
- `jeff/cognitive/research/memory_handoff.py`
- `jeff/infrastructure/model_adapters/base.py`
- `jeff/infrastructure/model_adapters/registry.py`
- `jeff/infrastructure/model_adapters/factory.py`
- provider implementations under `jeff/infrastructure/model_adapters/providers/`
- Interface surfaces
- Orchestrator flow semantics

These are not the problem.
Do not create damage where there is no current need.

---

## 13. Red flags

The migration fails architecturally if any of these happen:

- Step 2 deterministic transformer starts interpreting, inferring, or filling missing content
- Step 3 formatter receives the original evidence pack and becomes a second research pass
- Infrastructure starts owning research semantics such as what counts as a finding or inference
- debug checkpoints lie about actual stage boundaries
- current working downstream pieces are rewritten “for consistency” without concrete need
- `legacy.py` is deleted before callers/tests are migrated
- new infrastructure vocabulary is expanded into a framework before real reuse pressure exists
- Instructor/BAML/Guardrails are introduced before the primary path is stable

---

## 14. Final recommendation

The correct build posture is:

1. **prove the new research path first**
   - Step 1 bounded syntax contract
   - Step 2 deterministic transformer
   - Step 3 formatter fallback
   - downstream unchanged

2. **then harden infrastructure for reuse**
   - minimal purpose vocabulary
   - minimal output strategy vocabulary
   - minimal capability profiles
   - thin contract runtime

3. **then optionally add external helpers**
   - Instructor first if needed
   - Guardrails/Outlines/BAML only later and only for clear value

This keeps the migration:
- grounded in the real repo
- cheap to validate
- robust against broad rewrite drift
- reusable later for proposal and evaluation

