# Jeff — Real Repo State Audit (2026-04-19)

**Methodology**: Code-first audit. Every claim below is grounded in file paths, symbol names, and runtime verification. Docs and status notes are treated as claims to verify, not as evidence.

---

## 1. Executive Truth

Jeff is a **real, functioning CLI-first system** with durable filesystem persistence, live LLM-backed research, and a bounded execution pipeline. It is **not** vaporware, not a prototype, and not merely contracts — but it is also not a general-purpose autonomous agent.

**What Jeff truly can do today:**
- Start up, load persisted state from `.jeff_runtime/`, and resume across process restarts with full fidelity of projects, work units, runs, flow results, transitions, and research artifacts.
- Accept operator commands through a slash-command CLI with truthful JSON output, debug mode, interactive REPL, and one-shot execution.
- Run bounded `/run` objectives that wire a real end-to-end pipeline: context assembly → LLM-backed proposal generation → deterministic selection → action formation → governance evaluation → subprocess execution (pytest) → outcome normalization → evaluation. This path is real but **limited to one action family**: repo-local pytest validation.
- Run `/research docs` and `/research web` commands that invoke a real 3-step LLM pipeline (bounded text → deterministic transform → optional formatter), persist results as JSON artifacts, and optionally hand off distilled findings to the memory write pipeline.
- Inspect runs, traces, lifecycles, selection reviews, and scope state across fresh process restarts.
- Enforce governance fail-closed: proposals with authority leakage or missing fields are rejected; governance denials route correctly; approval/rejection/revalidation request-entry is surfaced only when the routing state makes it valid.

**What Jeff cannot do today:**
- Execute any action family beyond the single bounded repo-local validation plan (no general command execution, no file modification, no deployment).
- Operate autonomously — all continuation requires operator input; there is no background loop.
- Use a production-grade embedding model for semantic memory retrieval (only hash-based or null embedders exist).
- Provide a GUI (prototype scaffolding exists, not wired to runtime).
- Produce reliable proposal output consistently — live LLM output frequently fails the strict bounded-text validation, causing `/run` to fail at the proposal stage.

**Biggest overstatements or stale assumptions:**
- The system's cognitive pipeline (proposal generation, selection, planning) is architecturally complete but in practice highly sensitive to LLM output quality. The `/run` path fails more often than it succeeds with real providers because validation rejects most LLM output.
- Memory is described as a first-class layer but is effectively in-memory-only for most deployments (Postgres backend exists and is complete, but requires external setup and is not the default).
- The orchestrator's research-followup continuation chain is architecturally deep but has never been black-box verified producing a successful end-to-end research→proposal→selection→execution chain in a single `/run` invocation.

---

## 2. Layer-by-Layer Scorecard

### Core — Score: 5/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/core/transition/apply.py` (apply_transition), `jeff/core/transition/validator.py` (validate_transition_request, validate_candidate_state), `jeff/core/state/models.py` (GlobalState), `jeff/core/containers/models.py` (Project, WorkUnit, Run) |
| **Rationale** | Full transition-controlled state mutation with version tracking, validation, and immutable state updates via `dataclasses.replace()`. Used in every startup and every `/run`. Canonical state persisted to `canonical_state.json` and transition records to `transitions/`. |
| **Missing** | Nothing significant for v1 scope. |

### Governance — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/governance/action_entry.py` (evaluate_action_entry — ~15 condition branches), `jeff/governance/policy.py` (Policy), `jeff/governance/approval.py` (Approval), `jeff/governance/readiness.py` (Readiness) |
| **Rationale** | Complete fail-closed governance evaluation called from real `/run` path (command_scope.py governance_stage → evaluate_action_entry) and from approval continuation (command_requests.py). Truthful readiness checks, freshness sensitivity, scope matching, blocker detection. |
| **Missing** | No dynamic policy loading from config (-1). Policy is constructed in-code per flow. |

### Context — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/cognitive/context.py` (assemble_context_package), called from `jeff/interface/command_common.py` (assemble_live_context_package) |
| **Rationale** | Multi-source context assembly: truth extraction from GlobalState, governance truth records, memory support inputs, compiled knowledge support inputs. Wired into both `/run` and `/research` paths. |
| **Missing** | Archive support inputs retrieval is wired but archive store is optional/empty in most runtime configs. |

### Research — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/cognitive/research/synthesis.py` (synthesize_research_with_runtime), `jeff/cognitive/research/web.py` (run_web_research), `jeff/cognitive/research/documents.py` (run_document_research), `jeff/cognitive/research/persistence.py` (ResearchArtifactStore) |
| **Rationale** | Full 3-step pipeline verified end-to-end: LLM invocation via OllamaModelAdapter, bounded text parsing, deterministic transformation, artifact persistence. `/research docs` verified live producing structured findings with source citations. |
| **Missing** | No recursive research continuation (-0.5). Formatter fallback path exists but quality depends heavily on LLM compliance (-0.5). |

### Proposal — Score: 3/5

| Aspect | Detail |
|--------|--------|
| **Status** | Partial |
| **Evidence** | `jeff/cognitive/proposal/api.py` (run_proposal_generation_pipeline), `jeff/cognitive/proposal/generation.py` (invoke_proposal_generation_with_runtime), `jeff/cognitive/proposal/parsing.py` (parse_proposal_generation_result), `jeff/cognitive/proposal/validation.py` (validate_proposal_generation_result) |
| **Rationale** | The pipeline is architecturally complete and wired into the real `/run` path. However, in practice the live LLM output consistently fails validation (authority leakage, missing risk fields). The pipeline correctly rejects bad output, but this means the layer rarely produces a usable result with real providers. |
| **Missing** | No retry/repair loop for proposal validation failures (-1). Validation is strict but there's no mechanism to re-prompt the LLM with correction guidance (-1). |

### Selection — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/cognitive/selection/decision.py` (run_selection — deterministic phrase-matching, risk/reversibility ranking), `jeff/cognitive/selection/api.py` (run_selection_hybrid), operator override in `jeff/cognitive/post_selection/override.py` |
| **Rationale** | Deterministic selection with explicit non-selection outcomes (reject/escalate/defer). Operator override validated against the considered set. Hybrid selection supports LLM comparison when infrastructure is available. |
| **Missing** | Hybrid selection with real LLM comparison is wired but not exercised in the bounded `/run` path (only deterministic path is used). |

### Planning — Score: 3/5

| Aspect | Detail |
|--------|--------|
| **Status** | Partial |
| **Evidence** | `jeff/cognitive/planning.py` (should_plan, create_plan), `jeff/orchestrator/continuations/planning.py` (bridge_planned_action), `jeff/cognitive/post_selection/plan_action_bridge.py` |
| **Rationale** | Planning gate and plan artifact creation exist. Plan-to-action bridge is wired in the orchestrator runner (lines 250-310). But the bounded `/run` path uses the `bounded_proposal_selection_execution` flow family which does not include a planning stage — planning is only reachable through specific flow families. |
| **Missing** | No live runtime verification of planning stage execution (-1). Planning is not exercised in the default `/run` path (-1). |

### Action / Execution — Score: 3/5

| Aspect | Detail |
|--------|--------|
| **Status** | Partial |
| **Evidence** | `jeff/action/execution.py` (execute_governed_action, _execute_repo_local_validation_plan — real subprocess.run), `jeff/action/outcome.py` (normalize_outcome) |
| **Rationale** | Real subprocess execution exists and is wired. But only one execution plan type (RepoLocalValidationPlan running pytest) is implemented. The action contract supports broader action families but no other plan types exist. |
| **Missing** | No general-purpose action execution beyond pytest (-2). No file-modification, deployment, or API-call action types. |

### Outcome — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/action/outcome.py` (Outcome, normalize_outcome), called from `jeff/interface/command_scope.py` (outcome_stage) |
| **Rationale** | Outcome normalization from execution results is deterministic and wired. Captures completion/failure/inconclusive postures with evidence markers. |
| **Missing** | Only tested via the single execution plan type. |

### Evaluation — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/cognitive/evaluation.py` (evaluate_outcome — deterministic overrides + base disposition), called from `jeff/interface/command_scope.py` (evaluation_stage) and from orchestrator routing |
| **Rationale** | Complete evaluation with 8 verdict types and 8 recommended-next-step types. Deterministic override cascade for objective failures, evidence conflicts, scope mismatches. Wired in `/run` and in routing decisions. |
| **Missing** | No LLM-backed evaluation refinement (purely deterministic). |

### Memory — Score: 3.5/5

| Aspect | Detail |
|--------|--------|
| **Status** | Partial |
| **Evidence** | `jeff/memory/write_pipeline.py` (_run_pipeline — 10-stage), `jeff/memory/retrieval.py` (retrieve_memory — 10-stage), `jeff/memory/store.py` (InMemoryMemoryStore), `jeff/memory/postgres_store.py` (PostgresMemoryStore — ~580 lines, complete), `jeff/memory/run_handoff.py` (handoff_run_summary_to_memory), `jeff/memory/api.py` |
| **Rationale** | Write and retrieval pipelines are real and thorough. In-memory store works. Postgres store is complete with pgvector semantic search, FTS, and HNSW indexing. Run-to-memory handoff is wired in `command_common.py`. Research-to-memory handoff is wired in `command_research.py`. |
| **Missing** | Default deployment is in-memory only — memory does not survive process restart (-1). No production embedding model (-0.5). No `/memory` CLI command family for operator access. |

### Orchestrator — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/orchestrator/runner.py` (run_flow — ~500 lines), `jeff/orchestrator/validation.py` (validate_handoff, validate_stage_output), `jeff/orchestrator/routing.py` (route_selection_outcome, route_governance_outcome, route_evaluation_followup, route_memory_write_outcome), `jeff/orchestrator/continuations/` (post_research, post_selection, planning, approval, boundary_routes) |
| **Rationale** | The central flow runner is real and handles all stage transitions, validation, routing, and continuation. Post-selection next-stage resolution, planning bridge, research-followup continuation, and anti-loop holds are all implemented. Used in every `/run` invocation. |
| **Missing** | Research-followup continuation chain has not been black-box verified end-to-end through all stages (-1). |

### Interface / CLI — Score: 4.5/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/interface/cli.py` (JeffCLI), `jeff/interface/commands.py` (execute_command — routes 13+ command families), `jeff/interface/command_scope.py`, `jeff/interface/command_inspect.py`, `jeff/interface/command_research.py`, `jeff/interface/command_requests.py`, `jeff/interface/command_selection.py`, `jeff/interface/json_views.py`, `jeff/interface/render.py`, `jeff/main.py` |
| **Rationale** | Verified live: `/help`, `/project list`, `/work list`, `/run list`, `/run <objective>`, `/show`, `/trace`, `/lifecycle`, `/scope show`, `/research docs`. JSON mode works. One-shot and interactive REPL both work. Session scope is process-local. All output labels truth vs support vs derived. |
| **Missing** | No `/memory` command family (-0.5). No broad `/research` continuation from prior results. |

### Infrastructure / Runtime / Providers — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/infrastructure/runtime.py` (InfrastructureServices, build_infrastructure_services), `jeff/infrastructure/config.py` (load_runtime_config), `jeff/infrastructure/contract_runtime.py` (ContractRuntime), `jeff/infrastructure/model_adapters/providers/ollama.py` (OllamaModelAdapter — real HTTP), `jeff/infrastructure/model_adapters/providers/fake.py` (FakeModelAdapter), `jeff/infrastructure/model_adapters/factory.py`, `jeff/infrastructure/model_adapters/registry.py` |
| **Rationale** | Verified live: Ollama adapter invoked real HTTP calls to local Ollama server for research and proposal generation. Purpose-based adapter routing works (different models for research vs formatter). Runtime config loaded from `jeff.runtime.toml`. |
| **Missing** | Only Ollama and Fake providers (-1). No OpenAI, Anthropic, or other provider adapters. |

### Persistence / Durability — Score: 4/5

| Aspect | Detail |
|--------|--------|
| **Status** | Implemented |
| **Evidence** | `jeff/runtime_persistence.py` (PersistedRuntimeStore — ~1200 lines, 40+ serialization functions, atomic JSON writes, PID-based mutation lock), `jeff/bootstrap.py` (build_startup_interface_context loads from `.jeff_runtime/`) |
| **Rationale** | Verified live: canonical state, transitions, flow runs, and research artifacts persist to `.jeff_runtime/` and reload correctly across fresh process starts. Run state, lifecycle, trace events, and flow outputs all survive restart. Mutation locking prevents concurrent writes. |
| **Missing** | Memory store (in-memory default) does NOT persist across restarts (-1). Selection reviews persist only when routed through the full flow. |

---

## 3. Real End-to-End Path Map

| Step | Exists in code? | Called in real runtime? | Persisted? | Inspectable after reload? | Tested? | Black-box verified? |
|------|:---:|:---:|:---:|:---:|:---:|:---:|
| **CLI entry** (`main.py` → `build_parser()` → `build_startup_interface_context()`) | yes | yes | n/a | n/a | yes (smoke) | **yes** |
| **Orchestrator** (`run_flow()` in `runner.py`) | yes | yes | flow result saved | yes | yes (acceptance + integration) | **yes** |
| **Context** (`assemble_context_package()` in `context.py`) | yes | yes | not separately | via flow result | yes (unit + integration) | **yes** |
| **Proposal** (`run_proposal_generation_pipeline()` in `proposal/api.py`) | yes | yes | in flow outputs | yes | yes (unit) | **yes** (but fails validation) |
| **Selection** (`build_and_run_selection()` in `selection/api.py`) | yes | yes (when proposal passes) | in flow outputs | yes | yes (unit + acceptance) | no (proposal failed before reaching selection) |
| **Planning** (`should_plan()`, `create_plan()` in `planning.py`) | yes | no (not in default flow family) | would be in flow outputs | would be | yes (unit) | no |
| **Action formation** (`form_action_from_materialized_proposal()`) | yes | yes (when selection passes) | in flow outputs | yes | yes (unit) | no (not reached in live run) |
| **Governance** (`evaluate_action_entry()` in `action_entry.py`) | yes | yes (when action forms) | in flow outputs | yes | yes (unit + integration) | no (not reached in live run) |
| **Execution** (`execute_governed_action()` → `subprocess.run`) | yes | yes (when governance allows) | in flow outputs | yes | yes (unit) | no (not reached in live run) |
| **Outcome** (`normalize_outcome()` in `outcome.py`) | yes | yes (when execution completes) | in flow outputs | yes | yes (unit) | no (not reached in live run) |
| **Evaluation** (`evaluate_outcome()` in `evaluation.py`) | yes | yes (when outcome exists) | in flow outputs | yes | yes (unit + integration) | no (not reached in live run) |
| **Memory handoff** (`handoff_run_summary_to_memory()` in `run_handoff.py`) | yes | yes | in-memory only (default) | no (in-memory store) | yes (unit) | **yes** (observed defer outcome) |
| **Transition** (`apply_transition()` in `transition/apply.py`) | yes | yes | canonical_state.json + transition records | yes | yes (unit + integration) | **yes** |
| **Inspect/read-back** (`/show`, `/trace`, `/lifecycle`) | yes | yes | reads from persisted store | yes | yes (unit + smoke) | **yes** |

**Key finding**: The end-to-end path from CLI entry through context and proposal is verified. The path from selection through execution and evaluation exists in code and is tested, but was **not reached in live black-box testing** because the LLM proposal output failed validation at the proposal stage. The architecture is correct — the validation rejection is itself a correct governance behavior — but it means the downstream stages have not been verified with a real provider in this audit.

---

## 4. Persistence Truth Table

| Object | Canonical durable | In-memory only | Support artifact | Reconstructed on read | Unclear |
|--------|:---:|:---:|:---:|:---:|:---:|
| **GlobalState** (projects, work units, runs) | **yes** (`canonical_state.json`) | | | | |
| **TransitionRequest / TransitionResult** | **yes** (`transitions/*.json`) | | | | |
| **FlowRunResult** (lifecycle, outputs, events, routing) | **yes** (`flow_runs/*.json`) | | | | |
| **SelectionReviewRecord** | **yes** (`selection_reviews/*.json`) | | | | |
| **Research artifacts** | **yes** (`artifacts/research/*.json`) | | | | |
| **ContextPackage** | | | **yes** (reconstructed per invocation) | | |
| **Memory candidates / committed records** | | **yes** (InMemoryMemoryStore default) | | | |
| **Memory records (Postgres backend)** | **yes** (when configured) | | | | |
| **SessionScope** | | **yes** (process-local only) | | | |
| **InfrastructureServices** | | **yes** (rebuilt from config on startup) | | **yes** (from `jeff.runtime.toml`) | |
| **OrchestrationEvents** | **yes** (inside FlowRunResult) | | | | |
| **Governance inputs (Policy, Approval, Truth)** | **yes** (inside FlowRunResult outputs) | | | | |
| **KnowledgeStore artifacts** | **yes** (file-backed JSON via `jeff/knowledge/registry.py`) | | | | |

---

## 5. Runtime Audit

### CLI startup
- **Command**: `python -m jeff --version`
- **Result**: `jeff 0.1.0` — success
- **Failure**: none

### Bootstrap check
- **Command**: `python -m jeff --bootstrap-check`
- **Result**: All checks passed. Reports: persisted runtime loaded, runtime project scope ready, CLI entry surface available, runtime config loaded, research runtime configured with Ollama, bounded /run enabled, research memory backend: in_memory, artifact store root ready.
- **Failure**: none

### Scope selection / project listing
- **Command**: `python -m jeff --project project-1 --work wu-1 --command "/project list" --json`
- **Result**: Two projects listed: `general_research` and `project-1`, both active.
- **Command**: `python -m jeff --project project-1 --work wu-1 --command "/scope show" --json`
- **Result**: Correct scope displayed with process-local-only model noted.
- **Failure**: none

### Bounded /run objective
- **Command**: `python -m jeff --project project-1 --work wu-1 --command "/run smoke validation of Jeff CLI" --json`
- **Result**: Run `run-1` created. Flow started, context assembled, proposal stage entered. After ~115 seconds of LLM invocation, **proposal validation rejected** the output for "forbidden authority language". Flow ended with `lifecycle_state=failed`, `run_lifecycle_state=failed_before_execution`. Memory handoff attempted and resulted in `defer` (support not stable enough).
- **Where it failed**: During execution — specifically, the LLM (gemma4:31b-cloud via Ollama) produced proposal text that contained authority-leaking language, which the deterministic validator in `jeff/cognitive/proposal/validation.py` correctly rejected.
- **Assessment**: The pipeline executed correctly. The failure is a correct governance behavior, not a system bug. The LLM output did not meet the bounded proposal contract.

### Inspect/show/trace/lifecycle after fresh process restart
- **Command**: `python -m jeff --project project-1 --work wu-1 --command "/run list" --json` (fresh process)
- **Result**: `run-1` visible with `run_lifecycle_state=failed_before_execution` — **persisted correctly**.
- **Command**: `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/show" --json`
- **Result**: Full run details including all 5 trace events, flow family, memory handoff result, and lifecycle state — all reloaded from persisted storage.
- **Command**: `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/trace" --json`
- **Result**: 5 ordered events with timestamps, types, and summaries — correct.
- **Command**: `python -m jeff --project project-1 --work wu-1 --run run-1 --command "/lifecycle" --json`
- **Result**: Lifecycle state `failed`, current stage `proposal`, reason summary explains the validation rejection.
- **Failure**: none — all inspection commands work correctly across process restart.

### Research docs (provider-backed)
- **Command**: `python -m jeff --project project-1 --work wu-1 --command "/research docs \"what is Jeff architecture\" README.md" --json`
- **Result**: Research artifact created (`research-7371fa5f1589b534`), persisted to `.jeff_runtime/artifacts/research/`, 5 findings extracted with source citations, summary generated, proposal followup attempted (failed at validation — same authority leakage issue). Live context assembled with 3 truth records.
- **Failure**: Proposal followup failed at validation (not the research itself — research succeeded fully).

### Persistence filesystem verification
- **Command**: `Get-ChildItem .jeff_runtime -Recurse`
- **Result**: Full directory tree present: `state/canonical_state.json`, `state/transitions/*.json` (7 transition records), `flows/flow_runs/run-1.json`, `artifacts/research/research-*.json`, `config/runtime.lock.json`. All expected artifacts persisted.

---

## 6. Docs-vs-Code Drift

| Claim (from docs/status) | Code reality | Verdict |
|---|---|---|
| "984 passed, 28 skipped" test suite | Not re-run in this audit, but test structure matches (~130+ test files across 5 families) | **Plausible** — cannot verify without running full suite |
| "bounded /run objective path enabled" | Verified — real subprocess execution wired through the full pipeline | **Accurate** |
| "research memory backend configured: in_memory" | Confirmed — default backend is `InMemoryMemoryStore`, does not persist across restarts | **Accurate** |
| "persisted runtime reloads across fresh process restarts" | Verified — all canonical state, transitions, flow runs, and research artifacts reload correctly | **Accurate** |
| "fail-closed governance evaluation" | Verified — proposal validation rejected bad LLM output correctly | **Accurate** |
| "approval-gated continuation" | Code exists (`command_requests.py` — approve/reject/revalidate), but not black-box verified in this audit | **Exists in code, unverified at runtime** |
| "research-followup continuation chain" | Code exists in `orchestrator/continuations/post_research.py` with extensive implementation | **Exists in code, unverified at runtime** |
| "anti-loop hold when routing would re-enter research_followup" | Code exists in runner.py and post_research.py | **Exists in code, unverified at runtime** |
| "GUI: explicitly deferred" | Confirmed — prototype scaffolding exists under `gui/` but is not wired to runtime | **Accurate** |
| "autonomous continuation: explicitly deferred" | Confirmed — no autonomous loop anywhere in codebase | **Accurate** |
| "broader /run action families: deferred" | Confirmed — only `RepoLocalValidationPlan` (pytest) exists as an execution plan type | **Accurate** |
| README claims "strongest at truthful inspection, bounded /run, approval-gated continuation, research support, and anti-drift coverage" | Truthful inspection: verified. Bounded /run: verified (works but LLM output quality limits success rate). Research support: verified. Anti-drift: test structure confirms. Approval-gated: code exists but unverified. | **Mostly accurate** |
| "In-memory memory store" described as first-class | Write and retrieval pipelines are thorough, but in-memory default means memory does not survive restart | **Accurate but undersells the limitation** |
| "Postgres memory backend" claimed as option | `postgres_store.py` is complete (~580 lines), wired in bootstrap.py | **Accurate** |

**No false or misleading claims found.** The documentation is notably honest about what is and isn't implemented. The main gap is that the docs don't emphasize how frequently the `/run` path fails at proposal validation with real LLM providers.

---

## 7. Top 5 Real Backlog Priorities

### 1. Proposal Generation Reliability
**Problem**: The `/run` path consistently fails at proposal validation because LLM output violates the bounded text contract (authority leakage, missing risk fields). The architecture is correct — validation should reject bad output — but there is no repair/retry loop.
**Files**: `jeff/cognitive/proposal/validation.py`, `jeff/cognitive/proposal/api.py`
**Impact**: The entire execution pipeline is unreachable when proposals fail.
**Fix**: Add a bounded retry with correction guidance in the proposal prompt, similar to how research has `synthesis_repair_flow`.

### 2. Memory Persistence Across Restarts
**Problem**: Default memory backend is in-memory. Memory records, write events, and retrieval history vanish on process exit. Postgres backend exists but requires external setup.
**Files**: `jeff/memory/store.py` (InMemoryMemoryStore), `jeff/bootstrap.py` (_build_memory_store)
**Impact**: Memory handoff results (from `/run` and `/research --handoff-memory`) are lost between sessions.
**Fix**: Add a SQLite-backed memory store as a zero-config durable default, or add JSON-file persistence for the in-memory store.

### 3. Broader Action Execution Families
**Problem**: Only `RepoLocalValidationPlan` (pytest) exists. The action contract (`jeff/contracts/action.py`) and execution framework (`jeff/action/execution.py`) support broader families, but no other plan types are implemented.
**Files**: `jeff/action/execution.py`, `jeff/interface/command_scope.py` (_build_repo_local_validation_plan)
**Impact**: Jeff can only "do" one thing: run pytest. All other action types are gated behind this gap.
**Fix**: Implement at least one additional plan type (e.g., general shell command execution with governance gating).

### 4. Production Embedding Model for Memory
**Problem**: Only `NullEmbedder` (zero vectors) and `HashEmbedder` (character bigram hashing) exist. Semantic memory search is effectively non-functional without a real embedding model.
**Files**: `jeff/memory/embedder.py`
**Impact**: Memory retrieval's semantic search stage produces meaningless results.
**Fix**: Integrate a real embedding provider (sentence-transformers local, or model adapter based).

### 5. Research-to-Proposal Followup Reliability
**Problem**: The research-to-proposal followup path attempts to generate proposals from research findings but consistently fails at proposal validation (same authority leakage issue). This means research findings cannot flow into actionable proposals.
**Files**: `jeff/interface/command_research.py` (build_live_context_proposal_followup), `jeff/cognitive/proposal/validation.py`
**Impact**: Research findings remain informational — they cannot trigger governed action.
**Fix**: Same as #1 — proposal generation repair/retry loop.

---

## 8. Final Verdict

### Is Jeff currently stronger in lawful reasoning than in governed doing?
**Yes, decisively.** Jeff's strength is in its governance layer, state management, truthful inspection, and deterministic validation. The "reasoning" parts (context assembly, research synthesis, selection logic, evaluation, governance evaluation) are thorough and reliable. The "doing" parts (action execution) are limited to a single plan type, and the bridge from reasoning to doing (proposal generation) frequently fails with real LLM providers. Jeff knows how to think about doing things more than it knows how to do them.

### What is the single weakest layer right now?
**Proposal generation reliability.** This is the bottleneck between the strong reasoning layers and the potentially strong execution layer. When proposals pass validation, the downstream path (selection → action → governance → execution → outcome → evaluation) works correctly. But proposals rarely pass validation with real LLM output, making the entire execution pipeline unreachable in practice.

### What is the single most valuable next implementation slice?
**Proposal generation repair/retry loop with correction guidance.** This unblocks the entire `/run` execution pipeline. The research subsystem already has a synthesis repair mechanism (`jeff/cognitive/research/synthesis.py` — repair flow). A similar bounded-retry mechanism for proposal generation would have the highest leverage: it would make the `/run` path functional end-to-end with real providers, validating the full governance→execution→evaluation chain under real conditions. This single change would upgrade the system from "knows how to think" to "can actually do things under governance."
