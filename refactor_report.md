# Refactor Report

## Audit basis

- Canonical semantic sources used:
  - `v1_doc/ARCHITECTURE.md`
  - `v1_doc/ORCHESTRATOR_SPEC.md`
  - `v1_doc/CLI_V1_OPERATOR_SURFACE.md`
  - `v1_doc/MEMORY_SPEC_NEW.md`
- Implementation-reality sources used:
  - large-file snapshot from current repo
  - recent churn snapshot since 2026-04-17
  - `jeff/interface/*`, `jeff/orchestrator/*`, `jeff/cognitive/*`, `jeff/memory/*`, `jeff/infrastructure/*`, `jeff/runtime_persistence.py`, `jeff/bootstrap.py`
  - recent status updates, especially `WORK_STATUS_UPDATE_2026-04-19_1027.md`
- Code areas inspected:
  - command routing seams, projection/render seams, orchestration continuations, research pipeline, persistence serialization, memory store/runtime seams
- Test areas inspected:
  - interface, orchestrator, research, runtime persistence, memory, acceptance alignment suites
- Limitations / uncertainty notes:
  - churn evidence is recent and bounded; it shows concentration, not absolute long-term instability
  - some large files are large because they encode explicit serialization or validation detail, which is not automatically bad
  - recommendations below are intentionally bounded and architecture-preserving, not rewrite proposals

## Real refactor hotspots

### 1. `jeff/interface/commands.py`

- Problem class:
  - mixed responsibility
  - command blob growth
  - orchestration creep
  - boundary bleed
- Why it matters:
  - This file currently owns command parsing, session-scope mutation, run resolution, research execution wiring, live-context assembly, selection review materialization, override recomputation, request-entry handling, and JSON-mode application.
  - At 1659 lines it is the single largest Python file in the repo. That is a real maintenance problem, not aesthetic discomfort.
- Evidence:
  - file-size snapshot shows it as the largest file in the repo
  - CLI behavior for nearly every surface routes through it
  - it imports across cognitive, governance, memory, orchestrator, runtime persistence, and rendering boundaries
- Urgency:
  - high
- Recommendation:
  - refactor before more feature work lands

### 2. `jeff/runtime_persistence.py`

- Problem class:
  - mixed responsibility
  - persistence seam weakness
  - coupling pressure
- Why it matters:
  - It combines runtime-home layout ownership, JSON I/O, canonical state serialization, flow-run serialization, selection-review serialization, transition audit persistence, and compatibility handling.
  - This is currently the second-largest file at 821 lines. It is doing real work, but too many kinds of work.
- Evidence:
  - file-size snapshot ranks it second
  - `tests/integration/test_runtime_workspace_persistence.py` exercises many different concerns through one file
  - startup and runtime continuity depend on it heavily through `jeff/bootstrap.py`
- Urgency:
  - high
- Recommendation:
  - refactor soon

### 3. `jeff/orchestrator/runner.py`

- Problem class:
  - orchestration creep
  - coupling pressure
  - acceptable debt / not yet chaos
- Why it matters:
  - The runner still coordinates stage looping, pre-stage route checks, planning bridges, post-research continuation, finish helpers, hybrid selection failure handling, and event/lifecycle updates.
  - Recent work explicitly extracted continuation glue out of this file, which means the repo itself already identified it as a hotspot.
- Evidence:
  - `WORK_STATUS_UPDATE_2026-04-19_1027.md` explicitly says this extraction was needed because runner had become a continuation blob
  - file-size snapshot still shows 793 lines after extraction
  - recent work-status files from 2026-04-19 repeatedly touched `jeff/orchestrator/runner.py`
- Urgency:
  - medium
- Recommendation:
  - refactor soon, but only in small continuation-local slices

### 4. `jeff/interface/json_views.py`

- Problem class:
  - render/projection/meaning bleed
  - command blob growth by adjacency
  - acceptable debt trending worse
- Why it matters:
  - This file is the projection law for many CLI views, and that is good. But at 740 lines it now mixes run-show derivation, selection review projections, request receipts, research result/error projection, telemetry projection, evaluation summaries, and support summarization.
  - The risk is not wrong architecture today. The risk is that every new CLI view will keep accumulating here until truth/support/derived distinctions become harder to reason about.
- Evidence:
  - file-size snapshot ranks it fourth
  - acceptance and truthfulness tests rely on this file's distinctions, meaning small mistakes here can quietly distort operator meaning
- Urgency:
  - medium
- Recommendation:
  - refactor soon

### 5. `jeff/cognitive/research/synthesis.py`

- Problem class:
  - research-pipeline overgrowth
  - mixed responsibility
- Why it matters:
  - This module owns prompt construction, runtime invocation, debug emission, bounded text precheck, deterministic transform, citation remap, provenance validation, formatter fallback coordination, and exception translation.
  - Research is one of the strongest live capabilities in Jeff, which makes this file more important, not less.
- Evidence:
  - file-size snapshot ranks it fifth
  - research functionality is broad and well-tested, but the pipeline logic is concentrated in one module
  - many research tests indirectly depend on this file's behavior
- Urgency:
  - medium
- Recommendation:
  - refactor soon, but protect behavior with the current research test matrix

### 6. `jeff/orchestrator/continuations/post_selection.py`

- Problem class:
  - orchestration creep
  - coupling pressure
  - boundary bleed
- Why it matters:
  - The extraction from runner helped, but complexity did not disappear; it moved here. This continuation module still centralizes downstream handling for multiple post-selection branches.
- Evidence:
  - file-size snapshot shows 610 lines
  - multiple 2026-04-19 work-status entries added new post-selection continuation slices in rapid sequence
- Urgency:
  - medium
- Recommendation:
  - refactor later unless another post-selection feature lands soon

### 7. `jeff/memory/postgres_store.py`

- Problem class:
  - mixed responsibility
  - persistence seam weakness
  - acceptable debt / not yet chaos
- Why it matters:
  - It owns schema DDL, transaction management, CRUD, link persistence, lexical retrieval SQL, semantic retrieval SQL, and row mapping.
  - That is a lot, but it is also a fairly natural concentration for a store adapter.
- Evidence:
  - 540 lines
  - integration tests cover it directly
  - the module is large but still semantically cohesive compared to the interface/orchestrator blobs
- Urgency:
  - low to medium
- Recommendation:
  - leave it alone unless the Postgres path grows materially beyond current scope

### 8. `jeff/memory/write_pipeline.py`

- Problem class:
  - mixed responsibility
  - acceptable debt / not yet chaos
- Why it matters:
  - It is large because it coordinates the whole memory write pipeline, but that coordination role is legitimate.
- Evidence:
  - 457 lines
  - its docstring explicitly defines the stages and atomic write boundary
  - memory tests are extensive and the file is still centered on one use case
- Urgency:
  - low
- Recommendation:
  - leave it alone for now

### 9. `jeff/bootstrap.py`

- Problem class:
  - coupling pressure
  - acceptable debt / not yet chaos
- Why it matters:
  - Startup wiring, demo fixture creation, runtime service attachment, and selection-review demo materialization all live here.
  - It is active and central, but still reasonably bounded by startup concerns.
- Evidence:
  - recent churn snapshot shows it touched recently
  - startup and runtime tests cover it well
- Urgency:
  - low
- Recommendation:
  - leave it alone unless startup grows another major capability family

## Recommended bounded refactor plan

### 1. Split CLI command families out of `jeff/interface/commands.py`

- Exact files/modules touched:
  - `jeff/interface/commands.py`
  - new modules such as `jeff/interface/command_scope.py`, `jeff/interface/command_runs.py`, `jeff/interface/command_selection.py`, `jeff/interface/command_research.py`, `jeff/interface/command_requests.py`
- What problem it solves:
  - reduces the main command blob and separates scope navigation, inspection/history, selection review, research execution, and request-entry semantics
- What semantic invariants must remain unchanged:
  - slash-command surface stays the same
  - session scope remains local only
  - truth/support/derived separation remains identical
  - request commands remain explicitly non-authorizing
- What tests must be run before and after:
  - `tests/unit/interface`
  - `tests/smoke/test_cli_entry_smoke.py`
  - `tests/acceptance/test_acceptance_cli_orchestrator_alignment.py`
  - relevant research CLI integration tests
- Risk level:
  - medium
- Whether to do it now or later:
  - now
- What future work it unblocks:
  - adding missing CLI surfaces without turning one file into the repo’s second orchestrator

### 2. Extract runtime persistence serializers and stores out of `jeff/runtime_persistence.py`

- Exact files/modules touched:
  - `jeff/runtime_persistence.py`
  - new modules such as `jeff/runtime_persistence_state.py`, `jeff/runtime_persistence_flow_runs.py`, `jeff/runtime_persistence_reviews.py`, `jeff/runtime_persistence_serialization.py`
- What problem it solves:
  - separates runtime-home layout management from object serialization and support-store persistence
- What semantic invariants must remain unchanged:
  - canonical truth remains only in canonical state files
  - flow runs and selection reviews remain support records, not truth
  - current on-disk layout and legacy artifact compatibility stay intact
- What tests must be run before and after:
  - `tests/integration/test_runtime_workspace_persistence.py`
  - `tests/integration/test_bootstrap_runtime_config.py`
  - `tests/smoke/test_bootstrap_smoke.py`
- Risk level:
  - medium
- Whether to do it now or later:
  - now
- What future work it unblocks:
  - safer growth in runtime continuity, review persistence, and startup support records

### 3. Keep trimming `jeff/orchestrator/runner.py` by extracting finish/routing helpers

- Exact files/modules touched:
  - `jeff/orchestrator/runner.py`
  - possibly `jeff/orchestrator/continuations/boundary_routes.py`
  - possibly `jeff/orchestrator/runner_helpers.py`
- What problem it solves:
  - keeps runner focused on stage loop coordination instead of accumulating route/finish detail again
- What semantic invariants must remain unchanged:
  - stage ordering
  - handoff validation
  - no hidden business semantics
  - anti-loop and fail-closed behavior in current continuations
- What tests must be run before and after:
  - `tests/unit/orchestrator`
  - `tests/integration/test_orchestrator_post_selection_next_stage_routing.py`
  - `tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py`
  - `tests/acceptance/test_acceptance_backbone_flow.py`
- Risk level:
  - medium
- Whether to do it now or later:
  - now if more continuation work is about to land, otherwise later
- What future work it unblocks:
  - additional bounded orchestration features without re-growing the runner monolith

### 4. Split view projection builders out of `jeff/interface/json_views.py`

- Exact files/modules touched:
  - `jeff/interface/json_views.py`
  - new modules such as `jeff/interface/json_views_runs.py`, `jeff/interface/json_views_selection.py`, `jeff/interface/json_views_research.py`
- What problem it solves:
  - prevents operator projection rules from collapsing into one oversized file
- What semantic invariants must remain unchanged:
  - projection keys and payload shape for existing CLI/tests
  - truth/support/derived/telemetry separation
  - no semantic reinterpretation in the view layer
- What tests must be run before and after:
  - `tests/unit/interface/test_cli_truthfulness.py`
  - `tests/unit/interface/test_cli_json_views.py`
  - `tests/unit/interface/test_research_source_transparency.py`
  - `tests/acceptance/test_acceptance_cli_orchestrator_alignment.py`
- Risk level:
  - low to medium
- Whether to do it now or later:
  - later, but before adding many more CLI views
- What future work it unblocks:
  - safer addition of missing rationale/telemetry/health surfaces if they are later approved

### 5. Factor research synthesis into step-local helpers without changing behavior

- Exact files/modules touched:
  - `jeff/cognitive/research/synthesis.py`
  - new modules such as `jeff/cognitive/research/runtime_invocation.py`, `jeff/cognitive/research/citation_remap.py`, `jeff/cognitive/research/debug_events.py`
- What problem it solves:
  - reduces concentration of prompting, invocation, debug, transform, fallback, and provenance logic in one file
- What semantic invariants must remain unchanged:
  - current three-step bounded synthesis law
  - provenance validation
  - formatter fallback rules
  - debug checkpoint sequence and naming
- What tests must be run before and after:
  - research unit suite
  - `tests/integration/test_document_research_end_to_end.py`
  - `tests/integration/test_web_research_end_to_end.py`
  - CLI research integration tests
- Risk level:
  - medium
- Whether to do it now or later:
  - later
- What future work it unblocks:
  - safer expansion of runtime-backed research without destabilizing the strongest functional subsystem

## What should not be refactored yet

### Ugly-but-acceptable areas

- `jeff/memory/write_pipeline.py`
  - large, but still legitimately owns one coordination problem
- `jeff/memory/postgres_store.py`
  - large adapter, but still cohesive around the Postgres store boundary

### Active but still well-bounded areas

- `jeff/bootstrap.py`
  - central startup file, but not yet showing the same semantic sprawl as `commands.py` or `runtime_persistence.py`
- provider adapters under `jeff/infrastructure/model_adapters/providers/*`
  - they should stay provider-local rather than being prematurely abstracted into a wider framework

### Areas where refactoring now would create churn without real gain

- small bridge modules added on 2026-04-19 such as research decision-support and proposal-support consumers
  - these are new, explicit, and locally bounded; the right move is to let them stay small and separate

### Areas where missing capability is the real problem, not code cleanliness

- missing primary operator run-launch surface
- thin approval/recovery control flows
- broader provider/runtime hardening

Cleaning code around those does not substitute for adding the missing bounded capability.

## Refactor bottom line

- What is the single worst hotspot today?
  - `jeff/interface/commands.py`.

- What is the highest-value bounded refactor?
  - Split `jeff/interface/commands.py` into command-family modules while preserving the public CLI surface and truthfulness behavior.

- What should be left alone for now?
  - `jeff/memory/write_pipeline.py`, `jeff/memory/postgres_store.py`, and the newer small post-selection bridge modules.

- What kind of refactor would be a destructive mistake?
  - Any rewrite that recenters semantics into the interface or orchestrator, collapses support/truth distinctions, or tries to replace the current bounded architecture with a new workflow engine. Jeff does not need an architecture reset. It needs careful decomposition at the current seams.