# Full Repo Review — Jeff (v1)

Audit date: 2026-04-15
Scope: `C:\DATA\PROJECTS\JEFF` on branch `master` (working tree dirty; see §2).
Method: repo-grounded inspection of canon docs, handoffs, implementation, and a real run of the test suite and bootstrap preflight. No refactoring has been performed.

---

## 1. Executive Summary

Jeff is materially further along on the **research vertical** than on any other cognitive stage, and the v1 canonical backbone (state → transition → orchestrator → interface) is present as a clean, testable skeleton. The highest-signal fact right now: the research pipeline *has been transitioned* from a JSON-first synthesis path to the 3-step bounded-text pipeline (`synthesis.py`, `bounded_syntax.py`, `deterministic_transformer.py`, `fallback_policy.py`, `formatter.py`) as called for by `v1_doc/additional/3step_transition.md`, and the infrastructure layer has started growing the reusable vocabulary the buildplan asks for (`purposes.py`, `output_strategies.py`, `capability_profiles.py`, `contract_runtime.py`). Research is the only cognitive stage that runs through a real model adapter today.

The things I'd call load-bearing for a reader:

1. **The 3-step research pipeline is real and the primary path** (`jeff/cognitive/research/synthesis.py:92-394`). Step 1 bounded text → Step 2 deterministic transform → Step 3 formatter fallback. Verified by `tests/unit/cognitive/test_research_deterministic_transformer.py` and the contract-runtime adoption tests.
2. **Infrastructure now exposes a `ContractRuntime`** and research has adopted it on both Step 1 and the formatter bridge (`jeff/infrastructure/contract_runtime.py`, `jeff/cognitive/research/synthesis.py:163-394`).
3. **The rest of the canonical backbone (proposal, selection, governance, action, execution, outcome, evaluation, memory, transition) runs as deterministic/rule-based code against in-memory state**, and the orchestrator sequences them — but no non-research cognitive stage currently talks to a model adapter. The orchestrator itself is staged handlers, not a live runtime loop.
4. **Truth is in-memory only.** `bootstrap_global_state()` + `apply_transition()` work, but there is no persistence of `GlobalState`, no reload, and no cross-process store. `REPO_HANDOFF` says this plainly and the code agrees.
5. **`jeff/infrastructure/HANDOFF.md` is stale** — it does not mention Slices 6/7 (`purposes.py`, `output_strategies.py`, `capability_profiles.py`, `contract_runtime.py`), which are already merged and exported from `jeff/infrastructure/__init__.py`. Every other submodule handoff I read is current.
6. **There are 10 pre-existing test failures** in the full suite (378 pass / 10 fail). All 10 trace to fake-adapter output that does not satisfy the Step 1 bounded-text grammar, i.e. they are stuck on the *old* JSON-shaped synthesis contract. They are not a regression in the new code — they are tests that weren't rewritten when the pipeline was flipped.
7. **The artifact store path is double-nested on disk.** The runtime config sets `artifact_store_root = ".jeff_runtime/research_artifacts"` and `ResearchArtifactStore.__init__` then creates `{root_dir}/research_artifacts`, so persisted files land in `.jeff_runtime/research_artifacts/research_artifacts/research-*.json`. I can see this directly in the working tree — 25 such files are present. This is a small but real bug.
8. **Legacy/bridge surfaces still exist by design.** `jeff/cognitive/research/legacy.py` is intentionally retained for callers still on `ResearchResult`, and the formatter route is still wired through a runtime purpose literally named `research_repair` because the cleaner infrastructure-layer naming hasn't landed yet. Both are documented in the research handoff; neither is the main path.
9. **The CLI is the only operator surface and it is thin, command-driven, and per-command**. `jeff/interface/commands.py` is a long explicit dispatch with no hidden business logic; it routes into `cognitive.research` for `/research docs` and `/research web`, and into backend read functions for everything else.

My recommended next move is in §14 — it is narrow and lives entirely inside the infrastructure layer (retire the `research_repair` bridge naming, migrate `ContractCallRequest` to carry `reasoning_effort`/JSON schema so research can call `invoke()` instead of `invoke_with_request()`, and fix the artifact-store path). I am explicitly **not** recommending broad rewrites.

---

## 2. Current Repo State

Branch: `master` (the CLAUDE.md says main is normally `main`, but this tree is on `master`; there is no local `main` reference that I saw).

Recent commits (last 5):

```
f23c735 3step transition slice 4 completed
a801dfe before 3step transition
6581709 research before transition to 2step model
125038b research after debug_03
57bcf46 research after debug_02
```

Working tree: **dirty**. The modifications are consistent with the recent ContractRuntime adoption work (see `handoffs/WORK_STATUS_UPDATE_2026-04-15_1010.md`):

- `jeff.runtime.toml` — adapter config adjustments
- `jeff/cognitive/research/synthesis.py` — ContractRuntime threaded through
- `jeff/cognitive/research/formatter.py` — JSON-mode formatter request via `invoke_with_request`
- `jeff/cognitive/research/HANDOFF.md` — aligned with current pipeline
- `jeff/infrastructure/__init__.py`, `jeff/infrastructure/runtime.py` — contract_runtime property added
- ~12 integration tests updated to match the new pipeline
- `tests/unit/cognitive/test_research_synthesis_repair_pass.py` updated
- 25 untracked persisted research artifacts under `.jeff_runtime/research_artifacts/research_artifacts/` (the doubled path is the persistence bug; see §5).

`jeff.runtime.toml` currently points at three real Ollama adapters (`ollama_default=gemma4:31b-cloud`, `ollama_research=qwen3:8b`, `ollama_formatter=qwen3:8b`) against `http://127.0.0.1:11434`, with `purpose_overrides.research=ollama_research` and `purpose_overrides.research_repair=ollama_formatter`. Preflight comes up cleanly in my environment:

```
package imports resolved
demo interface context bootstrapped
demo project scope ready: project-1
CLI entry surface is available through jeff.interface.JeffCLI
local runtime config loaded: C:\DATA\PROJECTS\JEFF\jeff.runtime.toml
research runtime configured with default adapter ollama_default
research artifact store root ready: C:\DATA\PROJECTS\JEFF\.jeff_runtime\research_artifacts
```

Module tree under `jeff/`:

- `core/` — state, schemas (ids, scope, envelopes), transition, containers (project/work_unit/run). Narrow and clean.
- `infrastructure/` — config, runtime, model adapters (base/factory/registry/providers/telemetry), plus the new vocabulary modules (purposes, output_strategies, capability_profiles, contract_runtime).
- `cognitive/` — research (now a proper package with bounded_syntax, deterministic_transformer, fallback_policy, formatter, synthesis, documents, web, persistence, memory_handoff, contracts, legacy, debug, validators, errors), plus flat files for context/proposal/selection/planning/evaluation/types.
- `action/` — types, execution, outcome (stubbed but typed).
- `governance/` — policy, approval, readiness, action_entry.
- `memory/` — models, store, retrieval, write_pipeline, types.
- `orchestrator/` — flows, routing, runner, lifecycle, validation, trace.
- `interface/` — cli, commands, render, json_views, session.
- `contracts/` — action contract only (thin).
- `bootstrap.py`, `main.py`, `__main__.py` — entry points.

`v1_doc/` contains the full canonical specs and `v1_doc/additional/` holds the architecture and transition documents referenced by the handoffs (`RESEARCH_ARCHITECTURE.md`, `MEMORY_ARCHITECTURE.md`, `3step_transition.md`, `3step_transition_buildplan.md`, etc.). No doc was missing.

`tests/` splits into `unit/` (action, cognitive, core, governance, infrastructure, interface, memory, orchestrator) and `integration/` (bootstrap, CLI research, document and web research end-to-end, orchestrator handoff validation, research persistence/provenance/memory, action stage boundaries, governance boundaries). Running `python -m pytest tests/unit tests/integration -q` yields **378 passed / 10 failed** — see §5 and §11.

---

## 3. What Is Working Well

**The 3-step research pipeline, verified against code.** `jeff/cognitive/research/synthesis.py:92-394` implements exactly the shape `3step_transition.md` describes: build one bounded-text `ModelRequest` with `purpose="research_synthesis"`, `response_mode=TEXT`, `reasoning_effort="medium"`, `max_output_tokens=1200`; invoke via `ContractRuntime.invoke_with_request` when available, otherwise via the injected adapter; run `validate_step1_bounded_text` + `transform_step1_bounded_text_to_candidate_payload`; on `deterministic_transform_failed`, consult `fallback_policy.decide_formatter_fallback` and only then build a JSON-mode formatter request against `FORMATTER_BRIDGE_RUNTIME_OVERRIDE` (`"research_repair"`). Step 3 receives the already-validated Step 1 bounded text, **not** the original evidence pack. This matches the buildplan's red-flag checklist.

**Bounded Step 1 syntax is a real contract, not a convention.** `jeff/cognitive/research/bounded_syntax.py` enforces ordered `SUMMARY:`, `FINDINGS:`, `INFERENCES:`, `UNCERTAINTIES:`, `RECOMMENDATION:` sections; paired `- text: ` / `  cites: ` finding lines; bullet prefix for inferences/uncertainties; strict citation key pattern `^S[1-9][0-9]*$`; rejection of fenced code blocks and JSON-looking inputs. `deterministic_transformer.parse_step1_bounded_text` walks the sections, rejects extra headers, and refuses to "fix" missing pieces. This is the right shape: Step 2 is mechanical, not semantic.

**Fail-closed provenance.** `contracts.validate_research_provenance` refuses duplicate source IDs, refuses findings or evidence items that reference unknown source IDs, refuses artifacts with zero sources, and is called both during record construction and during load (`persistence.validate_research_artifact_record`, called on save *and* in `_record_from_payload`). Citation key discipline is symmetric: `formatter._sanitize_formatter_input` rewrites internal source IDs to `S1..Sn` keys on the way *into* the formatter, and Step 1 outputs are remapped from `S*` keys back to internal source IDs before provenance validation runs downstream.

**The infrastructure layer has started growing a reusable contract surface.** `jeff/infrastructure/contract_runtime.py` (`ContractCallRequest`, `ContractRuntime.invoke`, `invoke_with_request`, `invoke_with_adapter`) is explicitly and correctly scoped — the docstring spells out that it owns neither findings nor formatter fallback nor parsing. `InfrastructureServices` exposes a `contract_runtime` property, and the routing path (`get_adapter_for_purpose`) honours the `PurposeOverrides` table with a deliberate fallback for `research_repair`. The enums (`Purpose`, `OutputStrategy`) are thin, purpose-stringed, and do not drag domain semantics into infrastructure.

**The orchestrator is deterministic and side-effect-free.** `jeff/orchestrator/runner.py` is a small, explicit, staged handler dispatcher. It validates sequence before running, validates handoffs between stages, validates stage outputs, applies non-forward routing (`routing.py`) for selection/governance/memory/evaluation outcomes, and emits trace events — with no hidden business logic and no auto-execution (`RoutingDecision.__post_init__` actively refuses `auto_execute=True`). It does the right minimum.

**Transition is really transition-only.** `jeff/core/transition/apply.py` supports only `create_project`, `create_work_unit`, `create_run`, but the shape is correct: build a candidate state via `dataclasses.replace`, run `validate_candidate_state`, either commit with `state_version += 1` and `last_transition_id=request.transition_id` or reject with `validation_errors`. No other code path mutates `GlobalState`. Typed IDs and frozen containers (`jeff/core/containers/models.py`) enforce the relational invariants at construction time.

**CLI is thin and truthful.** `jeff/interface/cli.py` + `jeff/interface/commands.py` is a per-command dispatch that reads from `InterfaceContext` (read-only view over state + optional infrastructure/artifact store/memory). The research commands call the real pipeline and surface both text and JSON views. `/mode debug` keeps the debug checkpoint stream alive. There is no place where the CLI invents truth or mutates state outside transitions.

**Tests cover the research vertical thoroughly.** The `tests/unit/cognitive/test_research_*` files alone cover bounded syntax, deterministic transformer, citation keys, memory handoff, persistence, provenance, publish-date support, source cleaning, contract-runtime adoption, and the runtime-error surface. The `tests/integration/test_cli_research_*` files exercise the CLI through real synthesis with the fake adapter, the runtime config path, and the debug stream. `python -m pytest tests/unit/infrastructure tests/unit/cognitive/test_research_bounded_syntax.py tests/unit/cognitive/test_research_deterministic_transformer.py tests/unit/cognitive/test_research_synthesis.py tests/unit/cognitive/test_research_contract_runtime_adoption.py -q` passes clean in my run: **112 / 112**.

---

## 4. What Is Incomplete

**Orchestrator has no live runtime loop.** `run_flow` is a function you call with a dict of stage handlers; there is no runner process, no scheduler, no in-repo driver that actually exercises `bounded_proposal_selection_action` against real data, and the handlers themselves for non-research stages are not wired to a model adapter. The canonical backbone can be *run in tests* but it does not run as a service.

**Proposal / selection / planning / evaluation / action / execution / outcome are rule-based.** `jeff/cognitive/proposal.py`, `selection.py`, `planning.py`, `evaluation.py`, and `jeff/action/execution.py` exist and are exercised by tests (`tests/unit/cognitive/test_proposal_rules.py`, etc.), but they do not call the infrastructure contract runtime. The buildplan's Wave 2 ("Proposal/Evaluation adoption of ContractRuntime") has not been started — only Wave 1 (research) has landed.

**No persistence for `GlobalState`.** `bootstrap_global_state()` returns an empty in-memory `GlobalState` every time the process starts. There is no save/load, no snapshot, no migration, and no append-only transition log. `apply_transition` returns a new `GlobalState` but nothing writes it to disk. The CLI's demo state is hard-coded in `bootstrap.build_demo_state`, and the repo handoff acknowledges this.

**`transition/apply.py` supports exactly three transition types.** `create_project`, `create_work_unit`, `create_run`. Nothing else: no lifecycle-state transitions, no memory writes, no governance mutations, no outcome attachment, nothing that the spec says is the *only* way truth is allowed to change. So while the design *is* transition-only, in practice most of the canonical objects never mutate after creation.

**Memory handoff is selective but the memory store itself is `InMemoryMemoryStore`.** `memory/store.py` is in-memory, same as `GlobalState`. `memory_handoff.py` distils artifacts correctly and defers to the memory write pipeline, but the whole pipeline's memory evaporates on restart.

**No orchestrator-integrated research workflow.** The research handoff calls this out explicitly: verified research usage is through direct CLI commands and direct backend calls, not through a `bounded_research_direct_output` flow actually running via the orchestrator. The flow *exists* in `jeff/orchestrator/flows.py` but nothing composes a stage handler dict for it in production code — only tests do.

**Web acquisition is intentionally basic.** `jeff/cognitive/research/web.py` hits `html.duckduckgo.com` with a 10-second timeout, uses `html.parser.HTMLParser` to pull titles/snippets, fetches pages with `urllib.request` and strips HTML with a hand-rolled extractor. No ranking, no freshness comparison, no robots handling, no retry. The handoff correctly classifies this as deliberately thin.

**Buildplan Slices 5, 6 (partially), 7 (partially), 8 deferred:**
- No `jeff/infrastructure/fallback_policies.py` (Slice 5 — the buildplan wants an infrastructure-owned fallback policy registry; right now `fallback_policy.py` lives under `jeff/cognitive/research/`, which is correct for the domain-specific piece but does not yet have an infrastructure counterpart).
- No `jeff/infrastructure/typed_calls/` (Slice 8 — typed stage-level calls for proposal/evaluation/planning).
- No `jeff/infrastructure/telemetry/` subpackage — telemetry currently lives in `model_adapters/telemetry.py`, not as a standalone surface.
- No Instructor / Guardrails / BAML integration — the buildplan lists Instructor as "NOW" but it has not landed.

**Documentation for `InfrastructureServices` is stale.** `jeff/infrastructure/HANDOFF.md` only covers Slices A/B/C1/C1.5 model adapters; it does not mention the vocabulary modules or `ContractRuntime` even though both are exported from `__init__.py` and the status updates dated `2026-04-15_0900` / `_0930` / `_1010` are in `handoffs/`. This is the only module handoff I found to be materially out of sync with the code.

---

## 5. What Is Fragile or Not Working Well

**Doubled artifact store path.** `jeff.runtime.toml` sets `artifact_store_root = ".jeff_runtime/research_artifacts"`. `jeff/cognitive/research/persistence.py:52-56` then does:

```python
self.root_dir = Path(root_dir)
self._artifacts_dir = self.root_dir / "research_artifacts"
self._artifacts_dir.mkdir(parents=True, exist_ok=True)
```

So the effective on-disk location becomes `.jeff_runtime/research_artifacts/research_artifacts/`, and I can see 25 files under that nested path in the working tree. The fix is one line either way (either drop the inner `/ "research_artifacts"` in `ResearchArtifactStore.__init__` or drop the suffix from the config) but a caller who inspected the `research_artifacts/` directory the config names would see an empty folder and reasonably conclude persistence wasn't working.

**10 pre-existing test failures, all from the same cause.** Running the full test suite produces 378 passed / 10 failed. The 10 failures are:

```
tests/unit/interface/test_research_commands.py (7)
tests/integration/test_cli_research_runtime_config.py (3)
```

Every one of them is a test that constructs a `FakeModelAdapter` producing raw text like `"fake text response"` or a JSON blob, drives it through `synthesize_research`, and asserts the CLI output or the store. The new Step 1 pipeline rejects both: `bounded_syntax.validate_step1_bounded_text` refuses text that doesn't start with `SUMMARY:`, and actively refuses JSON-shaped input (`"step1 bounded text must not be JSON"`). These tests haven't been rewritten since the pipeline flipped, so they fail at `step1 bounded text must start with SUMMARY:` / `step1 bounded text must not be JSON`. The handoff `WORK_STATUS_UPDATE_2026-04-15_1010.md` confirms: *"378 unit+integration tests pass; 10 pre-existing failures confirmed unchanged from baseline."* So: this is known, it is not a new regression from the ContractRuntime adoption, but it *is* real technical debt that the rest of the suite doesn't cover and any fresh contributor will trip on.

**The `research_repair` runtime purpose is doing two jobs.** `FORMATTER_BRIDGE_RUNTIME_OVERRIDE = "research_repair"` in `formatter.py`, and `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_repair"` for the actual ModelRequest purpose. The runtime-level purpose key (`research_repair`) is the one the config and `PurposeOverrides` address, and it is explicitly being reused as the formatter adapter selector even though the name implies "repair". `InfrastructureServices.get_adapter_for_purpose` has a dedicated branch for this:

```python
if purpose == "research_repair":
    if fallback_adapter_id is not None:
        return self.get_model_adapter(fallback_adapter_id)
    return self.get_adapter_for_purpose("research")
```

This works, but the naming is a trap for readers. The research handoff flags this explicitly as a temporary bridge.

**`Purpose` enum vs `build_research_model_request` string.** The infrastructure vocabulary defines `Purpose.RESEARCH = "research"`, but `build_research_model_request` sets the `ModelRequest.purpose` field to the literal string `"research_synthesis"` (`synthesis.py:73`). Neither value is wrong — `Purpose.RESEARCH` is a *routing* key for adapter selection and `"research_synthesis"` is a *telemetry/tracing* label for the specific request — but there is no enum or constant binding them together. A future reader could reasonably expect them to match.

**`Purpose.RESEARCH_REPAIR` is enshrined in the enum even though it is explicitly described in the buildplan as a naming accident to retire.** Once `purposes.py` declares the value, removing it later is a breaking change. The enum should have been narrower.

**`json_schema` is dropped on the floor in `ContractCallRequest`.** `ContractCallRequest` has no `json_schema` field, and `ContractRuntime.invoke` hard-codes `json_schema=None` and `response_mode=_strategy_to_response_mode(strategy)` which always returns `TEXT`. The formatter bridge works only because research uses `invoke_with_request(request, adapter_id=...)`, which bypasses the strategy/mode mapping entirely and hands over a pre-built `ModelRequest`. So the "nice" path (`invoke(ContractCallRequest)`) is currently useless for any caller that needs JSON mode or JSON schema, and the research layer has had to add a second method to `ContractRuntime` to compensate. This is a real design debt — the abstraction works for the Step 1 call and breaks for the Step 3 call, and every future JSON-mode caller will hit the same wall.

**`get_adapter_for_purpose` silently swallows unknown purposes.** `PurposeOverrides.for_purpose` returns `None` for anything outside the five known keys, and the caller then either falls back to `"research_repair"` (handled specially) or the default adapter. A typo in a purpose override config key would be indistinguishable from "use the default." There is no validation path that says "you named an override we don't know about."

**Web acquisition swallows `OSError`.** `_fetch_web_page_excerpt` returns `None` on any `OSError`, which is the right behaviour for bounded best-effort extraction but means a badly-configured network environment produces empty-evidence runs that are indistinguishable from "there was no content on the page." There is no distinct `web_fetch_failed` debug event.

**`research_artifacts` global cache.** `_PUBLISHED_AT_CACHE: dict[tuple[str, int], str | None]` in `web.py:60` is module-level mutable state. It is not cleared between unrelated research runs, and the dict keys do not include the research_request or any scope, so in a long-lived process it will grow unbounded and occasionally fake up `published_at` values for URLs whose content has changed. Minor but present.

---

## 6. Canon vs Reality

This is the comparison the instructions asked for: what the canonical docs describe vs what I actually saw in the code.

### Matches — canon and reality agree

- **9-layer architecture, hard module placement, dependency rules.** `v1_doc/ARCHITECTURE.md` prescribes a 9-layer split with strict imports going "downward." The actual import graph under `jeff/` matches: `core` imports nothing else, `infrastructure` imports only `core`, `cognitive` imports `core`/`infrastructure`/`types`, `governance`/`memory`/`action` stay in their lanes, `orchestrator` imports `cognitive`/`governance`/`memory`/`core`, and `interface` is the only importer of everything. I did not find a single cross-layer back-import.
- **Transition-only mutation of truth.** `STATE_MODEL_SPEC.md` says truth changes only via transitions; `jeff/core/transition/apply.py` is the only writer of `GlobalState` in the codebase, and `CandidateState` is constructed with `replace()` (immutable), validated, and then committed or rejected. Confirmed by reading `apply.py` end-to-end.
- **`project + work_unit + run` as foundational containers.** `PROJECT_AND_WORK_UNIT_MODEL_SPEC.md` describes these; `jeff/core/containers/models.py` implements exactly these three, frozen, with typed-ID coercion, and `GlobalState.projects` is a MappingProxyType keyed by `ProjectId`.
- **Nested projects inside one global state.** `jeff/core/state/models.py:43` declares `projects: Mapping[ProjectId, Project]` as the only mutable child of `GlobalState`. There is no cross-project leakage because the only identity is the nested container.
- **CLI-first, per-command, thin operator surface.** `INTERFACE_OPERATOR_SPEC.md` calls for one CLI-first surface with no hidden business logic. `jeff/interface/commands.py` is exactly that: each command is an explicit function, and the heavy lifting all lives in `cognitive`/`orchestrator`/`core`.
- **Research owns research semantics, infrastructure owns routing.** The 3-step transition spec says this hard. `jeff/cognitive/research/*` owns bounded syntax, deterministic transform, formatter policy, synthesis orchestration, source acquisition, persistence, memory handoff; `jeff/infrastructure/*` owns adapter registry, purpose routing, `ContractRuntime`. I did not find any infrastructure code making research decisions.
- **Research artifacts are support, not truth and not memory.** Persistence writes JSON to `.jeff_runtime/research_artifacts/...` — no transitions are emitted, no memory is written without passing through `memory_handoff` which defers to the memory pipeline. Canonical.
- **3-step research pipeline, deterministic Step 2, formatter as fallback.** Matches `v1_doc/additional/3step_transition.md` exactly. Step 3 receives Step 1 bounded text, not the original evidence pack (`formatter.build_research_formatter_model_request` takes `bounded_text` as its primary input; the evidence pack is passed only to rebuild the citation key map).

### Gaps — canon says more than reality

- **`ORCHESTRATOR_SPEC.md` describes the orchestrator as an active runner with deterministic sequencing and handoff validation; implementation is a function you call.** The function is correct — it sequences, validates handoffs, applies routing, emits events — but there is no "orchestrator process." Nothing composes stage handler dicts for real flows; only tests do. Canon treats orchestration as a first-class runtime; reality treats it as a library.
- **`STATE_MODEL_SPEC.md` describes transitions over the full life of a project — create, close, attach memory, attach outcomes, etc.** `apply.py` only supports `create_project` / `create_work_unit` / `create_run`. Canon's transition vocabulary is much larger than reality's.
- **`MEMORY_SPEC.md` implies a durable memory store.** `memory/store.py` is `InMemoryMemoryStore`. Same gap as `GlobalState`.
- **`PLANNING_AND_RESEARCH_SPEC.md` describes planning as conditional but real.** `jeff/cognitive/planning.py` exists and has unit tests, but it is not wired into the running research or orchestrator paths, and it does not call a model. Canon describes a working planning subsystem; reality has the data structures.
- **`PROPOSAL_AND_SELECTION_SPEC.md` describes model-driven proposal.** `jeff/cognitive/proposal.py` is deterministic/rule-based, not model-driven. Same for `selection.py` and `evaluation.py`. Canon implies an LLM; reality has rules.
- **`INTERFACE_OPERATOR_SPEC.md` talks about persistent sessions and resumable operator context.** `CliSession` is in-memory and per-process. Resumability is not implemented.
- **`ROADMAP_V1.md` lists a set of v1 milestones; at least the orchestrator-integrated research flow milestone has not landed.** (The research handoff calls this out.)

### Reality says more than canon (reality ahead of or beside canon)

- **Infrastructure has `ContractRuntime` + `Purpose` enum + `OutputStrategy` enum + `CapabilityProfileRegistry` before anything outside research actually uses them.** These did not exist in canon until `3step_transition.md` added them, and they are currently one step ahead of the rest of the cognitive layer (only research adopts them).
- **Research is the only cognitive stage with a complete live 3-step pipeline.** Canon treats all cognitive stages roughly symmetrically; reality has research carrying the full weight.
- **The `research_repair` temporary bridge naming.** This is a reality artifact that is not in any canonical doc — it only exists in the research handoff and the code. It is not a canon violation, but a future reader going only from canon would be surprised to find it.

### Minor mismatches

- **`Purpose.RESEARCH_REPAIR`** is in the vocabulary enum even though canon's 3-step transition doc calls the formatter bridge a *temporary* naming. The enum enshrines temporary naming.
- **`build_research_model_request` sets `purpose="research_synthesis"`** on the `ModelRequest` while routing uses `"research"`. Canon's schema spec does not say whether these should be identical.
- **Bootstrap demo projects (`project-1`, `wu-1`, `run-1`, `general_research`) are hard-coded in `jeff/bootstrap.py` and `jeff/interface/commands.py` respectively.** Canon does not mandate any specific demo names, but it is worth noting that "general_research" is an implicit ambient scope that the CLI anchors to when no project is selected — it is a real convention embedded in code, not documented in canon.

---

## 7. Modularity and Architecture Review

**Layering is clean.** I looked for back-imports and found none: `core/` is a leaf; `infrastructure/` only imports from `core/` and its own submodules; `cognitive/` imports `core/`, `infrastructure/`, and `memory/` but never imports back from `orchestrator/` or `interface/`; `orchestrator/` imports `cognitive/governance/memory/core`; `interface/` imports everything downstream. The dependency direction in `ARCHITECTURE.md` holds.

**`jeff/cognitive/research/` is a good example of what a v1 submodule should look like.** Thirteen files, each with a single clear role:

| File | Role |
|---|---|
| `contracts.py` | Domain contracts: `ResearchRequest`, `SourceItem`, `EvidenceItem`, `EvidencePack`, `ResearchArtifact`, `ResearchFinding`, `Step1BoundedArtifact`, `Step1BoundedFinding`, `validate_research_provenance` |
| `bounded_syntax.py` | Step 1 syntax contract (ordered headers, paired finding lines, citation key regex) |
| `deterministic_transformer.py` | Step 2 mechanical parse → `Step1BoundedArtifact` → candidate payload |
| `fallback_policy.py` | Step-2-to-Step-3 gate: `decide_formatter_fallback` |
| `formatter.py` | Step 3 formatter request builder + sanitizer + output validator |
| `synthesis.py` | Orchestration: build request, call ContractRuntime/adapter, run Step 2, maybe Step 3, validate, remap, produce `ResearchArtifact` |
| `documents.py` | Bounded local-file source acquisition |
| `web.py` | Bounded web source acquisition |
| `persistence.py` | JSON-on-disk support store with fail-closed validation on save *and* load |
| `memory_handoff.py` | Distillation + delegation to the memory write pipeline |
| `debug.py` | Research debug event emitter and summary helpers |
| `errors.py` | Domain errors |
| `legacy.py` | Retained `ResearchResult` compatibility shell |
| `validators.py` | Shared candidate-payload schema + validators |

The only real coupling between these is that `persistence.py` imports `synthesize_research_with_runtime` to provide `run_and_persist_document_research` / `run_and_persist_web_research` convenience wrappers (`persistence.py:243-281`). That is *borderline* — persistence arguably shouldn't import synthesis — but it is a thin wrapper, not a dependency that couples the contracts. I'd leave it alone.

**Infrastructure has a slightly muddled shape.** `jeff/infrastructure/` is mostly flat: `runtime.py`, `config.py`, `contract_runtime.py`, `purposes.py`, `output_strategies.py`, `capability_profiles.py`, plus `model_adapters/` as a subpackage. That is fine for the current scope, but there are four things the buildplan wants (fallback policies, typed calls, telemetry, vocabulary) and only one of them (vocabulary) is a real subpackage shape. The other three are flat files or live inside `model_adapters/`.

**`jeff/orchestrator/` is nicely factored.** Six files: `flows.py` (flow vocabulary), `routing.py` (non-forward outcomes), `runner.py` (runner), `lifecycle.py` (state machine), `validation.py` (handoff + sequence + output validation), `trace.py` (events). The runner is ~350 lines and easy to read.

**`jeff/interface/commands.py` is 1047 lines and is the largest single file in the live path.** That is not a crisis — each command handler is a small function — but it is the file I'd watch. If proposal/selection/memory surfaces also become CLI commands, this file will outgrow its current shape and should probably split into `commands/research.py`, `commands/inspect.py`, `commands/lifecycle.py`, etc.

**Thin modules don't yet justify subpackages.** `jeff/action/`, `jeff/memory/`, `jeff/governance/`, and the flat `jeff/cognitive/*.py` files (context/proposal/selection/planning/evaluation) are all 3-6 files each, typed-and-rule-based, with minimal behavior. Promoting any of them to package shape *right now* would be premature — wait until one of them actually sprouts a pipeline the way research did.

---

## 8. Research Review

Research is the centerpiece of this review because it is the vertical that actually runs end-to-end through infrastructure today.

### What actually happens when you run `/research docs "question" path/`

1. `commands._research_command` parses the command line and builds a `ResearchRequest` with explicit `document_paths`. Scope defaults to the current CLI scope or `general_research` if no project is selected.
2. It calls `run_and_persist_document_research(request, infrastructure_services, store, debug_emitter=...)` in `persistence.py:234-257`.
3. That calls `collect_document_sources(request)` → `build_document_evidence_pack(request, sources)` from `documents.py`. Discovery walks paths, filters by extension set, reads each file (UTF-8, bounded `max_chars_per_file`), snippets them, assigns stable `document-{sha1[:12]}` source IDs. Evidence pack segmentation scores paragraphs by query-token overlap, picks top `max_evidence_items`, detects contradiction markers in scored segments.
4. It then calls `synthesize_research_with_runtime(...)` in `synthesis.py:140-233`. That function:
   - pulls `infrastructure_services.contract_runtime`
   - resolves the research adapter via `get_adapter_for_purpose("research")`
   - resolves the formatter adapter via `get_adapter_for_purpose(FORMATTER_BRIDGE_RUNTIME_OVERRIDE, fallback_adapter_id=...)`
   - delegates to `synthesize_research(..., contract_runtime=runtime)`.
5. `synthesize_research` builds a Step 1 `ModelRequest` via `build_research_model_request` (TEXT mode, reasoning_effort=medium, max_output_tokens=1200, purpose string `"research_synthesis"`, `expected_output_shape="step1_bounded_text_v1"`), then calls `_invoke_step1_bounded_text_and_transform`, which:
   - calls `contract_runtime.invoke_with_request(request, adapter_id=...)` when a runtime is present, otherwise `adapter.invoke(request)`
   - runs `validate_step1_bounded_text(bounded_text)`
   - runs `transform_step1_bounded_text_to_candidate_payload(bounded_text)`
   - on `ResearchSynthesisValidationError`, raises `deterministic_transform_failed`
6. On Step 2 failure, `synthesize_research` calls `decide_formatter_fallback(bounded_text=..., transform_error=...)`. If allowed, `_attempt_formatter_fallback` builds a JSON-mode `ModelRequest` through `build_research_formatter_model_request` (purpose `"research_synthesis_repair"`, routes via `research_repair` override to the formatter adapter), dispatches via `contract_runtime.invoke_with_request(..., adapter_id=formatter_adapter.adapter_id)`, validates the JSON output against the candidate payload schema, and produces a candidate payload.
7. Either way, the candidate payload is remapped back from citation keys (`S1..Sn`) to internal source IDs, provenance validation runs (fail-closed), and a `ResearchArtifact` is produced.
8. `persist_research_artifact` builds a `ResearchArtifactRecord` via `build_research_artifact_record` — which re-runs provenance validation — assigns a stable `research-{sha1[:16]}` artifact ID derived from content + nonce, and writes JSON to the store.
9. If `handoff_memory=true`, the CLI also calls `handoff_persisted_research_record_to_memory`, which checks `should_handoff_research_to_memory`, distils the artifact into a `MemoryCandidate`, and calls `write_memory_candidate` — which *may* return a write/reject/defer decision. The research layer does not decide; the memory pipeline does.

### Step 1 bounded-text contract

The contract is exactly as strict as it needs to be. `bounded_syntax.py` enforces:

- Required sections in canonical order: `SUMMARY:`, `FINDINGS:`, `INFERENCES:`, `UNCERTAINTIES:`, `RECOMMENDATION:`. Out-of-order or extra sections fail.
- Findings are paired text/cites lines; any unpaired or wrong-prefixed finding fails.
- Inferences/uncertainties are bullet lines with a specific prefix; anything else fails.
- Citation keys are restricted to `^S[1-9][0-9]*$`; text that contains non-citation identifiers will fail provenance later.
- Text that contains fenced code blocks or that looks like JSON is rejected up front (explicit grammar guard).

Step 2 (`deterministic_transformer.parse_step1_bounded_text`) is *purely* mechanical: split sections, pair finding lines, strip prefixes, validate. It does not infer. If something fails, it fails loud. This is the right invariant.

### Step 3 formatter fallback

`formatter.build_research_formatter_model_request` takes only the already-validated Step 1 bounded text + the citation key map + the transform failure reason + a reference to the primary request (for request_id continuity). It deliberately does **not** receive the evidence pack, preventing Step 3 from reintroducing evidence-driven generation — the exact red flag the buildplan calls out. The system instructions say "Preserve only content already materially present in the bounded artifact." The JSON schema built via `validate_candidate_research_payload` is locked to allowed citation keys. This is correct by the letter of the spec.

The **one** thing that bothers me is that Step 3 is still dispatched under a runtime purpose named `research_repair`. That is a naming trap even if functionally correct. See §12.

### Provenance

`validate_research_provenance` in `contracts.py:299-354` runs on construction of the record and again on load. It rejects duplicates, unknown source IDs, empty source_refs, and findings/evidence items that point at non-existent sources. Citation key remap from `S*` back to internal source IDs happens *before* this validation, so a bad remap shows up as an unknown-source-id error rather than silently corrupting the record.

### Persistence

`persistence.py` writes validated artifacts as pretty-printed JSON with sorted keys and a stable content-hashed `artifact_id`. It emits a debug event pair (`artifact_store_save_started` / `_succeeded`) around each save, a debug pair around each load, and a failure event on malformed files. `ResearchArtifactRecord` carries the whole source item list and evidence items, which is correct — a later reader can verify provenance without needing the original evidence pack.

The **doubled path** bug (§5) lives here.

### Web / document acquisition

Both acquisition paths split correctly into discover → extract → compose. `documents.py` walks paths with a whitelist of extensions, reads with a NUL-byte probe to reject binaries, and computes a stable `document-{sha1[:12]}` source ID. `web.py` search uses `html.duckduckgo.com/html/` with `JeffResearch/0.1` as the UA, parses results with a handwritten `HTMLParser`, fetches pages with a 10-second timeout and a bounded read, extracts with a second `HTMLParser`, and scores segments against query tokens. Published dates are extracted from meta tags and JSON-LD and cached module-globally (minor issue, §5).

### What I'd trust and what I'd watch

- **Trust:** bounded syntax, deterministic transform, provenance validation, persistence correctness, acquisition shape, Step 3 receiving only bounded text. The research handoff accurately describes what is live.
- **Watch:** the formatter purpose naming, the doubled artifact path, the 10 failing tests that still carry the old JSON-first assumptions, the `_PUBLISHED_AT_CACHE` global, and the fact that nothing outside research has yet been rewritten against this pattern.

---

## 9. Infrastructure Review

### Scope

Infrastructure right now owns:

- `config.py` — TOML loading, `JeffRuntimeConfig`, `AdapterConfig`, `PurposeOverrides`, `ResearchRuntimeConfig`.
- `runtime.py` — `InfrastructureServices`, `build_infrastructure_services`, `build_model_adapter_runtime_config`.
- `model_adapters/` — `ModelRequest`, `ModelResponse`, `ModelAdapter` base, `AdapterRegistry`, `FakeModelAdapter`, `OllamaModelAdapter`, telemetry, factory, errors.
- `purposes.py` — `Purpose` enum.
- `output_strategies.py` — `OutputStrategy` enum.
- `capability_profiles.py` — `CapabilityProfile` + registry.
- `contract_runtime.py` — `ContractCallRequest` + `ContractRuntime`.

### What is solid

- **Config loading is strict and explicit.** `load_runtime_config` requires `[runtime]` and `[research]` tables; `[[adapters]]` must be a non-empty list of tables with unique IDs; `purpose_overrides` is optional. Missing fields raise `ValueError` with clear messages. Duplicate `adapter_id` is caught in `JeffRuntimeConfig.__post_init__`. `_normalize_provider_kind` restricts to `{"fake", "ollama"}`.
- **`InfrastructureServices` is small and explicit.** `get_default_model_adapter`, `get_model_adapter(adapter_id)`, `get_adapter_for_purpose(purpose, fallback_adapter_id=None)`, and the `contract_runtime` property. `build_infrastructure_services` actively *warms* the default adapter and any overridden adapters at construction time so a missing adapter fails fast.
- **`ModelRequest` / `ModelResponse`** (`model_adapters/types.py`) are immutable, validated on construction, and the validation rules are right: JSON schema only with JSON mode, completed responses must carry output text or JSON, `reasoning_effort` is normalized to a stripped string. No surprise permissiveness.
- **`ContractRuntime.invoke(ContractCallRequest)`** is the clean path for TEXT-mode purpose-routed calls. `invoke_with_adapter` is the clean path for repair/retry when the adapter is pre-chosen. Both exist and are independently unit-tested (`tests/unit/infrastructure/test_contract_runtime.py`).
- **Purpose enum and OutputStrategy enum** are intentionally thin. `Purpose.known_names()` and `OutputStrategy.requires_delimiter_extraction()` are the only convenience helpers; nothing tries to turn them into dispatch tables yet.
- **Capability profile registry** is immutable and functional (`with_profile` returns a new registry). Lightweight and easy to grow later.

### What is weak

- **`ContractCallRequest` can't express JSON mode or JSON schema or reasoning effort.** This is the reason research had to add `invoke_with_request(request, adapter_id=...)` — the formatter bridge needs JSON mode and a JSON schema, and the clean path couldn't carry them. `_strategy_to_response_mode` unconditionally returns `TEXT` for all three current strategies, and `invoke()` hard-codes `json_schema=None, reasoning_effort=None`. This means the first non-research caller that needs JSON will hit exactly the same wall and either add a *third* method or give up on the clean path. The right fix is to add `response_mode`, `json_schema`, and `reasoning_effort` to `ContractCallRequest`, or to derive them from a richer `OutputStrategy` (e.g. a `JSON_SCHEMA_BOUND` strategy).
- **`Purpose.RESEARCH_REPAIR` is enshrined.** Once the enum has a value, removing it is a breaking change. Canon explicitly calls this name temporary; the enum makes it permanent.
- **The HANDOFF is stale.** `jeff/infrastructure/HANDOFF.md` only covers the old model-adapter slices; it does not mention the new vocabulary modules or `ContractRuntime`. A reader using the handoff to understand infrastructure ownership would miss four of the module's files. This is the only material doc drift I found.
- **`get_adapter_for_purpose("research_repair", ...)` special-cases the formatter bridge in infrastructure.** That branch in `runtime.py:36-44` is research-specific logic that has leaked into the infrastructure layer. It is *small* and documented by the `research_repair` bridge note, but it breaks the "infrastructure owns no domain semantics" invariant slightly.
- **There is no `ModelTelemetry` surface for the CLI to ingest.** Telemetry currently lives per-adapter in `model_adapters/telemetry.py` and is returned inside `ModelResponse.warnings`/`usage`. The buildplan calls for a centralized telemetry subpackage; it is not there.
- **Provider list is tiny.** `ollama` + `fake`. No OpenAI-compatible provider, no Anthropic provider. That is not a criticism of v1 scope — it is just the reality — but any model experimentation beyond local Ollama needs a new provider to land first.

### How adoption is going

Research has adopted `ContractRuntime` via `invoke_with_request` + `_services.get_adapter_for_purpose`. No other cognitive stage has adopted it. The `WORK_STATUS_UPDATE_2026-04-15_1010.md` handoff explicitly flags "consider migrating ContractCallRequest to support reasoning_effort so Step 1 can use invoke() instead of invoke_with_request, or proceed to Proposal/Evaluation adoption" as the next step. I agree with the first half and think it should happen before the second.

---

## 10. Interface / Operator Surface Review

### Shape

`jeff/interface/` is exactly five files: `cli.py` (JeffCLI class, one-shot vs interactive), `commands.py` (command dispatch + handlers, 1047 lines), `render.py` (text renderers for each view), `json_views.py` (JSON renderers for each view), `session.py` (tiny scope/mode holder). Entry points are `jeff/main.py` and `jeff/__main__.py`.

### What is solid

- **Commands are explicit.** `execute_command` in `commands.py:89-164` is a clean if/elif chain over `help`, `project`, `work`, `run`, `scope`, `mode`, `json`, `inspect`, `show`, `trace`, `lifecycle`, `research`, and the `approve/reject/retry/revalidate/recover` request-like commands. No command inference, no natural-language parsing, no hidden routes.
- **`CommandResult` carries both text and JSON payloads.** That lets the same command serve both modes without handlers caring which one is active.
- **Debug mode is orthogonal.** `/mode debug` toggles `session.output_mode`; when on, any command that emits research debug events will print them line-by-line above the final result. The plumbing goes through `CommandResult.debug_events` so it survives exception paths (`_compose_exception_output` in `cli.py:91-100` re-renders debug events alongside the error).
- **Truthful error rendering.** `ResearchSynthesisRuntimeError` has a dedicated JSON view (`research_error_json`) that preserves scope, mode, and debug events. The CLI does not swallow or reshape errors.
- **Read-only reads, mutation via transition.** `InterfaceContext` is a frozen dataclass that holds `state: GlobalState`, `flow_runs`, `infrastructure_services`, `research_artifact_store`, `memory_store`, `research_memory_handoff_enabled`. Anything that changes state goes through `apply_transition`. The CLI itself does not mutate state.
- **"general_research" anchoring is deliberate.** When no project is selected, `/research docs` and `/research web` anchor to the built-in `general_research` project so there is always a scope. This is documented in `jeff/interface/HANDOFF.md`. It is a small convention but a correct one.
- **Session is trivially serializable.** `CliSession` (64 lines) holds only scope IDs and a few flags; no opaque state.

### What is weak

- **`commands.py` at 1047 lines is already at the limit of "one big file is fine."** Each new cognitive surface the CLI grows (memory inspection, orchestrator flow dispatch, etc.) will push it bigger. Splitting on command family is a reasonable near-term cleanup, but I wouldn't do it *yet* — do it the first time a new command group lands.
- **The demo state (`project-1`, `wu-1`, `run-1`) is hard-coded in `build_demo_state`.** This is fine for a CLI demo, but any operator trying to bring their own state would have to write their own `InterfaceContext` builder because `JeffCLI` does not accept an alternative state bootstrapper. This is a missing injection point, not a bug.
- **There is no TTY detection.** `run_interactive` iterates arbitrary input lines; nothing currently reads from stdin in a live prompt loop. That is probably a `main.py`-level concern — I did not inspect `main.py` in full for this audit.
- **Truthfulness invariants are not enforced by tests for every command.** There are good research-path tests but no test that says "no command ever modifies `state` outside a transition." That invariant is upheld by code discipline.

---

## 11. Test Suite Review

### Shape

`tests/unit/` mirrors the module layout: `action/`, `cognitive/`, `core/`, `governance/`, `infrastructure/`, `interface/`, `memory/`, `orchestrator/`. `tests/integration/` is a flat directory of end-to-end scenarios, mostly research-focused.

### Coverage highlights

- **Research is thoroughly tested.** Unit tests cover bounded syntax (`test_research_bounded_syntax.py`), deterministic transformer (`test_research_deterministic_transformer.py`), contract-runtime adoption (`test_research_contract_runtime_adoption.py`), citation keys (`test_research_synthesis_citation_keys.py`), memory handoff (`test_research_memory_handoff.py`), persistence (`test_research_persistence.py`), provenance consistency (`test_research_provenance_consistency.py`), publish-date support (`test_research_publish_date_support.py`), source cleaning (`test_research_source_cleaning.py`), post-validation linkage (`test_research_post_validation_linkage.py`), the repair pass (`test_research_synthesis_repair_pass.py`), and runtime errors (`test_research_synthesis_runtime_errors.py`). Integration tests cover the CLI research flow, source transparency, source metadata, failure surface, synthesis runtime errors, debug stream, runtime config, document research end-to-end, web research end-to-end, memory handoff flow, persistence flow, provenance consistency, citation key flow, and the formatter fallback flow. That is a healthy set.
- **Infrastructure is covered at the unit level.** `test_runtime_config.py`, `test_runtime_services.py`, `test_runtime_purpose_overrides.py`, `test_model_adapter_types.py`, `test_model_adapter_registry.py`, `test_model_adapter_factory.py`, `test_model_adapter_telemetry.py`, `test_fake_model_adapter.py`, `test_ollama_model_adapter.py`, plus the new `test_purposes.py`, `test_output_strategies.py`, `test_capability_profiles.py`, `test_contract_runtime.py`. All 81+ of these pass. `build_infrastructure_services` fails fast when adapters are missing, which is exercised.
- **Orchestrator has a handoff validation test.** `tests/integration/test_orchestrator_handoff_validation.py` exercises real flows against deterministic stage handlers. `tests/unit/orchestrator/` covers flows, routing, validation, lifecycle, and trace individually.
- **Core is lean but covered.** `tests/unit/core/` tests transition validators, container invariants, typed IDs, scope, envelopes.
- **Governance negative boundaries.** `tests/integration/test_governance_negative_boundaries.py` confirms that policy/readiness/approval refusal produces routing decisions the orchestrator can act on.

### Coverage gaps

- **No end-to-end orchestrator test that drives a full `bounded_proposal_selection_action` flow against live state and real handlers.** The orchestrator tests use deterministic handler dicts, which is fine, but they don't prove that the rest of the cognitive layer composes into a flow.
- **No test for the doubled artifact path.** The store tests all write to a tmp_path, so the `_artifacts_dir = root / "research_artifacts"` nesting is visible but never asserted against. A hand-configured runtime config like the live one would surface it.
- **No test for `ContractCallRequest` + `invoke` happy path being useful for research.** The adoption tests use `invoke_with_request` — the path that proved necessary because `invoke` couldn't carry the necessary fields. There is no test for "research uses `invoke(ContractCallRequest)` end-to-end," because that path does not work yet.
- **No test for CLI truthfulness invariants** (nothing mutates state outside transitions).
- **No persistence test for `GlobalState`.** This is because there is no persistence.
- **No test for stale-config rejection** (e.g., a purpose override pointing at a non-existent adapter is caught by `build_infrastructure_services` during warm-up, but there is no failing test named after it).

### Pre-existing failures

`python -m pytest tests/unit tests/integration -q` in my run produces:

```
378 passed, 10 failed in 1.49s
```

All 10 failures live in two files and all have the same root cause — fake-adapter text that isn't Step 1 bounded text:

```
tests/unit/interface/test_research_commands.py::test_docs_command_parses_correctly
tests/unit/interface/test_research_commands.py::test_web_command_parses_correctly
tests/unit/interface/test_research_commands.py::test_research_without_project_scope_anchors_into_general_research_lawfully
tests/unit/interface/test_research_commands.py::test_research_with_current_project_and_work_unit_uses_current_scope
tests/unit/interface/test_research_commands.py::test_handoff_memory_flag_toggles_memory_handoff_explicitly
tests/unit/interface/test_research_commands.py::test_research_json_mode_returns_research_result_payload
tests/unit/interface/test_research_commands.py::test_research_json_payload_keeps_support_distinct_from_truth
tests/integration/test_cli_research_runtime_config.py::test_cli_research_works_with_runtime_config_and_anchors_general_research
tests/integration/test_cli_research_runtime_config.py::test_runtime_configured_research_adapter_is_used_instead_of_default_adapter
tests/integration/test_cli_research_runtime_config.py::test_runtime_configured_handoff_memory_still_delegates_to_current_memory_layer
```

Representative error:

```
ResearchSynthesisValidationError: step1 bounded text must start with SUMMARY:
```

and

```
ResearchSynthesisValidationError: step1 bounded text must not be JSON
```

The 10 failures do not indicate a new regression. They indicate that these 10 tests still carry the old JSON-first assumption and the fake adapter fixtures they build return either plain text (`"fake text response"`) or a JSON-shaped blob the new pipeline correctly refuses. These tests should be rewritten to have the fake adapter produce a valid Step 1 bounded-text artifact — it's a ~5-line fixture change per test. See §12 and §13.

---

## 12. Technical Debt and Temporary Bridges

In priority order (highest to lowest).

### Priority 1

**`research_repair` runtime purpose naming.** `formatter.py:13` defines `FORMATTER_BRIDGE_RUNTIME_OVERRIDE = "research_repair"` and `FORMATTER_BRIDGE_REQUEST_PURPOSE = "research_synthesis_repair"`. `runtime.py:36-44` has a dedicated `if purpose == "research_repair"` branch. `Purpose.RESEARCH_REPAIR` enshrines it in the infrastructure enum. The 3-step transition doc calls this a *naming accident*. Fixing this is the single highest-signal cleanup because it restores the "infrastructure owns no domain semantics" invariant. Suggested rename: `formatter_bridge` (or whatever lives in `OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER`).

**`ContractCallRequest` cannot carry JSON mode / JSON schema / reasoning effort.** The clean `invoke()` path is unusable for Step 3 and for any future JSON-mode caller. Research had to add `invoke_with_request(request, adapter_id=...)` to compensate. This is *active* debt — every future caller either works around it or makes it worse.

**10 pre-existing test failures from the old JSON-first assumption.** They masquerade as a regression risk to any contributor who runs the full suite. The fix is fake-adapter fixture updates, not product code changes.

### Priority 2

**Doubled artifact store path bug.** `persistence.py:52-56` appends `research_artifacts` to an already-`research_artifacts`-named root. Pick one side of the convention and delete the other. I'd vote for dropping the suffix in `persistence.py` so `artifact_store_root` in the config is the literal directory.

**`jeff/infrastructure/HANDOFF.md` is stale.** Does not mention `purposes.py`, `output_strategies.py`, `capability_profiles.py`, or `contract_runtime.py`. Needs a one-pass update.

**`legacy.py` / `ResearchResult` compatibility shell.** `jeff/cognitive/research/legacy.py` still exists because real callers/tests use it. The research handoff is honest about this. The debt cost is small right now but will grow every time a new feature is tempted to add "one more legacy shim."

### Priority 3

**`_PUBLISHED_AT_CACHE` global in `web.py`.** Module-level mutable state keyed on `(url, max_chars)`; unbounded growth in a long-lived process; not scoped to a research run.

**No validation for unknown `purpose_overrides` keys.** A typo in `jeff.runtime.toml` is silently ignored.

**`commands.py` at 1047 lines.** Not a problem today; will be a problem on the next command group.

**`purpose="research_synthesis"` in `build_research_model_request` vs `Purpose.RESEARCH = "research"` in the enum.** Not wrong, just unbound. Add a short constant linking them or drop one.

**Research debug emitter is ad-hoc.** Every research-layer function takes a `debug_emitter=None` parameter and emits strings; there is no structured contract for checkpoint names. A reader has to grep `emit_research_debug_event` call sites to know which checkpoints exist. A tiny `DebugCheckpoint` enum would help.

**`research.synthesize_research` accepts `**legacy_kwargs` and pops `repair_adapter` for backward compat.** (`synthesis.py:104-107`). This is a surface backward-compat shim that was explicitly called out as *intentional* in the handoff. It is fine to leave until the legacy callers are retired.

### Explicit bridges I am *not* labelling as debt

- **`legacy.py` exists, is isolated, and is documented.** Until you can point at "0 callers of `ResearchResult`" you should not delete it.
- **`invoke_with_request` exists as a deliberate infrastructure affordance for domain callers that need full control of `ModelRequest`.** This is not debt on its own — the debt is that `invoke` is *too thin* for JSON mode, not that `invoke_with_request` exists.
- **Demo state in `bootstrap.py`.** This is a CLI demo seed, not debt.

---

## 13. Refactor Candidates

Small, concrete, reversible. None of these is "rewrite the module." Each has a rough shape.

### R1. Retire `research_repair` runtime purpose naming (highest value)

Rename `FORMATTER_BRIDGE_RUNTIME_OVERRIDE` from `"research_repair"` to a non-domain-leaked name like `"research_formatter_bridge"` (or better, make the override a plain adapter ID lookup and not a named purpose at all). Remove `Purpose.RESEARCH_REPAIR`. Remove the `if purpose == "research_repair"` branch in `runtime.py`. Update `jeff.runtime.toml` to use the new override key or, if we drop named overrides, use `CapabilityProfileRegistry` for formatter adapter selection. Update `formatter.py` to address the adapter through the chosen mechanism. Update `purpose_overrides.research_repair` in the TOML accordingly.

Risk: low — there's only one caller of the old name (formatter), the config migration is trivial, and the tests that currently reference the name are the same failing tests from §11 that already need rewriting.

### R2. Fatten `ContractCallRequest` to carry JSON mode + reasoning effort

Add `response_mode: ModelResponseMode = ModelResponseMode.TEXT`, `json_schema: dict | None = None`, `reasoning_effort: str | None = None` to `ContractCallRequest`. Update `ContractRuntime.invoke` to forward them. Keep `invoke_with_request` as-is for callers that want to build the full `ModelRequest` themselves. Then let research's Step 1 path use `invoke(ContractCallRequest(...))` and retain `invoke_with_request` only for Step 3 (until that too can be expressed).

Risk: low — it is an additive API change. Existing callers still work.

### R3. Fix the doubled artifact store path

In `persistence.py:52-56`, drop the `/ "research_artifacts"` suffix so `ResearchArtifactStore(root_dir)` writes directly into `root_dir`. Or, alternatively, keep the suffix and change the default in `config.py` from `.jeff_runtime` to not include `research_artifacts`. Pick one side. Write a test that asserts the path is exactly the configured value.

Risk: low — one-liner. Existing persisted artifacts under the doubled path can be moved manually or left where they are for local dev.

### R4. Migrate `jeff/infrastructure/HANDOFF.md` to current state

One pass. Add the vocabulary modules, `ContractRuntime`, and the `contract_runtime` property. Move the old slice A/B/C1/C1.5 notes into the "history" section or the `WORK_STATUS_UPDATE.md` index.

Risk: zero — documentation only.

### R5. Rewrite the 10 failing test fixtures against Step 1 bounded text

Each failing test builds a `FakeModelAdapter` that returns either plain text or a JSON blob. Replace those fixtures with a helper that returns a valid Step 1 bounded-text artifact (5 sections in order, paired finding lines, S1..Sn citation keys) derived from the test's evidence pack. The tests themselves should not need to change — just the fake adapter wiring.

Risk: low and localized. Once done the full suite should be 388/388.

### R6. Extract command groups from `commands.py`

Only when the next command group lands. Split into `commands/_dispatch.py`, `commands/research.py`, `commands/inspect.py`, `commands/lifecycle.py`, `commands/request.py`. Keep `execute_command` in `_dispatch.py` as the single entry point. Do not do this until there's a real motivation.

Risk: low but churn-heavy; skip until there's a second reason.

### R7. Add a structured `ResearchDebugCheckpoint` enum

Every current `emit_research_debug_event` call uses a string literal. Grepping `emit_research_debug_event(debug_emitter, "...` shows ~25 distinct checkpoint names across research. A thin enum (or frozen set + constants) would let tests assert against the presence of a named checkpoint instead of the current "the string literal was emitted" pattern.

Risk: low, optional.

### R8. Dedicate a small `InfrastructureError` for validated purpose misconfigurations

Currently, an invalid `purpose_overrides.*` key is silently ignored (`PurposeOverrides.for_purpose` returns `None` for unknown purposes). Introduce a single validation pass in `build_infrastructure_services` that rejects unknown override keys. This is a few lines; it pays itself back on the first typo.

Risk: low.

### Refactors I would *not* recommend now

- **Rewriting the orchestrator to be a live daemon.** Premature until v1 canon's scope is frozen.
- **Promoting `action/` or `memory/` or `governance/` to packages.** Premature — they are 3-6 files and fine as flat modules.
- **Replacing the hand-rolled HTML parser in `web.py` with BeautifulSoup or lxml.** Would drag in a new dependency for something that is deliberately bounded; wait until the web path sprouts real ranking/freshness logic.
- **Rebuilding `persistence.py` on SQLite.** The JSON-on-disk shape is correct for bounded support records. If you want queryability, add a read index, not a database.
- **Adding Instructor / BAML / Guardrails.** The buildplan labels these "NOW" but the actual work they would do is exactly what the bounded-text + deterministic transformer + JSON-mode formatter already does. Wait until there's a concrete user-visible payoff.

---

## 14. Recommended Next Path

I think there are two reasonable next paths, and the wrong one is to start the Proposal/Evaluation adoption.

**Recommended: a tight infrastructure-hardening slice, *before* any Wave 2 adoption.**

In priority order, the single coherent next slice is:

1. **R2** — fatten `ContractCallRequest` with `response_mode`, `json_schema`, `reasoning_effort`. Rewrite research's Step 1 path to use `invoke(ContractCallRequest)`. Keep `invoke_with_request` for Step 3.
2. **R1** — retire `research_repair` naming in infrastructure (purposes enum, runtime branch, formatter constant, TOML override key). Let the formatter bridge be selected by adapter ID through the contract runtime, not by a confusingly-named purpose.
3. **R3** — fix the doubled artifact store path, and add a test that catches it.
4. **R5** — fix the 10 failing tests by updating fixture fake adapters to produce Step 1 bounded text.
5. **R4** — refresh `jeff/infrastructure/HANDOFF.md`.

This is ~1-2 days of focused work, it is entirely inside infrastructure + research + tests, it does not change any canonical semantics, and when it's done the repo is materially cleaner for Wave 2.

**Rationale for doing this before Wave 2:** If the next cognitive stage (proposal, then evaluation) adopts `ContractRuntime` *before* the clean `invoke(ContractCallRequest)` path supports JSON mode, they will either (a) end up using `invoke_with_request` and setting a precedent for every future stage to bypass the clean path, or (b) invent their own wrappers, duplicating the problem. Fixing the clean path *first* costs nothing extra — the research Step 3 call still uses `invoke_with_request` anyway — but it removes the trap for the next stage.

The *second* next path, after this, is:

- **Proposal → ContractRuntime adoption.** Start with proposal because it is the next cognitive stage on the canonical backbone after research and because it has deterministic unit tests already in place to anchor the migration. Keep the rule-based path as a strict fallback until the model-backed path is at parity.

**What I would explicitly NOT do next:**

- **Do not start orchestrator-integrated research yet.** The research CLI path is working and the orchestrator flow exists; integrating them is busywork that does not close any of the real gaps.
- **Do not add new providers (OpenAI, Anthropic).** The v1 scope is local Ollama + fake; providers should land alongside a real feature that needs them, not speculatively.
- **Do not start persistence of `GlobalState`.** That is canonical work and should be scheduled only after you know what transitions you actually need.
- **Do not rewrite `commands.py`.** Not yet.
- **Do not introduce Instructor / Guardrails / BAML.** Not yet.

---

## 15. Vision and Planning Improvements

This section is *suggestions for the canon*, not code changes. I have kept them narrow.

### Where the canon is already right

- **The 9-layer split with hard dependency direction.** The codebase confirms this is enforceable.
- **Transition-only mutation of truth.** Even in a half-implemented reality, this is the single invariant that has kept state reasoning clean.
- **Research owns semantics, infrastructure owns routing.** The `ContractRuntime` adoption shows this is a workable boundary — the one place it breaks (the `research_repair` special-case in `runtime.py`) is visibly ugly, which is the right failure mode.
- **Research artifacts are support records, not truth and not memory.** This is what lets persistence be simple JSON and memory handoff be a thin distillation.
- **Step 2 is deterministic, Step 3 only sees Step 1 bounded text.** The buildplan's red-flag checklist encodes exactly the foot-guns the first JSON-first implementation tripped on.

### Where I would sharpen the canon

1. **Name the formatter bridge vocabulary before v1 freezes.** `v1_doc/additional/3step_transition.md` is explicit that `research_repair` is a temporary name, but `v1_doc/ARCHITECTURE.md` and `PLANNING_AND_RESEARCH_SPEC.md` do not mention the formatter bridge at all. Add a short section to the architecture spec that says "the formatter bridge is selected via `OutputStrategy.BOUNDED_TEXT_THEN_FORMATTER` and an adapter addressable by capability profile, *not* by a purpose-named override." This closes off the foot-gun at the spec level.
2. **Specify `ContractCallRequest`'s surface.** The transition doc describes `ContractRuntime` but not the full shape of a call request. If the spec had said "the call request must carry response_mode, json_schema, and reasoning_effort" from the start, the current `invoke` / `invoke_with_request` split would not have been needed.
3. **Spec the debug checkpoint vocabulary.** The research layer emits ~25 debug checkpoints. The interface operator spec talks about `/mode debug` but does not enumerate the checkpoints. A small table in the spec would make the operator surface testable.
4. **Explicit handoff for "stale infrastructure doc allowed."** The handoff structure spec says handoffs are support, not canon. But there is no rule that says "a submodule handoff MUST reflect all currently-merged files in the module it owns." Add that — it would have caught the stale `jeff/infrastructure/HANDOFF.md`.
5. **Add a v1 decision about `GlobalState` persistence.** Right now canon implies it, the code does not have it, and the handoffs do not say when it will land. A one-paragraph decision — "v1 keeps state in-memory; durable state is a v1.1 milestone; transitions are designed to be replayable" — would stop readers from assuming it is already done.
6. **Add a v1 decision about `transition_type` vocabulary.** Canon describes transitions as the only truth-mutating path, but does not enumerate the v1 transition types. Today the code supports three. Nailing down which transitions v1 must support (and which explicitly are v1.1) would let the rest of the cognitive layer know what its "edge" with truth looks like.
7. **Sharpen the planning / research boundary.** `PLANNING_AND_RESEARCH_SPEC.md` puts them in the same document; in code they are separate modules and planning is dormant. Consider splitting the spec into two, with planning labeled "v1.1 if not needed now."
8. **Identify what Wave 2 adoption looks like concretely.** `3step_transition_buildplan.md` describes Slices 1-9 for research; it does not describe the equivalent slices for proposal or evaluation. A named Wave 2 Slice 1 would make the next piece of work estimable.
9. **State the "infrastructure owns no domain semantics" invariant as an enforceable rule.** Today it is implicit. A short section in `ARCHITECTURE.md` that says "no `if purpose == '...':` branches in `jeff/infrastructure/`" would be testable by grep.
10. **Decide what "selection ≠ permission, approval ≠ applied, outcome ≠ evaluation" means for the CLI.** The interface spec mentions these distinctions, but the CLI does not have commands that exercise them all (there is `/approve` / `/reject` / `/retry` / `/revalidate` / `/recover` for requests, but no `/select`, no `/outcome`, no `/evaluate`). Either the spec should narrow to "these are backbone concepts, not CLI commands," or the CLI should grow the matching surfaces.

### Process / methodology suggestions

- **Handoff-first drift guard.** The stale `jeff/infrastructure/HANDOFF.md` is the one real drift I found. A lightweight rule — "whenever a new file lands under `jeff/<module>/`, the module's HANDOFF.md owned-files list must be updated in the same change" — would have caught it.
- **One failing-test budget.** 10 pre-existing failures across the suite is small but sticky. An explicit rule — "no new commit increases the failing count; any increase must be accompanied by an issue" — would prevent this number from growing.
- **Reality-vs-canon section in handoffs.** Most submodule handoffs already have a "Current Implementation Reality" section. A companion "Canon Gap" section, even if it is just a list of bullet points, would make the canon-vs-reality comparison easier on future reviewers (and on future me).
- **Priority-tagged buildplans.** `3step_transition_buildplan.md` lists Slices 1-9 without explicit relative priority. Tagging "P1: must land for wave 1," "P2: can slip to wave 2," etc. would make the remaining work easier to sequence.
- **One audit, not many reviews.** The handoff history shows a pattern of "research after debug_02", "research after debug_03", "research before transition to 2step model", "research before 3step transition", "3step transition slice 4 completed." Each is a real milestone, but the handoff history is where a reviewer has to reconstruct the arc. A single rolling `MIGRATION_LOG.md` at the repo root would make the history one scroll instead of a git-log archaeology exercise.

---

*End of report.*
