# Deficiency Implementation Plan

Derived from: [FULL_REPO_REVIEW.md](C:/DATA/PROJECTS/JEFF/FULL_REPO_REVIEW.md)  
Source audit date: 2026-04-15  
Plan date: 2026-04-16

## Goal

Turn the deficiencies identified in the full repo review into a sequenced implementation plan that:

1. Stabilizes the current research vertical.
2. Cleans up infrastructure seams before wider adoption.
3. Removes avoidable contributor friction.
4. Prepares the repo for Wave 2 cognitive-stage adoption without broad rewrites.

## Planning Principles

- Follow the review's recommendation to avoid broad rewrites.
- Finish infrastructure cleanup before Proposal/Evaluation adoption.
- Prefer additive, reversible changes with tests.
- Treat spec-level ambiguity as a decision gate, not an excuse for ad hoc implementation.
- Keep research semantics in `jeff/cognitive/research/`; keep routing/runtime vocabulary in `jeff/infrastructure/`.

## Phase 0 - Baseline and Branch Hygiene

### Step 0.1 - Capture the current baseline

Actions:
- Run the full suite: `python -m pytest tests/unit tests/integration -q`
- Save the current failing list and confirm it is still the same 10 failures documented in the review.
- Record current artifact path behavior from `jeff.runtime.toml` + `jeff/cognitive/research/persistence.py`.

Files:
- [jeff.runtime.toml](C:/DATA/PROJECTS/JEFF/jeff.runtime.toml)
- [jeff/cognitive/research/persistence.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/research/persistence.py)

Exit criteria:
- Baseline failures are confirmed unchanged.
- No new undocumented failures exist.

### Step 0.2 - Freeze implementation targets for this slice

Actions:
- Treat the following as in-scope for the first slice:
  - `ContractCallRequest` expansion
  - `research_repair` naming cleanup
  - artifact-store path fix
  - rewrite the 10 outdated tests
  - refresh infrastructure handoff
- Treat the following as explicitly out-of-scope for the first slice:
  - global state persistence
  - live orchestrator daemon/runtime loop
  - new model providers
  - large CLI refactor

Exit criteria:
- A narrow first implementation slice is agreed and protected from scope creep.

## Phase 1 - Stabilize the Existing Research Vertical

### Step 1.1 - Fix the doubled artifact-store path

Actions:
- Change `ResearchArtifactStore` so it writes directly to the configured root instead of appending `research_artifacts` a second time.
- Preserve the configuration contract: `artifact_store_root` should mean the literal on-disk directory.
- Add a regression test that asserts the effective persistence path exactly matches config.

Primary files:
- [jeff/cognitive/research/persistence.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/research/persistence.py)
- Relevant persistence tests under [tests](C:/DATA/PROJECTS/JEFF/tests)

Notes:
- If local developer artifacts need migration, handle that as a one-time manual cleanup note instead of product logic.

Exit criteria:
- New artifacts land under `.jeff_runtime/research_artifacts/`.
- A test fails if the path becomes double-nested again.

### Step 1.2 - Rewrite the 10 failing tests for bounded Step 1 text

Actions:
- Replace old fake-adapter fixtures that return plain text or JSON blobs.
- Introduce a shared helper fixture that emits valid Step 1 bounded text with:
  - `SUMMARY:`
  - `FINDINGS:`
  - `INFERENCES:`
  - `UNCERTAINTIES:`
  - `RECOMMENDATION:`
- Ensure findings use paired `text` / `cites` lines and `S1..Sn` citation keys.

Primary files:
- [tests/unit/interface/test_research_commands.py](C:/DATA/PROJECTS/JEFF/tests/unit/interface/test_research_commands.py)
- [tests/integration/test_cli_research_runtime_config.py](C:/DATA/PROJECTS/JEFF/tests/integration/test_cli_research_runtime_config.py)

Implementation notes:
- Prefer a single helper fixture or factory used by both files.
- Keep the test intent the same; only update the fake synthesis payload contract.

Exit criteria:
- Full suite reaches the expected green state after this and Phase 2 changes.
- No test still assumes the pre-transition JSON-first contract.

## Phase 2 - Clean Up the Infrastructure Contract Surface

### Step 2.1 - Expand `ContractCallRequest`

Actions:
- Add the missing runtime-level fields required by current and future callers:
  - `response_mode`
  - `json_schema`
  - `reasoning_effort`
- Update `ContractRuntime.invoke()` to forward them into the `ModelRequest`.
- Keep `invoke_with_request()` for callers that need full manual control.

Primary files:
- [jeff/infrastructure/contract_runtime.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/contract_runtime.py)
- [jeff/infrastructure/runtime.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/runtime.py)
- Infrastructure tests under [tests/unit/infrastructure](C:/DATA/PROJECTS/JEFF/tests/unit/infrastructure)

Exit criteria:
- `invoke()` can express the Step 1 research call cleanly.
- The API remains backward-compatible for existing callers.

### Step 2.2 - Migrate research Step 1 onto the clean `invoke()` path

Actions:
- Replace the Step 1 `invoke_with_request()` usage in synthesis with `invoke(ContractCallRequest(...))`.
- Keep Step 3 on `invoke_with_request()` until formatter-bridge requirements are fully representable through the clean request surface.

Primary files:
- [jeff/cognitive/research/synthesis.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/research/synthesis.py)

Exit criteria:
- Step 1 no longer needs the escape-hatch API.
- Existing research behavior remains unchanged.

### Step 2.3 - Retire `research_repair` naming

Actions:
- Replace infrastructure-facing `research_repair` vocabulary with a neutral formatter-bridge name.
- Remove infrastructure special-casing that leaks research-domain semantics.
- Update runtime config override keys and formatter bridge constants accordingly.

Primary files:
- [jeff/infrastructure/purposes.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/purposes.py)
- [jeff/infrastructure/runtime.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/runtime.py)
- [jeff/cognitive/research/formatter.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/research/formatter.py)
- [jeff.runtime.toml](C:/DATA/PROJECTS/JEFF/jeff.runtime.toml)

Suggested target:
- Use neutral runtime vocabulary such as `formatter_bridge` or `research_formatter_bridge`.

Exit criteria:
- No infrastructure branch depends on `if purpose == "research_repair"`.
- Config, runtime, and formatter routing all use the new name consistently.

### Step 2.4 - Validate unknown `purpose_overrides`

Actions:
- Add startup validation so unknown keys in `purpose_overrides` fail loudly instead of being ignored.
- Surface a clear configuration error during infrastructure bootstrap.

Primary files:
- [jeff/infrastructure/config.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/config.py)
- [jeff/infrastructure/runtime.py](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/runtime.py)

Exit criteria:
- A typo in runtime config is caught during startup.

## Phase 3 - Documentation and Drift Repair

### Step 3.1 - Refresh the infrastructure handoff

Actions:
- Update the handoff to include:
  - `purposes.py`
  - `output_strategies.py`
  - `capability_profiles.py`
  - `contract_runtime.py`
  - `contract_runtime` exposure from services/runtime
- Mark old slice notes as history instead of current state.

Primary file:
- [jeff/infrastructure/HANDOFF.md](C:/DATA/PROJECTS/JEFF/jeff/infrastructure/HANDOFF.md)

Exit criteria:
- The handoff reflects the current code layout and exported surfaces.

### Step 3.2 - Add a lightweight anti-drift rule

Actions:
- Document a simple rule in the relevant handoff/process doc: new files under a module require corresponding handoff updates in the same change.
- If desired, enforce this later with a review checklist rather than immediate automation.

Exit criteria:
- The repo has an explicit process answer for the stale-doc issue found in the review.

## Phase 4 - Wave 2 ContractRuntime Adoption

This phase should begin only after Phases 1-3 are complete.

### Step 4.1 - Create a reusable adoption template

Actions:
- Use research adoption as the reference pattern:
  - clean runtime call construction
  - validation boundary
  - deterministic fallback path
  - tests first, then integration
- Document the minimum adoption checklist for another cognitive stage.

Exit criteria:
- Proposal and evaluation work from the same playbook instead of inventing new patterns.

### Step 4.2 - Adopt `ContractRuntime` in proposal

Actions:
- Add a model-backed proposal path behind the existing rule-based baseline.
- Keep the current deterministic/rule-based behavior as fallback until parity is proven.
- Add focused unit tests around request construction, validation, and fallback behavior.

Primary files:
- [jeff/cognitive/proposal.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/proposal.py)
- Supporting infrastructure/tests under [tests](C:/DATA/PROJECTS/JEFF/tests)

Exit criteria:
- Proposal can use model-backed runtime calls without weakening deterministic fallback behavior.

### Step 4.3 - Adopt `ContractRuntime` in evaluation

Actions:
- Repeat the same pattern used for proposal.
- Keep evaluation outputs validated and testable before any wider orchestration changes.

Primary files:
- [jeff/cognitive/evaluation.py](C:/DATA/PROJECTS/JEFF/jeff/cognitive/evaluation.py)

Exit criteria:
- Evaluation is contract-runtime capable and covered by unit tests.

### Step 4.4 - Fill the missing infrastructure pieces needed by Wave 2

Actions:
- Add `jeff/infrastructure/fallback_policies.py` if the second adopted stage needs shared fallback routing.
- Add `jeff/infrastructure/typed_calls/` only when at least one second-stage caller benefits from it.
- Do not add Instructor/BAML/Guardrails unless a concrete gap remains after the native contract surface is used.

Exit criteria:
- Missing infrastructure is introduced only in response to a real caller need.

## Phase 5 - Durable State and Memory

This is a larger design slice and should be treated as a separate milestone, not mixed into infrastructure cleanup.

### Step 5.1 - Decide the v1 durability model

Decision gate:
- Choose one explicit stance and document it before implementation:
  - v1 stays in-memory and replayable only
  - v1 gets file-backed snapshots and transition replay

Recommended direction:
- File-backed snapshots plus append-only transition log, because it preserves the transition-only truth model without forcing a database rewrite.

Exit criteria:
- The target durability model is written down before code changes start.

### Step 5.2 - Persist `GlobalState`

Actions:
- Add save/load support for `GlobalState`.
- Introduce snapshot serialization and startup reload.
- Add compatibility/versioning fields early to avoid brittle future migrations.

Primary areas:
- [jeff/core/state](C:/DATA/PROJECTS/JEFF/jeff/core)
- [bootstrap.py](C:/DATA/PROJECTS/JEFF/bootstrap.py)
- [jeff/interface/session.py](C:/DATA/PROJECTS/JEFF/jeff/interface/session.py)

Exit criteria:
- CLI restarts can reload prior truth state.

### Step 5.3 - Expand transition coverage

Actions:
- Add transition types for the truth mutations the repo actually needs next.
- Implement them incrementally, not all at once.
- Keep `apply_transition()` as the only truth mutation path.

Suggested order:
- work-unit lifecycle/status updates
- run lifecycle updates
- outcome attachment
- governance decision recording

Exit criteria:
- The main truth-changing flows no longer bypass the transition vocabulary by omission.

### Step 5.4 - Replace in-memory-only memory storage

Actions:
- Add durable backing for memory records.
- Keep the current distillation/handoff contract intact.
- Make memory persistence independent from research artifact persistence.

Primary areas:
- [jeff/memory/store.py](C:/DATA/PROJECTS/JEFF/jeff/memory/store.py)
- [jeff/memory/write_pipeline.py](C:/DATA/PROJECTS/JEFF/jeff/memory/write_pipeline.py)

Exit criteria:
- Memory survives process restart.

## Phase 6 - Orchestrator and Operator Surface

This is only worth doing after state durability and at least one more cognitive stage have matured.

### Step 6.1 - Wire a production handler set for orchestrated research/proposal flows

Actions:
- Build production-grade handler maps for at least one non-test orchestrator flow.
- Reuse existing validated stage handlers instead of duplicating logic.

Primary files:
- [jeff/orchestrator/flows.py](C:/DATA/PROJECTS/JEFF/jeff/orchestrator/flows.py)
- [jeff/orchestrator/runner.py](C:/DATA/PROJECTS/JEFF/jeff/orchestrator/runner.py)

Exit criteria:
- At least one orchestrator flow is runnable outside tests.

### Step 6.2 - Decide whether a live runtime loop is actually needed in v1

Decision gate:
- If command-driven orchestration is enough, do not add a daemon.
- If background execution is required, then design a minimal runtime loop around the existing orchestrator primitives.

Exit criteria:
- Runtime-loop work is justified by a concrete operator need, not architecture aesthetics.

### Step 6.3 - Expand CLI only where backbone concepts need exposure

Actions:
- Add new commands only if they exercise real backbone concepts that already exist in code.
- Keep `commands.py` intact until a new command family makes extraction worthwhile.

Exit criteria:
- CLI growth stays proportional to actual capabilities.

## Phase 7 - Lower-Priority Cleanup

### Step 7.1 - Add structured research debug checkpoints

Actions:
- Replace free-form string checkpoint names with a small enum or constant set.
- Update tests to assert against stable checkpoint identifiers.

Primary files:
- Research debug-emission sites under [jeff/cognitive/research](C:/DATA/PROJECTS/JEFF/jeff/cognitive/research)

### Step 7.2 - Review legacy compatibility shells

Actions:
- Inventory remaining callers of `ResearchResult` and `legacy.py`.
- Remove compatibility shims only when usage reaches zero or migration is trivial.

### Step 7.3 - Revisit `commands.py` split only when demand is real

Actions:
- Defer command extraction until at least one more command family lands.

## Recommended Execution Order

1. Baseline verification.
2. Artifact-store path fix.
3. Rewrite the 10 outdated tests.
4. Expand `ContractCallRequest`.
5. Move research Step 1 to `invoke()`.
6. Rename `research_repair` to neutral formatter-bridge vocabulary.
7. Validate `purpose_overrides` at startup.
8. Refresh `jeff/infrastructure/HANDOFF.md`.
9. Start Proposal adoption.
10. Start Evaluation adoption.
11. Make durability decisions before implementing state/memory persistence.
12. Wire production orchestrator flows only after the above is stable.

## Definition of Done for the First Slice

The first slice should be considered complete when all of the following are true:

- The full test suite passes.
- Research artifacts persist to the correct configured directory.
- `ContractCallRequest` supports the fields needed by clean runtime callers.
- Research Step 1 uses the clean `invoke()` path.
- Infrastructure no longer uses the `research_repair` special-case name.
- Runtime config rejects unknown purpose override keys.
- `jeff/infrastructure/HANDOFF.md` matches the codebase.

## Suggested Milestones

### Milestone A - Repo Stabilization

Includes:
- Phase 0
- Phase 1
- Phase 2
- Phase 3

Expected outcome:
- Green suite, cleaner infrastructure seam, less contributor confusion.

### Milestone B - Wave 2 Adoption

Includes:
- Phase 4

Expected outcome:
- Proposal and evaluation can use the same contract-runtime model as research.

### Milestone C - Durable System Backbone

Includes:
- Phase 5
- Phase 6

Expected outcome:
- Truth and memory survive restarts, and orchestration can move beyond test-only flows.
