## 2026-04-10 19:28 - TASK: M-001 - Added Phase 1 core backbone

- Scope: Phase 1 core schemas, canonical state root, containers, and transition path
- Done:
  - added shared typed IDs, scope, validation issue, and internal envelope models
  - added immutable global state, state metadata, system placeholder, and nested project registry
  - added minimal Project, WorkUnit, and Run models with ownership invariants
  - added transition request, validation, candidate construction, and commit/reject flow for create_project, create_work_unit, and create_run
  - added invariant-focused pytest coverage for schemas, topology, containers, and transitions
- Validation: `python -m pytest -q` passed with 16 tests
- Current state: the Phase 1 truth-safe core backbone is implemented as an in-memory, transition-controlled foundation
- Next step: build the next bounded Phase 2 slice without widening the core truth surface
- Files:
  - jeff/core/schemas/ids.py
  - jeff/core/state/models.py
  - jeff/core/containers/models.py
  - jeff/core/transition/apply.py
  - tests/test_transition_rules.py

## 2026-04-10 19:42 - TASK: M-002 - Added Phase 2 governance action-entry safety

- Scope: governance layer, transient action contract, and action-entry boundary tests
- Done:
  - added narrow transient Action contract with typed identity, scope linkage, and basis binding
  - added separate Policy, Approval, and Readiness models with distinct typed verdict/state families
  - added fail-closed action-entry evaluation for policy, approval binding, freshness, scope match, blockers, and escalation
  - added negative tests for selection-as-permission drift, raw action start attempts, stale approval reuse, and approval/readiness flattening
- Validation: targeted governance pytest files passed and full `python -m pytest -q` passed with 31 tests
- Current state: Phase 2 governance now exists as a separate layer that gates action start without mutating truth or implementing execution
- Next step: build the Phase 3 context, research, decision, and conditional planning slice on top of the governed action boundary
- Files:
  - jeff/contracts/action.py
  - jeff/governance/policy.py
  - jeff/governance/approval.py
  - jeff/governance/action_entry.py
  - tests/test_governance_negative_boundaries.py

  ## 2026-04-10 19:53 - TASK: M-003 - Added Phase 3 cognitive contracts

- Scope: truth-first context, bounded research, proposal, selection, and conditional planning
- Done:
  - added cognitive context package and assembler anchored on canonical truth with scope-checked support inputs
  - added source-aware research request/result contracts with distinct findings, inferences, uncertainty, and recommendation fields
  - added proposal and selection contracts with 0..3 honest option enforcement and explicit non-selection outcomes
  - added conditional planning gate and plan artifact model that refuses unjustified default planning
  - added Phase 3 boundary tests for context leakage, proposal padding, selection non-permission, and plan/action separation
- Validation: targeted Phase 3 pytest files passed and full `python -m pytest -q` passed with 44 tests
- Current state: Phase 3 cognitive contracts now exist as a separate layer without execution, memory, or orchestration creep
- Next step: build the Phase 4 governed execution, outcome, and evaluation slice on top of the current action and governance boundaries
- Files:
  - jeff/cognitive/context.py
  - jeff/cognitive/research.py
  - jeff/cognitive/proposal.py
  - jeff/cognitive/selection.py
  - jeff/cognitive/planning.py

  ## 2026-04-10 20:00 - TASK: M-004 - Added Phase 4 action and judgment contracts

- Scope: governed execution, normalized outcome, evaluation, and deterministic override checks
- Done:
  - added governed execution entry contract tied to a specific allowed governance decision and bounded action
  - added operational execution result, explicit outcome normalization, and bounded evaluation result contracts
  - added deterministic override checks for missing artifacts, missing verification, unmet mandatory targets, mismatch, and evidence gaps
  - added recommended next-step outputs that stay non-authorizing
  - added Phase 4 boundary tests for governance-before-execution, execution-outcome-evaluation separation, and optimistic-verdict caps
- Validation: targeted Phase 4 pytest files passed and full `python -m pytest -q` passed with 54 tests
- Current state: Phase 4 action, outcome, and evaluation contracts now exist without truth mutation, memory, or orchestration creep
- Next step: build the Phase 5 memory and durable continuity slice on top of the current evaluation outputs
- Files:
  - jeff/action/execution.py
  - jeff/action/outcome.py
  - jeff/action/evaluation.py
  - tests/test_evaluation_rules.py
  - tests/test_action_stage_boundaries.py

  ## 2026-04-10 20:38 - TASK: M-005 - Added minimal memory discipline

- Scope: Phase 5 memory contracts, write discipline, retrieval boundaries, and memory-vs-truth tests
- Done:
  - added separate `jeff.memory` package with bounded memory types, candidate model, committed record model, and in-memory store
  - added Memory-owned candidate creation plus selective write, reject, and defer pipeline with committed `memory_id` issuance
  - added truth-first retrieval contracts, local scope filtering, contradiction/staleness labeling, and canonical memory-link validation
  - added negative tests for direct candidate construction, duplicate and low-value rejection, wrong-project retrieval, and memory truth-separation
- Validation: targeted memory pytest files passed and full `python -m pytest -q` passed with 69 tests
- Current state: Phase 5 memory discipline now exists as a separate bounded layer without DB, vector-store, memory-as-truth, or orchestrator creep
- Next step: build the Phase 6 orchestrator integration and CLI-first operator surface on top of the now-stable stage contracts
- Files:
  - jeff/memory/models.py
  - jeff/memory/write_pipeline.py
  - jeff/memory/retrieval.py
  - tests/test_memory_write_rules.py
  - tests/test_memory_truth_separation.py

  ## 2026-04-10 20:56 - TASK: M-006A - Added orchestrator sequencing skeleton

- Scope: Phase 6A orchestrator flow sequencing, handoff validation, routing, lifecycle, and trace support
- Done:
  - added separate `jeff.orchestrator` package with bounded flow families and explicit stage orders
  - added fail-closed stage sequence and handoff validation over existing public stage contracts
  - added deterministic flow runner plus explicit blocked, escalated, approval-required, defer, retry, revalidate, recover, terminate-and-replan, and clarification routing
  - added orchestration-local lifecycle state and compact ordered trace events
- Validation: targeted orchestrator pytest files passed and full `python -m pytest -q` passed with 88 tests
- Current state: Phase 6A orchestrator skeleton now sequences existing stage contracts without taking over business logic or interface semantics
- Next step: build the remaining Phase 6 CLI-first truthful operator surface on top of the orchestrator outputs
- Files:
  - jeff/orchestrator/flows.py
  - jeff/orchestrator/validation.py
  - jeff/orchestrator/routing.py
  - jeff/orchestrator/runner.py
  - tests/test_orchestrator_failure_routing.py

  ## 2026-04-11 10:00 - TASK: M-006B - Added CLI-first truthful operator surface

- Scope: Phase 6B interface layer, CLI session scope, truthful read surfaces, and operator-facing tests
- Done:
  - added separate `jeff.interface` package with one-shot and interactive CLI facades over existing backend contracts
  - added local session scope handling for project, work unit, and run without mutating canonical state
  - added truthful `show`, `trace`, `lifecycle`, and request-receipt surfaces plus JSON views that preserve truth, support, derived, and telemetry distinctions
  - added CLI-focused tests for scope safety, semantic preservation, machine-readable JSON views, and live run visibility over orchestrator outputs
- Validation: targeted CLI pytest files passed and full `python -m pytest -q` passed with 101 tests
- Current state: Phase 6B CLI-first operator surface now exists as a separate interface layer without GUI, API bridge, or hidden control-plane semantics
- Next step: decide the next post-Phase-6 slice for packaging, integration, or additional operator capabilities
- Files:
  - jeff/interface/commands.py
  - jeff/interface/cli.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - tests/test_cli_truthfulness.py

  ## 2026-04-11 10:16 - TASK: M-007A - Phase 7A backbone hardening

- Scope: Phase 7A anti-drift coverage, bounded acceptance slices, and CLI/orchestrator truthfulness hardening
- Done:
  - added anti-drift tests for state/container invariants, governance boundaries, memory truth separation, orchestrator non-synthesis, and CLI semantic preservation
  - added bounded acceptance tests for a lawful backbone flow, an approval-gated stop flow, wrong-scope rejection, and CLI inspect/trace/lifecycle alignment
  - fixed CLI request JSON rendering, scoped run lookup rejection, ambiguous run lookup rejection, and evaluation stage semantic ownership in interface projections
  - noted that evaluation is now reported as Cognitive in operator views even though the current implementation file still lives under `jeff/action/`
  - kept GUI, broad API bridge, advanced memory backend, and autonomous continuation explicitly deferred with no new semantic layer added
- Validation: targeted hardening suite passed with 16 tests; full `python -m pytest -q` passed with 117 tests
- Current state: the v1 backbone is now acceptance-covered and hardened without widening post-Phase-6 scope
- Next step: continue only with bounded v1 follow-up work that preserves the current deferral boundary
- Files:
  - tests/test_antidrift_semantic_boundaries.py
  - tests/test_acceptance_backbone_flow.py
  - tests/test_acceptance_truthfulness.py
  - tests/test_acceptance_scope_isolation.py
  - tests/test_acceptance_cli_orchestrator_alignment.py
  - jeff/interface/commands.py
  - jeff/interface/json_views.py

## 2026-04-11 10:29 - TASK: M-007B - startup and packaging

- Scope: Phase 7B package entrypoint, demo bootstrap, startup docs, and smoke coverage
- Done:
  - added a stable `python -m jeff` entrypoint plus package script wiring in `pyproject.toml`
  - added explicit in-memory demo bootstrap and startup preflight checks for the current CLI-first surface
  - added `README.md` with truthful quickstart, test commands, current scope, and explicit deferrals
  - added bootstrap and CLI entry smoke tests for help, one-shot commands, quickstart paths, and clear startup failures
- Validation: `python -m pytest -q tests/test_bootstrap_smoke.py tests/test_cli_entry_smoke.py tests/test_quickstart_paths.py` passed with 12 tests; full `python -m pytest -q` passed with 129 tests
- Current state: Jeff now has a documented operator-ready start path over the existing in-memory v1 backbone with no new semantic layer added
- Next step: continue only with bounded v1 follow-up work that preserves the current deferred boundaries
- Files:
  - pyproject.toml
  - README.md
  - jeff/main.py
  - jeff/__main__.py
  - jeff/bootstrap.py
  - tests/test_bootstrap_smoke.py
  - tests/test_cli_entry_smoke.py
  - tests/test_quickstart_paths.py

## 2026-04-11 10:45 - TASK: M-007C - Evaluation layer alignment cleanup

- Scope: Cognitive-layer relocation of evaluation plus import, ownership, and note cleanup
- Done:
  - moved the active evaluation implementation to `jeff/cognitive/evaluation.py`
  - removed evaluation exports from `jeff.action` so Action now exposes execution and outcome only
  - updated orchestrator, bootstrap, and test imports to resolve evaluation from Cognitive
  - removed the README caveat about evaluation still living under `jeff/action/evaluation.py` and added alignment tests
- Validation: `python -m pytest -q tests/test_evaluation_rules.py tests/test_action_stage_boundaries.py tests/test_orchestrator_handoff_validation.py tests/test_orchestrator_failure_routing.py tests/test_acceptance_cli_orchestrator_alignment.py tests/test_evaluation_layer_alignment.py` passed with 23 tests; full `python -m pytest -q` passed with 132 tests
- Current state: evaluation now lives under Cognitive with unchanged semantics and no remaining active README mismatch note
- Next step: continue only with bounded follow-up work that preserves the current v1 architecture and deferral boundaries
- Files:
  - jeff/cognitive/evaluation.py
  - jeff/cognitive/__init__.py
  - jeff/action/__init__.py
  - jeff/action/types.py
  - jeff/orchestrator/runner.py
  - jeff/orchestrator/routing.py
  - jeff/orchestrator/validation.py
  - tests/test_evaluation_layer_alignment.py

## 2026-04-11 11:19 - TASK: M-007D - Added repo and module handoff surfaces

- Scope: repo-level and module-level continuation handoffs for the current Jeff v1 baseline
- Done:
  - added `handoffs/system/REPO_HANDOFF.md` with startup path, canonical doc entrypoints, module handoff index, current reality, and deferred boundaries
  - added module handoffs for `jeff.core`, `jeff.governance`, `jeff.cognitive`, `jeff.action`, `jeff.memory`, `jeff.orchestrator`, and `jeff.interface`
  - kept handoffs subordinate to `v1_doc/` and omitted an optional `jeff/contracts/HANDOFF.md` because the package remains a thin support surface
- Validation: handoff links, ownership statements, and startup wording were checked against `README.md`, `v1_doc/`, and the current package layout; `python -m pytest -q` passed with 132 tests
- Current state: the repo now has local continuation surfaces for the implemented major layers without introducing new semantic authority
- Next step: keep these handoffs updated only when local implementation reality changes materially
- Files:
  - handoffs/system/REPO_HANDOFF.md
  - jeff/core/HANDOFF.md
  - jeff/governance/HANDOFF.md
  - jeff/cognitive/HANDOFF.md
  - jeff/action/HANDOFF.md
  - jeff/memory/HANDOFF.md
  - jeff/orchestrator/HANDOFF.md
  - jeff/interface/HANDOFF.md  

## 2026-04-11 11:26 - TASK: M-007E - Reorganized tests by family and layer

- Scope: test-suite structure under `tests/` for family buckets, layer ownership, and cross-layer boundaries
- Done:
  - moved smoke, acceptance, and anti-drift tests into dedicated family directories
  - redistributed layer-owned tests under `tests/unit/core`, `governance`, `cognitive`, `action`, `memory`, `orchestrator`, and `interface`
  - moved cross-layer boundary tests into `tests/integration`
  - moved shared subprocess and CLI builders into `tests/fixtures` and updated helper imports
  - updated the README smoke command to match the new paths
- Validation: `python -m pytest -q tests/smoke` passed with 12 tests; `python -m pytest -q tests/unit/core tests/unit/interface` passed with 29 tests; `python -m pytest -q tests/acceptance tests/integration` passed with 23 tests; `python -m pytest -q tests/antidrift tests/unit/orchestrator` passed with 22 tests; `python -m pytest -q` passed with 132 tests
- Current state: the test suite now matches the repo's test-family and layer-ownership model without changing test semantics
- Next step: keep new tests in the matching family/layer bucket as the suite grows
- Files:
  - tests/smoke/
  - tests/acceptance/
  - tests/antidrift/
  - tests/unit/
  - tests/integration/
  - tests/fixtures/
  - README.md  

## 2026-04-11 11:51 - TASK: M-007F - CLI usability cleanup for operator flow

- Scope: CLI operator usability, command guidance, and shell readability without backend semantic changes
- Done:
  - added `/run list` for truthful run discovery inside current project/work scope
  - improved missing-scope and unknown-ID guidance for `/inspect`, `/project use`, `/work use`, and `/run use`
  - clarified `/help` and shell startup text so the CLI reads as a command-driven slash-command surface
  - added bounded prompt/error readability helpers with ANSI color support and plain-text fallback
  - updated README demo commands and added targeted CLI usability tests
- Validation: `python -m pytest -q tests/unit/interface tests/smoke/test_cli_entry_smoke.py` passed with 24 tests; `python -m pytest -q tests/acceptance/test_acceptance_cli_orchestrator_alignment.py tests/acceptance/test_acceptance_truthfulness.py` passed with 4 tests; `python -m pytest -q` passed with 139 tests
- Current state: the CLI is easier to navigate and read while preserving existing backend meaning and truth labels
- Next step: keep future CLI refinements bounded to operator usability unless canon explicitly expands the interface surface
- Files:
  - jeff/interface/commands.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - jeff/main.py
  - tests/unit/interface/test_cli_usability.py
  - README.md

## 2026-04-11 12:03 - TASK: M-007G - Work-unit-first automatic run handling

- Scope: CLI run resolution, lawful auto-create wiring, and work-unit-first operator flow
- Done:
  - added deterministic auto-run resolution so `/inspect` uses the current run, auto-selects the most recent existing run in the selected work unit, or creates a new run when none exists
  - wired automatic new-run creation through the existing Core `create_run` transition path instead of direct interface mutation
  - kept `/show`, `/trace`, and `/lifecycle` historical: they can auto-bind an existing run but do not create new runs
  - updated help, scope guidance, and README so normal flow is project -> work unit -> `/inspect`, with manual run commands positioned as history/debug tools
  - added fixture support and targeted interface tests for auto-bind, lawful auto-create, no-create history commands, and run-scope clearing
- Validation: `python -m pytest -q tests/unit/interface tests/smoke/test_cli_entry_smoke.py` passed with 30 tests; `python -m pytest -q tests/acceptance/test_acceptance_cli_orchestrator_alignment.py tests/acceptance/test_acceptance_truthfulness.py tests/acceptance/test_acceptance_scope_isolation.py` passed with 7 tests; `python -m pytest -q` passed with 145 tests
- Current state: normal CLI work is now work-unit-first while `run` remains a real canonical container for history, trace, lifecycle, and manual switching
- Next step: keep future CLI flow changes subordinate to canonical run truth and transition-only mutation
- Files:
  - jeff/interface/commands.py
  - jeff/interface/cli.py
  - jeff/interface/render.py
  - tests/fixtures/cli.py
  - tests/unit/interface/test_cli_run_resolution.py
  - README.md

## 2026-04-11 19:29 - Added infrastructure model adapter Slice A

- Scope: infrastructure model adapter foundations
- Done:
  - added standalone `jeff.infrastructure.model_adapters` package with typed request, response, usage, and status models
  - added narrow adapter contract, explicit registry, and adapter-layer error classes
  - added deterministic fake provider with consistent timeout and malformed-output failure behavior
  - added truthful `jeff/infrastructure/HANDOFF.md` for the new module
  - added focused pytest coverage for types, registry, and fake adapter behavior
- Validation: targeted adapter tests passed and full `python -m pytest -q` passed with 158 tests
- Current state: Slice A infrastructure adapter foundations exist as a standalone module with no real providers or runtime wiring yet
- Next step: add the next bounded infrastructure slice without leaking provider logic into semantic layers
- Files:
  - jeff/infrastructure/model_adapters/types.py
  - jeff/infrastructure/model_adapters/registry.py
  - jeff/infrastructure/model_adapters/providers/fake.py
  - jeff/infrastructure/HANDOFF.md
  - tests/unit/infrastructure/test_fake_model_adapter.py  

## 2026-04-11 19:37 - Added infrastructure model adapter Slice B

- Scope: infrastructure model adapter factory, telemetry, and Ollama provider
- Done:
  - added normalized adapter telemetry event model plus request/response-to-telemetry mapping
  - added explicit adapter factory with fail-closed fake and Ollama provider construction
  - added minimal standard-library Ollama HTTP adapter with normalized usage and failure mapping
  - updated `jeff/infrastructure/HANDOFF.md` to reflect Slice B reality and remaining deferrals
  - added focused pytest coverage for factory, telemetry, and Ollama adapter behavior
- Validation: targeted infrastructure adapter tests passed and full `python -m pytest -q` passed with 170 tests
- Current state: Slice B extends the standalone infrastructure adapter module with observability, construction, and one real provider while leaving runtime integration deferred
- Next step: add future infrastructure-only provider or wiring slices without leaking provider logic into semantic layers
- Files:
  - jeff/infrastructure/model_adapters/telemetry.py
  - jeff/infrastructure/model_adapters/factory.py
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - jeff/infrastructure/HANDOFF.md
  - tests/unit/infrastructure/test_ollama_model_adapter.py

## 2026-04-11 19:50 - Added infrastructure runtime assembly Slice C1

- Scope: infrastructure runtime wiring and explicit bootstrap assembly hook
- Done:
  - added `jeff/infrastructure/runtime.py` with runtime config, infrastructure services, and explicit registry assembly
  - exported the new runtime surface from `jeff.infrastructure`
  - added a minimal bootstrap helper that assembles infrastructure services from an explicit config object
  - updated `jeff/infrastructure/HANDOFF.md` to reflect Slice C1 runtime reality
  - added deterministic tests for runtime services and bootstrap assembly behavior
- Validation: targeted runtime tests passed and full `python -m pytest -q` passed with 178 tests
- Current state: Jeff can now explicitly construct and hold adapter infrastructure at runtime without integrating adapters into semantic layers
- Next step: keep future adapter usage or integration slices downstream of this assembly boundary without leaking provider logic into semantics
- Files:
  - jeff/infrastructure/runtime.py
  - jeff/infrastructure/__init__.py
  - jeff/bootstrap.py
  - tests/unit/infrastructure/test_runtime_services.py
  - tests/integration/test_bootstrap_model_adapters.py

## 2026-04-11 20:44 - Added research synthesis Slice C2a

- Scope: cognitive research synthesis over prepared evidence using the model adapter stack
- Done:
  - added bounded prepared-evidence research models and synthesis-only validation in `jeff/cognitive/research.py`
  - added provider-neutral model-request builder for research synthesis with explicit JSON output contract
  - added synthesis entry points for direct adapter use and infrastructure-runtime-backed adapter resolution
  - preserved the earlier `ResearchResult` contract for existing stage and orchestrator tests
  - added deterministic unit and integration tests for synthesis success, fail-closed validation, and runtime-backed adapter use
- Validation: targeted research synthesis tests passed and full `python -m pytest -q` passed with 187 tests
- Current state: Jeff now has a first bounded semantic-layer use of model adapters for research synthesis only, starting from explicit evidence and ending in a validated research artifact
- Next step: keep future research slices bounded to source acquisition or downstream integration without widening synthesis ownership
- Files:
  - jeff/cognitive/research.py
  - jeff/cognitive/__init__.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/integration/test_research_synthesis_with_runtime.py
  - handoffs/system/WORK_STATUS_UPDATE_2026-04-11_2044.md   

## 2026-04-11 20:56 - Added document research Slice C2b

- Scope: bounded local-document source acquisition and evidence extraction for research
- Done:
  - extended `ResearchRequest` with explicit bounded document-source inputs and limits
  - added `jeff/cognitive/research_documents.py` for deterministic local document collection and keyword-overlap evidence extraction
  - added a thin end-to-end `run_document_research(...)` helper that feeds collected evidence into the existing C2a synthesis path
  - kept provenance explicit through stable document source IDs, path locators, and source-bound evidence refs
  - added deterministic unit and integration tests for explicit paths, bounded limits, safe skipping, and runtime-backed end-to-end synthesis
- Validation: targeted document-research tests passed and full `python -m pytest -q` passed with 197 tests
- Current state: Jeff can now build bounded document sources and evidence packs from explicit local paths and feed them into the existing research synthesis path
- Next step: add future research source providers only as bounded slices that keep provenance explicit and stay downstream of the shared pipeline
- Files:
  - jeff/cognitive/research.py
  - jeff/cognitive/research_documents.py
  - jeff/cognitive/__init__.py
  - tests/unit/cognitive/test_research_documents.py
  - tests/integration/test_document_research_end_to_end.py

## 2026-04-11 21:07 - Refactored cognitive research into submodule package

- Scope: cognitive research module structure and ownership cleanup
- Done:
  - replaced the flat `jeff/cognitive/research.py` and `research_documents.py` files with a dedicated `jeff/cognitive/research/` package
  - split research contracts, synthesis behavior, document acquisition, errors, and legacy compatibility into bounded files
  - preserved the existing public research surface through package exports and updated `jeff.cognitive` re-exports
  - isolated the still-needed legacy `ResearchResult` contract into `research/legacy.py`
  - added a focused public-surface guard test and kept existing research tests green
- Validation: targeted research refactor tests passed and full `python -m pytest -q` passed with 199 tests
- Current state: research now has a cleaner package structure with stable behavior and clearer ownership boundaries
- Next step: keep future research work inside the new package slices without reintroducing blob modules or leaking provider logic
- Files:
  - jeff/cognitive/research/__init__.py
  - jeff/cognitive/research/contracts.py
  - jeff/cognitive/research/synthesis.py
  - jeff/cognitive/research/documents.py
  - jeff/cognitive/research/legacy.py

## 2026-04-11 21:21 - Added web research Slice C2c

- Scope: bounded web source acquisition and evidence extraction for research
- Done:
  - extended `ResearchRequest` with explicit bounded web-query inputs and limits
  - added `jeff/cognitive/research/web.py` for bounded search, fetch, provenance normalization, and deterministic evidence extraction
  - added thin `run_web_research(...)` wiring into the existing C2a synthesis path
  - exported the new web research surface through `jeff.cognitive.research` and `jeff.cognitive`
  - added deterministic unit and integration tests with mocked web acquisition boundaries
- Validation: targeted web-research tests passed and full `python -m pytest -q` passed with 209 tests
- Current state: Jeff can now acquire bounded web sources from explicit queries, normalize them into source-aware evidence packs, and feed that support into the existing research synthesis path
- Next step: keep future research-source slices bounded and explicit without widening into autonomy, persistence, or memory handoff
- Files:
  - jeff/cognitive/research/contracts.py
  - jeff/cognitive/research/web.py
  - jeff/cognitive/research/__init__.py
  - tests/unit/cognitive/test_research_web.py
  - tests/integration/test_web_research_end_to_end.py

## 2026-04-11 21:29 - Added research artifact persistence Slice C2d

- Scope: bounded persistence for validated research artifacts as durable support records
- Done:
  - added `jeff/cognitive/research/persistence.py` with `ResearchArtifactRecord`, `ResearchArtifactStore`, and record-building/persisting helpers
  - added thin document and web run-and-persist helpers built on the existing bounded research paths
  - exported the new persistence surface through `jeff.cognitive.research` and `jeff.cognitive`
  - kept persisted records explicit, JSON-backed, human-inspectable, and separate from memory and truth
  - added deterministic unit and integration tests for round-trip save/load, filtered listing, and document/web persistence flow
- Validation: targeted persistence tests passed and full `python -m pytest -q` passed with 218 tests
- Current state: Jeff can now persist validated research artifacts as bounded local support records with scope, provenance, sources, and evidence preserved
- Next step: keep future reuse or handoff slices downstream of these stored support artifacts without collapsing them into memory or truth
- Files:
  - jeff/cognitive/research/persistence.py
  - jeff/cognitive/research/__init__.py
  - jeff/cognitive/__init__.py
  - tests/unit/cognitive/test_research_persistence.py
  - tests/integration/test_research_persistence_flow.py

## 2026-04-11 21:39 - Added research-to-memory handoff Slice C2e

- Scope: selective handoff from validated research artifacts into the current memory write pipeline
- Done:
  - added `jeff/cognitive/research/memory_handoff.py` with bounded handoff input, pre-handoff gate, and thin memory-pipeline delegation
  - added persisted-record handoff support without redesigning research persistence or memory
  - exported the new handoff surface through `jeff.cognitive.research` and `jeff.cognitive`
  - kept memory write / reject / defer decisions owned by the existing `jeff.memory` write pipeline
  - added deterministic unit and integration tests for write, reject, and defer outcomes over document and web research flows
- Validation: targeted handoff tests passed and full `python -m pytest -q` passed with 226 tests
- Current state: Jeff can now selectively distill validated research artifacts into bounded inputs for the current memory layer while keeping research artifacts, memory, and truth separate
- Next step: keep future downstream research reuse bounded without redesigning memory or collapsing support artifacts into canonical truth
- Files:
  - jeff/cognitive/research/memory_handoff.py
  - jeff/cognitive/research/__init__.py
  - jeff/cognitive/__init__.py
  - tests/unit/cognitive/test_research_memory_handoff.py
  - tests/integration/test_research_memory_handoff_flow.py

## 2026-04-11 21:48 - Updated cognitive and research handoffs

- Scope: cognitive module and research submodule continuation handoffs
- Done:
  - updated `jeff/cognitive/HANDOFF.md` to reflect the current research package reality and point downward to a dedicated research handoff
  - added `jeff/cognitive/research/HANDOFF.md` using the required submodule structure from `HANDOFF_STRUCTURE.md`
  - aligned both handoffs with the implemented research slices: synthesis, documents, web, persistence, memory handoff, and bounded legacy support
  - validated that the handoff text matches the current `jeff/cognitive/research/` file layout
- Validation: checked `HANDOFF_STRUCTURE.md`, current cognitive/research package layout, and handoff cross-links; no code behavior changes were made
- Current state: cognitive and research handoffs now match the current repo layout and continuation reality
- Next step: keep future research changes updating the local research handoff first, then the parent cognitive handoff if the module view changes
- Files:
  - jeff/cognitive/HANDOFF.md
  - jeff/cognitive/research/HANDOFF.md

## 2026-04-11 22:35 - Added CLI research interface slice R1

- Scope: interface research command surface
- Done:
  - added `/research docs` and `/research web` command handling with explicit quoted-question parsing and optional `--handoff-memory`
  - added lawful scope helpers for current-scope research and ad-hoc anchoring into the built-in `general_research` project through transitions
  - added truthful research JSON and human renderers with support-vs-truth separation and explicit memory handoff outcomes
  - added unit and integration coverage for parsing, scope resolution, persistence, rendering, JSON output, and handoff behavior
- Validation: `python -m pytest -q tests\unit\interface\test_research_commands.py tests\integration\test_cli_research_flow.py` passed; full `python -m pytest -q` passed with 243 tests
- Current state: Jeff CLI now exposes a usable thin research command family over the existing backend slices without adding orchestrator-owned research flow
- Next step: keep future research operator work bounded to truthful presentation and lawful backend integration
- Files:
  - jeff/interface/commands.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - jeff/interface/HANDOFF.md
  - tests/unit/interface/test_research_commands.py
  - tests/integration/test_cli_research_flow.py

## 2026-04-11 23:04 - Added explicit runtime config and startup wiring for research CLI

- Scope: infrastructure runtime config and startup composition
- Done:
  - added typed `jeff.runtime.toml` config loading with explicit runtime, adapter, purpose override, and research sections
  - extended infrastructure runtime assembly with purpose-based adapter lookup and config-to-adapter construction
  - wired startup to load local runtime config when present and attach research runtime dependencies into the CLI context
  - added deterministic tests for config parsing, bootstrap behavior, CLI research runtime flow, and Ollama context-length mapping
- Validation: `python -m pytest -q tests\unit\infrastructure\test_runtime_config.py tests\integration\test_bootstrap_runtime_config.py tests\integration\test_cli_research_runtime_config.py` passed; full `python -m pytest -q` passed with 256 tests
- Current state: Jeff startup can now remain demo-safe without config and becomes research-runnable through explicit local runtime config when `jeff.runtime.toml` is present
- Next step: keep future runtime work bounded to explicit config evolution and downstream stage integration without adding CLI-owned model switching
- Files:
  - jeff/infrastructure/config.py
  - jeff/infrastructure/runtime.py
  - jeff/infrastructure/model_adapters/factory.py
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - jeff/bootstrap.py
  - tests/unit/infrastructure/test_runtime_config.py
  - tests/integration/test_bootstrap_runtime_config.py
  - tests/integration/test_cli_research_runtime_config.py

## 2026-04-12 10:54 â€” Repaired research provenance consistency

- Scope: cognitive research provenance validation and persistence/render guards
- Done:
  - added explicit provenance validation for findings, evidence items, source ids, and source items
  - enforced provenance checks after synthesis and during research artifact record build/save/load
  - guarded operator-facing research JSON projection from rendering invalid persisted linkage
  - added unit and integration regression tests for broken and valid provenance flows
- Validation: `python -m pytest -q tests\unit\cognitive\test_research_provenance_consistency.py tests\integration\test_research_provenance_consistency_flow.py` and full `python -m pytest -q` both passed
- Current state: invalid research source linkage now fails closed before persistence or operator-facing projection
- Next step: continue Research v2 Phase 01 repairs without widening beyond current v1 behavior
- Files:
  - jeff/cognitive/research/contracts.py
  - jeff/cognitive/research/synthesis.py
  - jeff/cognitive/research/persistence.py
  - jeff/interface/json_views.py
  - tests/unit/cognitive/test_research_provenance_consistency.py
  - tests/integration/test_research_provenance_consistency_flow.py

## 2026-04-12 11:00 â€” Repaired research source transparency in operator output

- Scope: interface research result projection and CLI rendering
- Done:
  - resolved finding source refs into bounded real source objects in research JSON output
  - exposed compact support source entries with source_id, source_type, title, and locator
  - updated CLI research rendering to show title plus locator instead of opaque source ids
  - added unit and integration tests for source-transparent text and JSON output
- Validation: `python -m pytest -q tests\unit\interface\test_research_source_transparency.py tests\integration\test_cli_research_source_transparency.py` and full `python -m pytest -q` both passed
- Current state: operator-facing research output now shows real cited sources while keeping support separate from truth
- Next step: continue bounded Research v2 Phase 01 repairs without widening research semantics
- Files:
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - tests/unit/interface/test_research_source_transparency.py
  - tests/integration/test_cli_research_source_transparency.py
  - tests/integration/test_cli_research_flow.py                    

## 2026-04-12 11:09 â€” Repaired research snippet cleaning and publish-date support

- Scope: cognitive research web-source support quality and interface metadata projection
- Done:
  - added bounded web snippet cleaning to reduce HTML, CSS, and JS sludge
  - added nullable `published_at` support on research source items with strict bounded extraction from fetched metadata
  - carried cleaned snippet and published date through persistence, JSON projection, and CLI rendering
  - added unit and integration tests for cleaning, publish-date extraction, persistence compatibility, and CLI metadata output
- Validation: `python -m pytest -q tests\unit\cognitive\test_research_source_cleaning.py tests\unit\cognitive\test_research_publish_date_support.py tests\integration\test_cli_research_source_metadata.py` and full `python -m pytest -q` both passed
- Current state: web research support is cleaner, publish dates surface when confidently available, and unknown dates remain explicit `null`/omitted in CLI
- Next step: continue bounded Research v2 Phase 01 repairs without widening acquisition architecture
- Files:
  - jeff/cognitive/research/contracts.py
  - jeff/cognitive/research/web.py
  - jeff/interface/json_views.py
  - jeff/interface/render.py
  - tests/unit/cognitive/test_research_source_cleaning.py
  - tests/unit/cognitive/test_research_publish_date_support.py
  - tests/integration/test_cli_research_source_metadata.py

## 2026-04-12 11:45 â€” Repaired research synthesis runtime timeout and error transparency

- Scope: research synthesis invocation behavior and CLI/json failure surfacing
- Done:
  - removed the hardcoded research request timeout so runtime-configured adapter timeouts remain authoritative
  - added bounded research runtime error classification for timeout, connection, provider HTTP, malformed output, unsupported runtime config, and generic invocation failure
  - exposed structured research error JSON for failed research commands in json mode
  - added unit and integration tests for runtime error mapping, timeout handling, and CLI failure output
- Validation: `python -m pytest -q tests\unit\cognitive\test_research_synthesis_runtime_errors.py tests\integration\test_cli_research_synthesis_runtime_errors.py tests\unit\cognitive\test_research_synthesis.py` and full `python -m pytest -q` both passed
- Current state: research synthesis now respects configured adapter timeout behavior and surfaces bounded useful failure detail to operators
- Next step: continue bounded Research v2 Phase 01 repairs without widening research semantics or runtime architecture
- Files:
  - jeff/cognitive/research/synthesis.py
  - jeff/cognitive/research/errors.py
  - jeff/infrastructure/model_adapters/errors.py
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - jeff/interface/commands.py
  - jeff/interface/json_views.py
  - tests/unit/cognitive/test_research_synthesis_runtime_errors.py
  - tests/integration/test_cli_research_synthesis_runtime_errors.py

## 2026-04-12 11:53 â€” Repaired live CLI research failure surfacing

- Scope: live CLI research runtime failure output in interactive text and `/json on` modes
- Done:
  - added CLI-side rendering helper for bounded research runtime failures
  - updated `JeffCLI.run_interactive` to surface classified research failures instead of propagating them raw
  - updated the real interactive shell loop to emit structured `research_error` JSON in `/json on` mode and bounded human-readable detail otherwise
  - added unit and integration tests for live failure surfacing and unchanged success behavior
- Validation: `python -m pytest -q tests\unit\interface\test_research_failure_json_mode.py tests\integration\test_cli_research_failure_surface.py` and full `python -m pytest -q` both passed
- Current state: live CLI research failures now surface the backend’s bounded runtime detail instead of reverting to a generic message
- Next step: continue bounded Research v2 Phase 01 repairs without widening CLI or research semantics
- Files:
  - jeff/interface/cli.py
  - jeff/main.py
  - tests/unit/interface/test_research_failure_json_mode.py
  - tests/integration/test_cli_research_failure_surface.py

## 2026-04-12 13:56 â€” Added research synthesis citation-key remap

- Scope: research synthesis contract hardening for citation handling
- Done:
  - replaced model-facing raw `source_id` citations with deterministic request-local `S1..Sn` keys in research synthesis requests
  - added dynamic allowed-key JSON schema constraints for `findings[].source_refs`
  - remapped returned citation keys back to real internal `source_id` values before artifact construction and provenance validation
  - added unit and integration coverage for citation-key generation, model-facing projection, remap success, and fail-closed invented-key drift
  - updated existing research synthesis test fixtures to return citation keys while preserving final real-source artifact semantics
- Validation: targeted citation-key pytest files passed; full `pytest -q` passed with 312 passed
- Current state: research synthesis now uses bounded citation keys for the model and preserves real internal source identity after deterministic remap
- Next step: later slices can address malformed-output repair and other robustness work without changing this remap contract
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/unit/cognitive/test_research_synthesis_citation_keys.py
  - tests/integration/test_research_synthesis_citation_key_flow.py   

## 2026-04-12 14:11 â€” Added bounded research malformed-output repair pass

- Scope: research synthesis malformed-output recovery
- Done:
  - added one bounded repair attempt for research synthesis when the primary adapter call fails with `malformed_output`
  - kept the repair prompt formatting-only and limited it to malformed content, exact schema, and allowed citation keys
  - preserved Slice A citation-key remap and fail-closed provenance validation after successful repair
  - added unit and integration coverage for successful repair, failed repair, one-attempt behavior, and non-malformed no-repair paths
  - refined malformed adapter errors to carry bounded raw output needed for repair input
- Validation: targeted repair-path pytest files passed; full `pytest -q` passed with 322 passed
- Current state: research synthesis can recover from one formatting-only malformed-output failure without changing successful artifact semantics
- Next step: later slices can build on this without adding retry loops or changing research semantics
- Files:
  - jeff/cognitive/research/synthesis.py
  - jeff/infrastructure/model_adapters/errors.py
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/integration/test_research_synthesis_repair_flow.py

## 2026-04-12 14:20 â€” Added separate research repair adapter override

- Scope: infrastructure runtime/config wiring for research repair adapter selection
- Done:
  - added optional `purpose_overrides.research_repair` parsing and typed config support
  - extended runtime adapter lookup so `research_repair` can resolve separately and still fall back cleanly
  - wired research malformed-output repair to use a separate repair adapter when configured and the primary adapter otherwise
  - added unit and integration coverage for repair override resolution, fallback behavior, and unchanged artifact semantics
  - updated the example `jeff.runtime.toml` and infrastructure handoff to show the new optional override
- Validation: targeted runtime/repair pytest files passed; full `pytest -q` passed with 328 passed
- Current state: research synthesis repair can use a separately configured formatter/repair adapter without changing default behavior
- Next step: later slices can build on this narrow split without adding broader capability routing
- Files:
  - jeff/infrastructure/config.py
  - jeff/infrastructure/runtime.py
  - jeff/cognitive/research/synthesis.py
  - tests/unit/infrastructure/test_runtime_purpose_overrides.py
  - tests/integration/test_research_synthesis_repair_flow.py

## 2026-04-12 14:49 â€” Added live research debug checkpoints for /mode debug

- Scope: bounded research-debug observability in the CLI
- Done:
  - added bounded research debug checkpoint emission through synthesis, repair, remap, and provenance stages
  - wired `/mode debug` to render progressive live research debug lines during interactive CLI runs
  - kept non-debug output compact and added debug events to JSON-mode research result/error payloads only when debug mode is active
  - added interface tests for bounded debug output, truncation, and debug/json coexistence
  - added integration coverage for live malformed-output repair streaming and later-stage provenance failure checkpoints
- Validation: targeted debug-mode pytest files passed; full `pytest -q` passed with 334 passed
- Current state: operators can now see bounded live research pipeline checkpoints in `/mode debug` without changing research semantics
- Next step: later slices can add more observability only if they stay bounded and avoid broad tracing-framework expansion
- Files:
  - jeff/cognitive/research/synthesis.py
  - jeff/interface/commands.py
  - jeff/interface/cli.py
  - tests/unit/interface/test_research_debug_mode.py
  - tests/integration/test_cli_research_debug_stream.py


## 2026-04-12 15:01 â€” Fixed post-validation research source linkage

- Scope: research downstream persistence, projection, and debug checkpoints
- Done:
  - added downstream debug checkpoints for artifact record build, store save/load, projection, and render
  - fixed document and web persist flows to reuse the same evidence pack for synthesis and persistence
  - wrapped malformed persisted-record linkage failures cleanly at load time
  - added unit and integration coverage for downstream source-linkage stability and debug streaming
- Validation: targeted downstream tests passed; full `pytest -q` passed
- Current state: valid post-remap research artifacts now keep consistent real source IDs through persistence and rendering, with bounded downstream debug visibility in `/mode debug`
- Next step: use the new downstream checkpoints to diagnose any remaining live research failures without widening research semantics
- Files:
  - jeff/cognitive/research/persistence.py
  - jeff/interface/commands.py
  - tests/unit/cognitive/test_research_post_validation_linkage.py
  - tests/integration/test_cli_research_post_validation_debug.py



## 2026-04-12 15:30 Pre-Phase-02 Research Refactor: COMPLETE

## Summary

Successfully implemented all three pre-Phase-02 refactors for Jeff's research subsystem. The refactor maintains 100% backward compatibility while preparing the codebase for Phase 02 improvements.

## What Was Done

### 1. Consolidated Debug Helpers ✅
- Moved shared debugging functions into `jeff/cognitive/research/debug.py`
- Removed 100 lines of duplicated code across 3 files
- Functions now imported from centralized location
- All debug tests passing (128 tests)

### 2. Extended SourceItem with Phase-02 Fields ✅
- Added 5 new optional fields to `SourceItem` dataclass:
  - `extractor_used` – tracks which extractor was used
  - `extraction_quality` – quality assessment
  - `fetched_at` – when content was retrieved
  - `domain` – source domain
  - `discovery_rank` – position in discovery order
- Validated `discovery_rank` to prevent silent bugs
- 100% backward compatible (all existing code unaffected)

### 3. Separated Discovery from Extraction ✅
- **Web sources**: Created `discover_web_sources()` and `extract_web_source()` as separate phases
- **Document sources**: Created `discover_document_sources()` and `extract_document_source()` as separate phases
- Clear boundaries enable Phase 02 to plug in new providers (SearXNG, Trafilatura, etc.)
- Behavior identical to before (all 128 research tests pass)

## Test Results

- **Total tests**: 350 passing ✅
  - 128 research tests (existing)
  - 12 refactor verification tests (new)
  - 210 other tests (unchanged)
- **Test suite duration**: 2.59s
- **Zero test failures**: 100% green

## Key Design Decisions

1. **Private intermediate types** – `_DiscoveredWebSource`, `_ExtractedWebSource`, etc. not exported
2. **Optional fields with None defaults** – Phase 02 will populate as needed
3. **Explicit composition** – Discovery and extraction composed explicitly in `collect_*_sources()`
4. **No provider abstraction yet** – Phase 02 will decide on abstraction model
5. **Validation for safety** – Added checks for `discovery_rank` to prevent silent errors

## Phase-02 Readiness

The refactor specifically enables Phase 02 to:

1. **Add SearXNG** for better web discovery without touching extraction
2. **Add Trafilatura** for better web extraction without touching discovery  
3. **Add fallbacks** (e.g., Crawl4AI) in extraction layer
4. **Add Unstructured** for document parsing (PDF, DOCX)
5. **Implement ranking** using new SourceItem fields
6. **Add capability routing** without rewriting the whole pipeline

## What Did NOT Change (Intentionally)

- Evidence pack structure
- Synthesis/repair logic
- CLI interface
- Persistence format
- Governance/approval flows
- Runtime/config ownership

## Files Modified

```
NEW:  jeff/cognitive/research/debug.py (+50 lines)
NEW:  tests/unit/cognitive/test_refactor_phase_02_readiness.py (+180 lines)
MOD:  jeff/cognitive/research/contracts.py (+20 lines)
MOD:  jeff/cognitive/research/web.py (+100 lines)
MOD:  jeff/cognitive/research/documents.py (+90 lines)
MOD:  jeff/cognitive/research/synthesis.py (-30 lines)
MOD:  jeff/cognitive/research/persistence.py (-50 lines)
MOD:  jeff/interface/commands.py (-20 lines)
MOD:  jeff/cognitive/research/__init__.py (+8 lines)
```

**Net effect**: ~350 lines of improved structure (mostly new code for clarity)

## Verification

All changes verified:
```bash
python -m pytest tests/ -v
# Result: 350 passed ✅
```

## Documentation

Full details available in:
- `REFACTOR_PHASE_02_READINESS_SUMMARY.md` – Complete technical summary
- Inline code comments – All refactored functions documented
- Test file – `test_refactor_phase_02_readiness.py` shows usage patterns

## Recommendation

**Status: READY FOR PHASE 02**

The research subsystem is now cleanly structured for Phase 02 work. All three refactors are complete, all tests pass, and the architecture supports the planned improvements without requiring rewrites.

Next steps: Phase 02 implementation can begin (SearXNG, Trafilatura, etc.) using the new discovery/extraction boundaries.  

## 2026-04-12 17:06 â€” Hardened research synthesis and repair prompts

- Scope: research synthesis prompt contract and malformed-output repair prompt
- Done:
  - simplified the primary synthesis prompt into a shorter structured JSON-only contract
  - removed the handwritten required-JSON-shape block and kept `json_schema` as the authoritative schema path
  - hardened system instructions and prompt wording against markdown, code fences, and extra prose
  - tightened repair prompt typing rules for `findings` and `finding.source_refs`
  - updated deterministic unit coverage for the new prompt contract
- Validation: targeted synthesis/repair prompt tests passed; full `pytest -q` passed
- Current state: research synthesis and repair prompts are shorter, stricter, citation-key safe, and still preserve the existing artifact semantics
- Next step: use live runtime results to judge whether additional bounded prompt cleanup is needed before any broader research-runtime changes
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/unit/cognitive/test_research_synthesis_citation_keys.py

  ## 2026-04-12 17:19 â€” Hardened research repair success boundary

- Scope: research malformed-output repair boundary and debug truthfulness
- Done:
  - added a root-shape gate for repaired JSON before `repair_pass_succeeded` is emitted
  - made schema-incomplete repaired JSON fail at the repair boundary instead of later artifact construction
  - updated debug flow so incomplete repair output emits `repair_pass_failed` with a bounded reason
  - added unit and integration coverage for missing root fields, wrong root types, and CLI debug behavior
- Validation: targeted repair-boundary tests passed; full `pytest -q` passed
- Current state: repair success now means the repaired JSON is schema-complete enough to proceed into artifact construction, while successful valid repair flows remain unchanged
- Next step: continue using live debug checkpoints to tighten any remaining misleading success boundaries without widening research semantics
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/unit/cognitive/test_research_synthesis_runtime_errors.py
  - tests/integration/test_research_synthesis_repair_flow.py

## 2026-04-12 17:33 â€” Unified research schema-completeness boundary

- Scope: research synthesis and repair success-boundary truthfulness
- Done:
  - replaced the repair-only root-shape check with one shared schema-completeness gate for progression
  - made primary synthesis emit `primary_synthesis_failed` instead of false success for schema-incomplete JSON
  - kept repair pass fail-closed and made `repair_pass_succeeded` depend on the same shared gate
  - added unit and integration coverage to ensure schema-incomplete payloads stop before citation remap and debug output stays truthful
- Validation: targeted synthesis-boundary tests passed; full `pytest -q` passed
- Current state: both primary and repair branches now require schema-complete research payloads before success is reported or citation remap begins
- Next step: continue tightening only misleading success boundaries while preserving existing research semantics and downstream validation
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/unit/cognitive/test_research_synthesis_runtime_errors.py
  - tests/integration/test_research_synthesis_repair_flow.py

## 2026-04-12 17:47 â€” Fixed repair-branch schema-incomplete debug surfacing

- Scope: research repair-branch debug truthfulness at the shared schema-completeness boundary
- Done:
  - normalized blank/invalid root-field gate failures into `ResearchSynthesisValidationError` inside the shared progression helper
  - ensured schema-incomplete repair payloads emit `repair_pass_failed` with `failure_class=schema_incomplete`
  - added deterministic coverage for blank-summary repair output and live CLI debug surfacing
- Validation: targeted repair/debug tests passed; full `pytest -q` passed
- Current state: schema-incomplete repair output now shows a truthful repair failure checkpoint with bounded reason before the final fail-closed error
- Next step: continue only small truthfulness fixes where live debug and final failure still diverge
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/integration/test_cli_research_debug_stream.py

## 2026-04-12 18:25 — Wired Ollama structured JSON requests

- Scope: infrastructure Ollama adapter JSON-mode request path
- Done:
  - switched Ollama JSON-mode requests from `/api/generate` prompt text to `/api/chat` messages
  - wired `ModelRequest.json_schema` through to Ollama `format` for structured outputs
  - kept non-JSON requests on the existing generate path
  - added unit and integration assertions for outgoing JSON payload shape, endpoint, and absence of an explicit `think` flag
- Validation: `pytest -q` passed (`366 passed`)
- Current state: Ollama JSON-mode requests now send real structured-output fields on the wire and the repo tests prove the payload shape
- Next step: address the next synthesis-boundary fix without changing research semantics yet
- Files:
  - jeff/infrastructure/model_adapters/providers/ollama.py
  - tests/unit/infrastructure/test_ollama_model_adapter.py
  - tests/integration/test_cli_research_runtime_config.py
  - tests/integration/test_cli_research_synthesis_runtime_errors.py

## 2026-04-12 18:48 — Extended bounded repair to schema-incomplete primary JSON

- Scope: research synthesis repair trigger and shared schema-completeness boundary
- Done:
  - extended the single repair pass to run for primary `schema_incomplete` JSON as well as `malformed_output`
  - reused the existing repair request path by serializing near-miss primary JSON into the same repair prompt flow
  - tightened the shared progression validator to catch nested finding field/type mismatches before any false success checkpoint
  - updated unit and integration tests for repair triggering, debug sequencing, and unchanged malformed-output behavior
- Validation: `pytest -q` passed (`374 passed`)
- Current state: primary near-miss JSON now gets one bounded normalization repair attempt with truthful debug checkpoints and no extra retries
- Next step: move to the next smallest synthesis-boundary fix without widening research semantics
- Files:
  - jeff/cognitive/research/synthesis.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/unit/cognitive/test_research_synthesis_repair_pass.py
  - tests/unit/cognitive/test_research_synthesis_runtime_errors.py
  - tests/integration/test_research_synthesis_repair_flow.py
  - tests/integration/test_cli_research_debug_stream.py

## 2026-04-13 19:36 — Added Step 1 bounded syntax contract foundation

- Scope: `jeff.cognitive.research` Slice 1 contract-only transition work
- Done:
  - added `Step1BoundedFinding` and `Step1BoundedArtifact` contract types in research contracts
  - added `bounded_syntax.py` with canonical Step 1 section constants and fail-closed structural validators
  - added focused unit tests for valid structure, malformed sections, citation-key shape, duplicate citations, empty required content, and contract boundaries
  - confirmed the live synthesis request remains the current JSON-first runtime path
- Validation: passed `pytest tests/unit/cognitive/test_research_bounded_syntax.py tests/unit/cognitive/test_research_synthesis.py tests/unit/cognitive/test_research_synthesis_citation_keys.py tests/unit/cognitive/test_research_public_surface.py`
- Current state: Step 1 contract foundations exist locally in research without switching the active synthesis flow
- Next step: implement Slice 2 deterministic bounded-text transformer without changing downstream remap/provenance behavior
- Files:
  - jeff/cognitive/research/contracts.py
  - jeff/cognitive/research/bounded_syntax.py
  - tests/unit/cognitive/test_research_bounded_syntax.py

## 2026-04-13 19:43 — Added deterministic Step 2 bounded-text transformer

- Scope: `jeff.cognitive.research` Slice 2 deterministic transformation layer
- Done:
  - added `deterministic_transformer.py` to parse Step 1 bounded text into a citation-key candidate research payload
  - added `validators.py` for fail-closed candidate payload validation with exact field and citation-key checks
  - added focused unit tests for valid transform, missing sections, malformed findings, malformed citation keys, duplicate citations, ambiguous structure, and non-invention boundaries
  - confirmed the live synthesis request path remains the current JSON-first runtime
- Validation: passed `pytest tests/unit/cognitive/test_research_deterministic_transformer.py tests/unit/cognitive/test_research_bounded_syntax.py tests/unit/cognitive/test_research_synthesis.py tests/unit/cognitive/test_research_synthesis_citation_keys.py tests/unit/cognitive/test_research_public_surface.py`
- Current state: Step 2 deterministic parsing and candidate-payload validation exist locally without changing the active synthesis flow
- Next step: wire Step 1 and Step 2 into synthesis as the primary path in Slice 3
- Files:
  - jeff/cognitive/research/deterministic_transformer.py
  - jeff/cognitive/research/validators.py
  - tests/unit/cognitive/test_research_deterministic_transformer.py

## 2026-04-13 19:56 — Wired Step 1 and Step 2 into live research synthesis

- Scope: `jeff.cognitive.research` Slice 3 primary-path transition
- Done:
  - switched `research_synthesis` requests from JSON mode to bounded Step 1 text mode
  - wired live synthesis through syntax precheck and deterministic Step 2 transform before existing citation remap/provenance validation
  - updated research debug checkpoints to truthful content-generation and deterministic-transform labels
  - updated focused unit and runtime-integration tests for bounded-text-first synthesis and no live repair fallback
- Validation: passed `pytest tests/unit/cognitive/test_research_bounded_syntax.py tests/unit/cognitive/test_research_deterministic_transformer.py tests/unit/cognitive/test_research_synthesis.py tests/unit/cognitive/test_research_synthesis_citation_keys.py tests/unit/cognitive/test_research_synthesis_runtime_errors.py tests/unit/cognitive/test_research_synthesis_repair_pass.py tests/unit/cognitive/test_research_public_surface.py tests/unit/interface/test_research_debug_mode.py tests/integration/test_research_synthesis_with_runtime.py`
- Current state: live research synthesis now uses Step 1 bounded text and Step 2 deterministic transform while downstream remap/provenance behavior stays unchanged
- Next step: add Slice 4 formatter fallback without changing downstream remap/provenance semantics
- Files:
  - jeff/cognitive/research/synthesis.py
  - jeff/cognitive/research/debug.py
  - tests/unit/cognitive/test_research_synthesis.py
  - tests/unit/interface/test_research_debug_mode.py

## 2026-04-13 20:07 — Added Step 3 formatter fallback bridge

- Scope: `jeff.cognitive.research` Slice 4 formatter fallback wiring
- Done:
  - added `formatter.py` for Step 3 formatter request building and hard output validation
  - added `fallback_policy.py` for explicit formatter eligibility after deterministic-transform failure
  - wired formatter fallback into live synthesis after Step 2 failure while keeping downstream remap/provenance unchanged
  - updated debug checkpoints and focused unit/integration tests for truthful formatter fallback behavior
- Validation: passed `pytest tests/unit/cognitive/test_research_bounded_syntax.py tests/unit/cognitive/test_research_deterministic_transformer.py tests/unit/cognitive/test_research_synthesis.py tests/unit/cognitive/test_research_synthesis_citation_keys.py tests/unit/cognitive/test_research_synthesis_runtime_errors.py tests/unit/cognitive/test_research_synthesis_repair_pass.py tests/unit/cognitive/test_research_public_surface.py tests/unit/interface/test_research_debug_mode.py tests/integration/test_research_synthesis_with_runtime.py tests/integration/test_research_synthesis_repair_flow.py tests/integration/test_cli_research_debug_stream.py`
- Current state: research now runs Step 1, Step 2, and Step 3 fallback with the existing `research_repair` runtime purpose used explicitly as a temporary formatter bridge
- Next step: clean up temporary repair naming and compatibility surfaces after the formatter bridge is stable
- Files:
  - jeff/cognitive/research/formatter.py
  - jeff/cognitive/research/fallback_policy.py
  - jeff/cognitive/research/synthesis.py
  - tests/integration/test_research_synthesis_repair_flow.py

## 2026-04-13 20:48 — Completed 3-step research transition summary

- Scope: `jeff.cognitive.research` bounded-text-first transition completion summary
- Done:
  - completed Slice 1 bounded syntax foundations and Slice 2 deterministic transformer/validator work
  - switched the live primary path to Step 1 bounded text -> Step 2 deterministic transform with truthful debug checkpoints
  - wired Step 3 formatter fallback only after Step 2 failure, with bounded text passed to the formatter and downstream remap/provenance/persistence/projection/memory-handoff semantics left unchanged
  - updated stale research integration tests to bounded-text-first assumptions and refreshed `jeff/cognitive/research/HANDOFF.md` to the live 3-step state
  - cleaned active repair-era naming to formatter-fallback wording while intentionally keeping `research_repair` / `research_synthesis_repair` as temporary bridge names and `legacy.py` as a compatibility surface
- Validation: passed focused 3-step research unit/integration sweep (`94 passed`); current research handoff reflects the verified live CLI/runtime path
- Current state: research now runs bounded-text-first with deterministic primary normalization and formatter fallback only after Step 2 failure while downstream semantics remain unchanged
- Next step: retire remaining bridge surfaces only after runtime naming and real callers move off `research_repair` and `legacy.py`
- Files:
  - jeff/cognitive/research/bounded_syntax.py
  - jeff/cognitive/research/deterministic_transformer.py
  - jeff/cognitive/research/formatter.py
  - jeff/cognitive/research/synthesis.py
  - jeff/cognitive/research/HANDOFF.md
  - tests/fixtures/research.py

## 2026-04-15 09:00 — Infrastructure Slice 6: vocabulary modules added

- Scope: jeff/infrastructure vocabulary layer
- Done:
  - added `purposes.py` with `Purpose` enum (RESEARCH, RESEARCH_REPAIR, PROPOSAL, PLANNING, EVALUATION) — values match existing PurposeOverrides string keys
  - added `output_strategies.py` with `OutputStrategy` enum (PLAIN_TEXT, BOUNDED_TEXT_THEN_PARSE, BOUNDED_TEXT_THEN_FORMATTER)
  - added `capability_profiles.py` with `CapabilityProfile` dataclass and `CapabilityProfileRegistry`
  - exported all three from `jeff/infrastructure/__init__.py`
  - added 20 focused unit tests across three new test files (all pass)
- Validation: 63/63 infrastructure unit tests pass; no regressions
- Current state: vocabulary modules exist, are reusable, contain no research/domain semantics; research runtime behavior unchanged; config.py and runtime.py untouched
- Next step: Slice 7 — wire vocabulary into runtime routing or begin Proposal/Evaluation domain layer
- Files:
  - jeff/infrastructure/purposes.py (new)
  - jeff/infrastructure/output_strategies.py (new)
  - jeff/infrastructure/capability_profiles.py (new)
  - jeff/infrastructure/__init__.py (4 lines added)
  - tests/unit/infrastructure/test_purposes.py (new)
  - tests/unit/infrastructure/test_output_strategies.py (new)
  - tests/unit/infrastructure/test_capability_profiles.py (new)

## 2026-04-15 09:30 — Infrastructure Slice 7: contract_runtime added

- Scope: jeff/infrastructure contract runtime surface
- Done:
  - added `contract_runtime.py` with `ContractCallRequest` (validated descriptor) and `ContractRuntime` (thin wrapper over InfrastructureServices)
  - `ContractRuntime.invoke` routes by purpose, maps strategy to response mode, auto-generates request_id when absent
  - `ContractRuntime.invoke_with_adapter` added for explicit adapter selection (repair/retry paths)
  - added `contract_runtime` property to `InfrastructureServices` for convenient access
  - exported `ContractCallRequest` and `ContractRuntime` from `jeff/infrastructure/__init__.py`
  - added 18 focused unit tests; 81/81 infrastructure tests pass
- Validation: full infrastructure unit test suite passed, no regressions
- Current state: Infrastructure now has a thin reusable strategy-aware/purpose-aware call entrypoint; existing research flow unchanged; no domain semantics in infrastructure
- Next step: Research or Proposal layer adopts ContractRuntime, or Slice 8 wires CapabilityProfileRegistry into routing
- Files:
  - jeff/infrastructure/contract_runtime.py (new)
  - jeff/infrastructure/runtime.py (contract_runtime property added)
  - jeff/infrastructure/__init__.py (2 exports added)
  - tests/unit/infrastructure/test_contract_runtime.py (new)  

## 2026-04-15 10:10 — Research ContractRuntime adoption: Step 1 and formatter bridge route through InfrastructureServices.contract_runtime

- Scope: jeff/cognitive/research/synthesis.py + jeff/infrastructure/contract_runtime.py
- Done:
  - added `ContractRuntime.invoke_with_request(request, adapter_id)` — dispatches a pre-built ModelRequest through the registry; supports both TEXT and JSON mode
  - added optional `contract_runtime` param to `synthesize_research`, `_invoke_step1_bounded_text_and_transform`, and `_attempt_formatter_fallback`
  - `synthesize_research_with_runtime` now passes `infrastructure_services.contract_runtime` so both Step 1 and formatter bridge calls route through ContractRuntime
  - direct adapter path (`synthesize_research(adapter=...)`) unchanged — all existing tests pass with no modification
  - added 6 focused adoption tests covering `invoke_with_request`, runtime path, formatter fallback, and backward compat
- Validation: 378 unit+integration tests pass; 10 pre-existing failures confirmed unchanged from baseline
- Current state: runtime research path dispatches through ContractRuntime; direct adapter path intact; formatter JSON mode supported via invoke_with_request passthrough
- Next step: consider migrating ContractCallRequest to support reasoning_effort so Step 1 can use invoke() instead of invoke_with_request, or proceed to Proposal/Evaluation adoption
- Files:
  - jeff/infrastructure/contract_runtime.py (invoke_with_request added)
  - jeff/cognitive/research/synthesis.py (contract_runtime threaded through runtime path)
  - tests/unit/cognitive/test_research_contract_runtime_adoption.py (new, 6 tests)  