# Functionality Report

## Audit basis

- Canonical semantic sources used:
  - `v1_doc/ARCHITECTURE.md`
  - `v1_doc/ORCHESTRATOR_SPEC.md`
  - `v1_doc/MEMORY_SPEC_NEW.md`
  - `v1_doc/CLI_V1_OPERATOR_SURFACE.md`
- Implementation-reality sources used:
  - startup/runtime: `jeff/main.py`, `jeff/bootstrap.py`, `jeff/runtime_persistence.py`, `jeff/infrastructure/*`
  - semantic layers: `jeff/core/*`, `jeff/governance/*`, `jeff/cognitive/*`, `jeff/action/*`, `jeff/memory/*`, `jeff/orchestrator/*`, `jeff/interface/*`
  - recent status files for post-selection and orchestrator continuation work on 2026-04-18 and 2026-04-19
- Code areas inspected:
  - startup, packaging, runtime assembly, provider adapters, research pipeline, proposal/selection bridges, orchestrator continuation modules, CLI projections, memory pipeline, persisted runtime support stores
- Test areas inspected:
  - smoke: startup and CLI entry
  - unit: core, governance, cognitive, interface, infrastructure, memory, orchestrator
  - integration: research flows, runtime persistence, CLI research, orchestrator routing, Postgres memory
  - acceptance: backbone flow, CLI/orchestrator alignment, truthfulness, scope isolation, post-selection routing
- Limitations / uncertainty notes:
  - most live-provider and live-network behavior is simulated with fake adapters or monkeypatched web/document acquisition
  - optional Postgres integration and optional runtime config paths exist, but are not the default path exercised by every test run
  - green tests prove bounded law and implementation wiring, not production readiness

## What functionality is actually proven

### Startup / packaging

Directly proven by tests:
- `tests/smoke/test_cli_entry_smoke.py` proves `python -m jeff` one-shot command execution reaches the CLI surface.
- `tests/integration/test_runtime_workspace_persistence.py` proves startup initializes `.jeff_runtime`, reloads persisted state instead of rebuilding demo truth, persists transition audit records, and keeps support stores outside canonical truth.
- `tests/integration/test_bootstrap_runtime_config.py` proves startup loads `jeff.runtime.toml` when present and remains usable without it.

Appears implemented but only weakly proven:
- Real operator startup experience in a long-lived shell is only lightly tested.

Mostly contract-level or design-level:
- none in this area; startup is actually wired.

Confidence level:
- high

### Core / state / transitions

Directly proven by tests:
- `tests/unit/core/test_transition_rules.py` proves stale basis rejection, unknown scope rejection, lawful object creation, and no mutation on rejection.
- `tests/acceptance/test_acceptance_backbone_flow.py` proves the core transition path can serve as the lawful commit at the end of a full bounded flow.

Appears implemented but only weakly proven:
- broader transition families beyond create project/work unit/run are not there, so there is not much unproven hidden breadth here.

Mostly contract-level or design-level:
- richer truth mutation semantics beyond the current narrow transition set.

Confidence level:
- high

### Governance

Directly proven by tests:
- `tests/integration/test_governance_negative_boundaries.py` proves bounded action requirement, stale approval rejection, mismatched approval rejection, and no permission-by-workflow drift.
- governance outcomes are further exercised indirectly in acceptance and orchestrator alignment tests.

Appears implemented but only weakly proven:
- long-lived operator approval lifecycle behavior is not deeply exercised because the CLI does not drive a full approval workflow.

Mostly contract-level or design-level:
- richer persisted approval/review/change control processes.

Confidence level:
- high for semantic gating, medium for operational workflow

### Context / cognitive boundaries

Directly proven by tests:
- `tests/unit/cognitive/test_context_truth_first.py` and `test_context_compiled_knowledge_integration.py` prove truth-first ordering and compiled knowledge integration behavior.
- `tests/integration/test_live_context_compiled_knowledge_flow.py` and `test_inspect_live_context.py` exercise live context projection and support ordering.

Appears implemented but only weakly proven:
- how well context quality holds up across many live runtime cases is less proven than the ordering and isolation rules.

Mostly contract-level or design-level:
- none at the boundary-law level; the boundary rules are materially exercised.

Confidence level:
- high

### Research

Directly proven by tests:
- unit tests cover bounded syntax validation, deterministic transform, provenance consistency, citation keys, repair flow, prompt files, source cleaning, publish date support, persistence, memory handoff, and archive behavior.
- `tests/integration/test_document_research_end_to_end.py` and `test_web_research_end_to_end.py` prove end-to-end research over collected evidence using the runtime stack.
- `tests/integration/test_research_persistence_flow.py` proves artifact persistence and archive persistence.
- CLI research tests prove docs/web parsing, scope handling, debug streams, structured JSON errors, and source transparency.

Appears implemented but only weakly proven:
- web reliability under real network conditions; tests monkeypatch web acquisition.
- live model-provider behavior beyond fake adapters and adapter-level Ollama tests.

Mostly contract-level or design-level:
- none for bounded research itself; this is one of the most substantively implemented areas.

Confidence level:
- high for bounded repo-local behavior
- medium for real-world live-runtime reliability

### Proposal / selection / planning

Directly proven by tests:
- proposal tests cover parsing, validation, runtime invocation surface, prompt files, public surface, and proposal-generation bridge behavior.
- selection tests cover rules, parsing, comparison/runtime behavior, validation, public surface, override handling, action resolution, and proposal-output-to-selection bridge behavior.
- post-selection tests cover next-stage resolution, plan-action bridge, research sufficiency, decision-support, and research-to-proposal support consumers.
- acceptance/integration tests prove the post-selection routing chain for defer, planning, governance, escalation, and anti-loop behavior.

Appears implemented but only weakly proven:
- quality of live proposal generation under real providers is only lightly proven relative to the amount of semantic machinery around it.
- planning exists semantically, but there is limited evidence of rich operator use beyond bridge behavior and route selection.

Mostly contract-level or design-level:
- a broad planning workflow surface and richer proposal/selection operator tooling.

Confidence level:
- medium

### Execution / outcome / evaluation

Directly proven by tests:
- `tests/unit/action/test_execution_models.py` and `test_outcome_models.py` prove contract correctness.
- `tests/unit/cognitive/test_evaluation_rules.py` and `tests/integration/test_evaluation_layer_alignment.py` prove evaluation semantics and layer ownership.
- `tests/acceptance/test_acceptance_backbone_flow.py` proves the end-to-end bounded slice through execution, outcome, evaluation, memory, and transition.

Appears implemented but only weakly proven:
- real-world execution side effects, rollback, and recovery are not materially exercised because the action layer is mostly semantic and deterministic.

Mostly contract-level or design-level:
- broader operational execution features and stronger recovery flows.

Confidence level:
- medium

### Memory

Directly proven by tests:
- `tests/unit/memory/test_memory_v1_spec.py` is broad and checks write discipline, truth separation, retrieval boundaries, dedupe, merge/supersede, maintenance, and API scoping.
- `tests/unit/memory/test_memory_truth_separation.py`, `test_memory_retrieval_rules.py`, and related files strengthen boundary coverage.
- `tests/integration/memory/test_postgres_memory.py` proves the Postgres store path works when DSN is supplied.

Appears implemented but only weakly proven:
- day-to-day runtime use of durable memory is weakly proven because default startup still uses in-memory memory when enabled.

Mostly contract-level or design-level:
- none for the write/retrieval law itself; memory law is heavily exercised.

Confidence level:
- high for semantic discipline
- medium for default operational durability

### Orchestrator

Directly proven by tests:
- unit tests cover stage order, trace/lifecycle, failure routing, selection hybrid behavior, and post-selection continuation behavior.
- `tests/integration/test_orchestrator_post_selection_next_stage_routing.py` proves recent continuation slices are actually wired.
- `tests/acceptance/test_acceptance_orchestrator_post_selection_next_stage.py` proves bounded post-selection next-stage routing behavior end to end.
- `tests/acceptance/test_acceptance_backbone_flow.py` proves a lawful orchestrated backbone slice.

Appears implemented but only weakly proven:
- long-running and operationally messy orchestration conditions are not deeply exercised.
- the research-followup continuation chain is well covered semantically, but still newly built and bounded.

Mostly contract-level or design-level:
- future continuation across time, scheduling, and richer workflow behavior.

Confidence level:
- medium to high for current bounded flow law
- medium for operational reality under broader workloads

### CLI / interface

Directly proven by tests:
- smoke tests prove entry and one-shot behavior.
- unit tests prove scope handling, run resolution, usability, truthfulness, selection override, research command parsing, debug mode, and JSON projections.
- acceptance proves CLI/orchestrator alignment.

Appears implemented but only weakly proven:
- full operator experience for prolonged work remains weakly proven.
- conditional request commands are wired, but only as bounded request-entry surfaces.

Mostly contract-level or design-level:
- launch/run command family, health/telemetry/rationale command families, richer review/change control surfaces.

Confidence level:
- high for implemented inspection/research surfaces
- medium for end-to-end operator control capability

### Infrastructure / runtime / providers

Directly proven by tests:
- unit tests cover runtime config, adapter registry/factory/telemetry, output strategies, purpose routing, and fake adapters.
- `tests/unit/infrastructure/test_ollama_model_adapter.py` proves actual request construction and error mapping for Ollama adapter behavior.
- bootstrap runtime config integration tests prove services are assembled and purpose overrides work.

Appears implemented but only weakly proven:
- real live-provider behavior under sustained use.
- richer provider interoperability beyond fake and Ollama.

Mostly contract-level or design-level:
- streaming, async, more providers, richer operational telemetry.

Confidence level:
- medium

## Functional gaps and confidence gaps

### Functionality that works in-memory/demo mode but is not durable

- default startup state and run continuity are local `.jeff_runtime` JSON, not a stronger runtime service
- default memory usage is in-memory when enabled through runtime config
- demo selection review and flow-run support records are persisted locally for inspection, not canonized as stronger runtime truth

### Functionality that is semantically tested but not operationally hardened

- proposal generation runtime path
- selection follow-up chain after research
- request-command surfaces for approve/reject/retry/revalidate/recover
- Ollama provider path

### Areas with unit coverage but weak end-to-end confidence

- planning
- broader action/governance/recovery control flows
- some proposal/selection runtime quality concerns
- provider/runtime behavior beyond bounded adapter tests

### Areas with acceptance slices but weak live-run confidence

- acceptance backbone flow proves a lawful slice, but it is still a bounded test harness path
- post-selection continuation acceptance is real, but narrow and recent
- CLI/orchestrator acceptance proves alignment, not broad operator throughput

### Areas designed but not really exercised

- richer CLI rationale/health/telemetry surfaces from the spec
- true run-launch operator flows
- broader change/recovery workflows
- future continuation and scheduling semantics

### Areas that could break without current tests noticing

- real web research reliability under unstable network conditions
- real provider behaviors that differ from fake adapters and stubbed Ollama responses
- operational durability assumptions around local JSON runtime persistence
- user-facing ergonomics of thin request surfaces that look larger than they are

### Specific high-interest gaps

- research live reliability gaps:
  - source acquisition and runtime providers are bounded and tested mostly with stubs/fakes
- persistence gaps:
  - durable memory exists, but default runtime still skews in-memory/local
- orchestrator real-flow gaps:
  - no broad operator-launched flow execution surface
- provider/runtime integration gaps:
  - narrow provider set and modest operational hardening
- action/governance/selection live wiring gaps:
  - strong semantics, thinner real operator workflows
- CLI command-surface confidence gaps:
  - research commands are stronger than action/governance control paths

## What works vs what only looks like it works

### Tests are green but the capability is still thin

- `/approve`, `/reject`, `/retry`, `/revalidate`, and `/recover` look like control commands, but the code proves they are request receipts, not richer workflow execution.
- proposal generation looks substantial because there are many bridge and parsing tests, but the operational capability is still a bounded generation pipeline, not a broad mature proposal engine.
- runtime persistence looks like durable runtime infrastructure, but it is still local JSON workspace persistence.

### Contracts are strong but real behavior is still weak

- planning
- execution/recovery richness
- broader operator approval lifecycle
- provider breadth and production runtime behavior

### Acceptance exists only for a narrow slice

- acceptance backbone flow
- post-selection next-stage routing
- CLI/orchestrator alignment

These are meaningful and real, but they are still slices, not broad operational soak tests.

### Implementation is truthful but not yet production-strong

- This is the recurring pattern across Jeff.
- The repo is unusually disciplined about not overstating support artifacts, permission, or completion.
- That truthfulness is real strength, but it should not be mistaken for production-grade operational breadth.

## Functionality bottom line

- Is Jeff functionally strong today, or mainly structurally strong?
  - Jeff is structurally strong first, with several functionally real slices on top of that structure. The strongest functional slice is research. The weakest area is broad operator-driven live work execution/control.

- Which subsystem has the strongest real confidence?
  - Research, especially bounded research synthesis plus persistence and CLI research surfaces.

- Which subsystem is weakest in operational reality?
  - Action/governance/operator control as a live operator workflow. The semantics are good, but the CLI control surface and execution depth are still thin.

- What is the most important next hardening target?
  - Harden one truthful end-to-end operator-driven path that launches bounded work through proposal/selection/action/governance, with persistence and clear operator review semantics, instead of relying mainly on inspection, demo bootstrap data, and request receipts.